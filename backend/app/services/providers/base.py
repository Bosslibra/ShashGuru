# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Protocol, Union


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


StreamItem = Union[str, Usage]


class LLMProvider(Protocol):
    """Streams text deltas, then (when the API reports it) one final ``Usage``."""

    name: str

    def output_cap(self, max_tokens: int) -> int:
        """Worst-case number of billable output tokens for a request with this ``max_tokens``."""

    def stream(self, messages: list[dict], model: str, max_tokens: int) -> AsyncIterator[StreamItem]:
        ...

    async def ping(self) -> None:
        ...

    async def close(self) -> None:
        ...


class ProviderError(Exception):
    """A provider call failed in a way worth telling the user about (bad key, quota, ...)."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status
