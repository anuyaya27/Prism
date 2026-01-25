import asyncio
import os
import time
from typing import Any, Optional

import httpx

from app.llms.base import LLMClient, LLMGeneration


class OpenAIClient(LLMClient):
    """
    Minimal OpenAI chat completion client using HTTPX to avoid extra SDK dependencies.
    """

    provider = "openai"

    def __init__(self, model: str, api_key: Optional[str] = None, timeout: float = 15.0, max_retries: int = 2):
        self.model_name = model
        self.name = f"openai:{model}"
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
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
                error="OPENAI_API_KEY is missing",
            )

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                message = choice["message"]["content"]
                latency_ms = (time.perf_counter() - start) * 1000
                return LLMGeneration(
                    model=self.name,
                    response=message,
                    latency_ms=latency_ms,
                    provider=self.provider,
                    usage=data.get("usage"),
                    finish_reason=choice.get("finish_reason"),
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
