# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.api.deps import get_engines, rate_limited
from app.services.accounts import Principal
from app.schemas import Evaluation, EvaluationRequest, GameAnalysis, GameAnalysisRequest
from app.services.engine_pool import EngineService, EngineUnavailable, to_evaluation

router = APIRouter(tags=["engine"])


def _cap_depth(request: Request, principal: Principal, depth: int) -> int:
    """Anonymous visitors get a lower maximum depth (cached results make this cheap for everyone)."""
    settings = request.app.state.settings
    if principal.is_anonymous and settings.is_saas:
        return min(depth, settings.anon_max_depth)
    return depth


@router.post("/evaluations", response_model=Evaluation, response_model_by_alias=True)
async def create_evaluation(body: EvaluationRequest, request: Request, engines: EngineService = Depends(get_engines),
                            principal: Principal = Depends(rate_limited("engine"))):
    """Evaluate a position. Scores are from the point of view of the side to move."""
    body.depth = _cap_depth(request, principal, body.depth)
    try:
        result = await run_in_threadpool(engines.analyse, body.engine, body.fen, body.depth, body.lines)
    except EngineUnavailable as e:
        raise HTTPException(503, str(e)) from e
    return to_evaluation(body.fen, result)


@router.post("/games/analysis", response_model=GameAnalysis, response_model_by_alias=True)
async def analyse_game(body: GameAnalysisRequest, request: Request, engines: EngineService = Depends(get_engines),
                       principal: Principal = Depends(rate_limited("game"))):
    """Analyse every position of a game given as PGN or as a list of UCI moves."""
    body.depth = _cap_depth(request, principal, body.depth)
    source = body.pgn if body.pgn else body.moves
    try:
        positions = await run_in_threadpool(engines.analyse_game, body.engine, source, body.depth, body.lines)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except EngineUnavailable as e:
        raise HTTPException(503, str(e)) from e
    return {"engine": body.engine, "depth": body.depth, "lines": body.lines, "positions": positions}
