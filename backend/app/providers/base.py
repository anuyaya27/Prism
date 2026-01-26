import abc
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ProviderModel:
    id: str
    provider: str
    available: bool
    reason: str | None = None
    description: str | None = None


@dataclass
class GenerationResult:
    model_id: str
    provider: str
    text: str | None
    usage: dict[str, Any] | None
    meta: dict[str, Any] | None
    latency_ms: float | None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def ok(self) -> bool:
        return self.error_code is None and self.error_message is None


class Provider(abc.ABC):
    """
    Provider interface for all model backends.
    """

    name: str

    @abc.abstractmethod
    def list_models(self) -> list[ProviderModel]:
        """Return models exposed by this provider, including availability/reason."""

    @abc.abstractmethod
    async def generate(
        self, model_id: str, prompt: str, *, temperature: float, max_tokens: int
    ) -> GenerationResult:
        """Generate text for a given model."""


class ProviderFactory(Protocol):
    def __call__(self) -> Provider: ...
