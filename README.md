# PRISM (Parallel Reasoning & Inference Synthesis Machine)

PRISM runs a single prompt across multiple LLMs, compares their outputs, and synthesizes a transparent final response. Run everything locally—no GitHub Pages needed.

## Run locally

### Prerequisites
- Node.js 20+
- Python 3.10+ (3.11 recommended)

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

set PYTHONPATH=backend         # PowerShell: $env:PYTHONPATH='backend'
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000/docs to exercise the API.

Create `../.env` (or copy `.env.example`) if you want real models:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

### Frontend (Vite + React)
```bash
cd frontend
npm install

echo VITE_API_BASE_URL=http://127.0.0.1:8000 > .env.local

npm run dev   # http://localhost:5173
```

### Run both together
- Terminal 1: start the backend (uvicorn command above).
- Terminal 2: start the frontend (`npm run dev` in `frontend/`).
- Visit http://localhost:5173, enter a prompt, select models, and run an evaluation.

### Troubleshooting
- If the API is down, the UI still loads but shows an offline/health warning.
- If builds fail due to encoding/BOM issues, re-save the affected files as UTF-8 and rerun `npm run build`.

## How it works (systems view)
1. FastAPI receives an `/evaluate` request containing a prompt and optional model list.
2. The evaluation engine fans the prompt out to each `LLMClient` asynchronously.
3. Raw generations and timing metadata are captured with per-model timeouts.
4. Lightweight similarity heuristics (Jaccard token overlap) are computed for pairwise comparison.
5. A rule-based synthesizer returns either the majority response or, if none exists, the longest response as a coverage proxy, along with its rationale.

## Folder structure
- `backend/` – FastAPI app, LLM abstractions, evaluation pipeline, synthesis strategies, tests.
- `frontend/` – Vite + React UI for running and comparing evaluations.
- `docs/` – Architecture, evaluation methodology, and roadmap notes.

## Example request
```bash
curl -X POST http://127.0.0.1:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"List three benefits of testing","models":["mock:echo","mock:pseudo"],"temperature":0,"max_tokens":256,"timeout_s":12,"synthesis_method":"best_of_n"}'
```

PowerShell equivalent:
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/evaluate" `
  -ContentType "application/json" `
  -Body (@{
    prompt           = "List three benefits of testing"
    models           = @("mock:echo","mock:pseudo")
    temperature      = 0
    max_tokens       = 256
    timeout_s        = 12
    synthesis_method = "best_of_n"
  } | ConvertTo-Json)
```

Discover available models at `GET /models` (includes availability + reason when API keys are missing).

### Response contract (stable)
- `request_id`, `created_at`, `prompt`, `params` (echoed models/temp/max_tokens/timeout_s/synthesis_method)
- `results[]`: `{ model, provider, ok, status, text?, error_code?, error_message?, latency_ms?, usage?, meta? }`
- `synthesis`: `{ ok, method, text, rationale? }`
- `compare`: `{ pairs: [{ a, b, token_overlap_jaccard, length_ratio, keyword_coverage }], summary: { avg_similarity, most_disagree_pair?, notes } }`

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

PRISM is intentionally minimal—no auth, databases, or external infra. Build on it as evaluation needs grow.
