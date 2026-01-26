export interface ModelInfo {
  id: string;
  provider: string | null;
  enabled: boolean;
  disabled_reason: string | null;
  description?: string | null;
}

export interface EvaluateRequestPayload {
  prompt: string;
  models: string[];
  temperature: number;
  max_tokens: number;
  timeout_s: number;
}

export interface ModelResult {
  model: string;
  ok: boolean;
  text?: string | null;
  error?: string | null;
  latency_ms?: number | null;
  status: "success" | "error" | "timeout";
  provider?: string | null;
}

export interface SynthesisPayload {
  ok: boolean;
  text: string | null;
  method: string;
  rationale?: string | null;
}

export interface ComparePair {
  a: string;
  b: string;
  score: number;
}

export interface CompareResult {
  pairs: ComparePair[];
  note?: string | null;
}

export interface EvaluateResponse {
  request_id: string;
  prompt: string;
  results: ModelResult[];
  synthesis: SynthesisPayload;
  compare: CompareResult;
}
