from app.providers.base import GenerationResult, Provider, ProviderModel


class GeminiProvider(Provider):
    """
    Gemini provider disabled per request. It always reports unavailable.
    """

    name = "gemini"

    def list_models(self) -> list[ProviderModel]:
        return [
            ProviderModel(
                id="gemini:disabled",
                provider=self.name,
                available=False,
                reason="Gemini provider disabled",
                description=None,
            )
        ]

    async def generate(self, model_id: str, prompt: str, *, temperature: float, max_tokens: int) -> GenerationResult:
        return GenerationResult(
            model_id=model_id,
            provider=self.name,
            text=None,
            usage=None,
            meta=None,
            latency_ms=0.0,
            error_code="GEMINI_DISABLED",
            error_message="Gemini provider disabled",
        )
