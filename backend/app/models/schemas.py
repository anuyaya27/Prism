from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    prompt: str
    models: list[str] | None = Field(default=None, description="Subset of models to query. Defaults to all available.")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Unused for mocks; forwarded when supported.")
    max_tokens: int = Field(default=512, ge=1, le=4096, description="Upper bound for generated tokens when supported.")
    timeout_s: float = Field(default=15.0, ge=1.0, le=120.0, description="Per-model timeout (seconds).")
    synthesis_method: Literal["longest_nonempty", "consensus_overlap", "best_of_n"] = Field(
        default="longest_nonempty", description="Synthesis strategy to apply to results."
    )


class EvaluateParams(BaseModel):
    models: list[str]
    temperature: float
    max_tokens: int
    timeout_s: float
    synthesis_method: Literal["longest_nonempty", "consensus_overlap", "best_of_n"]


class ModelResult(BaseModel):
    model: str
    provider: str
    ok: bool
    status: Literal["success", "error", "timeout"]
    text: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: float | None = None
    usage: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class ComparePair(BaseModel):
    a: str
    b: str
    token_overlap_jaccard: float
    length_ratio: float
    keyword_coverage: float


class CompareSummary(BaseModel):
    avg_similarity: float
    most_disagree_pair: ComparePair | None = None
    notes: str | None = None


class CompareResult(BaseModel):
    pairs: list[ComparePair]
    summary: CompareSummary


class SynthesisPayload(BaseModel):
    ok: bool
    method: Literal["longest_nonempty", "consensus_overlap", "best_of_n"]
    text: str | None
    rationale: str | None = None


class EvaluateResponse(BaseModel):
    request_id: str
    created_at: datetime
    prompt: str
    params: EvaluateParams
    results: list[ModelResult]
    synthesis: SynthesisPayload
    compare: CompareResult
