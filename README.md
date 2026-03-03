# PRISM  
**Parallel Reasoning & Inference Synthesis Machine**

PRISM is an evaluation and reasoning orchestration system for large language models.

Instead of relying on a single model output, PRISM runs the same prompt across multiple LLMs, analyzes their responses, and synthesizes a transparent final answer. The system exposes the full reasoning surface area of each model while providing a structured comparison and a synthesized result.

PRISM is designed for developers, researchers, and teams building AI systems who want reliable outputs, model transparency, and a structured evaluation pipeline.

---

# Why PRISM exists

Modern AI systems often rely on a single model response, even though different models reason differently. This creates problems:

- A single model may hallucinate or fail silently  
- Outputs can vary significantly across providers  
- There is limited visibility into model disagreement  
- Developers lack systematic tools for comparing reasoning quality  

PRISM addresses this by treating models as **parallel reasoning engines** and providing tools to analyze and synthesize their outputs.

Instead of asking *“What did the model say?”*, PRISM helps answer:

- Which models agree?  
- Where do they disagree?  
- Which response is most complete?  
- What is the best synthesized answer across models?  

---

# Key Features

## Parallel Model Execution
PRISM sends a prompt to multiple LLMs simultaneously and collects their responses asynchronously.

This allows the system to compare reasoning across models such as OpenAI, Gemini, or any custom provider.

---

## Transparent Model Comparison
PRISM evaluates responses using lightweight similarity and coverage heuristics, including:

- Token overlap (Jaccard similarity)  
- Response length comparison  
- Keyword coverage  
- Pairwise disagreement analysis  

This provides insight into **how models differ**, not just what they output.

---

## Response Synthesis
After evaluating responses, PRISM produces a synthesized final answer using configurable strategies.

Current synthesis strategies include:

- **Majority agreement** when models converge  
- **Coverage-based selection** when responses diverge  
- Transparent rationale for the chosen answer  

---

## Local-First Architecture
PRISM runs entirely locally and does not require external infrastructure.

There is no dependency on:

- hosted databases  
- managed queues  
- deployment platforms  

This makes PRISM easy to experiment with and extend.

---

## Extensible Model Layer
PRISM provides a clean abstraction for integrating new model providers.

Adding support for a new LLM only requires implementing a client that subclasses `LLMClient`.

---

# Product Architecture

PRISM consists of three main components.

### 1. Evaluation Engine
The backend receives prompts and orchestrates parallel model calls.

Responsibilities:

- fan-out prompt execution  
- manage model timeouts  
- collect responses and metadata  
- compute similarity metrics  

---

### 2. Synthesis Layer
After collecting model outputs, PRISM applies synthesis strategies to produce a final answer.

This layer is modular and allows experimentation with different reasoning aggregation methods.

---

### 3. Interactive UI
The frontend provides a simple interface for running evaluations.

Users can:

- enter prompts  
- select models  
- view responses side-by-side  
- inspect synthesis decisions  
- explore model disagreement  

---

# Example Workflow

1. A user submits a prompt through the UI or API.
2. The evaluation engine sends the prompt to multiple models.
3. Each model returns a response.
4. PRISM compares the responses using similarity heuristics.
5. The synthesis engine selects or constructs the final answer.
6. The system returns:

- all raw model outputs  
- comparison metrics  
- synthesized response  
- rationale  

---

# API Example

```bash
curl -X POST http://127.0.0.1:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List three benefits of testing",
    "models": ["mock:echo","mock:pseudo"],
    "temperature": 0,
    "max_tokens": 256,
    "timeout_s": 12,
    "synthesis_method": "best_of_n"
}'
```

The response includes:

- model outputs  
- latency metadata  
- similarity metrics  
- synthesized result  

---

# Project Structure

```
PRISM
│
├── backend/
│   FastAPI evaluation service
│   LLM provider abstractions
│   evaluation pipeline
│   synthesis strategies
│
├── frontend/
│   React + Vite interface
│   prompt runner and model comparison UI
│
└── docs/
    architecture notes
    evaluation methodology
    roadmap
```

---

# Running PRISM Locally

## Prerequisites

- Node.js 20+
- Python 3.10+ (3.11 recommended)

---

# Backend (FastAPI)

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# PowerShell (from backend/)
$env:PYTHONPATH="."
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Alternative (from repo root)
# $env:PYTHONPATH="backend"
# uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

API docs will be available at:

```
http://127.0.0.1:8000/docs
```

---

## Environment Variables

Create a `.env` file in the project root if you want to use real models.

```
OPENAI_API_KEY=...
GEMINI_API_KEY=...
```

Mock models will work without any keys.

---

# Frontend (React + Vite)

```bash
cd frontend

npm install

echo VITE_API_BASE_URL=http://127.0.0.1:8000 > .env.local

npm run dev
```

Open:

```
http://localhost:5173
```

---

# Running the Full System

Terminal 1

```
start backend server
```

Terminal 2

```
npm run dev
```

Then open the UI and run prompt evaluations.

---

# Testing

```bash
$env:PYTHONPATH="backend"
pytest backend/tests -q
```

---

# Extending PRISM

### Add a new model provider

Create a subclass of:

```
backend/app/llms/LLMClient
```

and implement the `generate()` interface.

---

### Add new evaluation metrics

Extend:

```
backend/app/evaluation/pipeline.py
```

---

### Add new synthesis strategies

Add implementations in:

```
backend/app/synthesis/
```

---

# Current Model Support

| Provider | Example Model |
|--------|--------|
| OpenAI | `openai:gpt-4o-mini` |
| Gemini | `gemini:2.5-flash` |
| Mock | `mock:echo`, `mock:pseudo` |

---

# Roadmap

Future improvements planned for PRISM include:

- reasoning trace comparison  
- structured output evaluation  
- weighted model voting  
- dataset-level benchmarking  
- experiment tracking  
- evaluation dashboards  

---

# Philosophy

PRISM treats LLMs as **parallel reasoning systems rather than single sources of truth**.

The goal is not just to generate answers, but to understand how models reason, where they disagree, and how to combine their strengths.
