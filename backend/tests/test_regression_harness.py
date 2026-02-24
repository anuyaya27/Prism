import json
import pathlib
from typing import Any

from prism_cli.regression import load_pack, compare


def test_load_pack_core():
    pack = load_pack("core")
    assert pack["id"] == "core"
    assert len(pack["prompts"]) >= 8
    assert all("prompt" in p for p in pack["prompts"])


def test_compare_detects_format_drop():
    base = [{
        "request_id": "r1",
        "results": [{"format_compliance": 1.0}],
        "compare": {"summary": {"disagreement_summary": {"max_distance": 0.1}}},
    }]
    curr = [{
        "request_id": "r1",
        "results": [{"format_compliance": 0.6}],
        "compare": {"summary": {"disagreement_summary": {"max_distance": 0.1}}},
    }]
    issues = compare(curr, base, format_drop=0.2)
    assert issues, "Regression should be detected"
