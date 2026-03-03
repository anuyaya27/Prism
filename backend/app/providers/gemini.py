import asyncio
import os
import time
from typing import Any, Optional

import httpx

from app.providers.base import GenerationResult, Provider, ProviderModel
from app.utils.redact import sanitize_raw_io


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, *, api_key: Optional[str] = None, timeout: float = 20.0, max_retries: int = 2):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self._models = ["2.5-flash"]
        self._deprecated_aliases = {
            "1.5-flash": "2.5-flash",
            "gemini-1.5-flash": "gemini-2.5-flash",
        }
        self.base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/models")

    def list_models(self) -> list[ProviderModel]:
        available = bool(self.api_key)
        reason = None if available else "GEMINI_API_KEY missing"
        return [
            ProviderModel(
                id=f"gemini:{m}",
                provider=self.name,
                available=available,
                reason=reason,
                description="Google Gemini generateContent",
            )
            for m in self._models
        ]

    async def generate(self, model_id: str, prompt: str, *, temperature: float, max_tokens: int) -> GenerationResult:
        start = time.perf_counter()
        if not self.api_key:
            latency_ms = (time.perf_counter() - start) * 1000
            return GenerationResult(
                model_id=model_id,
                provider=self.name,
                text=None,
                usage=None,
                meta=None,
                raw_request=None,
                raw_response=None,
                latency_ms=latency_ms,
                error_code="missing_api_key",
                error_message="GEMINI_API_KEY is missing",
            )

        requested_model = model_id.split(":", 1)[1] if ":" in model_id else model_id
        remapped_model = self._deprecated_aliases.get(requested_model, requested_model)
        model_name = remapped_model if remapped_model.startswith("gemini-") else f"gemini-{remapped_model}"
        url = f"{self.base_url}/{model_name}:generateContent?key={self.api_key}"
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        last_error: str | None = None
        sanitized_request = sanitize_raw_io(url=url, headers={}, body=payload)

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                candidate = data.get("candidates", [{}])[0]
                parts = candidate.get("content", {}).get("parts", [])
                text = parts[0].get("text") if parts else None
                latency_ms = (time.perf_counter() - start) * 1000
                return GenerationResult(
                    model_id=model_id,
                    provider=self.name,
                    text=text,
                    usage=data.get("usageMetadata"),
                    meta={"finish_reason": candidate.get("finishReason"), "model": model_name},
                    raw_request=sanitized_request,
                    raw_response=sanitize_raw_io(
                        url=str(response.url),
                        headers=dict(response.headers),
                        body={"status_code": response.status_code, "body_snippet": str(response.text)[:500]},
                    ),
                    latency_ms=latency_ms,
                )
            except httpx.HTTPStatusError as exc:
                last_error = f"http_{exc.response.status_code}"
                if exc.response.status_code in (401, 403):
                    last_error = "auth_error"
                elif exc.response.status_code == 404:
                    last_error = (
                        f"http_404_model_not_found ({model_name}). "
                        "Try gemini:2.5-flash."
                    )
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                await asyncio.sleep(0.5 * (attempt + 1))

        latency_ms = (time.perf_counter() - start) * 1000
        return GenerationResult(
            model_id=model_id,
            provider=self.name,
            text=None,
            usage=None,
            meta=None,
            raw_request=sanitized_request,
            raw_response=None,
            latency_ms=latency_ms,
            error_code=last_error or "unknown_error",
            error_message="Gemini generation failed",
        )
