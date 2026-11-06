# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""OpenAI-compatible chat completions: OpenAI, OpenRouter, custom endpoints, self-hosted OVMS/vLLM."""
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI

from app.services.providers.base import StreamItem, Usage


class OpenAICompatProvider:
    def __init__(self, client: Any, name: str = "openai", *, include_usage: bool = True, temperature: Optional[float] = 0.0):
        self._client = client
        self.name = name
        self._include_usage = include_usage
        self._temperature = temperature

    @classmethod
    def create(cls, *, api_key: str, base_url: Optional[str], name: str, include_usage: bool = True,
               temperature: Optional[float] = 0.0) -> "OpenAICompatProvider":
        client = AsyncOpenAI(api_key=api_key or "unused", base_url=base_url, timeout=120.0, max_retries=1)
        return cls(client, name, include_usage=include_usage, temperature=temperature)

    def output_cap(self, max_tokens: int) -> int:
        return max_tokens

    async def stream(self, messages: list[dict], model: str, max_tokens: int) -> AsyncIterator[StreamItem]:
        kwargs: dict[str, Any] = dict(model=model, messages=messages, stream=True, max_completion_tokens=max_tokens)
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        if self._include_usage:
            kwargs["stream_options"] = {"include_usage": True}
        stream = await self._client.chat.completions.create(**kwargs)
        usage: Optional[Usage] = None
        async for chunk in stream:
            raw = getattr(chunk, "usage", None)
            if raw is not None:
                usage = Usage(int(getattr(raw, "prompt_tokens", 0) or 0), int(getattr(raw, "completion_tokens", 0) or 0))
            if not chunk.choices:
                continue
            # Do not stop at finish_reason: the last chunk may still carry text.
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
        if usage is not None:
            yield usage

    async def ping(self) -> None:
        """Cheap authenticated call: raises if the key or endpoint is wrong."""
        await self._client.models.list()

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close:
            await close()
