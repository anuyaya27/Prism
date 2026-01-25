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

### Environment variables
Create a `.env` file at the repo root (already git-ignored). It is auto-loaded on startup:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```
See `.env.example` for the template.

## Example request
```bash
curl -X POST http://localhost:8000/evaluate ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"List three benefits of testing\", \"models\": [\"mock:echo\", \"mock:pseudo\"]}"
```

Response fields include per-model generations, metrics, and the synthesized answer with its selection rationale.
Discover available models at `GET /models`.

### Response contract (stable)
- `run_id`: unique identifier for the evaluation.
- `request`: echoed request with defaults (prompt, models, temperature, max_tokens, timeout_s).
- `responses[]`: `{ id, provider, model, text, latency_ms, usage, finish_reason, error, created_at }`
- `metrics`: agreement, unique_responses, average_length, similarity, semantic_similarity.
- `synthesis`: `{ strategy, response, rationale, explain }` (deterministic, rule-based).

## Tests
```bash
set PYTHONPATH=backend
pytest backend/tests -q
```

## Extending
- Implement new providers by subclassing `LLMClient` in `backend/app/llms/`.
- Add metrics in `backend/app/evaluation/pipeline.py`.
- Experiment with synthesis strategies in `backend/app/synthesis/`.

### Real model support
- OpenAI: set `OPENAI_API_KEY` and use model IDs like `openai:gpt-4o-mini`.
- Gemini: set `GEMINI_API_KEY` and use `gemini:1.5-flash`.
- Mock models remain available as `mock:echo` and `mock:pseudo` (alias of `mock:reasoner`).

PRISM is intentionally minimal at this stage—no auth, databases, or external infra. Build on it as evaluation needs grow.

## Frontend quickstart
Prereqs: Node 18+.
```bash
cd frontend
npm install
npm run dev  # starts Vite on http://localhost:5173
```
The UI auto-fetches `/models`, lets you pick enabled models, run `/evaluate`, and shows per-model outputs, metrics, and the synthesized answer.

## Demo flow
1) Set API keys in `.env` (optional for real models).  
2) Start backend: `PYTHONPATH=backend uvicorn app.main:app --reload --app-dir backend`.  
3) Start frontend: `cd frontend && npm install && npm run dev`.  
4) Visit http://localhost:5173, enter a prompt, select models, run, and inspect responses/metrics/synthesis.  
5) Use `GET /models` to verify which providers are enabled.
