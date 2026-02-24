import argparse
import json
import os
import pathlib
from typing import Any, Dict, List

import httpx

DEFAULT_API = os.getenv("PRISM_API_BASE_URL") or os.getenv("VITE_API_BASE_URL") or "http://127.0.0.1:8000"
PACKS_DIR = pathlib.Path("prompt_packs")
BASELINE_DIR = pathlib.Path("baselines")
BASELINE_DIR.mkdir(exist_ok=True)


def slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")


def load_pack(pack_name: str) -> Dict[str, Any]:
    path = PACKS_DIR / f"{pack_name}.json"
    if not path.exists():
        raise SystemExit(f"Pack not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def call_eval(client: httpx.Client, prompt: Dict[str, Any], models: List[str]) -> Dict[str, Any]:
    payload = {"prompt": prompt["prompt"], "models": models, "synthesis_method": "best_of_n"}
    r = client.post(f"{DEFAULT_API}/evaluate", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def write_baseline(pack_id: str, results: List[Dict[str, Any]]) -> None:
    path = BASELINE_DIR / f"{pack_id}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(res) + "\n")
    print(f"Baseline written to {path}")


def load_baseline(pack_id: str) -> List[Dict[str, Any]]:
    path = BASELINE_DIR / f"{pack_id}.jsonl"
    if not path.exists():
        raise SystemExit(f"Baseline not found: {path}")
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def compare(current: List[Dict[str, Any]], baseline: List[Dict[str, Any]], format_drop: float = 0.2) -> List[str]:
    issues: List[str] = []
    baseline_map = {item["request_id"]: item for item in baseline if "request_id" in item}
    for res in current:
        rid = res.get("request_id")
        if not rid:
            issues.append("missing request_id")
            continue
        if rid not in baseline_map:
            continue
        base = baseline_map[rid]
        # schema checks
        for field in ["synthesis", "compare", "results"]:
            if field not in res:
                issues.append(f"{rid}: missing field {field}")
        # disagreement summary
        summary = res.get("compare", {}).get("summary", {})
        if not summary.get("disagreement_summary"):
            issues.append(f"{rid}: missing disagreement_summary")
        # format compliance
        fmt_current = min((r.get("format_compliance", 1.0) or 1.0) for r in res.get("results", []) if r.get("format_compliance") is not None) if res.get("results") else 1.0
        fmt_base = min((r.get("format_compliance", 1.0) or 1.0) for r in base.get("results", []) if r.get("format_compliance") is not None) if base.get("results") else 1.0
        if fmt_base - fmt_current > format_drop:
            issues.append(f"{rid}: format_compliance dropped by {fmt_base - fmt_current:.2f}")
    return issues


def run_pack(pack_id: str, models: List[str], write_base: bool, compare_base: bool) -> int:
    pack = load_pack(pack_id)
    results = []
    with httpx.Client() as client:
        for prompt in pack["prompts"]:
            res = call_eval(client, prompt, models)
            results.append(res)
    if write_base:
        write_baseline(pack_id, results)
        return 0
    if compare_base:
        baseline = load_baseline(pack_id)
        issues = compare(results, baseline)
        if issues:
            print("Regression detected:")
            for i in issues:
                print(f" - {i}")
            return 1
        print("No regressions detected")
    else:
        print(json.dumps(results, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="PRISM regression harness")
    parser.add_argument("pack", help="Pack name (without .json)")
    parser.add_argument("--models", nargs="*", default=["mock:echo", "mock:pseudo"], help="Models list")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()
    code = run_pack(args.pack, args.models, args.write_baseline, args.compare)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
