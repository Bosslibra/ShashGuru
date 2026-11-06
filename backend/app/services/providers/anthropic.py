# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Anthropic Messages API (Claude). Imported lazily so the SDK is only needed when used."""
from typing import Any, AsyncIterator, Optional

from app.services.providers.base import StreamItem, Usage

# Thinking tokens count against max_tokens on current Claude models: leave room beyond the visible answer.
MIN_MAX_TOKENS = 4096


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client: Any = None, *, api_key: str = "", effort: Optional[str] = None):
        if client is None:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key, timeout=120.0, max_retries=1)
        self._client = client
        self._effort = effort

    def with_effort(self, effort: Optional[str]) -> "AnthropicProvider":
        return AnthropicProvider(self._client, effort=effort)

    def output_cap(self, max_tokens: int) -> int:
        return max(max_tokens, MIN_MAX_TOKENS)

    async def stream(self, messages: list[dict], model: str, max_tokens: int) -> AsyncIterator[StreamItem]:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        turns = [m for m in messages if m["role"] != "system"]
        kwargs: dict[str, Any] = dict(model=model, max_tokens=self.output_cap(max_tokens), messages=turns)
        if system:
            kwargs["system"] = system
        if self._effort:
            # keeps short answers cheap on models that think by default; omit sampling params: rejected by 5.x models
            kwargs["output_config"] = {"effort": self._effort}
        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text
            final = await stream.get_final_message()
        usage = getattr(final, "usage", None)
        if usage is not None:
            yield Usage(int(usage.input_tokens or 0), int(usage.output_tokens or 0))

    async def ping(self) -> None:
        await self._client.models.list(limit=1)

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close:
            await close()
