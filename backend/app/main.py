from fastapi import FastAPI, HTTPException

from app.evaluation.pipeline import EvaluationEngine
from app.llms.mock import MockEchoClient, MockReasonerClient
from app.models.schemas import EvaluateRequest, EvaluateResponse
from app.synthesis.aggregator import SimpleSynthesizer


def build_app() -> FastAPI:
    """
    Construct the FastAPI application and wire dependencies.
    This keeps creation side-effect free for easier testing.
    """
    synthesizer = SimpleSynthesizer()
    clients = [
        MockEchoClient(),
        MockReasonerClient(),
    ]
    engine = EvaluationEngine(clients=clients, synthesizer=synthesizer)

    api = FastAPI(title="PRISM", version="0.1.0")

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/evaluate", response_model=EvaluateResponse)
    async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
        try:
            return await engine.evaluate(prompt=request.prompt, model_names=request.models)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return api


app = build_app()
