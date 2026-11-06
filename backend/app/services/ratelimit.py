# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Fixed-window rate limiter: Redis when available, in-process otherwise."""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import redis
from fastapi.concurrency import run_in_threadpool

log = logging.getLogger(__name__)


@dataclass
class LimitResult:
    allowed: bool
    retry_after: int = 0


class RateLimiter:
    def __init__(self, client: Optional[redis.Redis] = None, clock=time.time):
        self._client = client
        self._clock = clock
        self._local: dict[str, tuple[int, int]] = {}  # key -> (window, count)

    def _hit_local(self, key: str, limit: int, window: int) -> LimitResult:
        now = int(self._clock())
        bucket = now // window
        current, count = self._local.get(key, (bucket, 0))
        if current != bucket:
            count = 0
        count += 1
        self._local[key] = (bucket, count)
        if len(self._local) > 50_000:  # bound memory under a key-spraying attack
            self._local = {k: v for k, v in self._local.items() if v[0] == bucket}
        return LimitResult(count <= limit, (bucket + 1) * window - now)

    def _hit_redis(self, key: str, limit: int, window: int) -> LimitResult:
        now = int(self._clock())
        bucket = now // window
        rkey = f"rl:{key}:{bucket}"
        pipe = self._client.pipeline()
        pipe.incr(rkey)
        pipe.expire(rkey, window + 1)
        count = int(pipe.execute()[0])
        return LimitResult(count <= limit, (bucket + 1) * window - now)

    def _hit(self, key: str, limit: int, window: int) -> LimitResult:
        if self._client is not None:
            try:
                return self._hit_redis(key, limit, window)
            except redis.RedisError as e:
                log.warning("Rate limiter falling back to memory: %s", e)
        return self._hit_local(key, limit, window)

    async def hit(self, key: str, limit: int, window: int = 60) -> LimitResult:
        return await run_in_threadpool(self._hit, key, limit, window)
