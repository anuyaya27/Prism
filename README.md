# PRISM (Parallel Reasoning & Inference Synthesis Machine)

PRISM is a research-grade system for running the same prompt across multiple LLMs, comparing their outputs, and synthesizing a transparent final response. It favors clarity, determinism, and extensibility over production complexity.

## Why it exists
- Compare model behaviors side-by-side for a given prompt.
- Quantify agreement/divergence with lightweight, inspectable metrics.
- Produce a rule-based synthesized answer with a clear rationale.
- Serve as a foundation for experimenting with evaluation strategies and model mixtures.

## How it works (systems view)
1. FastAPI receives an `/evaluate` request containing a prompt and optional model list.
2. The evaluation engine fans the prompt out to each `LLMClient` asynchronously.
3. Raw generations and timing metadata are captured.
4. Metrics (agreement ratio, uniqueness, length, Jaccard similarity) are computed deterministically.
5. A rule-based synthesizer returns either the majority response or, if none exists, the longest response as a coverage proxy, along with its rationale.

## Folder structure
- `backend/` – FastAPI app, LLM abstractions, evaluation pipeline, synthesis strategies, tests.
- `frontend/` – Placeholder React/TypeScript structure; UI will be layered on after backend stabilization.
- `docs/` – Architecture, evaluation methodology, and roadmap notes.

## Backend quickstart
Prereqs: Python 3.11+, `pip`.

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r backend/requirements.txt

# run the API (app dir ensures imports resolve)
set PYTHONPATH=backend  # PowerShell: $env:PYTHONPATH='backend'
uvicorn app.main:app --reload --app-dir backend
```

Open http://localhost:8000/docs to try the interactive API.

## Example request
```bash
curl -X POST http://localhost:8000/evaluate ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"List three benefits of testing\", \"models\": [\"mock-echo\", \"mock-reasoner\"]}"
```

Response fields include per-model generations, metrics, and the synthesized answer with its selection rationale.

## Tests
```bash
set PYTHONPATH=backend
pytest backend/tests -q
```

## Extending
- Implement new providers by subclassing `LLMClient` in `backend/app/llms/`.
- Add metrics in `backend/app/evaluation/pipeline.py`.
- Experiment with synthesis strategies in `backend/app/synthesis/`.

PRISM is intentionally minimal at this stage—no auth, databases, or external infra. Build on it as evaluation needs grow.
