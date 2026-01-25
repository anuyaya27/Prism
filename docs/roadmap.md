# Roadmap

## Near-term
- Add real provider clients (OpenAI, Anthropic, local models) behind `LLMClient`.
- Introduce judge-model based scoring to compare candidate answers.
- Expand synthesis strategies (ranking, weighted voting, structured scoring).
- Add CLI runner for batch evaluation over datasets.

## Mid-term
- Dataset mode for benchmarking prompts across curated sets.
- Pluggable embeddings backend for semantic similarity.
- Persist evaluation artifacts (JSONL per run) for offline analysis.
- Basic frontend charts for agreement/divergence trends.

## Long-term
- Experiment tracking and experiment comparison UI.
- Guardrail integrations (toxicity, hallucination checks).
- Multi-turn dialogue evaluation.
