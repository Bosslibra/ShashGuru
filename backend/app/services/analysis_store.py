# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Server-side storage of the context of an LLM analysis.

The client never sends the (hidden) analysis prompt back: it sends an ``analysis_id`` and the
server re-attaches the stored prompt. This stops /chat from being used as a generic LLM proxy.
"""
import json
import logging
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Optional

import redis
from fastapi.concurrency import run_in_threadpool

log = logging.getLogger(__name__)


@dataclass
class StoredAnalysis:
    id: str
    owner: Optional[int]  # user id, None for the self-hosted / anonymous principal
    style: str
    prompt: str
    created_at: float


class AnalysisStore:
    def __init__(self, client: Optional[redis.Redis], ttl: int, clock=time.time):
        self._client = client
        self._ttl = ttl
        self._clock = clock
        self._local: dict[str, StoredAnalysis] = {}

    @staticmethod
    def _key(analysis_id: str) -> str:
        return f"analysis:{analysis_id}"

    def _put(self, item: StoredAnalysis) -> None:
        if self._client is not None:
            try:
                self._client.setex(self._key(item.id), self._ttl, json.dumps(asdict(item)))
                return
            except redis.RedisError as e:
                log.warning("Analysis store falling back to memory: %s", e)
        now = self._clock()
        if len(self._local) > 5000:
            self._local = {k: v for k, v in self._local.items() if now - v.created_at < self._ttl}
        self._local[item.id] = item

    def _get(self, analysis_id: str) -> Optional[StoredAnalysis]:
        if self._client is not None:
            try:
                raw = self._client.get(self._key(analysis_id))
                if raw:
                    return StoredAnalysis(**json.loads(raw))
            except (redis.RedisError, ValueError, TypeError) as e:
                log.warning("Analysis store read error: %s", e)
        item = self._local.get(analysis_id)
        if item and self._clock() - item.created_at < self._ttl:
            return item
        return None

    async def create(self, owner: Optional[int], style: str, prompt: str) -> StoredAnalysis:
        item = StoredAnalysis(secrets.token_hex(12), owner, style, prompt, self._clock())
        await run_in_threadpool(self._put, item)
        return item

    async def get(self, analysis_id: str, owner: Optional[int]) -> Optional[StoredAnalysis]:
        """None if unknown, expired, or owned by somebody else."""
        item = await run_in_threadpool(self._get, analysis_id)
        if item is None or item.owner != owner:
            return None
        return item
