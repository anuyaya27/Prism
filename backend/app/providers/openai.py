import asyncio
import os
import time
from typing import Any, Optional

import httpx

from app.providers.base import GenerationResult, Provider, ProviderModel
from app.utils.redact import sanitize_raw_io


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, *, api_key: Optional[str] = None, timeout: float = 20.0, max_retries: int = 2):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self._models = ["gpt-4o-mini"]
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")

    def list_models(self) -> list[ProviderModel]:
        available = bool(self.api_key)
        reason = None if available else "OPENAI_API_KEY missing"
        return [
            ProviderModel(
                id=f"openai:{m}",
                provider=self.name,
                available=available,
                reason=reason,
                description="OpenAI Chat Completions",
            )
            for m in self._models
        ]

    async def generate(
        self, model_id: str, prompt: str, *, temperature: float, max_tokens: int
    ) -> GenerationResult:
        start = time.perf_counter()
        if not self.api_key:
            latency_ms = (time.perf_counter() - start) * 1000
            return GenerationResult(
                model_id=model_id,
                provider=self.name,
                text=None,
                usage=None,
                meta=None,
                latency_ms=latency_ms,
                raw_request=None,
                raw_response=None,
                error_code="missing_api_key",
                error_message="OPENAI_API_KEY is missing",
            )

        model_name = model_id.split(":", 1)[1] if ":" in model_id else model_id
        url = self.base_url
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: str | None = None
        sanitized_request = sanitize_raw_io(url=url, headers=headers, body=payload)
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                message = choice["message"]["content"]
                latency_ms = (time.perf_counter() - start) * 1000
                return GenerationResult(
                    model_id=model_id,
                    provider=self.name,
                    text=message,
                    usage=data.get("usage"),
                    meta={"finish_reason": choice.get("finish_reason"), "model": model_name},
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
            error_message="OpenAI generation failed",
        )
