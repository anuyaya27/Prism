import pytest
from fastapi.testclient import TestClient

from app.main import build_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = build_app()
    return TestClient(app)


def test_evaluate_endpoint_returns_results(client: TestClient) -> None:
    payload = {"prompt": "Summarize the value of testing.", "models": ["mock:echo", "mock:pseudo"]}
    response = client.post("/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["prompt"] == payload["prompt"]
    assert len(body["results"]) == 2
    assert all("ok" in r for r in body["results"])
    assert "synthesis" in body and "method" in body["synthesis"]
    assert "compare" in body and "pairs" in body["compare"]


def test_models_endpoint_lists_alias_and_enabled(client: TestClient) -> None:
    response = client.get("/models")
    assert response.status_code == 200
    models = response.json()
    ids = {m["id"] for m in models}
    assert "mock:echo" in ids
    assert "mock:pseudo" in ids
    # alias should be enabled
    pseudo = next(m for m in models if m["id"] == "mock:pseudo")
    assert pseudo["enabled"] is True
