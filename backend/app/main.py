import logging
import os
from pathlib import Path
from dataclasses import asdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from dotenv import load_dotenv

from app.evaluation.pipeline import EvaluationEngine
from app.models.schemas import EvaluateRequest, EvaluateResponse
from app.providers.registry import ProviderRegistry
from app.providers.mock import MockProvider
from app.providers.openai import OpenAIProvider
from app.synthesis.aggregator import MultiStrategySynthesizer


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
    synthesizer = MultiStrategySynthesizer()
    registry = ProviderRegistry()
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Providers
    registry.register("mock", lambda: MockProvider())
    registry.register("openai", lambda: OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY")))
    # Gemini disabled per request; not registered.

    engine = EvaluationEngine(registry=registry, synthesizer=synthesizer)

    api = FastAPI(title="PRISM", version="0.3.0")
    api.state.engine = engine

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
    async def models() -> dict:
        models = registry.list_models()
        grouped: dict[str, list[dict]] = {}
        for m in models:
            grouped.setdefault(m.provider, []).append(asdict(m))
        return {"models": [asdict(m) for m in models], "grouped": grouped}

    @api.options("/models")
    async def models_options(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/evaluate", response_model=EvaluateResponse)
    async def evaluate(request: EvaluateRequest, http_request: Request) -> EvaluateResponse:
        try:
            return await engine.evaluate(request=request, client_request=http_request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.options("/evaluate")
    async def evaluate_options(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/runs")
    async def list_runs(limit: int = 20, status: str | None = None) -> dict:
        return {"runs": engine.list_runs(limit=limit, status=status)}

    @api.get("/runs/{run_id}")
    async def get_run(run_id: str) -> dict:
        run = engine.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

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
