import asyncio
import json
import os
import statistics
import time
from collections import Counter
from datetime import datetime
from typing import Iterable, Sequence
from uuid import uuid4

from app.llms.base import LLMClient, LLMGeneration
from app.llms.registry import ModelRegistry
from app.models.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    EvaluationMetrics,
    ModelResponse,
    SynthesizedResponse,
)
from app.synthesis.aggregator import ResponseSynthesizer


class EvaluationEngine:
    """
    Coordinates running prompts across LLM clients and computing lightweight metrics.
    """

    def __init__(self, registry: ModelRegistry, synthesizer: ResponseSynthesizer, runs_dir: str = "backend/runs"):
        self._registry = registry
        self._synthesizer = synthesizer
        self._runs_dir = runs_dir

    async def evaluate(self, request: EvaluateRequest) -> EvaluateResponse:
        prompt = request.prompt
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        run_id = uuid4().hex
        selected = self._registry.resolve(request.models)
        generations = await self._gather(
            prompt,
            selected,
            timeout_s=request.timeout_s,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        metrics = self._compute_metrics(generations)
        synthesis = self._synthesizer.synthesize(prompt=prompt, generations=generations)

        responses = [self._map_generation(gen) for gen in generations]

        response = EvaluateResponse(
            run_id=run_id,
            request=request,
            responses=responses,
            metrics=metrics,
            synthesis=synthesis,
        )

        self._persist_run(run_id, request, response)
        return response

    async def _gather(
        self,
        prompt: str,
        clients: Iterable[LLMClient],
        *,
        timeout_s: float,
        temperature: float,
        max_tokens: int,
    ) -> list[LLMGeneration]:
        tasks = [
            asyncio.create_task(
                self._safe_generate(client, prompt, timeout_s=timeout_s, temperature=temperature, max_tokens=max_tokens)
            )
            for client in clients
        ]
        return list(await asyncio.gather(*tasks))

    async def _safe_generate(
        self,
        client: LLMClient,
        prompt: str,
        *,
        timeout_s: float,
        temperature: float,
        max_tokens: int,
    ) -> LLMGeneration:
        start = time.perf_counter()
        try:
            generation = await asyncio.wait_for(
                client.generate(prompt, temperature=temperature, max_tokens=max_tokens), timeout=timeout_s
            )
            # Ensure provider is always set if the client exposes it.
            if not getattr(generation, "provider", None) and hasattr(client, "provider"):
                generation.provider = getattr(client, "provider")
            return generation
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            provider = getattr(client, "provider", None)
            return LLMGeneration(
                model=getattr(client, "name", "unknown"),
                response="",
                latency_ms=latency_ms,
                provider=provider,
                error=str(exc),
            )

    def _map_generation(self, gen: LLMGeneration) -> ModelResponse:
        return ModelResponse(
            id=gen.model,
            provider=gen.provider,
            model=gen.meta.get("model") if gen.meta else gen.model,
            text=gen.response,
            latency_ms=gen.latency_ms,
            usage=gen.usage,
            finish_reason=gen.finish_reason,
            error=gen.error,
            created_at=gen.created_at,
        )

    def _compute_metrics(self, generations: Sequence[LLMGeneration]) -> EvaluationMetrics:
        successful = [gen for gen in generations if not gen.error and gen.response]
        baseline = successful if successful else generations

        responses = [gen.response for gen in baseline]
        lengths = [len(resp) for resp in responses]
        normalized = [resp.strip().lower() for resp in responses]
        counter = Counter(normalized)
        most_common = counter.most_common(1)[0][1] if counter else 0
        agreement = most_common / len(responses) if responses else 0.0

        divergence = len(counter)
        similarity = self._pairwise_jaccard(normalized)
        semantic_similarity = self._semantic_similarity(responses)

        return EvaluationMetrics(
            agreement=agreement,
            unique_responses=divergence,
            average_length=statistics.mean(lengths) if lengths else 0.0,
            similarity=similarity,
            semantic_similarity=semantic_similarity,
            evaluated_at=datetime.utcnow(),
        )

    def _pairwise_jaccard(self, responses: Sequence[str]) -> float:
        """
        Very lightweight similarity heuristic: average Jaccard similarity over token sets.
        """
        if len(responses) < 2:
            return 1.0
        pairs = []
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                pairs.append(self._jaccard(responses[i], responses[j]))
        return statistics.mean(pairs) if pairs else 0.0

    def _semantic_similarity(self, responses: Sequence[str]) -> float | None:
        """
        Compute average pairwise cosine similarity over TF-IDF vectors.
        Returns None if the library is unavailable or insufficient data.
        """
        if len(responses) < 2:
            return 1.0
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except Exception:
            return None

        vectorizer = TfidfVectorizer()
        matrix = vectorizer.fit_transform(responses)
        cosine = cosine_similarity(matrix)

        # Upper triangle without diagonal
        scores = []
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                scores.append(cosine[i, j])
        return float(statistics.mean(scores)) if scores else None

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        aset, bset = set(a.split()), set(b.split())
        if not aset and not bset:
            return 1.0
        intersection = len(aset & bset)
        union = len(aset | bset)
        return intersection / union if union else 0.0

    def _persist_run(self, run_id: str, request: EvaluateRequest, response: EvaluateResponse) -> None:
        os.makedirs(self._runs_dir, exist_ok=True)
        payload = {
            "run_id": run_id,
            "request": request.model_dump(),
            "response": response.model_dump(mode="json"),
        }
        path = os.path.join(self._runs_dir, f"{run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
