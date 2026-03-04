
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ConsensusReviewResponse,
  EvaluateResponse,
  ModelInfo,
  SynthesisMethod,
} from "./types";

const DEFAULT_API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const CLIENT_TIMEOUT_MS = Number(import.meta.env.VITE_EVALUATE_TIMEOUT_MS ?? 120_000) || 120_000;

type StatusState = "idle" | "connecting" | "online" | "offline";

function normalizeBaseUrl(url: string): string {
  return (url || DEFAULT_API_URL).trim().replace(/\/$/, "");
}

function App() {
  const [apiUrl, setApiUrl] = useState(() => normalizeBaseUrl(localStorage.getItem("prism_api_url") || DEFAULT_API_URL));
  const [status, setStatus] = useState<StatusState>("idle");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [prompt, setPrompt] = useState("Compare the tradeoffs between unit tests and integration tests.");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(512);
  const [timeoutS, setTimeoutS] = useState(30);
  const [synthesisMethod, setSynthesisMethod] = useState<SynthesisMethod>("best_of_n");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<EvaluateResponse | null>(null);
  const [reviewRunning, setReviewRunning] = useState(false);
  const [reviewResult, setReviewResult] = useState<ConsensusReviewResponse | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [round2Pulse, setRound2Pulse] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const round2Ref = useRef<HTMLDivElement | null>(null);
  const previousRunningRef = useRef(false);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const statusText = useMemo(() => {
    if (status === "connecting") return "CONNECTING...";
    if (status === "online") return "STATUS: ONLINE";
    if (status === "offline") return "STATUS: OFFLINE";
    return "INIT...";
  }, [status]);

  const selectedIds = useMemo(() => [...selected].filter((id) => models.some((m) => m.id === id && m.available)), [selected, models]);

  const requestJson = async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const response = await fetch(`${normalizeBaseUrl(apiUrl)}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json() as Promise<T>;
  };

  const ping = async (): Promise<boolean> => {
    setStatus("connecting");
    try {
      try {
        await requestJson("/health");
      } catch {
        await requestJson("/models");
      }
      setStatus("online");
      return true;
    } catch {
      setStatus("offline");
      return false;
    }
  };

  const loadModels = async () => {
    setModelsLoading(true);
    try {
      const data = await requestJson<{ models?: ModelInfo[] } | ModelInfo[]>("/models");
      const payload = Array.isArray(data) ? data : data.models || [];
      setModels(payload);
      setSelected(new Set(payload.filter((m) => m.available).map((m) => m.id)));
    } catch {
      const fallback: ModelInfo[] = [
        { id: "mock:echo", provider: "mock", available: true, reason: null },
        { id: "mock:pseudo", provider: "mock", available: true, reason: null },
      ];
      setModels(fallback);
      setSelected(new Set(fallback.map((m) => m.id)));
      setToast("Unable to fetch models; using mock fallback list.");
    } finally {
      setModelsLoading(false);
    }
  };

  useEffect(() => {
    const initialize = async () => {
      const ok = await ping();
      if (ok) await loadModels();
    };
    void initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleModel = (id: string, available: boolean) => {
    if (!available) return;
    setSelected((previous) => {
      const next = new Set(previous);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const run = async () => {
    if (!prompt.trim()) {
      setToast("Prompt required.");
      return;
    }
    if (!selectedIds.length) {
      setToast("No models selected.");
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), CLIENT_TIMEOUT_MS);
    setRunning(true);
    setReviewResult(null);
    setReviewError(null);

    try {
      const payload = {
        prompt: prompt.trim(),
        models: selectedIds,
        temperature,
        max_tokens: maxTokens,
        timeout_s: timeoutS,
        synthesis_method: synthesisMethod,
      };

      const response = await requestJson<EvaluateResponse>("/evaluate", {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify(payload),
      });
      setResult(response);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Evaluation failed.";
      setToast(message);
    } finally {
      window.clearTimeout(timer);
      setRunning(false);
    }
  };

  const persistApiUrl = (value: string) => {
    const next = normalizeBaseUrl(value);
    setApiUrl(next);
    localStorage.setItem("prism_api_url", next);
  };

  const exportResult = () => {
    if (!result) {
      setToast("No result.");
      return;
    }
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `prism-${result.request_id || Date.now()}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const clearResult = () => {
    setPrompt("");
    setResult(null);
    setReviewResult(null);
    setReviewError(null);
  };

  const isMockEntry = (provider?: string | null, modelId?: string | null): boolean => {
    const providerValue = (provider || "").toLowerCase();
    const modelValue = (modelId || "").toLowerCase();
    return providerValue === "mock" || modelValue.startsWith("mock:");
  };

  const eligibleConsensusOutputs = useMemo(() => {
    if (!result) return [];
    return result.results.filter((entry) => {
      if (isMockEntry(entry.provider, entry.model)) return false;
      if (entry.status !== "success") return false;
      return Boolean((entry.text || "").trim());
    });
  }, [result]);

  const canRunConsensusReview = !!result && !running && !reviewRunning && eligibleConsensusOutputs.length >= 2;

  const consensusDisabledReason = useMemo(() => {
    if (running) return "Waiting for models to finish...";
    if (!result) return "Run an evaluation first";
    if (eligibleConsensusOutputs.length < 2) return "Need at least 2 successful non-mock model outputs";
    return null;
  }, [running, result, eligibleConsensusOutputs.length]);

  useEffect(() => {
    const wasRunning = previousRunningRef.current;
    if (wasRunning && !running && result && round2Ref.current) {
      const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      round2Ref.current.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" });
      setRound2Pulse(true);
      const timer = window.setTimeout(() => setRound2Pulse(false), 1500);
      previousRunningRef.current = running;
      return () => window.clearTimeout(timer);
    }
    previousRunningRef.current = running;
    return undefined;
  }, [running, result]);

  const runConsensusReview = async () => {
    if (!result) return;
    if (eligibleConsensusOutputs.length < 2) {
      setReviewError("Consensus Review needs at least 2 successful non-mock model outputs.");
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), CLIENT_TIMEOUT_MS);
    setReviewRunning(true);
    setReviewError(null);
    try {
      const payload = {
        original_prompt: result.prompt || prompt,
        run_id: result.request_id,
        model_outputs: result.results.map((entry) => ({
          model_id: entry.model,
          provider: entry.provider,
          text: entry.text || null,
          latency_ms: entry.latency_ms ?? null,
          usage: entry.usage ?? null,
          status: entry.status,
        })),
      };
      const response = await requestJson<ConsensusReviewResponse>("/consensus_review", {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify(payload),
      });
      setReviewResult(response);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Consensus review failed.";
      setReviewError(message);
    } finally {
      window.clearTimeout(timer);
      setReviewRunning(false);
    }
  };

  const compareSummary = result?.compare?.summary;
  const disagreePair = compareSummary?.most_disagree_pair;
  const disagreeLabel = disagreePair ? `${disagreePair.a} :: ${disagreePair.b}` : "-";

  return (
    <>
      <div className="boot-header">
        <div className="boot-line">// PRISM v0.1.0 - PARALLEL REASONING &amp; INFERENCE SYNTHESIS MACHINE</div>
        <div className="boot-title glow">
          <em>PRI</em>SM<span className="cursor" />
        </div>
        <div className="boot-sub">Evaluation Framework // Multi-model comparison engine</div>
      </div>

      <div className="statusbar">
        <div className="sb-item active">
          <div className={`sdot ${status === "online" ? "on" : status === "offline" ? "off" : "chk"}`} />
          <span>{statusText}</span>
        </div>
        <div className="sb-item">
          <span className="dim">API_URL:</span>
          <input
            className="sb-input"
            value={apiUrl}
            onChange={(event) => setApiUrl(event.target.value)}
            onBlur={(event) => persistApiUrl(event.target.value)}
            type="text"
            spellCheck={false}
            placeholder="http://127.0.0.1:8000"
          />
          <button
            className="tb"
            onClick={() =>
              ping().then((ok) => {
                if (ok) return loadModels();
                return undefined;
              })
            }
            disabled={modelsLoading}
          >
            PING
          </button>
        </div>
        <div className="ml">
          <button className="tb" onClick={exportResult}>
            EXPORT
          </button>
          <button className="tb" onClick={clearResult}>
            CLEAR
          </button>
        </div>
      </div>

      <div className="shell">
        <div className="pane">
          <div className="prompt-label">PROMPT INPUT</div>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                void run();
              }
            }}
            placeholder="Enter prompt... (Ctrl+Enter to run)"
            rows={5}
          />
          <div className="params-grid">
            <div className="pg">
              <label>Temperature</label>
              <input type="number" value={temperature} onChange={(event) => setTemperature(Number(event.target.value))} min={0} max={2} step={0.1} />
            </div>
            <div className="pg">
              <label>Max Tokens</label>
              <input type="number" value={maxTokens} onChange={(event) => setMaxTokens(Number(event.target.value))} min={1} max={4096} />
            </div>
            <div className="pg">
              <label>Timeout (s)</label>
              <input type="number" value={timeoutS} onChange={(event) => setTimeoutS(Number(event.target.value))} min={1} max={120} />
            </div>
            <div className="pg">
              <label>Synthesis</label>
              <select value={synthesisMethod} onChange={(event) => setSynthesisMethod(event.target.value as SynthesisMethod)}>
                <option value="best_of_n">best_of_n</option>
                <option value="consensus_overlap">consensus_overlap</option>
                <option value="longest_nonempty">longest_nonempty</option>
              </select>
            </div>
          </div>

          <button className={`run-btn ${running ? "loading" : ""}`} onClick={() => void run()} disabled={running}>
            {running ? (
              <>
                <span className="spinner" /> PROCESSING...
              </>
            ) : (
              "EXECUTE EVALUATION"
            )}
          </button>

          <div className={`results ${result ? "vis" : ""}`}>
            <div className="rsect-head">
              <span className="rsh-tag">OUT</span>SYNTHESIS
            </div>
            <div className="syn-box">
              <div className="syn-meta">
                <span>//SYNTHESIS</span>
                <span>METHOD:{result?.synthesis?.method || "-"}</span>
              </div>
              <div className="syn-text">{result?.synthesis?.text || ""}</div>
              {result?.synthesis?.rationale && <div className="syn-rat">// {result.synthesis.rationale}</div>}
            </div>

            <div className="rsect-head">
              <span className="rsh-tag">OUT</span>MODEL RESPONSES
            </div>
            <div className="resp-grid">
              {result?.results.map((entry, index) => (
                <div key={`${entry.model}-${index}`} className="resp-card" style={{ animationDelay: `${index * 0.05}s` }}>
                  <div className="resp-head">
                    <span className="resp-model">{entry.model}</span>
                    <span className={`resp-meta ${entry.ok ? "resp-ok" : "resp-err"}`}>
                      [{entry.ok ? "OK" : "ERR"}] {entry.latency_ms != null ? `${entry.latency_ms.toFixed(1)}ms` : ""}
                    </span>
                  </div>
                  {entry.ok ? (
                    <div className="resp-body">{entry.text || ""}</div>
                  ) : (
                    <div className="resp-error">{(entry.error_code || "ERR") + (entry.error_message ? `: ${entry.error_message}` : "")}</div>
                  )}
                </div>
              ))}
            </div>

            <div ref={round2Ref} className={`round2-card ${round2Pulse ? "round2-pulse" : ""}`}>
              <div className="round2-title">Round 2: Consensus Review</div>
              <div className="round2-subtitle">
                A comprehensive analysis of all the models lead to the final answer
              </div>
              <div className="round2-eligibility">
                <span className="round2-eligible-count">Eligible models: {eligibleConsensusOutputs.length}</span>
                {eligibleConsensusOutputs.length >= 2 ? (
                  <span className="round2-eligible-list">
                    {eligibleConsensusOutputs.map((entry) => entry.model).join(", ")}
                  </span>
                ) : (
                  <span className="round2-eligible-list">Need at least 2 successful non-mock outputs</span>
                )}
              </div>
              <div className="consensus-actions">
                <button className="round2-button" onClick={() => void runConsensusReview()} disabled={!canRunConsensusReview}>
                  {reviewRunning ? "Reviewing..." : "Run Consensus Review ->"}
                </button>
              </div>
              {!canRunConsensusReview && consensusDisabledReason && <div className="round2-helper">{consensusDisabledReason}</div>}
              {reviewError && <div className="resp-error">consensus_review: {reviewError}</div>}
              {reviewResult && (
                <div className="consensus-content">
                  <div className="syn-meta">
                    <span>SUMMARY</span>
                    <span>CONFIDENCE:{String(reviewResult.confidence ?? "-")}</span>
                  </div>
                  <div className="syn-rat">{reviewResult.summary}</div>
                  <div className="consensus-final">{reviewResult.final_answer}</div>

                  <div className="consensus-list-head">KEY TAKEAWAYS</div>
                  <ul className="consensus-list">
                    {reviewResult.key_takeaways.map((item, index) => (
                      <li key={`takeaway-${index}`}>{item}</li>
                    ))}
                  </ul>

                  <div className="consensus-list-head">DISAGREEMENTS</div>
                  <ul className="consensus-list">
                    {reviewResult.disagreements.map((item, index) => (
                      <li key={`disagreement-${index}`}>
                        {item.topic} | {item.models_involved.join(", ")} | {item.resolution}
                      </li>
                    ))}
                  </ul>

                  <div className="consensus-list-head">PER-MODEL NOTES</div>
                  {Object.entries(reviewResult.per_model_notes).map(([modelId, note]) => (
                    <div key={modelId} className="consensus-model-note">
                      <div className="resp-model">{modelId}</div>
                      <div>Strengths: {note.strengths.join(" | ") || "-"}</div>
                      <div>Weaknesses: {note.weaknesses.join(" | ") || "-"}</div>
                      <div>Issues: {note.issues.join(" | ") || "-"}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rsect-head">
              <span className="rsh-tag">OUT</span>COMPARISON
            </div>
            <div className="cmp-box">
              <div className="cmp-summary">
                <div>
                  <div className="cs-label">AVG_SIM</div>
                  <div className="cs-val glow-sm">{compareSummary?.avg_similarity != null ? `${(compareSummary.avg_similarity * 100).toFixed(1)}%` : "-"}</div>
                </div>
                <div>
                  <div className="cs-label">DIVERGE</div>
                  <div className="cs-val small-val">{disagreeLabel}</div>
                </div>
              </div>

              {!!compareSummary?.notes && <div className="cmp-notes">// {compareSummary.notes}</div>}

              {!!result?.compare?.pairs?.length && (
                <table>
                  <thead>
                    <tr>
                      <th>PAIR</th>
                      <th>JACCARD</th>
                      <th>LEN_RATIO</th>
                      <th>KW_COV</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.compare.pairs.map((pair, index) => (
                      <tr key={`${pair.a}-${pair.b}-${index}`}>
                        <td>
                          {pair.a} :: {pair.b}
                        </td>
                        <td>
                          <div className="bar-wrap">
                            <div className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, pair.token_overlap_jaccard * 100)).toFixed(0)}%` }} />
                          </div>{" "}
                          {(pair.token_overlap_jaccard * 100).toFixed(1)}%
                        </td>
                        <td>{pair.length_ratio != null ? pair.length_ratio.toFixed(2) : "-"}</td>
                        <td>{pair.keyword_coverage != null ? `${(pair.keyword_coverage * 100).toFixed(1)}%` : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="req-foot">
              REQUEST_ID: <span>{result?.request_id || "-"}</span>
              <span>|</span>
              TS: <span>{result?.created_at ? new Date(result.created_at).toLocaleString() : "-"}</span>
              <span>|</span>
              MODELS: <span>{result?.params?.models?.join(",") || ""}</span>
            </div>
          </div>
        </div>

        <div className="pane-right">
          <div className="sect-head">MODEL SELECT</div>
          <div id="modelGrid">
            {modelsLoading && <div className="loading-models">LOADING MODELS...</div>}
            {!modelsLoading &&
              models.map((model) => {
                const isSelected = selected.has(model.id) && model.available;
                const isMock = (model.provider || model.id || "").startsWith("mock");
                return (
                  <div
                    key={model.id}
                    className={`model-row ${isSelected ? "sel" : ""} ${model.available ? "" : "model-na"}`}
                    onClick={() => toggleModel(model.id, model.available)}
                    title={model.reason || ""}
                  >
                    <div className="chkbox">{isSelected ? "?" : ""}</div>
                    <span className="model-id">{model.id}</span>
                    <span className="model-prov">{model.provider || ""}</span>
                    {isMock ? <span className="mbadge mock">mock</span> : !model.available ? <span className="mbadge">no key</span> : null}
                  </div>
                );
              })}
            {!modelsLoading && models.length === 0 && <div className="loading-models">NO MODELS FOUND</div>}
          </div>
          <button
            className="ref-btn"
            onClick={() =>
              ping().then((ok) => {
                if (ok) return loadModels();
                return undefined;
              })
            }
            disabled={modelsLoading}
          >
            REFRESH
          </button>
        </div>
      </div>

      <div className={`toast ${toast ? "" : "hidden"}`}>[ERR] {toast || ""}</div>
    </>
  );
}

export default App;
