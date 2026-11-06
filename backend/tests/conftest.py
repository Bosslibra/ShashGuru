import json
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.adapters.auth.dev import DevAuth
from app.bootstrap import build_state
from app.config import Settings
from app.db.session import Database
from app.main import create_app
from app.services.crypto import generate_key
from app.services.providers.base import Usage
from app.services.providers.openai_compat import OpenAICompatProvider
from app.services.providers.resolver import ProviderRegistry

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
        self.calls.append((name, "game", depth, lines))
        raise ValueError("Illegal move 'e2e5' at ply 1")

    def pool_stats(self):
        return {"NNUE": {"initialized": True, "pool_size": 1, "available": 1, "busy": 0}}


class FakeCache:
    connected = False
    client = None

    def stats(self):
        return {"connected": False}

    def clear(self):
        pass


class FakeLLM:
    """Looks like an AsyncOpenAI client."""

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


class FakeProvider:
    """A provider that streams canned tokens and reports usage."""
    name = "fake"

    def __init__(self, tokens=("Hel", "lo"), usage=Usage(1000, 200), fail_at=None, cap=1024, bad_key=False):
        self.tokens, self.usage, self.fail_at, self.cap, self.bad_key = tokens, usage, fail_at, cap, bad_key
        self.calls: list[tuple[list, str, int]] = []
        self.closed = False

    def output_cap(self, max_tokens):
        return self.cap

    async def stream(self, messages, model, max_tokens):
        self.calls.append((messages, model, max_tokens))
        for i, t in enumerate(self.tokens):
            if self.fail_at == i:
                raise RuntimeError("provider exploded with secret sk-platform-1234")
            yield t
        if self.usage:
            yield self.usage

    async def ping(self):
        if self.bad_key:
            raise RuntimeError("401")

    async def close(self):
        self.closed = True


def events(response_or_text):
    text = response_or_text if isinstance(response_or_text, str) else response_or_text.text
    return [json.loads(l) for l in text.splitlines() if l]


def selfhosted_settings(**kw) -> Settings:
    return Settings(_env_file=None, deployment_mode="selfhosted", **kw)


@pytest.fixture
def client():
    """Self-hosted deployment: no accounts, the historical behaviour."""
    app = create_app()
    settings = selfhosted_settings()
    registry = ProviderRegistry(settings, None, None, None, platform={},
                                selfhosted=OpenAICompatProvider(FakeLLM(), "selfhosted", include_usage=False))
    build_state(app, settings, FakeCache(), FakeEngines(), registry=registry)
    app.state.llm_fake = registry.selfhosted._client
    return TestClient(app)  # no `with`: the real lifespan (engines, redis) is not started


class Saas:
    """A SaaS app over a file-backed SQLite database, driven through httpx on one event loop."""

    def __init__(self, app, db, provider, engines):
        self.app, self.db, self.provider, self.engines = app, db, provider, engines


@pytest_asyncio.fixture
async def saas(tmp_path, monkeypatch):
    import httpx

    settings = Settings(_env_file=None, deployment_mode="saas", auth_provider="dev", allow_dev_auth=True,
                        auth_admin_subjects=["boss"], key_encryption_keys=f"v1:{generate_key()}",
                        anthropic_api_key="platform-key", database_url=f"sqlite+aiosqlite:///{tmp_path / 't.db'}",
                        rate_limit_enabled=False, public_url="https://app.test")
    db = Database(settings.database_url)
    await db.create_all()
    provider = FakeProvider()
    engines = FakeEngines()
    app = create_app()
    registry = ProviderRegistry(settings, None, None, db, platform={"anthropic": provider})
    build_state(app, settings, FakeCache(), engines, db=db, registry=registry, auth=DevAuth(["boss"]))
    registry.catalog, registry.vault = app.state.catalog, app.state.vault

    async def fake_build(provider_name, api_key, base_url):
        fake = FakeProvider(bad_key=api_key.startswith("bad"))
        app.state.byok_providers.append(fake)
        return fake

    app.state.byok_providers = []
    monkeypatch.setattr("app.services.providers.resolver.build_user_provider", fake_build)
    monkeypatch.setattr("app.services.keys.build_user_provider", fake_build)
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    s = Saas(app, db, provider, engines)
    s.http = http
    yield s
    await http.aclose()
    await db.close()


def bearer(subject="alice", email="alice@example.com") -> dict:
    return {"Authorization": f"Bearer dev:{subject}:{email}"}
