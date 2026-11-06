# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Account, API keys, billing and public meta endpoints (SaaS mode)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import require_account
from app.db.models import Subscription
from app.ports.auth import AuthError
from app.ports.payments import PaymentError
from app.schemas import CheckoutRequestBody, KeyCreate
from app.services.accounts import Principal
from app.services.billing import credits
from app.services.billing.pricing import TYPICAL_INPUT_TOKENS, TYPICAL_OUTPUT_TOKENS, cost_credits
from app.services.billing.service import BillingError
from app.services.keys import KeyError_

log = logging.getLogger(__name__)
router = APIRouter(tags=["account"])


# ------------------------------------------------------------------ public ----

@router.get("/config")
async def public_config(request: Request):
    s = request.app.state.settings
    return {
        "deployment_mode": s.deployment_mode,
        "billing_enabled": s.is_saas and request.app.state.payments.name != "none",
        "byok_enabled": s.is_saas,
        "engine_anon_max_depth": s.anon_max_depth if s.is_saas else None,
    }


@router.get("/offers")
async def list_offers(request: Request):
    state = request.app.state
    if not state.settings.is_saas or state.payments.name == "none":
        return []
    return [o.public() for o in state.offers.all() if o.external.get(state.payments.name)]


@router.get("/models")
async def list_models(request: Request):
    state, s = request.app.state, request.app.state.settings
    managed = []
    if s.is_saas:
        for m in state.catalog.available(s):
            managed.append({"id": m.id, "label": m.label, "provider": m.provider,
                            "requires_subscription": m.requires_subscription,
                            "est_credits": cost_credits(m, TYPICAL_INPUT_TOKENS, TYPICAL_OUTPUT_TOKENS,
                                                        s.credit_markup, s.usd_per_credit)})
    return {"managed": managed, "byok_suggestions": state.catalog.byok_suggestions,
            "default_managed": state.catalog.default(s) if s.is_saas else None}


# ---------------------------------------------------------------------- me ----

@router.get("/me")
async def me(request: Request, principal: Principal = Depends(require_account)):
    state = request.app.state
    async with state.db.session() as s:
        sub = await s.get(Subscription, principal.user_id)
        balance = await credits.read_balance(s, principal.user_id)
    return {
        "id": principal.user_id, "email": principal.email, "is_admin": principal.is_admin,
        "plan": sub.offer_id if sub and sub.status in ("active", "past_due") else None,
        "subscription": ({"status": sub.status, "offer_id": sub.offer_id,
                          "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None}
                         if sub else None),
        "balance": balance.as_dict(),
        "usage_month": await state.accounts.usage_month(principal.user_id),
    }


@router.get("/me/usage")
async def my_usage(request: Request, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                   principal: Principal = Depends(require_account)):
    rows, total = await request.app.state.accounts.usage_page(principal.user_id, limit, offset)
    return {"total": total, "items": [
        {"id": u.id, "created_at": u.created_at.isoformat(), "source": u.source, "provider": u.provider,
         "model": u.model, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
         "credits_charged": u.credits_charged, "status": u.status} for u in rows]}


@router.get("/me/export")
async def export_me(request: Request, principal: Principal = Depends(require_account)):
    data = await request.app.state.accounts.export(principal.user_id)
    return JSONResponse(data, headers={"Content-Disposition": 'attachment; filename="shashguru-export.json"'})


@router.delete("/me", status_code=204)
async def delete_me(request: Request, principal: Principal = Depends(require_account)):
    """Erase the account: keys and personal data are deleted, the subscription is cancelled."""
    state = request.app.state
    subject = principal.subject
    await state.accounts.delete_user(principal.user_id, state.payments)
    try:
        await state.auth.delete_identity(subject)
    except AuthError:
        log.exception("Could not delete identity %s at the auth provider", subject)
    return Response(status_code=204)


# -------------------------------------------------------------------- keys ----

def _key_http(e: KeyError_) -> HTTPException:
    return HTTPException(e.status, e.message)


@router.get("/keys")
async def list_keys(request: Request, principal: Principal = Depends(require_account)):
    return await request.app.state.keys.list(principal.user_id)


@router.post("/keys", status_code=201)
async def add_key(body: KeyCreate, request: Request, principal: Principal = Depends(require_account)):
    try:
        return await request.app.state.keys.add(principal.user_id, body.provider, body.api_key, body.label,
                                                body.base_url)
    except KeyError_ as e:
        raise _key_http(e) from e


@router.delete("/keys/{key_id}", status_code=204)
async def delete_key(key_id: int, request: Request, principal: Principal = Depends(require_account)):
    if not await request.app.state.keys.delete(principal.user_id, key_id):
        raise HTTPException(404, "API key not found")
    return Response(status_code=204)


@router.post("/keys/{key_id}/test")
async def test_key(key_id: int, request: Request, principal: Principal = Depends(require_account)):
    try:
        return await request.app.state.keys.test(principal.user_id, key_id)
    except KeyError_ as e:
        raise _key_http(e) from e


# ----------------------------------------------------------------- billing ----

@router.post("/billing/checkout")
async def checkout(body: CheckoutRequestBody, request: Request, principal: Principal = Depends(require_account)):
    try:
        return {"url": await request.app.state.billing.checkout(principal.user_id, body.offer_id)}
    except BillingError as e:
        raise HTTPException(e.status, str(e)) from e


@router.post("/billing/portal")
async def portal(request: Request, principal: Principal = Depends(require_account)):
    try:
        return {"url": await request.app.state.billing.portal(principal.user_id)}
    except BillingError as e:
        raise HTTPException(e.status, str(e)) from e


# ---------------------------------------------------------------- webhooks ----
# Public: authenticity comes from the provider's signature, checked by the adapter.

@router.post("/webhooks/payments", include_in_schema=False)
async def payments_webhook(request: Request):
    state = request.app.state
    if not state.settings.is_saas:
        raise HTTPException(404)
    body = await request.body()
    try:
        processed = await state.billing.handle_webhook(request.headers, body)
    except PaymentError as e:
        raise HTTPException(400, str(e)) from e
    return {"received": True, "duplicate": not processed}


@router.post("/webhooks/auth", include_in_schema=False)
async def auth_webhook(request: Request):
    from app.ports.auth import UserDeleted, UserUpdated
    state = request.app.state
    if not state.settings.is_saas:
        raise HTTPException(404)
    body = await request.body()
    try:
        events = state.auth.parse_webhook(request.headers, body)
    except AuthError as e:
        raise HTTPException(400, str(e)) from e
    for event in events:
        if isinstance(event, UserDeleted):
            await state.accounts.delete_by_subject(event.provider, event.subject, state.payments)
        elif isinstance(event, UserUpdated):
            await state.accounts.update_email(event.provider, event.subject, event.email)
    return {"received": True}
