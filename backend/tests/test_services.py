# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import json
import os
from pathlib import Path

import chess
import pytest

from app.config import Settings
from app.services import llm
from app.services.engine_cache import EngineCache
from app.services.engine_pool import EngineService
from app.services.fen_explainer import fen_explainer

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_fen_explainer_no_castling_and_plural():
    text, side = fen_explainer("4k3/8/8/8/8/8/8/4K3 b - - 0 1")
    assert side == "Black"
    assert "Neither side has castling rights." in text
    assert "0 moves without captures" in text
    text, _ = fen_explainer("4k3/8/8/8/8/8/8/4K3 w - - 1 1")
    assert "1 move without captures" in text


@pytest.mark.parametrize("wp,expected", [
    (0, "decisive disadvantage"), (5.4, "decisive disadvantage"), (5.6, "decisive disadvantage"),
    (50, "equal"), (62.5, "initiative"), (100, "decisive advantage"),
])
def test_map_win_prob_has_no_gaps_for_floats(wp, expected):
    assert expected in llm.map_win_prob(wp, "White")


def test_map_win_prob_unknown():
    assert "chaos" in llm.map_win_prob(None, "White")


def test_position_context_king_on_a1_is_not_ignored():
    board = chess.Board("4k3/8/8/8/8/8/8/K7 w - - 0 1")
    assert "White king appears castled/safe" in llm.analyze_position_context(board)


def test_create_prompt_uses_san_and_continuation():
    lines = [{"pv": ["e2e4", "e7e5", "g1f3"], "winprob": 55.0}]
    prompt = llm.create_analysis_prompt(START, lines, "default")
    assert "play e4" in prompt and "e5 Nf3" in prompt


def test_build_messages_keeps_context_message():
    history = [{"role": "user", "content": f"m{i}"} for i in range(30)]
    msgs = llm.build_messages("q", history, "default")
    assert msgs[0]["role"] == "system" and msgs[1]["content"] == "m0"
    assert len(msgs) == 1 + llm.MAX_HISTORY + 1 and msgs[-1]["content"] == "q"


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, k):
        return self.data.get(k)

    def set(self, k, v):
        self.data[k] = v


def make_cache():
    cache = EngineCache.__new__(EngineCache)
    cache.client = FakeRedis()
    return cache


def test_cache_key_separates_engines_and_uses_reached_depth():
    cache = make_cache()
    cache.put("NNUE", START, 12, 3, {"lines": ["nnue"]})
    assert cache.get("HUMAN", START, 10, 3) is None
    assert cache.get("NNUE", START, 10, 3) == {"lines": ["nnue"]}
    assert cache.get("NNUE", START, 20, 3) is None  # requested deeper than stored
    assert cache.get("NNUE", START, 10, 1) is None  # different multipv


ENGINE = Settings().engine_path("shashchess")


@pytest.mark.skipif(not Path(ENGINE).exists() or os.name != "nt" and not os.access(ENGINE, os.X_OK),
                    reason="engine binary not available")
def test_real_engine_analysis_and_terminal_positions():
    settings = Settings(engine_pool_size=1, engine_threads=1, redis_host="localhost", redis_port=1)
    service = EngineService(settings, make_cache())
    try:
        res = service.analyse("NNUE", START, 8, 3)
        assert res["status"] == "ok" and len(res["lines"]) == 3
        assert res["lines"][0]["pv"][0] == res["lines"][0]["move"]
        assert res["lines"][0]["winprob"] is not None

        mate = service.analyse("NNUE", "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3", 8, 3)
        assert mate["status"] == "checkmate" and mate["lines"] == []

        # fewer legal moves than requested lines must not produce None entries
        few = service.analyse("NNUE", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 6, 5)
        assert few["status"] in ("stalemate", "ok")

        # healthy engines are reused, not replaced
        pool = service._pool("NNUE")
        with pool.acquire() as first:
            pass
        with pool.acquire() as second:
            assert second is first

        game = service.analyse_game("NNUE", ["e2e4", "e7e5"], 6, 1)
        assert [p["move_number"] for p in game] == [0, 1, 2]
        with pytest.raises(ValueError):
            service.analyse_game("NNUE", ["e2e5"], 6, 1)
    finally:
        service.shutdown()
