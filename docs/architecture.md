# PRISM Architecture Overview

## High-level flow
1. Receive a prompt and target model set via FastAPI `/evaluate`.
2. Dispatch the prompt concurrently to each configured `LLMClient`.
3. Collect raw generations and timing metadata.
4. Compute lightweight agreement/divergence metrics.
5. Apply rule-based synthesis to emit a single consolidated answer with rationale.

## Backend components
- `app.llms`: Abstractions and concrete clients. Mock clients keep local runs deterministic.
- `app.evaluation`: Orchestrates parallel execution and metric computation.
- `app.synthesis`: Rule-based aggregation strategies.
- `app.main`: FastAPI wiring for dependency setup and HTTP exposure.

## Data contracts
- Request: `{ prompt: str, models?: [str] }`
- Response: `{ evaluations: [...], metrics: {...}, synthesis: {...} }`

## Execution model
- Uses `asyncio` with `gather` for parallel fan-out.
- Each `LLMClient` is responsible for latency reporting and metadata.
- Metrics are intentionally simple (Jaccard similarity, agreement ratios) to keep the system deterministic and inspectable.
