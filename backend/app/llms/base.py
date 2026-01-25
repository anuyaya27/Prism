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


class LLMClient(abc.ABC):
    """
    Minimal interface that all LLM providers must follow.
    """

    name: str

    @abc.abstractmethod
    async def generate(self, prompt: str) -> LLMGeneration:
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
