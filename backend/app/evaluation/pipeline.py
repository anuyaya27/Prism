import asyncio
import contextlib
import json
import logging
import os
import shutil
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence
from uuid import uuid4

from fastapi import Request

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
from app.utils.canonical import canonicalize_request
from app.utils.metrics import (
    distance_summary,
    format_compliance,
    hedge_count,
    jaccard,
    keyword_coverage,
    length_ratio,
    rouge_l,
    tokenize,
)
from app.utils.runtime import provider_runtime_info, runtime_context


class EvaluationEngine:
    """
    Coordinates running prompts across providers and computing comparison + synthesis.
    """

    SCHEMA_VERSION = "1.1.0"

    def __init__(self, registry: ProviderRegistry, synthesizer: MultiStrategySynthesizer, runs_dir: str = "backend/runs"):
        self._registry = registry
        self._synthesizer = synthesizer
        self._runs_dir = runs_dir
        self._run_timeout_s = float(os.getenv("PRISM_RUN_TIMEOUT_S", "30"))
        self._max_models_per_request = int(os.getenv("PRISM_MAX_MODELS", "6"))
        self._max_prompt_chars = int(os.getenv("PRISM_MAX_PROMPT_CHARS", "8000"))

    async def evaluate(self, request: EvaluateRequest, client_request: Request | None = None) -> EvaluateResponse:
        prompt = request.prompt.strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty")
        if len(prompt) > self._max_prompt_chars:
            raise ValueError(f"Prompt exceeds maximum length of {self._max_prompt_chars} characters")

        selected_models = self._registry.resolve_models(request.models)
        if not selected_models:
            raise ValueError("No models available for evaluation")
        if len(selected_models) > self._max_models_per_request:
            raise ValueError(f"Too many models requested; max is {self._max_models_per_request}")

        canonical, canonical_bytes, run_hash = canonicalize_request(request)

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
            client_request=client_request,
        )

        # annotate per-generation metrics
        for gen in generations:
            if gen.text:
                gen.meta = gen.meta or {}
                gen.meta["format_compliance"] = format_compliance(prompt, gen.text)
                gen.meta["hedge_count"] = hedge_count(gen.text)

        synthesis = self._synthesizer.synthesize(prompt=prompt, generations=generations, method=params.synthesis_method)
        compare = self._compare(prompt, generations)
        results = [self._map_generation(gen) for gen in generations]

        status = self._status(results)
        response = EvaluateResponse(
            request_id=request_id,
            created_at=created_at,
            run_hash=run_hash,
            schema_version=self.SCHEMA_VERSION,
            api_version="0.3.0",
            prompt=prompt,
            params=params,
            results=results,
            synthesis=synthesis,
            compare=compare,
            status=status,
            partial_success=status == "partial",
        )

        self._persist_run(request_id, request, response, canonical, canonical_bytes, generations, provider_map)
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
        client_request: Request | None = None,
    ) -> list[GenerationResult]:
        tasks: dict[str, asyncio.Task] = {}
        for model in models:
            task = asyncio.create_task(
                self._safe_generate(
                    provider=self._provider_for(model.provider, provider_map),
                    model=model,
                    prompt=prompt,
                    timeout_s=timeout_s,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
            tasks[model.id] = task

        monitor_task = (
            asyncio.create_task(self._monitor_disconnect(client_request)) if client_request is not None else None
        )

        pending_tasks = set(tasks.values())
        try:
            done, pending = await asyncio.wait(
                pending_tasks | ({monitor_task} if monitor_task else set()), timeout=self._run_timeout_s
            )
        finally:
            pass

        cancel_reason = None
        if monitor_task and monitor_task in done and monitor_task.result():
            cancel_reason = "client_disconnected"
        elif any(t not in done for t in tasks.values()):
            cancel_reason = "run_timeout"

        if cancel_reason:
            for t in tasks.values():
                if not t.done():
                    t.cancel()

        results: list[GenerationResult] = []
        for model_id, task in tasks.items():
            try:
                result = await task
            except asyncio.CancelledError:
                provider_name = model_id.split(":", 1)[0]
                result = GenerationResult(
                    model_id=model_id,
                    provider=provider_map.get(provider_name).name if provider_name in provider_map else provider_name,
                    text=None,
                    usage=None,
                    meta={"cancel_reason": cancel_reason},
                    raw_request=None,
                    raw_response=None,
                    latency_ms=None,
                    error_code="cancelled",
                    error_message=cancel_reason or "Cancelled",
                )
            results.append(result)

        if monitor_task:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task

        return results

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
                raw_request=None,
                raw_response=None,
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
                raw_request=None,
                raw_response=None,
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
                raw_request=None,
                raw_response=None,
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
            raw_request=gen.raw_request,
            raw_response=gen.raw_response,
            error_code=gen.error_code,
            error_message=gen.error_message,
            latency_ms=gen.latency_ms,
            usage=gen.usage,
            meta=gen.meta,
            format_compliance=(gen.meta or {}).get("format_compliance") if gen.meta else None,
            hedge_count=(gen.meta or {}).get("hedge_count") if gen.meta else None,
        )

    def _compare(self, prompt: str, generations: Sequence[GenerationResult]) -> CompareResult:
        usable = [gen for gen in generations if gen.text]
        if len(usable) < 2:
            empty_summary = CompareSummary(
                avg_similarity=1.0,
                most_disagree_pair=None,
                notes="Not enough responses to compare; need at least two non-empty outputs.",
                disagreement_summary={"max_distance": 0.0, "pair": None, "reason": "Insufficient responses"},
            )
            return CompareResult(pairs=[], summary=empty_summary)

        prompt_keywords = extract_keywords(prompt)
        pairs: list[ComparePair] = []
        distance_inputs = []
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                a, b = usable[i], usable[j]
                tokens_a = tokenize(a.text or "")
                tokens_b = tokenize(b.text or "")
                tokens_a_set, tokens_b_set = set(tokens_a), set(tokens_b)
                jaccard_score = jaccard(tokens_a_set, tokens_b_set)
                length_ratio_score = length_ratio(tokens_a, tokens_b)
                keyword_coverage_score = keyword_coverage(prompt_keywords, tokens_a_set, tokens_b_set)
                rouge = rouge_l(a.text or "", b.text or "")
                pairs.append(
                    ComparePair(
                        a=a.model_id,
                        b=b.model_id,
                        token_overlap_jaccard=jaccard_score,
                        length_ratio=length_ratio_score,
                        keyword_coverage=keyword_coverage_score,
                        rouge_l=rouge,
                    )
                )
                distance_inputs.append((a.model_id, b.model_id, rouge, jaccard_score))

        avg_similarity = statistics.mean(p.token_overlap_jaccard for p in pairs) if pairs else 0.0
        sorted_pairs = sorted(pairs, key=lambda p: p.token_overlap_jaccard)
        summary = CompareSummary(
            avg_similarity=avg_similarity,
            most_disagree_pair=sorted_pairs[0] if sorted_pairs else None,
            notes="token_overlap_jaccard: 1.0 = identical; length_ratio: shorter/longer; keyword_coverage vs prompt keywords.",
            disagreement_summary=distance_summary(distance_inputs),
        )
        return CompareResult(pairs=pairs, summary=summary)

    async def _monitor_disconnect(self, client_request: Request | None) -> bool:
        if client_request is None:
            return False
        try:
            while True:
                if await client_request.is_disconnected():
                    return True
                await asyncio.sleep(0.25)
        except Exception:
            return False

    def _persist_run(
        self,
        request_id: str,
        request: EvaluateRequest,
        response: EvaluateResponse,
        canonical: dict,
        canonical_bytes: bytes,
        generations: Sequence[GenerationResult],
        provider_map: dict[str, Provider],
    ) -> None:
        os.makedirs(self._runs_dir, exist_ok=True)
        project_root = Path(__file__).resolve().parents[2]
        provider_info = []
        for gen in generations:
            prov = self._provider_for(gen.provider, provider_map) if gen.provider in provider_map else None
            base_url = getattr(prov, "base_url", None) if prov else None
            retries = getattr(prov, "max_retries", None) if prov else None
            timeout_s = getattr(prov, "timeout", response.params.timeout_s if hasattr(response, "params") else None)
            provider_info.append(
                {
                    "provider_name": gen.provider,
                    "model_id": gen.model_id,
                    "runtime": provider_runtime_info(
                        base_url=base_url,
                        timeout_s=timeout_s if timeout_s is not None else response.params.timeout_s,
                        retries=retries or 0,
                        temperature=response.params.temperature,
                        max_tokens=response.params.max_tokens,
                    ),
                }
            )

        payload = {
            "request_id": request_id,
            "run_hash": response.run_hash,
            "schema_version": self.SCHEMA_VERSION,
            "api_version": response.api_version,
            "timestamp_utc": response.created_at.isoformat() + "Z",
            "canonical_request": canonical,
            "execution_context": {
                "runtime": runtime_context(str(project_root)),
                "providers": provider_info,
            },
            "request": request.model_dump(),
            "response": response.model_dump(mode="json"),
            "raw_generations": [
                {
                    "model_id": gen.model_id,
                    "provider": gen.provider,
                    "raw_request": gen.raw_request,
                    "raw_response": gen.raw_response,
                    "error_code": gen.error_code,
                    "error_message": gen.error_message,
                }
                for gen in generations
            ],
        }
        tmp_path = os.path.join(self._runs_dir, f"{request_id}.json.tmp")
        final_path = os.path.join(self._runs_dir, f"{request_id}.json")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str, sort_keys=True)
        try:
            os.replace(tmp_path, final_path)
        except Exception:
            try:
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.replace(tmp_path, final_path)
            except Exception:
                try:
                    shutil.copyfile(tmp_path, final_path)
                finally:
                    with contextlib.suppress(Exception):
                        os.remove(tmp_path)
                    logging.warning("Fell back to non-atomic write for run %s", request_id)

    def list_runs(self, limit: int = 20, status: str | None = None) -> list[dict]:
        os.makedirs(self._runs_dir, exist_ok=True)
        entries = []
        for fname in sorted(os.listdir(self._runs_dir), reverse=True):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self._runs_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                run_status = data.get("response", {}).get("status")
                if status and run_status != status:
                    continue
                entries.append(
                    {
                        "run_id": data.get("request_id"),
                        "created_at": data.get("response", {}).get("created_at"),
                        "status": run_status,
                        "run_hash": data.get("run_hash"),
                    }
                )
                if len(entries) >= limit:
                    break
            except Exception:
                continue
        return entries

    def get_run(self, run_id: str) -> dict | None:
        path = os.path.join(self._runs_dir, f"{run_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _status(self, results: Sequence[ModelResult]) -> str:
        successes = [r for r in results if r.ok]
        if len(successes) == len(results):
            return "success"
        if successes:
            return "partial"
        return "failed"
