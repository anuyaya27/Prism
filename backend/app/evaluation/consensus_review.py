import asyncio
import contextlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from app.models.schemas import (
    ConsensusDisagreement,
    ConsensusModelNote,
    ConsensusReviewModelOutput,
    ConsensusReviewRequest,
    ConsensusReviewResponse,
)
from app.utils.redact import sanitize_raw_io
from app.utils.runtime import runtime_context


class ConsensusReviewEngine:
    """
    Round 2 review engine that judges successful non-mock Round 1 outputs with a dedicated OpenAI call.
    """

    def __init__(self, runs_dir: str = "backend/runs"):
        self._runs_dir = runs_dir
        self._judge_timeout_s = float(os.getenv("PRISM_CONSENSUS_TIMEOUT_S", "30"))
        self._judge_retries = int(os.getenv("PRISM_CONSENSUS_RETRIES", "1"))
        self._openai_model = os.getenv("PRISM_CONSENSUS_MODEL", "gpt-4o-mini")
        self._openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        self._openai_api_key = os.getenv("OPENAI_API_KEY")

    def _eligible_outputs(self, outputs: list[ConsensusReviewModelOutput]) -> list[ConsensusReviewModelOutput]:
        return [
            output
            for output in outputs
            if output.status == "success"
            and bool((output.text or "").strip())
            and output.provider != "mock"
            and not output.model_id.startswith("mock:")
        ]

    async def review(self, request: ConsensusReviewRequest) -> ConsensusReviewResponse:
        eligible = self._eligible_outputs(request.model_outputs)
        if len(eligible) < 2:
            raise ValueError("Consensus review requires at least 2 successful non-mock model outputs.")
        if not self._openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for consensus review.")

        review_id = uuid4().hex
        judged_models = [item.model_id for item in eligible]
        prompt = self._build_prompt(request.original_prompt, eligible)

        response_payload: dict[str, Any] | None = None
        raw_request = sanitize_raw_io(
            url=self._openai_base_url,
            headers={"Authorization": f"Bearer {self._openai_api_key}", "Content-Type": "application/json"},
            body={
                "model": self._openai_model,
                "temperature": 0.2,
                "max_tokens": 1400,
                "messages": [{"role": "system", "content": "consensus_judge"}, {"role": "user", "content": prompt}],
            },
        )

        last_error: str | None = None
        for attempt in range(self._judge_retries + 1):
            try:
                response_payload = await self._call_judge(prompt=prompt)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                await self._sleep_backoff(attempt)

        if response_payload is None:
            fallback = self._fallback_review(review_id=review_id, judged_models=judged_models, reason=last_error or "")
            self._persist_review(
                review=fallback,
                request=request,
                judged_outputs=eligible,
                raw_judge_response={"error": last_error, "raw_request": raw_request},
            )
            return fallback

        parsed, parse_error = self._parse_judge_payload(response_payload)
        if parsed is None:
            fallback = self._fallback_review(review_id=review_id, judged_models=judged_models, reason=parse_error or "")
            fallback.raw_judge_response = sanitize_raw_io(body=response_payload)
            self._persist_review(
                review=fallback,
                request=request,
                judged_outputs=eligible,
                raw_judge_response={"raw_request": raw_request, "raw_response": sanitize_raw_io(body=response_payload)},
            )
            return fallback

        parsed.review_id = review_id
        parsed.judged_models = judged_models
        parsed.raw_judge_response = sanitize_raw_io(body=response_payload)
        self._persist_review(
            review=parsed,
            request=request,
            judged_outputs=eligible,
            raw_judge_response={"raw_request": raw_request, "raw_response": sanitize_raw_io(body=response_payload)},
        )
        return parsed

    async def _call_judge(self, *, prompt: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._openai_api_key}", "Content-Type": "application/json"}
        body = {
            "model": self._openai_model,
            "temperature": 0.2,
            "max_tokens": 1400,
            "messages": [
                {"role": "system", "content": "You are a strict consensus judge for model outputs."},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self._judge_timeout_s) as client:
            response = await client.post(self._openai_base_url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return {"completion": content, "usage": data.get("usage"), "model": data.get("model")}

    def _parse_judge_payload(self, payload: dict[str, Any]) -> tuple[ConsensusReviewResponse | None, str | None]:
        completion = (payload.get("completion") or "").strip()
        if not completion:
            return None, "Empty judge completion"

        parsed = self._parse_json_text(completion)
        if parsed is None:
            repaired = self._repair_json_text(completion)
            parsed = self._parse_json_text(repaired) if repaired else None
        if parsed is None:
            return None, "Judge output could not be parsed as JSON"

        try:
            response = ConsensusReviewResponse.model_validate(
                {
                    "review_id": "",
                    "judged_models": [],
                    "summary": parsed.get("summary", ""),
                    "final_answer": parsed.get("final_answer", ""),
                    "per_model_notes": parsed.get("per_model_notes", {}),
                    "key_takeaways": parsed.get("key_takeaways", []),
                    "disagreements": parsed.get("disagreements", []),
                    "confidence": parsed.get("confidence"),
                    "raw_judge_response": None,
                }
            )
            return response, None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    @staticmethod
    def _parse_json_text(text: str) -> dict[str, Any] | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json\n", "", 1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = cleaned[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _repair_json_text(text: str) -> str | None:
        # Single repair attempt: trim to first balanced object and normalize smart quotes.
        normalized = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return normalized[start : end + 1]

    @staticmethod
    def _build_prompt(original_prompt: str, outputs: list[ConsensusReviewModelOutput]) -> str:
        # Prompt location: this method. It enforces strict JSON and explicitly asks for hallucination checks.
        answer_blocks = []
        for output in outputs:
            answer_blocks.append(
                f"MODEL_ID: {output.model_id}\nPROVIDER: {output.provider}\nLATENCY_MS: {output.latency_ms}\nANSWER:\n{output.text}\n"
            )
        joined_answers = "\n---\n".join(answer_blocks)
        return (
            "You are running Round 2 Consensus Review on model answers.\n"
            "Task requirements:\n"
            "1) Compare answers for correctness and logic.\n"
            "2) Explicitly call out hallucinations or unsupported claims.\n"
            "3) Pick best parts and produce one consolidated final answer.\n"
            "4) Return STRICT JSON only, no markdown, no prose outside JSON.\n\n"
            "Required JSON shape:\n"
            "{\n"
            '  "summary": "short text",\n'
            '  "final_answer": "consolidated best answer",\n'
            '  "per_model_notes": {\n'
            '    "<model_id>": {\n'
            '      "strengths": ["..."],\n'
            '      "weaknesses": ["..."],\n'
            '      "issues": ["hallucination/unsupported claim/etc"]\n'
            "    }\n"
            "  },\n"
            '  "key_takeaways": ["..."],\n'
            '  "disagreements": [{"topic":"...", "models_involved":["..."], "resolution":"..."}],\n'
            '  "confidence": "low|medium|high"\n'
            "}\n\n"
            f"ORIGINAL_PROMPT:\n{original_prompt}\n\n"
            f"MODEL_OUTPUTS:\n{joined_answers}\n"
        )

    @staticmethod
    async def _sleep_backoff(attempt: int) -> None:
        await asyncio.sleep(0.4 * (attempt + 1))

    def _fallback_review(self, *, review_id: str, judged_models: list[str], reason: str) -> ConsensusReviewResponse:
        return ConsensusReviewResponse(
            review_id=review_id,
            judged_models=judged_models,
            summary="Consensus review fallback due to judge parse/runtime issue.",
            final_answer="Unable to produce a high-confidence consensus answer from the judge output.",
            per_model_notes={mid: ConsensusModelNote(strengths=[], weaknesses=[], issues=[reason or "unknown_error"]) for mid in judged_models},
            key_takeaways=["Round 2 review failed; inspect backend logs and raw_judge_response."],
            disagreements=[ConsensusDisagreement(topic="review_runtime", models_involved=judged_models, resolution="fallback_used")],
            confidence="low",
            raw_judge_response=None,
        )

    def _persist_review(
        self,
        *,
        review: ConsensusReviewResponse,
        request: ConsensusReviewRequest,
        judged_outputs: list[ConsensusReviewModelOutput],
        raw_judge_response: dict[str, Any] | None,
    ) -> None:
        os.makedirs(self._runs_dir, exist_ok=True)
        project_root = Path(__file__).resolve().parents[2]
        payload = {
            "review_id": review.review_id,
            "run_id": request.run_id,
            "schema_version": "1.0.0",
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "execution_context": {"runtime": runtime_context(str(project_root))},
            "request": request.model_dump(mode="json"),
            "judged_outputs": [item.model_dump(mode="json") for item in judged_outputs],
            "response": review.model_dump(mode="json"),
            "raw_judge_response": raw_judge_response,
        }
        suffix = f".consensus_review.{review.review_id}.json"
        base_name = request.run_id if request.run_id else review.review_id
        tmp_path = os.path.join(self._runs_dir, f"{base_name}{suffix}.tmp")
        final_path = os.path.join(self._runs_dir, f"{base_name}{suffix}")
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, default=str, sort_keys=True)
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
