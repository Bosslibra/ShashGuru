# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
from fastapi import Request

from app.services.engine_cache import EngineCache
from app.services.engine_pool import EngineService


def get_engines(request: Request) -> EngineService:
    return request.app.state.engines


def get_cache(request: Request) -> EngineCache:
    return request.app.state.cache
