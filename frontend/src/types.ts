export interface ModelInfo {
  id: string;
  provider: string | null;
  enabled: boolean;
  disabled_reason: string | null;
  description?: string | null;
}

export interface ModelResponse {
  id: string;
  provider: string | null;
  model: string | null;
  text: string;
  latency_ms: number;
  usage?: Record<string, unknown> | null;
  finish_reason?: string | null;
  error?: string | null;
  created_at: string;
}

export interface Metrics {
  agreement: number;
  unique_responses: number;
  average_length: number;
  similarity: number;
  semantic_similarity?: number | null;
  evaluated_at: string;
}

export interface Synthesis {
  strategy: string;
  response: string;
  rationale: string;
  explain: string;
}

export interface EvaluateResponse {
  run_id: string;
  request: {
    prompt: string;
    models?: string[] | null;
  };
  responses: ModelResponse[];
  metrics: Metrics;
  synthesis: Synthesis;
}
