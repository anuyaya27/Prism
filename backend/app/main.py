import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from dotenv import load_dotenv

from app.evaluation.pipeline import EvaluationEngine
from app.llms.gemini_client import GeminiClient
from app.llms.mock import MockEchoClient, MockReasonerClient
from app.llms.openai_client import OpenAIClient
from app.llms.registry import ModelRegistry
from app.models.schemas import EvaluateRequest, EvaluateResponse
from app.synthesis.aggregator import SimpleSynthesizer


def load_environment() -> None:
    """
    Load environment variables from a project-root .env file if present.
    Safe to call multiple times; no effect if file is missing.
    """
    project_root = Path(__file__).resolve().parents[2]
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)


def build_app() -> FastAPI:
    """
    Construct the FastAPI application and wire dependencies.
    This keeps creation side-effect free for easier testing.
    """
    load_environment()
    synthesizer = SimpleSynthesizer()
    registry = ModelRegistry()
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Mock models always available
    registry.register(
        "mock:echo",
        lambda: MockEchoClient(),
        provider="mock",
        enabled=True,
        description="Deterministic echo model",
    )
    registry.register(
        "mock:reasoner",
        lambda: MockReasonerClient(),
        provider="mock",
        enabled=True,
        description="Pseudo reasoning model",
    )
    # Backward compatibility alias
    registry.register(
        "mock:pseudo",
        lambda: MockReasonerClient(),
        provider="mock",
        enabled=True,
        description="Alias of mock:reasoner",
    )

    # Real providers (enabled only if keys are present)
    openai_key = os.getenv("OPENAI_API_KEY")
    registry.register(
        "openai:gpt-4o-mini",
        lambda: OpenAIClient(model="gpt-4o-mini", api_key=openai_key),
        provider="openai",
        enabled=bool(openai_key),
        description="OpenAI GPT-4o-mini",
        disabled_reason=None if openai_key else "OPENAI_API_KEY missing",
    )

    gemini_key = os.getenv("GEMINI_API_KEY")
    registry.register(
        "gemini:1.5-flash",
        lambda: GeminiClient(model="gemini-1.5-flash", api_key=gemini_key),
        provider="gemini",
        enabled=bool(gemini_key),
        description="Gemini 1.5 Flash",
        disabled_reason=None if gemini_key else "GEMINI_API_KEY missing",
    )

    engine = EvaluationEngine(registry=registry, synthesizer=synthesizer)

    api = FastAPI(title="PRISM", version="0.3.0")

    allow_methods = ["*"]
    allow_headers = ["*"]

    api.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )

    @api.on_event("startup")
    async def log_startup() -> None:
        route_summaries = []
        for route in api.routes:
            if isinstance(route, APIRoute):
                methods = ",".join(sorted(route.methods))
                route_summaries.append(f"{methods} {route.path}")
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        logging.info(
            "PRISM is running with CORS enabled. Origins: %s; Methods: %s; Headers: %s",
            ", ".join(allowed_origins),
            ", ".join(allow_methods),
            ", ".join(allow_headers),
        )
        logging.info("Available routes: %s", "; ".join(route_summaries))

    @api.get("/")
    async def root() -> dict[str, str]:
        return {
            "message": "PRISM API. Use POST /evaluate to run prompts. Interactive docs at /docs.",
        }

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/debug/cors")
    async def cors_debug(request: Request) -> dict[str, object]:
        origin = request.headers.get("origin")
        return {
            "origin": origin,
            "allowed_origins": allowed_origins,
            "version": api.version,
            "base_url": str(request.base_url),
        }

    @api.get("/debug/ping")
    async def debug_ping(request: Request) -> dict[str, object]:
        origin = request.headers.get("origin")
        host = request.headers.get("host")
        return {"ok": True, "origin": origin, "host": host, "version": api.version}

    @api.get("/models")
    async def models() -> list[dict]:
        return registry.list_models()

    @api.options("/models")
    async def models_options(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/evaluate", response_model=EvaluateResponse)
    async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
        try:
            return await engine.evaluate(request=request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.options("/evaluate")
    async def evaluate_options(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    return api


app = build_app()


if __name__ == "__main__":
    import uvicorn

    # Running via `python backend/app/main.py` for convenience in dev environments (Windows-friendly).
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
