# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Runs an LLM call end to end: pre-authorise credits -> stream -> settle the real cost.

Settlement happens in a ``finally`` (shielded from cancellation), so a client that disconnects
mid-stream is still charged for what the provider actually produced and the hold is released.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

from app.config import Settings
from app.metrics import LLM_CALLS, LLM_CREDITS, LLM_TOKENS
from app.services import llm
from app.services.accounts import Principal
from app.services.billing.credits import CreditService, InsufficientCredits
from app.services.billing.pricing import cost_credits, estimate_tokens
from app.services.providers.base import Usage
from app.services.providers.resolver import Resolved

log = logging.getLogger(__name__)


class PaymentRequired(Exception):
    """Not enough credits for the requested model (HTTP 402)."""

    def __init__(self, message: str, needed: int = 0, available: int = 0):
        super().__init__(message)
        self.needed, self.available = needed, available


@dataclass
class Call:
    principal: Principal
    resolved: Resolved
    messages: list[dict]
    analysis_id: Optional[str]
    est_input_tokens: int
    usage_id: Optional[str] = None


class LLMGateway:
    def __init__(self, settings: Settings, credits: Optional[CreditService]):
        self.settings, self.credits = settings, credits

    async def prepare(self, principal: Principal, resolved: Resolved, prompt: str, history: Optional[list[dict]],
                      style: str, analysis_id: Optional[str]) -> Call:
        messages = llm.build_messages(prompt, history, style)
        est_in = sum(estimate_tokens(m["content"]) for m in messages)
        call = Call(principal, resolved, messages, analysis_id, est_in)
        if resolved.billing == "managed":
            entry = resolved.entry
            worst = cost_credits(entry, est_in, resolved.provider.output_cap(self.settings.max_completion_tokens),
                                 self.settings.credit_markup, self.settings.usd_per_credit)
            try:
                call.usage_id = await self.credits.reserve(
                    principal.user_id, worst, analysis_id=analysis_id, provider=resolved.provider_name,
                    model=resolved.model)
            except InsufficientCredits as e:
                LLM_CALLS.labels("managed", "payment_required").inc()
                raise PaymentRequired("Not enough credits for this model: top up or choose a cheaper model",
                                      e.needed, e.available) from e
        return call

    async def events(self, call: Call) -> AsyncIterator[dict[str, Any]]:
        """Token / usage / done / error events. Always settles, even when the consumer goes away."""
        chars = 0
        usage: Optional[Usage] = None
        error: Optional[BaseException] = None
        settled = False
        try:
            try:
                async for item in call.resolved.provider.stream(call.messages, call.resolved.model,
                                                                self.settings.max_completion_tokens):
                    if isinstance(item, Usage):
                        usage = item
                    else:
                        chars += len(item)
                        yield {"type": "token", "text": item}
            except Exception as e:  # provider failure: report it, do not crash the stream
                error = e
                log.warning("LLM call failed (%s/%s): %s", call.resolved.provider_name, call.resolved.model,
                            type(e).__name__)
            balance = await self._settle(call, usage, chars, "error" if error else "ok")
            settled = True
            if error is not None:
                yield {"type": "error", "message": self._error_message(call, error)}
                return
            if call.resolved.billing != "free":
                charged = balance[0] if balance else 0
                yield {"type": "usage", "input_tokens": balance[2], "output_tokens": balance[3],
                       "credits": charged, "balance": balance[1]}
            yield {"type": "done"}
        finally:
            if not settled:  # cancelled / client gone
                await asyncio.shield(self._settle(call, usage, chars, "aborted"))

    async def _settle(self, call: Call, usage: Optional[Usage], chars: int, status: str):
        """Returns (credits_charged, balance_dict | None, input_tokens, output_tokens)."""
        resolved = call.resolved
        if resolved.owned:
            await _safe_close(resolved.provider)
        LLM_CALLS.labels(resolved.billing, status).inc()
        if resolved.billing == "free":
            return None
        in_tok = usage.input_tokens if usage else call.est_input_tokens
        out_tok = usage.output_tokens if usage else (estimate_tokens("x" * chars) if chars else 0)
        LLM_TOKENS.labels(resolved.provider_name, resolved.model, "input").inc(in_tok)
        LLM_TOKENS.labels(resolved.provider_name, resolved.model, "output").inc(out_tok)
        try:
            if resolved.billing == "byok":
                await self.credits.record_byok(call.principal.user_id, analysis_id=call.analysis_id,
                                               provider=resolved.provider_name, model=resolved.model,
                                               input_tokens=in_tok, output_tokens=out_tok, status=status)
                return (0, None, in_tok, out_tok)
            nothing_produced = status != "ok" and usage is None and chars == 0
            cost = 0 if nothing_produced else cost_credits(
                resolved.entry, in_tok, out_tok, self.settings.credit_markup, self.settings.usd_per_credit)
            settled = await self.credits.settle(call.usage_id, cost=cost, input_tokens=in_tok,
                                                output_tokens=out_tok, status=status)
            if settled is None:  # already settled by the reaper
                return (0, (await self.credits.balance(call.principal.user_id)).as_dict(), in_tok, out_tok)
            balance, charged = settled
            LLM_CREDITS.labels(resolved.provider_name, resolved.model).inc(charged)
            return (charged, balance.as_dict(), in_tok, out_tok)
        except Exception:
            log.exception("Could not settle LLM usage %s", call.usage_id)
            return (0, None, in_tok, out_tok)

    @staticmethod
    def _error_message(call: Call, error: BaseException) -> str:
        billing = call.resolved.billing
        if billing == "free":
            return f"LLM request failed: {error}"
        if billing == "byok":
            status = getattr(error, "status_code", None)
            detail = str(getattr(error, "message", "") or error)[:200]
            return f"Your provider returned an error{f' ({status})' if status else ''}: {detail}"
        return "The AI provider returned an error. You were not charged for this request."


async def _safe_close(provider) -> None:
    try:
        await provider.close()
    except Exception:
        log.debug("closing provider failed", exc_info=True)
