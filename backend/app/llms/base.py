import abc
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LLMGeneration:
    model: str
    response: str
    latency_ms: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    meta: dict[str, Any] = field(default_factory=dict)
    provider: str | None = None
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    error: str | None = None


class LLMClient(abc.ABC):
    """
    Minimal interface that all LLM providers must follow.
    """

    name: str

    @abc.abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> LLMGeneration:
        """
        Produce a response for the given prompt.
        Implementations should avoid mutating shared state.
        """

    async def _wrap_timing(self, prompt: str) -> LLMGeneration:
        start = time.perf_counter()
        generation = await self.generate(prompt)
        elapsed = (time.perf_counter() - start) * 1000
        generation.latency_ms = elapsed
        return generation
