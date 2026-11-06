# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import json
import logging
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.api.deps import get_engines
from app.schemas import AnalysisRequest, ChatRequest, StyleInfo
from app.services import llm
from app.services.engine_pool import EngineService, EngineUnavailable

log = logging.getLogger(__name__)
router = APIRouter(tags=["llm"])

NDJSON_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}


def _event(**payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _check_style(style: str) -> None:
    if not llm.is_known_style(style):
        raise HTTPException(422, f"Unknown style '{style}'")


async def _token_stream(request: Request, prompt: str, history, style: str,
                        context: Optional[str] = None) -> AsyncIterator[str]:
    """NDJSON events: [context] -> token* -> done | error."""
    if context is not None:
        yield _event(type="context", prompt=context)
    try:
        async for text in llm.stream_completion(
            request.app.state.llm, request.app.state.settings.llm_model, prompt, history, style
        ):
            yield _event(type="token", text=text)
        yield _event(type="done")
    except Exception as e:
        log.exception("LLM streaming failed")
        yield _event(type="error", message=f"LLM request failed: {e}")


@router.get("/styles", response_model=list[StyleInfo])
async def list_styles():
    return llm.get_analysis_styles()


@router.post("/analyses", response_class=StreamingResponse)
async def create_analysis(body: AnalysisRequest, request: Request, engines: EngineService = Depends(get_engines)):
    """Engine analysis of a position explained by the LLM (application/x-ndjson stream)."""
    _check_style(body.style)
    lines = 1 if body.style == "default" else 3
    try:
        result = await run_in_threadpool(engines.analyse, "NNUE", body.fen, body.depth, lines)
    except EngineUnavailable as e:
        raise HTTPException(503, str(e)) from e
    if result["status"] != "ok" or not result["lines"]:
        raise HTTPException(422, f"Nothing to analyse: position is {result['status']}")

    prompt = llm.create_analysis_prompt(body.fen, result["lines"], body.style)
    return StreamingResponse(
        _token_stream(request, prompt, None, body.style, context=prompt),
        media_type="application/x-ndjson", headers=NDJSON_HEADERS,
    )


@router.post("/chat", response_class=StreamingResponse)
async def chat(body: ChatRequest, request: Request):
    """Follow-up question about an analysis (application/x-ndjson stream)."""
    _check_style(body.style)
    history = [m.model_dump() for m in body.messages[:-1]]
    return StreamingResponse(
        _token_stream(request, body.messages[-1].content, history, body.style),
        media_type="application/x-ndjson", headers=NDJSON_HEADERS,
    )
