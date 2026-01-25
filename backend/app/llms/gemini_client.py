import asyncio
import os
import time
from typing import Any, Optional

import httpx

from app.llms.base import LLMClient, LLMGeneration


class GeminiClient(LLMClient):
    """
    Minimal Gemini client via REST API.
    """

    provider = "gemini"

    def __init__(self, model: str, api_key: Optional[str] = None, timeout: float = 15.0, max_retries: int = 2):
        self.model_name = model
        self.name = f"gemini:{model}"
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries

    async def generate(self, prompt: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> LLMGeneration:
        start = time.perf_counter()
        if not self.api_key:
            latency_ms = (time.perf_counter() - start) * 1000
            return LLMGeneration(
                model=self.name,
                response="",
                latency_ms=latency_ms,
                provider=self.provider,
                error="GEMINI_API_KEY is missing",
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload: dict[str, Any] = {"contents": [{"parts": [{"text": prompt}]}]}
        if temperature is not None:
            payload["generationConfig"] = payload.get("generationConfig", {})
            payload["generationConfig"]["temperature"] = temperature
        if max_tokens is not None:
            payload["generationConfig"] = payload.get("generationConfig", {})
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                candidate = data.get("candidates", [{}])[0]
                parts = candidate.get("content", {}).get("parts", [])
                text = parts[0].get("text", "") if parts else ""
                latency_ms = (time.perf_counter() - start) * 1000
                return LLMGeneration(
                    model=self.name,
                    response=text,
                    latency_ms=latency_ms,
                    provider=self.provider,
                    finish_reason=candidate.get("finishReason"),
                    usage=data.get("usageMetadata"),
                    meta={"model": self.model_name},
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                backoff = 0.5 * (attempt + 1)
                await asyncio.sleep(backoff)

        latency_ms = (time.perf_counter() - start) * 1000
        return LLMGeneration(
            model=self.name,
            response="",
            latency_ms=latency_ms,
            provider=self.provider,
            error=last_error,
        )
