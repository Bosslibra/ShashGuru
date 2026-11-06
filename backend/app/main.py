# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, engine
from app.api.v1 import llm as llm_api
from app.config import get_settings
from app.metrics import MetricsMiddleware, metrics_response
from app.services import llm
from app.services.engine_cache import create_cache
from app.services.engine_pool import EngineService

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    cache = create_cache(settings)
    engines = EngineService(settings, cache)
    await run_in_threadpool(engines.start)
    app.state.settings = settings
    app.state.cache = cache
    app.state.engines = engines
    app.state.llm = llm.create_client(settings)
    yield
    await app.state.llm.close()
    await run_in_threadpool(engines.shutdown)


def create_app() -> FastAPI:
    app = FastAPI(title="ShashGuru API", version="1.0.0", lifespan=lifespan)
    settings = get_settings()
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["*"], allow_headers=["*"])

    app.include_router(engine.router, prefix="/api/v1")
    app.include_router(llm_api.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    @app.get("/health", tags=["ops"])
    async def health():
        return {
            "status": "healthy",
            "redis": app.state.cache.connected,
            "engines": app.state.engines.pool_stats(),
        }

    @app.get("/metrics", tags=["ops"], include_in_schema=False)
    async def metrics():
        return metrics_response()

    return app


app = create_app()
