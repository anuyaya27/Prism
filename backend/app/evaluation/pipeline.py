import asyncio
import statistics
from collections import Counter
from datetime import datetime
from typing import Iterable, Sequence

from app.llms.base import LLMClient, LLMGeneration
from app.models.schemas import (
    EvaluateResponse,
    EvaluationMetrics,
    ModelEvaluation,
    SynthesizedResponse,
)
from app.synthesis.aggregator import ResponseSynthesizer


class EvaluationEngine:
    """
    Coordinates running prompts across LLM clients and computing lightweight metrics.
    """

    def __init__(self, clients: Sequence[LLMClient], synthesizer: ResponseSynthesizer):
        if not clients:
            raise ValueError("At least one client is required")
        self._clients = {client.name: client for client in clients}
        self._synthesizer = synthesizer

    async def evaluate(self, prompt: str, model_names: Sequence[str] | None = None) -> EvaluateResponse:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        selected = self._select_clients(model_names)
        generations = await self._gather(prompt, selected)

        metrics = self._compute_metrics(generations)
        synthesis = self._synthesizer.synthesize(prompt=prompt, generations=generations)

        evaluations = [
            ModelEvaluation(model=gen.model, response=gen.response, latency_ms=gen.latency_ms, created_at=gen.created_at)
            for gen in generations
        ]

        return EvaluateResponse(
            prompt=prompt,
            evaluations=evaluations,
            metrics=metrics,
            synthesis=synthesis,
        )

    def _select_clients(self, model_names: Sequence[str] | None) -> list[LLMClient]:
        if model_names is None:
            return list(self._clients.values())

        missing = [name for name in model_names if name not in self._clients]
        if missing:
            raise ValueError(f"Unknown model(s): {', '.join(missing)}")
        return [self._clients[name] for name in model_names]

    async def _gather(self, prompt: str, clients: Iterable[LLMClient]) -> list[LLMGeneration]:
        tasks = [asyncio.create_task(client.generate(prompt)) for client in clients]
        return list(await asyncio.gather(*tasks))

    def _compute_metrics(self, generations: Sequence[LLMGeneration]) -> EvaluationMetrics:
        responses = [gen.response for gen in generations]
        lengths = [len(resp) for resp in responses]
        normalized = [resp.strip().lower() for resp in responses]
        counter = Counter(normalized)
        most_common = counter.most_common(1)[0][1] if counter else 0
        agreement = most_common / len(responses) if responses else 0.0

        divergence = len(counter)
        similarity = self._pairwise_jaccard(normalized)

        return EvaluationMetrics(
            agreement=agreement,
            unique_responses=divergence,
            average_length=statistics.mean(lengths) if lengths else 0.0,
            similarity=similarity,
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

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        aset, bset = set(a.split()), set(b.split())
        if not aset and not bset:
            return 1.0
        intersection = len(aset & bset)
        union = len(aset | bset)
        return intersection / union if union else 0.0
