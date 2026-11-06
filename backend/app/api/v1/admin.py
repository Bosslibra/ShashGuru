# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import redis
from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_cache, get_engines
from app.schemas import CacheStats
from app.services.engine_cache import EngineCache
from app.services.engine_pool import EngineService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/cache", response_model=CacheStats)
async def cache_stats(cache: EngineCache = Depends(get_cache)):
    stats = cache.stats()
    if not stats["connected"]:
        raise HTTPException(503, "Redis not connected")
    return stats


@router.delete("/cache", status_code=204)
async def clear_cache(cache: EngineCache = Depends(get_cache)):
    try:
        cache.clear()
    except redis.RedisError as e:
        raise HTTPException(503, str(e)) from e
    return Response(status_code=204)


@router.get("/engines")
async def engine_stats(engines: EngineService = Depends(get_engines)):
    return engines.pool_stats()
