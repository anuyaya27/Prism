import time
from typing import Any

from app.llms.mock import MockEchoClient, MockReasonerClient
from app.providers.base import GenerationResult, Provider, ProviderModel


class MockProvider(Provider):
    name = "mock"

    def __init__(self) -> None:
        self._models = {
            "mock:echo": {"description": "Deterministic echo model", "factory": MockEchoClient},
            "mock:reasoner": {"description": "Pseudo reasoning model", "factory": MockReasonerClient},
            "mock:pseudo": {"description": "Alias of mock:reasoner", "factory": MockReasonerClient},
        }

    def list_models(self) -> list[ProviderModel]:
        return [
            ProviderModel(id=model_id, provider=self.name, available=True, reason=None, description=meta["description"])
            for model_id, meta in self._models.items()
        ]

    async def generate(
        self, model_id: str, prompt: str, *, temperature: float, max_tokens: int
    ) -> GenerationResult:
        if model_id not in self._models:
            return GenerationResult(
                model_id=model_id,
                provider=self.name,
                text=None,
                usage=None,
                meta=None,
                latency_ms=None,
                error_code="unknown_model",
                error_message=f"Model {model_id} is not registered",
            )

        client_factory = self._models[model_id]["factory"]
        client = client_factory()
        start = time.perf_counter()
        try:
            generation = await client.generate(prompt, temperature=temperature, max_tokens=max_tokens)
            latency_ms = (time.perf_counter() - start) * 1000
            return GenerationResult(
                model_id=model_id,
                provider=self.name,
                text=generation.response,
                usage=generation.usage,
                meta={"provider_model": getattr(generation, "meta", None), "model": getattr(generation, "model", None)},
                latency_ms=latency_ms,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            return GenerationResult(
                model_id=model_id,
                provider=self.name,
                text=None,
                usage=None,
                meta=None,
                latency_ms=latency_ms,
                error_code="mock_error",
                error_message=str(exc),
            )
