# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import asyncio
import base64
import hashlib
import hmac
import json
import time

import pytest

from app.adapters.auth.clerk import ClerkAuth
from app.adapters.auth.oidc import OidcAuth
from app.config import Settings
from app.db.session import Database
from app.ports.auth import AuthError, UserDeleted, UserUpdated
from app.services.billing import credits
from app.services.billing.credits import CreditService, InsufficientCredits
from app.services.billing.pricing import Catalog, ModelEntry, cost_credits
from app.services.crypto import CryptoError, KeyVault, generate_key
from app.services.ratelimit import RateLimiter
from app.services.ssrf import UnsafeUrl, assert_public_https_url


# ---------------------------------------------------------------- crypto ----

def test_vault_roundtrip_and_aad_binding():
    vault = KeyVault(f"v1:{generate_key()}")
    ct, nonce, version = vault.encrypt("sk-secret", b"user:1")
    assert b"sk-secret" not in ct and version == "v1"
    assert vault.decrypt(ct, nonce, version, b"user:1") == "sk-secret"
    with pytest.raises(CryptoError):
        vault.decrypt(ct, nonce, version, b"user:2")  # tied to its owner
    with pytest.raises(CryptoError):
        vault.decrypt(ct[:-1] + bytes([ct[-1] ^ 1]), nonce, version, b"user:1")  # tampering is detected


def test_vault_key_rotation_keeps_old_data_readable():
    old, new = generate_key(), generate_key()
    ct, nonce, version = KeyVault(f"v1:{old}").encrypt("sk-old")
    rotated = KeyVault(f"v2:{new},v1:{old}")
    assert rotated.decrypt(ct, nonce, version) == "sk-old"
    assert rotated.encrypt("sk-new")[2] == "v2"  # new writes use the newest key


def test_vault_rejects_bad_config():
    with pytest.raises(CryptoError):
        KeyVault("v1:short")
    assert not KeyVault("").configured
    with pytest.raises(CryptoError):
        KeyVault("").encrypt("x")


# ------------------------------------------------------------------ ssrf ----

def public(host, port):
    return ["93.184.216.34"]


@pytest.mark.parametrize("url", [
    "http://api.example.com/v1",  # not https
    "https://user:pw@api.example.com/v1",
    "https://127.0.0.1/v1", "https://[::1]/v1", "https://10.0.0.5/v1", "https://192.168.1.10/v1",
    "https://169.254.169.254/latest/meta-data", "https://100.64.0.1/v1",  # metadata, CGNAT
    "https://[::ffff:127.0.0.1]/v1", "https://localhost/v1", "https://db.internal/v1", "https://",
])
async def test_ssrf_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeUrl):
        await assert_public_https_url(url, resolver=public)


async def test_ssrf_rejects_names_resolving_to_private_addresses():
    with pytest.raises(UnsafeUrl):
        await assert_public_https_url("https://evil.example.com/v1", resolver=lambda h, p: ["10.1.2.3"])
    with pytest.raises(UnsafeUrl):  # one private answer among public ones is enough to refuse
        await assert_public_https_url("https://evil.example.com/v1", resolver=lambda h, p: ["93.184.216.34", "127.0.0.1"])


async def test_ssrf_accepts_public_https():
    assert await assert_public_https_url("https://api.example.com/v1/", resolver=public) == "https://api.example.com/v1"


# ------------------------------------------------------------ rate limit ----

async def test_rate_limiter_window():
    now = [1000.0]
    rl = RateLimiter(None, clock=lambda: now[0])
    assert [(await rl.hit("k", 3, 60)).allowed for _ in range(4)] == [True, True, True, False]
    assert (await rl.hit("other", 3, 60)).allowed
    now[0] += 60
    assert (await rl.hit("k", 3, 60)).allowed  # new window


async def test_rate_limiter_with_redis():
    import fakeredis
    now = [1000.0]
    rl = RateLimiter(fakeredis.FakeRedis(), clock=lambda: now[0])
    assert [(await rl.hit("k", 2, 60)).allowed for _ in range(3)] == [True, True, False]


# --------------------------------------------------------------- pricing ----

def test_cost_is_rounded_up_and_never_free():
    haiku = ModelEntry("m", "M", "anthropic", price_in=0.10, price_out=0.50)
    assert cost_credits(haiku, 1, 1, 1.5, 0.001) == 1
    assert cost_credits(haiku, 1_000_000, 100_000, 1.5, 0.001) == 225
    assert cost_credits(haiku, 0, 0, 1.5, 0.001) == 1


def test_catalog_hides_models_without_a_platform_key(tmp_path):
    from app.config import DATA_DIR
    catalog = Catalog.load(DATA_DIR / "models.yaml")
    assert catalog.available(Settings(_env_file=None)) == []
    assert catalog.default(Settings(_env_file=None)) is None
    assert {m.provider for m in catalog.available(Settings(_env_file=None, anthropic_api_key="k"))} == {"anthropic"}


# --------------------------------------------------------------- credits ----

@pytest.fixture
async def ledger_db(tmp_path):
    from app.db.models import User
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'c.db'}")
    await db.create_all()
    async with db.session() as s:
        s.add(User(id=1, auth_provider="dev", auth_subject="a"))
    yield db
    await db.close()


async def test_concurrent_holds_never_overdraw(ledger_db):
    """Twenty simultaneous 100-credit holds against 1000 credits: exactly ten succeed, the balance is exact."""
    svc = CreditService(ledger_db)
    await credits.retrying(ledger_db, lambda s: credits.add_purchased(s, 1, 1000, "seed"))

    async def attempt():
        try:
            await svc.reserve(1, 100, analysis_id=None, provider="p", model="m")
            return True
        except InsufficientCredits:
            return False

    results = await asyncio.gather(*(attempt() for _ in range(20)))
    assert sum(results) == 10
    assert (await svc.balance(1)).total == 0


async def test_settle_is_idempotent_and_refunds_to_the_right_buckets(ledger_db):
    svc = CreditService(ledger_db)

    async def seed(s):
        await credits.grant_subscription(s, 1, 100, "g")
        await credits.add_purchased(s, 1, 100, "t")
    await credits.retrying(ledger_db, seed)

    usage_id = await svc.reserve(1, 150, analysis_id=None, provider="p", model="m")  # 100 sub + 50 purchased
    assert (await svc.balance(1)).as_dict() == {"subscription": 0, "purchased": 50, "total": 50}
    balance, charged = await svc.settle(usage_id, cost=120, input_tokens=1, output_tokens=1, status="ok")
    assert charged == 120
    assert balance.as_dict() == {"subscription": 0, "purchased": 80, "total": 80}  # 30 of the 50 came back
    assert await svc.settle(usage_id, cost=0, input_tokens=0, output_tokens=0, status="ok") is None  # second call: no-op
    assert (await svc.balance(1)).total == 80


async def test_subscription_period_replaces_leftover_credits(ledger_db):
    async def renew(amount, ref):
        await credits.retrying(ledger_db, lambda s: credits.grant_subscription(s, 1, amount, ref))
    await renew(1000, "inv1")
    await credits.retrying(ledger_db, lambda s: credits.add_purchased(s, 1, 50, "t"))
    await renew(1000, "inv2")  # unused subscription credits expire, purchased ones stay
    assert (await CreditService(ledger_db).balance(1)).as_dict() == {"subscription": 1000, "purchased": 50, "total": 1050}


# ------------------------------------------------------------------ auth ----

def _svix(secret: bytes, body: bytes, ts: int | None = None):
    ts = ts or int(time.time())
    sig = base64.b64encode(hmac.new(secret, f"msg_1.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    return {"svix-id": "msg_1", "svix-timestamp": str(ts), "svix-signature": f"v1,{sig}"}


def test_clerk_webhooks_are_verified_and_normalised():
    secret = b"super-secret-key-material-000000"
    auth = ClerkAuth(issuer="https://x.clerk.accounts.dev", key_resolver=lambda t: None,
                     webhook_secret="whsec_" + base64.b64encode(secret).decode())
    body = json.dumps({"type": "user.deleted", "data": {"id": "user_1"}}).encode()
    assert auth.parse_webhook(_svix(secret, body), body) == [UserDeleted("clerk", "user_1")]
    upd = json.dumps({"type": "user.updated", "data": {"id": "user_1", "primary_email_address_id": "e2",
                      "email_addresses": [{"id": "e1", "email_address": "a@x.it"},
                                          {"id": "e2", "email_address": "b@x.it"}]}}).encode()
    assert auth.parse_webhook(_svix(secret, upd), upd) == [UserUpdated("clerk", "user_1", "b@x.it")]
    with pytest.raises(AuthError):
        auth.parse_webhook(_svix(b"wrong-secret-wrong-secret-0000", body), body)
    with pytest.raises(AuthError):  # replayed after the tolerance window
        auth.parse_webhook(_svix(secret, body, ts=int(time.time()) - 3600), body)


async def test_oidc_verifies_signature_issuer_expiry_and_admin_role():
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = OidcAuth(issuer="https://idp.test", audience="shash", admin_subjects=["boss"],
                    key_resolver=lambda token: key.public_key())

    def token(sub="u1", signer=key, **claims):
        base = {"sub": sub, "iss": "https://idp.test", "aud": "shash", "exp": int(time.time()) + 60,
                "email": f"{sub}@x.it"}
        return jwt.encode({**base, **claims}, signer, algorithm="RS256")

    ident = await auth.verify_token(token())
    assert (ident.subject, ident.email, ident.is_admin) == ("u1", "u1@x.it", False)
    assert (await auth.verify_token(token("boss"))).is_admin
    for bad in (token(signer=other), token(exp=int(time.time()) - 600), token(iss="https://evil.test"),
                token(aud="someone-else"), "garbage"):
        with pytest.raises(AuthError):
            await auth.verify_token(bad)


def test_auth_factory_refuses_insecure_configurations():
    from app.adapters.auth import build_auth
    with pytest.raises(RuntimeError):  # SaaS without an identity provider
        build_auth(Settings(_env_file=None, deployment_mode="saas", auth_provider="none"))
    with pytest.raises(RuntimeError):  # dev tokens are forgeable by anyone
        build_auth(Settings(_env_file=None, deployment_mode="saas", auth_provider="dev"))
    with pytest.raises(RuntimeError):
        build_auth(Settings(_env_file=None, deployment_mode="selfhosted", auth_provider="clerk"))
    assert build_auth(Settings(_env_file=None)).name == "none"


def test_saas_refuses_to_start_without_an_encryption_key():
    from fastapi import FastAPI
    from app.bootstrap import build_state
    from tests.conftest import FakeCache, FakeEngines
    s = Settings(_env_file=None, deployment_mode="saas", auth_provider="dev", allow_dev_auth=True)
    with pytest.raises(RuntimeError, match="KEY_ENCRYPTION_KEYS"):
        build_state(FastAPI(), s, FakeCache(), FakeEngines())


def test_settings_parse_comma_separated_lists(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.test, https://b.test")
    monkeypatch.setenv("AUTH_ADMIN_SUBJECTS", "user_1,user_2")
    s = Settings(_env_file=None)
    assert s.cors_origins == ["https://a.test", "https://b.test"] and s.auth_admin_subjects == ["user_1", "user_2"]
