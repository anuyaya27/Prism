import pytest
from fastapi.testclient import TestClient

from app.main import build_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = build_app()
    return TestClient(app)


def test_evaluate_endpoint_returns_results(client: TestClient) -> None:
    payload = {"prompt": "Summarize the value of testing.", "models": ["mock-echo", "mock-reasoner"]}
    response = client.post("/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["prompt"] == payload["prompt"]
    assert len(body["evaluations"]) == 2
    assert body["metrics"]["agreement"] >= 0
    assert body["synthesis"]["response"]
