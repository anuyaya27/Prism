from typing import Literal

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    prompt: str
    models: list[str] | None = Field(default=None, description="Subset of models to query. Defaults to all.")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Unused for mocks; forwarded when supported.")
    max_tokens: int = Field(default=512, ge=1, le=4096, description="Upper bound for generated tokens when supported.")
    timeout_s: float = Field(default=15.0, ge=1.0, le=120.0, description="Per-request timeout to external providers.")


class ModelResult(BaseModel):
    model: str
    ok: bool
    text: str | None = None
    error: str | None = None
    latency_ms: float | None = None
    status: Literal["success", "error", "timeout"] = "success"
    provider: str | None = None


class SynthesisPayload(BaseModel):
    ok: bool
    text: str | None
    method: str
    rationale: str | None = None


class ComparePair(BaseModel):
    a: str
    b: str
    score: float


class CompareResult(BaseModel):
    pairs: list[ComparePair]
    note: str | None = None


class EvaluateResponse(BaseModel):
    request_id: str
    prompt: str
    results: list[ModelResult]
    synthesis: SynthesisPayload
    compare: CompareResult
