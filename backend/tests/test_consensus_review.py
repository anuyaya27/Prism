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


def test_consensus_review_requires_two_non_mock_successes() -> None:
    payload = {
        "original_prompt": "Prompt",
        "run_id": "abc",
        "model_outputs": [
            {"model_id": "mock:echo", "provider": "mock", "text": "x", "latency_ms": 1, "status": "success"},
            {"model_id": "openai:gpt-4o-mini", "provider": "openai", "text": "", "latency_ms": 2, "status": "success"},
        ],
    }
    response = asyncio.run(_request("POST", "/consensus_review", json=payload))
    assert response.status_code == 400
    assert "at least 2 successful non-mock" in response.json()["detail"]


def test_consensus_review_requires_openai_key_after_filtering_mocks() -> None:
    payload = {
        "original_prompt": "Prompt",
        "run_id": "abc",
        "model_outputs": [
            {"model_id": "openai:gpt-4o-mini", "provider": "openai", "text": "a", "latency_ms": 1, "status": "success"},
            {"model_id": "gemini:2.5-flash", "provider": "gemini", "text": "b", "latency_ms": 2, "status": "success"},
            {"model_id": "mock:echo", "provider": "mock", "text": "c", "latency_ms": 3, "status": "success"},
        ],
    }
    response = asyncio.run(_request("POST", "/consensus_review", json=payload))
    assert response.status_code == 400
    assert "OPENAI_API_KEY" in response.json()["detail"]
