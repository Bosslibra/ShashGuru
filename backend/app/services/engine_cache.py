# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import json
import logging
from typing import Any, Optional

import redis

from app.config import Settings

log = logging.getLogger(__name__)


class EngineCache:
    """
    Redis cache of engine analyses.
    Key: ``{engine}:{fen}:{lines}``; value: ``{depth: result}``.
    A cached analysis is reused if its depth is >= the requested one.
    """

    def __init__(self, host: str, port: int, db: int = 0):
        try:
            self.client: Optional[redis.Redis] = redis.Redis(
                host=host, port=port, db=db, decode_responses=True,
                socket_connect_timeout=5, socket_timeout=5,
            )
            self.client.ping()
            log.info("Connected to Redis at %s:%s", host, port)
        except Exception as e:  # redis is optional: run uncached
            log.warning("Redis unavailable, caching disabled: %s", e)
            self.client = None

    @property
    def connected(self) -> bool:
        if not self.client:
            return False
        try:
            return bool(self.client.ping())
        except redis.RedisError:
            return False

    @staticmethod
    def _key(engine: str, fen: str, lines: int) -> str:
        return f"{engine}:{fen}:{lines}"

    def get(self, engine: str, fen: str, depth: int, lines: int) -> Optional[dict[str, Any]]:
        if not self.client:
            return None
        try:
            raw = self.client.get(self._key(engine, fen, lines))
            if not raw:
                return None
            by_depth = json.loads(raw)
            suitable = [int(d) for d in by_depth if int(d) >= depth]
            if not suitable:
                return None
            return by_depth[str(min(suitable))]
        except (json.JSONDecodeError, redis.RedisError, ValueError) as e:
            log.warning("Cache read error: %s", e)
            return None

    def put(self, engine: str, fen: str, depth: int, lines: int, result: dict[str, Any]) -> None:
        """`depth` must be the depth actually reached, not the requested one."""
        if not self.client:
            return
        try:
            key = self._key(engine, fen, lines)
            raw = self.client.get(key)
            by_depth = json.loads(raw) if raw else {}
            by_depth[str(depth)] = result
            self.client.set(key, json.dumps(by_depth))
        except (json.JSONDecodeError, redis.RedisError) as e:
            log.warning("Cache write error: %s", e)

    def clear(self) -> None:
        if not self.client:
            raise redis.ConnectionError("Redis not connected")
        self.client.flushdb()

    def stats(self) -> dict[str, Any]:
        if not self.client:
            return {"connected": False}
        try:
            info = self.client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_keys": self.client.dbsize(),
            }
        except redis.RedisError:
            return {"connected": False}


def create_cache(settings: Settings) -> EngineCache:
    return EngineCache(settings.redis_host, settings.redis_port)
