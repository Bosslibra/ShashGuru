# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
from typing import Literal, Optional

import chess
from pydantic import BaseModel, Field, field_validator, model_validator

EngineName = Literal["NNUE", "HUMAN"]
Style = str  # validated against services.llm.SYSTEM_MESSAGES at the router level


def _validate_fen(value: str) -> str:
    value = value.strip()
    try:
        chess.Board(value)
    except ValueError as e:
        raise ValueError(f"Invalid FEN: {e}") from e
    return value


# ---------------------------------------------------------------- engine ----

class Score(BaseModel):
    """Score from the point of view of the side to move."""
    cp: Optional[int] = None
    mate: Optional[int] = None


class Wdl(BaseModel):
    w: int
    d: int
    l: int


class EngineLine(BaseModel):
    rank: int
    move: str
    pv: list[str]
    score: Score
    wdl: Optional[Wdl] = None
    winprob: Optional[float] = Field(None, description="Win probability 0-100 for the side to move")
    depth: int


PositionStatus = Literal["ok", "checkmate", "stalemate", "draw"]


class EvaluationRequest(BaseModel):
    fen: str
    depth: int = Field(15, ge=1, le=40)
    lines: int = Field(3, ge=1, le=5)
    engine: EngineName = "NNUE"

    _fen = field_validator("fen")(_validate_fen)


class Evaluation(BaseModel):
    fen: str
    side_to_move: Literal["white", "black"] = Field(alias="sideToMove")
    status: PositionStatus
    depth: int
    lines: list[EngineLine]

    model_config = {"populate_by_name": True}


class GameAnalysisRequest(BaseModel):
    pgn: Optional[str] = None
    moves: Optional[list[str]] = Field(None, description="UCI moves, e.g. ['e2e4', 'e7e5']")
    depth: int = Field(15, ge=1, le=30)
    lines: int = Field(3, ge=1, le=10)
    engine: EngineName = "NNUE"

    @model_validator(mode="after")
    def _exactly_one_source(self):
        if bool(self.pgn) == bool(self.moves):
            raise ValueError("Provide exactly one of 'pgn' or 'moves'")
        return self


class PositionAnalysis(BaseModel):
    move_number: int = Field(alias="moveNumber")
    fen: str
    move_played: Optional[str] = Field(None, alias="movePlayed")
    analysis: Evaluation

    model_config = {"populate_by_name": True}


class GameAnalysis(BaseModel):
    engine: EngineName
    depth: int
    lines: int
    positions: list[PositionAnalysis]


# ------------------------------------------------------------------- llm ----

class StyleInfo(BaseModel):
    value: str
    label: str


Source = Literal["managed", "byok"]
MAX_CHAT_MESSAGES = 40  # the history is trimmed again to the most recent turns before it reaches the LLM
MAX_USER_CHARS = 2000  # what a person types
MAX_ASSISTANT_CHARS = 8000  # earlier answers sent back as history (completions are capped at ~1k tokens)


class LLMTarget(BaseModel):
    """Which LLM answers: the platform's models (billed in credits) or one of the user's own keys."""
    source: Source = "managed"
    key_id: Optional[int] = None
    model: Optional[str] = Field(None, max_length=128)


class AnalysisRequest(LLMTarget):
    fen: str
    depth: int = Field(20, ge=1, le=40)
    style: str = "default"

    _fen = field_validator("fen")(_validate_fen)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @model_validator(mode="after")
    def _limit_length(self):
        limit = MAX_USER_CHARS if self.role == "user" else MAX_ASSISTANT_CHARS
        if len(self.content) > limit:
            raise ValueError(f"A {self.role} message can have at most {limit} characters")
        return self


class ChatRequest(LLMTarget):
    analysis_id: str = Field(min_length=8, max_length=64)
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_CHAT_MESSAGES)
    style: str = "default"

    @model_validator(mode="after")
    def _last_is_user(self):
        if self.messages[-1].role != "user":
            raise ValueError("The last message must have role 'user'")
        return self


# ------------------------------------------------------------------ keys ----

class KeyCreate(BaseModel):
    provider: Literal["openai", "anthropic", "openrouter", "custom"]
    api_key: str = Field(min_length=8, max_length=512)
    label: str = Field("", max_length=80)
    base_url: Optional[str] = Field(None, max_length=512)


class CheckoutRequestBody(BaseModel):
    offer_id: str = Field(max_length=64)


# ----------------------------------------------------------------- admin ----

class CacheStats(BaseModel):
    connected: bool
    used_memory: Optional[str] = None
    keyspace_hits: Optional[int] = None
    keyspace_misses: Optional[int] = None
    total_keys: Optional[int] = None
