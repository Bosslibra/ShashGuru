# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import json
import logging
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.api.deps import get_engines, rate_limited
from app.schemas import AnalysisRequest, ChatRequest, LLMTarget, StyleInfo
from app.services import llm
from app.services.accounts import Principal
from app.services.engine_pool import EngineService, EngineUnavailable
from app.services.gateway import Call, PaymentRequired
from app.services.providers.resolver import ResolveError, Resolved

log = logging.getLogger(__name__)
router = APIRouter(tags=["llm"])

NDJSON_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}


def _event(**payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _check_style(style: str) -> None:
    if not llm.is_known_style(style):
        raise HTTPException(422, f"Unknown style '{style}'")


async def _resolve(request: Request, principal: Principal, target: LLMTarget) -> Resolved:
    try:
        return await request.app.state.registry.resolve(principal, target.source, target.key_id, target.model)
    except ResolveError as e:
        raise HTTPException(e.status, e.message, headers={"WWW-Authenticate": "Bearer"} if e.status == 401 else None) from e


async def _prepare(request: Request, principal: Principal, resolved: Resolved, prompt: str, history, style: str,
                   analysis_id: Optional[str]) -> Call:
    try:
        return await request.app.state.gateway.prepare(principal, resolved, prompt, history, style, analysis_id)
    except PaymentRequired as e:
        if resolved.owned:
            await resolved.provider.close()
        raise HTTPException(402, str(e)) from e
    except Exception:
        if resolved.owned:
            await resolved.provider.close()
        raise


async def _stream(request: Request, call: Call, context: Optional[dict] = None) -> AsyncIterator[str]:
    """NDJSON events: [context] -> token* -> usage? -> done | error."""
    if context is not None:
        yield _event(type="context", **context)
    async for event in request.app.state.gateway.events(call):
        yield _event(**event)


@router.get("/styles", response_model=list[StyleInfo])
async def list_styles():
    return llm.get_analysis_styles()


@router.post("/analyses", response_class=StreamingResponse)
async def create_analysis(body: AnalysisRequest, request: Request, engines: EngineService = Depends(get_engines),
                          principal: Principal = Depends(rate_limited("llm"))):
    """Engine analysis of a position explained by the LLM (application/x-ndjson stream)."""
    _check_style(body.style)
    resolved = await _resolve(request, principal, body)  # fail fast (401/422/...) before spending engine time
    lines = 1 if body.style == "default" else 3
    try:
        result = await run_in_threadpool(engines.analyse, "NNUE", body.fen, body.depth, lines)
    except EngineUnavailable as e:
        if resolved.owned:
            await resolved.provider.close()
        raise HTTPException(503, str(e)) from e
    if result["status"] != "ok" or not result["lines"]:
        if resolved.owned:
            await resolved.provider.close()
        raise HTTPException(422, f"Nothing to analyse: position is {result['status']}")

    prompt = llm.create_analysis_prompt(body.fen, result["lines"], body.style)
    stored = await request.app.state.analyses.create(principal.user_id, body.style, prompt)
    call = await _prepare(request, principal, resolved, prompt, None, body.style, stored.id)
    return StreamingResponse(
        _stream(request, call, context={"analysis_id": stored.id, "prompt": prompt}),
        media_type="application/x-ndjson", headers=NDJSON_HEADERS,
    )


@router.post("/chat", response_class=StreamingResponse)
async def chat(body: ChatRequest, request: Request, principal: Principal = Depends(rate_limited("llm"))):
    """Follow-up question about an analysis (application/x-ndjson stream).

    ``messages`` holds only the visible turns; the analysis prompt is re-attached from the server.
    """
    _check_style(body.style)
    stored = await request.app.state.analyses.get(body.analysis_id, principal.user_id)
    if stored is None:
        raise HTTPException(404, "Analysis not found or expired: run the analysis again")
    resolved = await _resolve(request, principal, body)
    history = [{"role": "user", "content": stored.prompt}, *(m.model_dump() for m in body.messages[:-1])]
    call = await _prepare(request, principal, resolved, body.messages[-1].content, history, body.style, stored.id)
    return StreamingResponse(
        _stream(request, call), media_type="application/x-ndjson", headers=NDJSON_HEADERS,
    )
