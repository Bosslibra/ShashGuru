# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""End-to-end behaviour of the SaaS deployment: auth, credits, BYOK, abuse protection."""
import pytest
from sqlalchemy import select

from app.db.models import ProviderKey, UsageEvent
from app.services.billing import credits
from app.services.providers.base import Usage
from tests.conftest import START, bearer, events

A = bearer("alice")
B = bearer("bob", "bob@example.com")
ANALYSE = {"fen": START, "style": "default"}


async def user_id(saas, headers=A) -> int:
    return (await saas.http.get("/api/v1/me", headers=headers)).json()["id"]


async def give(saas, uid: int, purchased=0, subscription=0):
    async def work(s):
        if purchased:
            await credits.add_purchased(s, uid, purchased, "test")
        if subscription:
            await credits.grant_subscription(s, uid, subscription, "test-sub")
    await credits.retrying(saas.db, work)


async def balance(saas, headers=A) -> dict:
    return (await saas.http.get("/api/v1/me", headers=headers)).json()["balance"]


# ---------------------------------------------------------------- auth -----

async def test_llm_requires_login(saas):
    r = await saas.http.post("/api/v1/analyses", json=ANALYSE)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


async def test_invalid_token_is_401_even_on_open_endpoints(saas):
    r = await saas.http.post("/api/v1/evaluations", json={"fen": START},
                             headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401


async def test_engine_is_open_to_anonymous_with_capped_depth(saas):
    r = await saas.http.post("/api/v1/evaluations", json={"fen": START, "depth": 40})
    assert r.status_code == 200
    assert saas.engines.calls[-1][2] == 20  # anon_max_depth
    await saas.http.post("/api/v1/evaluations", json={"fen": START, "depth": 40}, headers=A)
    assert saas.engines.calls[-1][2] == 40


async def test_me_creates_the_user_and_starts_empty(saas):
    r = await saas.http.get("/api/v1/me", headers=A)
    body = r.json()
    assert r.status_code == 200 and body["email"] == "alice@example.com"
    assert body["balance"] == {"subscription": 0, "purchased": 0, "total": 0}
    assert body["plan"] is None and body["is_admin"] is False
    assert (await saas.http.get("/api/v1/me")).status_code == 401


async def test_admin_endpoints_need_the_admin_role(saas):
    assert (await saas.http.get("/api/v1/admin/engines")).status_code == 401
    assert (await saas.http.get("/api/v1/admin/engines", headers=A)).status_code == 403
    assert (await saas.http.get("/api/v1/admin/engines", headers=bearer("boss"))).status_code == 200


# ------------------------------------------------------------- credits -----

async def test_managed_analysis_without_credits_is_402(saas):
    await user_id(saas)
    r = await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)
    assert r.status_code == 402
    assert saas.provider.calls == []  # the provider was never called


async def test_managed_analysis_charges_real_usage(saas):
    saas.provider.cap = 1_000_000  # a pessimistic hold (750 credits) ...
    saas.provider.usage = Usage(1_000_000, 100_000)  # ... while the real cost is 225 credits
    uid = await user_id(saas)
    await give(saas, uid, purchased=1000)

    r = await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)
    evs = events(r)
    assert [e["type"] for e in evs] == ["context", "token", "token", "usage", "done"]
    usage = evs[3]
    assert usage["credits"] == 225 and usage["input_tokens"] == 1_000_000
    assert usage["balance"] == {"subscription": 0, "purchased": 775, "total": 775}
    assert await balance(saas) == usage["balance"]

    history = (await saas.http.get("/api/v1/me/usage", headers=A)).json()
    assert history["total"] == 1 and history["items"][0]["credits_charged"] == 225
    assert history["items"][0]["source"] == "managed" and history["items"][0]["status"] == "ok"
    assert (await saas.http.get("/api/v1/me", headers=A)).json()["usage_month"]["credits"] == 225


async def test_subscription_credits_are_spent_before_purchased(saas):
    saas.provider.cap = 1_000_000
    saas.provider.usage = Usage(1_000_000, 100_000)  # 225 credits
    uid = await user_id(saas)
    await give(saas, uid, purchased=900, subscription=100)
    await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)
    assert await balance(saas) == {"subscription": 0, "purchased": 775, "total": 775}


async def test_charge_never_exceeds_the_hold(saas):
    """A provider reporting more tokens than the worst case can bill at most what was reserved."""
    saas.provider.usage = Usage(1_000_000, 100_000)  # would be 225 credits, but the hold is ~1
    uid = await user_id(saas)
    await give(saas, uid, purchased=1000)
    await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)
    assert (await balance(saas))["total"] >= 998


async def test_provider_failure_is_not_charged_and_hides_provider_details(saas):
    saas.provider.fail_at = 0
    uid = await user_id(saas)
    await give(saas, uid, purchased=1000)
    r = await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)
    last = events(r)[-1]
    assert last["type"] == "error" and "not charged" in last["message"]
    assert "sk-platform" not in r.text  # the platform's key material must not leak to users
    assert (await balance(saas))["total"] == 1000


async def test_dropped_stream_settles_and_releases_the_hold(saas):
    """The client vanishes after the first token: what was produced is billed, the rest is released."""
    saas.provider.usage = None  # no usage report: the cost is estimated from the text received
    saas.provider.cap = 1_000_000
    uid = await user_id(saas)
    await give(saas, uid, purchased=1000)
    principal = (await saas.app.state.accounts.principal_for(
        await saas.app.state.auth.verify_token("dev:alice:alice@example.com")))
    resolved = await saas.app.state.registry.resolve(principal, "managed", None, None)
    call = await saas.app.state.gateway.prepare(principal, resolved, "hi", None, "default", "an1")
    assert 245 <= (await balance(saas))["total"] <= 250  # ~750 credits held while streaming
    stream = saas.app.state.gateway.events(call)
    assert (await stream.__anext__())["type"] == "token"
    await stream.aclose()  # what Starlette does when the client disconnects
    after = (await balance(saas))["total"]
    assert 990 < after <= 1000  # almost everything came back
    async with saas.db.session() as s:
        ev = (await s.execute(select(UsageEvent))).scalars().one()
    assert ev.status == "aborted" and ev.credits_charged >= 1


async def test_reaper_releases_orphaned_holds(saas):
    from datetime import timedelta
    uid = await user_id(saas)
    await give(saas, uid, purchased=1000)
    await saas.app.state.credits.reserve(uid, 400, analysis_id=None, provider="x", model="m")
    assert (await balance(saas))["total"] == 600
    assert await saas.app.state.credits.reap_stale(older_than=timedelta(seconds=-1)) == 1
    assert (await balance(saas))["total"] == 1000


async def test_models_requiring_a_subscription(saas):
    uid = await user_id(saas)
    await give(saas, uid, purchased=5000)
    r = await saas.http.post("/api/v1/analyses", json={**ANALYSE, "model": "claude-sonnet-5-5"}, headers=A)
    assert r.status_code == 402 and "subscription" in r.json()["detail"]
    assert (await saas.http.post("/api/v1/analyses", json={**ANALYSE, "model": "nope"}, headers=A)).status_code == 422


async def test_model_catalog_lists_only_configured_providers(saas):
    body = (await saas.http.get("/api/v1/models")).json()
    assert {m["id"] for m in body["managed"]} == {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"}
    assert body["default_managed"] == "claude-haiku-5-5"
    assert all(m["est_credits"] >= 1 for m in body["managed"])
    assert "anthropic" in body["byok_suggestions"]


# -------------------------------------------------------------- chat -------

async def test_chat_is_scoped_to_the_analysis_owner(saas):
    uid = await user_id(saas)
    await give(saas, uid, purchased=1000)
    await user_id(saas, B)
    aid = events(await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A))[0]["analysis_id"]
    msgs = [{"role": "assistant", "content": "x"}, {"role": "user", "content": "why?"}]
    mine = await saas.http.post("/api/v1/chat", json={"analysis_id": aid, "messages": msgs}, headers=A)
    assert events(mine)[-1] == {"type": "done"} or events(mine)[-1]["type"] == "done"
    theirs = await saas.http.post("/api/v1/chat", json={"analysis_id": aid, "messages": msgs}, headers=B)
    assert theirs.status_code == 404
    sent = saas.provider.calls[-1][0]
    assert sent[1]["role"] == "user" and "e4" in sent[1]["content"]  # server-side context


# -------------------------------------------------------------- BYOK -------

async def add_key(saas, headers=A, **kw):
    body = {"provider": "openai", "api_key": "sk-test-abcdef1234", "label": "mine", **kw}
    return await saas.http.post("/api/v1/keys", json=body, headers=headers)


async def test_byok_key_lifecycle_and_encryption_at_rest(saas):
    r = await add_key(saas)
    assert r.status_code == 201
    key = r.json()
    assert key["hint"] == "1234" and "api_key" not in key and "sk-test" not in r.text
    assert (await saas.http.get("/api/v1/keys", headers=A)).json()[0]["id"] == key["id"]
    async with saas.db.session() as s:
        row = (await s.execute(select(ProviderKey))).scalars().one()
    assert b"sk-test-abcdef1234" not in row.ciphertext  # encrypted at rest
    assert saas.app.state.vault.decrypt(row.ciphertext, row.nonce, row.key_version,
                                        f"user:{row.user_id}".encode()) == "sk-test-abcdef1234"
    # bound to its owner: moving the row to another user makes it undecryptable
    with pytest.raises(Exception):
        saas.app.state.vault.decrypt(row.ciphertext, row.nonce, row.key_version, b"user:999")

    assert (await saas.http.post(f"/api/v1/keys/{key['id']}/test", headers=A)).json() == {"ok": True}
    assert (await saas.http.delete(f"/api/v1/keys/{key['id']}", headers=A)).status_code == 204
    assert (await saas.http.get("/api/v1/keys", headers=A)).json() == []


async def test_byok_rejects_bad_keys_and_unsafe_endpoints(saas):
    assert (await add_key(saas, api_key="bad-key-0000")).status_code == 422
    assert (await add_key(saas, provider="custom", base_url="http://example.com/v1")).status_code == 422
    assert (await add_key(saas, provider="custom", base_url="https://127.0.0.1/v1")).status_code == 422
    assert (await saas.http.get("/api/v1/keys", headers=A)).json() == []


async def test_byok_keys_are_private_to_their_owner(saas):
    key = (await add_key(saas)).json()
    assert (await saas.http.get("/api/v1/keys", headers=B)).json() == []
    assert (await saas.http.delete(f"/api/v1/keys/{key['id']}", headers=B)).status_code == 404
    body = {**ANALYSE, "source": "byok", "key_id": key["id"], "model": "gpt-x"}
    assert (await saas.http.post("/api/v1/analyses", json=body, headers=B)).status_code == 404


async def test_byok_analysis_is_free_but_recorded(saas):
    key = (await add_key(saas)).json()
    body = {**ANALYSE, "source": "byok", "key_id": key["id"], "model": "gpt-x"}
    r = await saas.http.post("/api/v1/analyses", json=body, headers=A)
    evs = events(r)
    assert evs[-1] == {"type": "done"} and evs[-2]["type"] == "usage"
    assert evs[-2]["credits"] == 0 and evs[-2]["balance"] is None
    assert saas.provider.calls == []  # the platform's key was not used
    assert saas.app.state.byok_providers[-1].calls[0][1] == "gpt-x"
    assert saas.app.state.byok_providers[-1].closed  # per-request client released
    item = (await saas.http.get("/api/v1/me/usage", headers=A)).json()["items"][0]
    assert item["source"] == "byok" and item["credits_charged"] == 0
    assert (await balance(saas))["total"] == 0


async def test_byok_requires_a_model_and_a_key(saas):
    key = (await add_key(saas)).json()
    no_model = {**ANALYSE, "source": "byok", "key_id": key["id"]}
    assert (await saas.http.post("/api/v1/analyses", json=no_model, headers=A)).status_code == 422
    no_key = {**ANALYSE, "source": "byok", "model": "gpt-x"}
    assert (await saas.http.post("/api/v1/analyses", json=no_key, headers=A)).status_code == 422


# ----------------------------------------------------- abuse protection ----

async def test_rate_limits(saas):
    s = saas.app.state.settings
    s.rate_limit_enabled, s.rate_llm_per_min, s.rate_engine_anon_per_min = True, 2, 3
    for _ in range(3):
        assert (await saas.http.post("/api/v1/evaluations", json={"fen": START})).status_code == 200
    r = await saas.http.post("/api/v1/evaluations", json={"fen": START})
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1
    # users are limited independently of the anonymous IP bucket
    assert (await saas.http.post("/api/v1/evaluations", json={"fen": START}, headers=A)).status_code == 200
    for _ in range(2):
        await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)
    assert (await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)).status_code == 429


# --------------------------------------------------------------- GDPR -------

async def test_export_and_account_deletion(saas):
    uid = await user_id(saas)
    await give(saas, uid, purchased=100)
    await add_key(saas)
    export = await saas.http.get("/api/v1/me/export", headers=A)
    assert export.status_code == 200 and "attachment" in export.headers["content-disposition"]
    assert "ciphertext" not in export.text and "sk-test" not in export.text
    assert export.json()["balance"]["purchased"] == 100

    assert (await saas.http.delete("/api/v1/me", headers=A)).status_code == 204
    async with saas.db.session() as s:
        assert (await s.execute(select(ProviderKey))).scalars().all() == []  # keys erased
    again = (await saas.http.get("/api/v1/me", headers=A)).json()  # same login = a brand new account
    assert again["id"] != uid and again["balance"]["total"] == 0


async def test_usage_is_exported_as_metrics(saas):
    from prometheus_client import REGISTRY
    saas.provider.usage = Usage(1000, 200)
    uid = await user_id(saas)
    await give(saas, uid, purchased=1000)
    before = REGISTRY.get_sample_value("shashguru_llm_tokens_total",
                                       {"provider": "anthropic", "model": "claude-haiku-5-5", "direction": "input"}) or 0
    await saas.http.post("/api/v1/analyses", json=ANALYSE, headers=A)
    after = REGISTRY.get_sample_value("shashguru_llm_tokens_total",
                                      {"provider": "anthropic", "model": "claude-haiku-5-5", "direction": "input"})
    assert after - before == 1000
