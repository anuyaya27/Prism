import asyncio
import httpx
import pytest

from app.main import build_app


async def _request(method: str, path: str, **kwargs):
    app = build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


@pytest.fixture(autouse=True)
def clear_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")


def test_models_endpoint_includes_availability() -> None:
    response = asyncio.run(_request("GET", "/models"))
    assert response.status_code == 200
    models = response.json()["models"]
    model_map = {m["id"]: m for m in models}
    assert "mock:echo" in model_map
    assert model_map["mock:echo"]["available"] is True
    assert model_map["openai:gpt-4o-mini"]["available"] is False
    assert "OPENAI_API_KEY" in (model_map["openai:gpt-4o-mini"]["reason"] or "")


def test_evaluate_returns_partial_success() -> None:
    payload = {
        "prompt": "Summarize the value of testing.",
        "models": ["mock:echo", "openai:gpt-4o-mini"],
        "synthesis_method": "longest_nonempty",
    }
    response = asyncio.run(_request("POST", "/evaluate", json=payload))
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["created_at"]
    assert len(body["results"]) == 2
    statuses = {r["model"]: r["status"] for r in body["results"]}
    assert statuses["mock:echo"] == "success"
    assert body["synthesis"]["text"] is not None


def test_compare_and_synthesis_are_present() -> None:
    payload = {
        "prompt": "List two benefits of unit testing.",
        "models": ["mock:echo", "mock:pseudo"],
        "synthesis_method": "consensus_overlap",
    }
    response = asyncio.run(_request("POST", "/evaluate", json=payload))
    assert response.status_code == 200
    body = response.json()
    assert body["compare"]["summary"]["avg_similarity"] >= 0
    assert body["synthesis"]["method"] in {"consensus_overlap", "longest_nonempty"}
