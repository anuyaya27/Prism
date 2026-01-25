from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    prompt: str
    models: list[str] | None = Field(default=None, description="Subset of models to query. Defaults to all.")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Unused for mocks; forwarded when supported.")
    max_tokens: int = Field(default=512, ge=1, le=4096, description="Upper bound for generated tokens when supported.")
    timeout_s: float = Field(default=15.0, ge=1.0, le=120.0, description="Per-request timeout to external providers.")


class ModelResponse(BaseModel):
    id: str  # model identifier requested
    provider: str | None
    model: str | None
    text: str
    latency_ms: float
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    error: str | None = None
    created_at: datetime


class EvaluationMetrics(BaseModel):
    agreement: float = Field(ge=0, le=1)
    unique_responses: int
    average_length: float
    similarity: float = Field(ge=0, le=1)
    semantic_similarity: float | None = Field(default=None, ge=0, le=1)
    evaluated_at: datetime


class SynthesizedResponse(BaseModel):
    strategy: Literal["consensus", "longest", "first"]
    response: str
    rationale: str
    explain: str


class EvaluateResponse(BaseModel):
    run_id: str
    request: EvaluateRequest
    responses: list[ModelResponse]
    metrics: EvaluationMetrics
    synthesis: SynthesizedResponse
