import argparse
import json
import os
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, List

import httpx

API_DEFAULT = os.getenv("PRISM_API_BASE_URL") or os.getenv("VITE_API_BASE_URL") or "http://127.0.0.1:8000"
RUNS_DIR = pathlib.Path("demo_outputs")
PACKS_DIR = pathlib.Path("prompt_packs")


def slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")


def load_pack(pack_name: str) -> Dict[str, Any]:
    path = PACKS_DIR / f"{pack_name}.json"
    if not path.exists():
        raise SystemExit(f"Pack not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_prompt(client: httpx.Client, prompt: Dict[str, Any], models: List[str], out_dir: pathlib.Path) -> None:
    payload = {
        "prompt": prompt["prompt"],
        "models": models,
        "synthesis_method": "best_of_n",
    }
    resp = client.post(f"{API_DEFAULT}/evaluate", json=payload, timeout=60)
    resp.raise_for_status()
    body = resp.json()
    run_id = body.get("request_id")
    run_hash = body.get("run_hash")
    status = body.get("status")
    synthesis = body.get("synthesis", {})
    compare = body.get("compare", {})
    summary = compare.get("summary", {})
    avg_latency = None
    if body.get("results"):
        latencies = [r.get("latency_ms") for r in body["results"] if r.get("latency_ms") is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
    print(f"- {prompt['id']}: run_id={run_id} hash={run_hash} status={status} latency={avg_latency}ms strategy={synthesis.get('strategy_id')} conf={synthesis.get('confidence')}")
    if summary:
        ds = summary.get("disagreement_summary")
        if ds:
            print(f"    disagreement: max_dist={ds.get('max_distance')} pair={ds.get('pair')} reason={ds.get('reason')}")
    slug = slugify(prompt["id"])
    with open(out_dir / f"{slug}.json", "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PRISM demo prompts")
    parser.add_argument("--pack", default="core", help="Prompt pack name (without .json)")
    parser.add_argument("--models", nargs="*", default=["mock:echo", "mock:pseudo"], help="Models to evaluate")
    args = parser.parse_args()

    pack = load_pack(args.pack)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%SZ")
    out_dir = RUNS_DIR / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        for prompt in pack["prompts"]:
            run_prompt(client, prompt, args.models, out_dir)
            time.sleep(0.1)

    print(f"Saved outputs to {out_dir}")


if __name__ == "__main__":
    main()
