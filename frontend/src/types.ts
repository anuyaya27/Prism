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
   raw_request?: Record<string, unknown> | null;
   raw_response?: Record<string, unknown> | null;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms?: number | null;
  usage?: Record<string, unknown> | null;
  meta?: Record<string, unknown> | null;
   format_compliance?: number | null;
   hedge_count?: number | null;
}

export interface ComparePair {
  a: string;
  b: string;
  token_overlap_jaccard: number;
  length_ratio: number;
  keyword_coverage: number;
  rouge_l: number;
}

export interface CompareSummary {
  avg_similarity: number;
  most_disagree_pair: ComparePair | null;
  notes?: string | null;
  disagreement_summary?: {
    max_distance: number;
    pair: { a: string; b: string } | null;
    reason?: string | null;
  } | null;
}

export interface CompareResult {
  pairs: ComparePair[];
  summary: CompareSummary;
}

export interface SynthesisPayload {
  ok: boolean;
  strategy_id: "longest" | "consensus_overlap" | "best_of_n" | "none";
  method: SynthesisMethod;
  text: string | null;
  rationale?: string | null;
  confidence?: number | null;
  attribution?: { source_model_id: string; span?: string | null; sentence_index?: number | null }[] | null;
  synthesized_text?: string | null;
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
  run_hash: string;
  schema_version: string;
  api_version: string;
  prompt: string;
  params: EvaluateParams;
  results: ModelResult[];
  synthesis: SynthesisPayload;
  compare: CompareResult;
  status: "success" | "partial" | "failed";
  partial_success?: boolean | null;
}
