export type SynthesisMethod = "longest_nonempty" | "consensus_overlap" | "best_of_n";

export interface ModelInfo {
  id: string;
  provider: string;
  available: boolean;
  reason: string | null;
  description?: string | null;
}

export interface EvaluateRequestPayload {
  prompt: string;
  models: string[];
  temperature: number;
  max_tokens: number;
  timeout_s: number;
  synthesis_method: SynthesisMethod;
}

export interface ModelResult {
  model: string;
  provider: string;
  ok: boolean;
  status: "success" | "error" | "timeout";
  text?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms?: number | null;
  usage?: Record<string, unknown> | null;
  meta?: Record<string, unknown> | null;
}

export interface ComparePair {
  a: string;
  b: string;
  token_overlap_jaccard: number;
  length_ratio: number;
  keyword_coverage: number;
}

export interface CompareSummary {
  avg_similarity: number;
  most_disagree_pair: ComparePair | null;
  notes?: string | null;
}

export interface CompareResult {
  pairs: ComparePair[];
  summary: CompareSummary;
}

export interface SynthesisPayload {
  ok: boolean;
  method: SynthesisMethod;
  text: string | null;
  rationale?: string | null;
}

export interface EvaluateParams {
  models: string[];
  temperature: number;
  max_tokens: number;
  timeout_s: number;
  synthesis_method: SynthesisMethod;
}

export interface EvaluateResponse {
  request_id: string;
  created_at: string;
  prompt: string;
  params: EvaluateParams;
  results: ModelResult[];
  synthesis: SynthesisPayload;
  compare: CompareResult;
}
