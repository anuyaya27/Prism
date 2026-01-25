# Evaluation Methodology

## Goals
- Quickly surface agreement/divergence across LLM outputs.
- Keep computations deterministic and traceable for research use.

## Metrics (current)
- **Agreement ratio:** frequency of the most common normalized response.
- **Unique responses:** number of distinct normalized outputs (lower implies convergence).
- **Average length:** crude proxy for verbosity/coverage.
- **Similarity (Jaccard):** average token-set overlap across all pairs.

## Normalization
- Trim whitespace and lowercase the full string prior to counting/overlap.
- No additional cleaning is applied to preserve raw behavior; adjust per experiment as needed.

## Synthesis
- Majority response wins when present.
- Otherwise the longest response is used as a coverage heuristic, with rationale emitted alongside the selection.

## Extensibility
- Swap or extend metrics in `app.evaluation.pipeline`.
- Add richer synthesis strategies in `app.synthesis`.
- Replace mock clients with real providers by implementing `LLMClient`.
