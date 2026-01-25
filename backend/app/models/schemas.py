from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    prompt: str
    models: list[str] | None = Field(default=None, description="Subset of models to query. Defaults to all.")


class ModelEvaluation(BaseModel):
    model: str
    response: str
    latency_ms: float
    created_at: datetime


class EvaluationMetrics(BaseModel):
    agreement: float = Field(ge=0, le=1)
    unique_responses: int
    average_length: float
    similarity: float = Field(ge=0, le=1)
    evaluated_at: datetime


class SynthesizedResponse(BaseModel):
    strategy: Literal["consensus", "longest", "first"]
    response: str
    rationale: str


class EvaluateResponse(BaseModel):
    prompt: str
    evaluations: list[ModelEvaluation]
    metrics: EvaluationMetrics
    synthesis: SynthesizedResponse
