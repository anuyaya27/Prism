import asyncio
import json
import os
import re
import statistics
import time
from datetime import datetime
from typing import Iterable, Sequence
from uuid import uuid4

from app.models.schemas import (
    ComparePair,
    CompareResult,
    CompareSummary,
    EvaluateParams,
    EvaluateRequest,
    EvaluateResponse,
    ModelResult,
)
from app.providers.base import GenerationResult, Provider, ProviderModel
from app.providers.registry import ProviderRegistry
from app.synthesis.aggregator import MultiStrategySynthesizer
from app.synthesis.keywords import extract_keywords


class EvaluationEngine:
    """
    Coordinates running prompts across providers and computing comparison + synthesis.
    """

    def __init__(self, registry: ProviderRegistry, synthesizer: MultiStrategySynthesizer, runs_dir: str = "backend/runs"):
        self._registry = registry
        self._synthesizer = synthesizer
        self._runs_dir = runs_dir

    async def evaluate(self, request: EvaluateRequest) -> EvaluateResponse:
        prompt = request.prompt.strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        selected_models = self._registry.resolve_models(request.models)
        if not selected_models:
            raise ValueError("No models available for evaluation")

        params = EvaluateParams(
            models=[m.id for m in selected_models],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout_s=request.timeout_s,
            synthesis_method=request.synthesis_method,
        )

        request_id = uuid4().hex
        created_at = datetime.utcnow()

        provider_map = {p.name: p for p in self._registry.providers()}

        generations = await self._gather(
            prompt=prompt,
            models=selected_models,
            timeout_s=params.timeout_s,
            temperature=params.temperature,
            max_tokens=params.max_tokens,
            provider_map=provider_map,
        )

        synthesis = self._synthesizer.synthesize(prompt=prompt, generations=generations, method=params.synthesis_method)
        compare = self._compare(prompt, generations)
        results = [self._map_generation(gen) for gen in generations]

        response = EvaluateResponse(
            request_id=request_id,
            created_at=created_at,
            prompt=prompt,
            params=params,
            results=results,
            synthesis=synthesis,
            compare=compare,
        )

        self._persist_run(request_id, request, response)
        return response

    async def _gather(
        self,
        *,
        prompt: str,
        models: Iterable[ProviderModel],
        timeout_s: float,
        temperature: float,
        max_tokens: int,
        provider_map: dict[str, Provider],
    ) -> list[GenerationResult]:
        tasks = [
            asyncio.create_task(
                self._safe_generate(
                    provider=self._provider_for(model.provider, provider_map),
                    model=model,
                    prompt=prompt,
                    timeout_s=timeout_s,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
            for model in models
        ]
        return list(await asyncio.gather(*tasks))

    def _provider_for(self, provider_name: str, provider_map: dict[str, Provider]) -> Provider:
        if provider_name not in provider_map:
            raise ValueError(f"Provider {provider_name} not registered")
        return provider_map[provider_name]

    async def _safe_generate(
        self,
        *,
        provider: Provider,
        model: ProviderModel,
        prompt: str,
        timeout_s: float,
        temperature: float,
        max_tokens: int,
    ) -> GenerationResult:
        start = time.perf_counter()
        if not model.available:
            latency_ms = (time.perf_counter() - start) * 1000
            return GenerationResult(
                model_id=model.id,
                provider=model.provider,
                text=None,
                usage=None,
                meta=None,
                latency_ms=latency_ms,
                error_code="unavailable",
                error_message=model.reason or "Model unavailable",
            )

        try:
            return await asyncio.wait_for(
                provider.generate(model.id, prompt, temperature=temperature, max_tokens=max_tokens), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start) * 1000
            return GenerationResult(
                model_id=model.id,
                provider=model.provider,
                text=None,
                usage=None,
                meta=None,
                latency_ms=latency_ms,
                error_code="timeout",
                error_message=f"timeout after {timeout_s}s",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            return GenerationResult(
                model_id=model.id,
                provider=model.provider,
                text=None,
                usage=None,
                meta=None,
                latency_ms=latency_ms,
                error_code="provider_error",
                error_message=str(exc),
            )

    def _map_generation(self, gen: GenerationResult) -> ModelResult:
        status: str
        if gen.error_code == "timeout":
            status = "timeout"
        elif gen.error_code:
            status = "error"
        else:
            status = "success"

        return ModelResult(
            model=gen.model_id,
            provider=gen.provider,
            ok=gen.ok,
            status=status,  # type: ignore[arg-type]
            text=gen.text,
            error_code=gen.error_code,
            error_message=gen.error_message,
            latency_ms=gen.latency_ms,
            usage=gen.usage,
            meta=gen.meta,
        )

    def _compare(self, prompt: str, generations: Sequence[GenerationResult]) -> CompareResult:
        usable = [gen for gen in generations if gen.text]
        if len(usable) < 2:
            empty_summary = CompareSummary(
                avg_similarity=1.0,
                most_disagree_pair=None,
                notes="Not enough responses to compare; need at least two non-empty outputs.",
            )
            return CompareResult(pairs=[], summary=empty_summary)

        prompt_keywords = extract_keywords(prompt)
        pairs: list[ComparePair] = []
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                a, b = usable[i], usable[j]
                tokens_a = self._tokens(a.text or "")
                tokens_b = self._tokens(b.text or "")
                jaccard = self._jaccard(tokens_a, tokens_b)
                length_ratio = self._length_ratio(tokens_a, tokens_b)
                keyword_coverage = self._keyword_coverage(prompt_keywords, tokens_a, tokens_b)
                pairs.append(
                    ComparePair(
                        a=a.model_id,
                        b=b.model_id,
                        token_overlap_jaccard=jaccard,
                        length_ratio=length_ratio,
                        keyword_coverage=keyword_coverage,
                    )
                )

        avg_similarity = statistics.mean(p.token_overlap_jaccard for p in pairs) if pairs else 0.0
        sorted_pairs = sorted(pairs, key=lambda p: p.token_overlap_jaccard)
        summary = CompareSummary(
            avg_similarity=avg_similarity,
            most_disagree_pair=sorted_pairs[0] if sorted_pairs else None,
            notes="token_overlap_jaccard: 1.0 = identical; length_ratio: shorter/longer; keyword_coverage vs prompt keywords.",
        )
        return CompareResult(pairs=pairs, summary=summary)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in re.findall(r"\b\w+\b", text.lower()) if t]

    @staticmethod
    def _jaccard(tokens_a: list[str], tokens_b: list[str]) -> float:
        aset, bset = set(tokens_a), set(tokens_b)
        if not aset and not bset:
            return 1.0
        intersection = len(aset & bset)
        union = len(aset | bset)
        return intersection / union if union else 0.0

    @staticmethod
    def _length_ratio(tokens_a: list[str], tokens_b: list[str]) -> float:
        len_a, len_b = len(tokens_a), len(tokens_b)
        if len_a == 0 or len_b == 0:
            return 0.0
        shorter, longer = sorted([len_a, len_b])
        return shorter / longer if longer else 0.0

    @staticmethod
    def _keyword_coverage(prompt_keywords: set[str], tokens_a: list[str], tokens_b: list[str]) -> float:
        if not prompt_keywords:
            return 0.0
        combined = set(tokens_a) | set(tokens_b)
        return len(combined & prompt_keywords) / len(prompt_keywords)

    def _persist_run(self, request_id: str, request: EvaluateRequest, response: EvaluateResponse) -> None:
        os.makedirs(self._runs_dir, exist_ok=True)
        payload = {
            "request_id": request_id,
            "request": request.model_dump(),
            "response": response.model_dump(mode="json"),
        }
        path = os.path.join(self._runs_dir, f"{request_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
