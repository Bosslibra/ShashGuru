# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MATE = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"


def line(move="e2e4", pv=None, cp=30):
    return {"rank": 1, "move": move, "pv": pv or [move, "e7e5", "g1f3"], "score": {"cp": cp, "mate": None},
            "wdl": {"w": 400, "d": 200, "l": 400}, "winprob": 50.0, "depth": 12}


class FakeEngines:
    def __init__(self):
        self.calls = []

    def analyse(self, name, fen, depth, lines):
        self.calls.append((name, fen, depth, lines))
        if fen == MATE:
            return {"status": "checkmate", "depth": 0, "lines": [], "ponder": None}
        return {"status": "ok", "depth": depth, "lines": [line()], "ponder": "e7e5"}

    def analyse_game(self, name, source, depth, lines):
        raise ValueError("Illegal move 'e2e5' at ply 1")

    def pool_stats(self):
        return {"NNUE": {"initialized": True, "pool_size": 1, "available": 1, "busy": 0}}


class FakeCache:
    connected = False

    def stats(self):
        return {"connected": False}

    def clear(self):
        pass


class FakeLLM:
    def __init__(self, tokens=("Hel", "lo")):
        self.tokens = tokens
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.requests = []

    async def _create(self, **kwargs):
        self.requests.append(kwargs)

        async def gen():
            for t in self.tokens:
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=t))])
            # final chunk carries both text and finish_reason: must not be lost
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="!"), finish_reason="stop")])

        return gen()


@pytest.fixture
def client():
    app = create_app()
    app.state.settings = SimpleNamespace(llm_model="test-model")
    app.state.engines = FakeEngines()
    app.state.cache = FakeCache()
    app.state.llm = FakeLLM()
    return TestClient(app)  # no `with`: the real lifespan (engines, redis) is not started


def events(response):
    return [json.loads(l) for l in response.text.splitlines() if l]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "healthy"


def test_evaluation_ok(client):
    r = client.post("/api/v1/evaluations", json={"fen": START, "depth": 12, "lines": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["sideToMove"] == "white" and body["status"] == "ok"
    assert body["lines"][0]["move"] == "e2e4"
    assert client.app.state.engines.calls[0][0] == "NNUE"


@pytest.mark.parametrize("payload", [
    {"fen": "not a fen"},
    {"fen": START, "depth": 0},
    {"fen": START, "depth": 99},
    {"fen": START, "lines": 9},
    {"fen": START, "engine": "STOCKFISH"},
])
def test_evaluation_validation(client, payload):
    assert client.post("/api/v1/evaluations", json=payload).status_code == 422


def test_evaluation_checkmate_has_no_lines(client):
    body = client.post("/api/v1/evaluations", json={"fen": MATE}).json()
    assert body["status"] == "checkmate" and body["lines"] == []


def test_game_analysis_requires_exactly_one_source(client):
    assert client.post("/api/v1/games/analysis", json={}).status_code == 422
    assert client.post("/api/v1/games/analysis", json={"pgn": "1. e4", "moves": ["e2e4"]}).status_code == 422


def test_game_analysis_illegal_move_is_422(client):
    r = client.post("/api/v1/games/analysis", json={"moves": ["e2e5"]})
    assert r.status_code == 422 and "Illegal" in r.json()["detail"]


def test_styles(client):
    values = {s["value"] for s in client.get("/api/v1/styles").json()}
    assert values == {"default", "grandmaster"}


def test_analysis_stream_events(client):
    r = client.post("/api/v1/analyses", json={"fen": START, "style": "default"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson")
    evs = events(r)
    assert evs[0]["type"] == "context" and "e4" in evs[0]["prompt"]
    assert "".join(e["text"] for e in evs if e["type"] == "token") == "Hello!"
    assert evs[-1] == {"type": "done"}
    assert client.app.state.engines.calls[0][3] == 1  # commentator asks for one line


def test_analysis_grandmaster_asks_three_lines(client):
    client.post("/api/v1/analyses", json={"fen": START, "style": "grandmaster"})
    assert client.app.state.engines.calls[0][3] == 3


def test_analysis_terminal_position_is_422(client):
    r = client.post("/api/v1/analyses", json={"fen": MATE})
    assert r.status_code == 422 and "checkmate" in r.json()["detail"]


def test_analysis_unknown_style(client):
    assert client.post("/api/v1/analyses", json={"fen": START, "style": "nope"}).status_code == 422


def test_chat_stream_and_history(client):
    msgs = [{"role": "user", "content": "context"}, {"role": "assistant", "content": "analysis"},
            {"role": "user", "content": "why?"}]
    r = client.post("/api/v1/chat", json={"messages": msgs})
    assert events(r)[-1] == {"type": "done"}
    sent = client.app.state.llm.requests[0]["messages"]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]
    assert sent[-1]["content"] == "why?"


def test_chat_rejects_bad_roles_and_trailing_assistant(client):
    assert client.post("/api/v1/chat", json={"messages": [{"role": "system", "content": "x"}]}).status_code == 422
    assert client.post("/api/v1/chat", json={"messages": [{"role": "assistant", "content": "x"}]}).status_code == 422


def test_admin_cache_unavailable(client):
    assert client.get("/api/v1/admin/cache").status_code == 503
    assert client.get("/api/v1/admin/engines").status_code == 200
