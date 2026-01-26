import asyncio
import json
import os
import statistics
import time
from typing import Iterable, Sequence
from uuid import uuid4

from app.llms.base import LLMClient, LLMGeneration
from app.llms.registry import ModelRegistry
from app.models.schemas import ComparePair, CompareResult, EvaluateRequest, EvaluateResponse, ModelResult
from app.synthesis.aggregator import ResponseSynthesizer


class EvaluationEngine:
    """
    Coordinates running prompts across LLM clients and computing lightweight comparisons.
    """

    def __init__(self, registry: ModelRegistry, synthesizer: ResponseSynthesizer, runs_dir: str = "backend/runs"):
        self._registry = registry
        self._synthesizer = synthesizer
        self._runs_dir = runs_dir

    async def evaluate(self, request: EvaluateRequest) -> EvaluateResponse:
        prompt = request.prompt.strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        model_ids = list(request.models or self._registry.available_ids())
        clients = self._registry.resolve(model_ids)
        if not clients:
            raise ValueError("No models available for evaluation")

        request_id = uuid4().hex
        generations = await self._gather(
            prompt=prompt,
            model_ids=model_ids,
            clients=clients,
            timeout_s=request.timeout_s,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        synthesis = self._synthesizer.synthesize(prompt=prompt, generations=generations)
        compare = self._compare(generations)
        results = [self._map_generation(gen) for gen in generations]

        response = EvaluateResponse(
            request_id=request_id,
            prompt=prompt,
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
        model_ids: Iterable[str],
        clients: Iterable[LLMClient],
        timeout_s: float,
        temperature: float,
        max_tokens: int,
    ) -> list[LLMGeneration]:
        tasks = [
            asyncio.create_task(
                self._safe_generate(
                    requested_id=model_id,
                    client=client,
                    prompt=prompt,
                    timeout_s=timeout_s,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
            for model_id, client in zip(model_ids, clients)
        ]
        return list(await asyncio.gather(*tasks))

    async def _safe_generate(
        self,
        *,
        requested_id: str,
        client: LLMClient,
        prompt: str,
        timeout_s: float,
        temperature: float,
        max_tokens: int,
    ) -> LLMGeneration:
        start = time.perf_counter()
        try:
            generation = await asyncio.wait_for(
                client.generate(prompt, temperature=temperature, max_tokens=max_tokens), timeout=timeout_s
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            if not getattr(generation, "latency_ms", None):
                generation.latency_ms = elapsed_ms
            provider_model = generation.model
            if hasattr(generation, "meta") and isinstance(generation.meta, dict):
                generation.meta.setdefault("requested_id", requested_id)
                generation.meta.setdefault("provider_model", provider_model)
            generation.model = requested_id
            if not getattr(generation, "provider", None) and hasattr(client, "provider"):
                generation.provider = getattr(client, "provider")
            return generation
        except asyncio.TimeoutError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            provider = getattr(client, "provider", None)
            return LLMGeneration(
                model=requested_id,
                response="",
                latency_ms=latency_ms,
                provider=provider,
                error=f"timeout after {timeout_s} seconds",
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            provider = getattr(client, "provider", None)
            return LLMGeneration(
                model=requested_id,
                response="",
                latency_ms=latency_ms,
                provider=provider,
                error=str(exc),
            )

    def _map_generation(self, gen: LLMGeneration) -> ModelResult:
        status: str
        if gen.error:
            status = "timeout" if "timeout" in gen.error.lower() else "error"
        else:
            status = "success"

        return ModelResult(
            model=gen.model,
            provider=getattr(gen, "provider", None),
            ok=not gen.error,
            text=gen.response if not gen.error else None,
            error=gen.error,
            latency_ms=gen.latency_ms,
            status=status,
        )

    def _compare(self, generations: Sequence[LLMGeneration]) -> CompareResult:
        usable = [gen for gen in generations if gen.response]
        if len(usable) < 2:
            return CompareResult(pairs=[], note="Not enough responses to compare; need at least two non-empty outputs.")

        pairs: list[ComparePair] = []
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                score = self._jaccard(usable[i].response, usable[j].response)
                pairs.append(ComparePair(a=usable[i].model, b=usable[j].model, score=score))

        pairs = sorted(pairs, key=lambda p: p.score)
        avg_score = statistics.mean(p.score for p in pairs) if pairs else 0.0
        note = "score=jaccard(token overlap) where 1.0 means identical; lower scores indicate disagreement"
        note += f"; avg_score={avg_score:.2f}"
        return CompareResult(pairs=pairs, note=note)

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        aset, bset = set(a.split()), set(b.split())
        if not aset and not bset:
            return 1.0
        intersection = len(aset & bset)
        union = len(aset | bset)
        return intersection / union if union else 0.0

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
