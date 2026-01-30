import json
import os
import httpx
import pytest

from app.main import build_app
from app.models.schemas import EvaluateRequest
from app.utils.canonical import canonicalize_request
from app.utils.metrics import rouge_l


def test_canonicalization_hash_stable() -> None:
    req1 = EvaluateRequest(prompt="  hello world  ", models=["b", "a"], temperature=0.1, max_tokens=10)
    req2 = EvaluateRequest(prompt="hello world", models=["a", "b"], temperature=0.1, max_tokens=10)
    _, _, hash1 = canonicalize_request(req1)
    _, _, hash2 = canonicalize_request(req2)
    assert hash1 == hash2


def test_rouge_l_simple() -> None:
    score = rouge_l("a b c d", "a b c")
    assert abs(score - 0.75) < 1e-6


@pytest.mark.asyncio
async def test_runs_endpoints(tmp_path) -> None:
    # Build app and repoint runs directory
    app = build_app()
    app.state.engine._runs_dir = str(tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # create a fake run file
        sample = {"request_id": "abc", "response": {"created_at": "2024-01-01T00:00:00Z", "status": "success"}, "run_hash": "h"}
        path = os.path.join(tmp_path, "abc.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sample, f)

        list_resp = await client.get("/runs")
        assert list_resp.status_code == 200
        runs = list_resp.json()["runs"]
        assert len(runs) == 1
        assert runs[0]["run_id"] == "abc"

        get_resp = await client.get("/runs/abc")
        assert get_resp.status_code == 200
        assert get_resp.json()["request_id"] == "abc"
