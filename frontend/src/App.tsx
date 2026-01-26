import React, { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, debugPing, getModels, postEvaluate } from "./api/client";
import ComparisonCard from "./components/ComparisonCard";
import Header from "./components/Header";
import ModelChips from "./components/ModelChips";
import ResultCard from "./components/ResultCard";
import StatusBadge from "./components/StatusBadge";
import SynthesisCard from "./components/SynthesisCard";
import Toast from "./components/Toast";
import { EvaluateRequestPayload, EvaluateResponse, ModelInfo, SynthesisMethod } from "./types";

const requestDefaults = {
  temperature: 0,
  max_tokens: 512,
  timeout_s: 15,
  synthesis_method: "best_of_n" as SynthesisMethod,
};

function App() {
  const [prompt, setPrompt] = useState("Compare the tradeoffs between unit tests and integration tests.");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [synthesisMethod, setSynthesisMethod] = useState<SynthesisMethod>(requestDefaults.synthesis_method);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<EvaluateResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [timeoutBanner, setTimeoutBanner] = useState<string | null>(null);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsStatus, setModelsStatus] = useState<"idle" | "ok" | "error">("idle");
  const [healthStatus, setHealthStatus] = useState<"idle" | "ok" | "error">("idle");
  const [pingResult, setPingResult] = useState<string | null>(null);
  const [pingError, setPingError] = useState<string | null>(null);
  const [pingLoading, setPingLoading] = useState(false);
  const [formErrors, setFormErrors] = useState<{ prompt?: string; models?: string }>({});
  const [showUsage, setShowUsage] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; tone: "success" | "error" } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    const loadModels = async () => {
      setModelsLoading(true);
      try {
        const data = await getModels();
        const safeModels: ModelInfo[] = Array.isArray((data as any)?.models)
          ? (data as any).models
          : Array.isArray(data)
            ? (data as ModelInfo[])
            : [];
        setModels(safeModels);
        const defaults = ["mock:echo", "mock:pseudo"].filter((id) => safeModels.some((m: ModelInfo) => m.id === id && m.available));
        const enabledFallback = safeModels.filter((m: ModelInfo) => m.available).map((m: ModelInfo) => m.id);
        const initial = new Set<string>(defaults.length ? defaults : enabledFallback);
        setSelected(initial);
        const unavailable = safeModels.find((m: ModelInfo) => !m.available && m.reason);
        setUnavailableReason(unavailable ? unavailable.reason || "Some providers are unavailable." : null);
        setRunError(null);
        setModelsStatus("ok");
      } catch (err: any) {
        console.error("Failed to load models", err);
        const message = err?.message || "Failed to load models";
        const isUnreachable = message.toLowerCase().includes("failed to fetch");
        const reason = isUnreachable ? "Backend unreachable or blocked by CORS" : message;
        setRunError(`Failed to load models from ${API_BASE_URL}. ${reason}. Check backend is running at ${API_BASE_URL} and CORS allows localhost:5173.`);
        setModelsStatus("error");
        setModels([]);
        setSelected(new Set<string>());
      } finally {
        setModelsLoading(false);
      }
    };

    loadModels();
  }, []);

  const toggleModel = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next as Set<string>;
    });
  };

  const enabledSelectionCount = useMemo(() => models.filter((m) => m.available && selected.has(m.id)).length, [models, selected]);

  const handleRun = async () => {
    const errors: { prompt?: string; models?: string } = {};
    if (!prompt.trim()) {
      errors.prompt = "Prompt is required.";
    }
    if (enabledSelectionCount === 0) {
      errors.models = "Pick at least one available model.";
    }
    setFormErrors(errors);
    if (Object.keys(errors).length > 0) return;

    const controller = new AbortController();
    const timeoutMs = requestDefaults.timeout_s * 1000;
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);

    setRunning(true);
    setRunError(null);
    setTimeoutBanner(null);

    try {
      const body: EvaluateRequestPayload = {
        prompt,
        models: Array.from(selected),
        temperature: requestDefaults.temperature,
        max_tokens: requestDefaults.max_tokens,
        timeout_s: requestDefaults.timeout_s,
        synthesis_method: synthesisMethod,
      };
      const data = await postEvaluate(body, controller.signal);
      setResult(data as EvaluateResponse);
    } catch (err: any) {
      console.error("Evaluation failed", err);
      if (err?.name === "AbortError") {
        setTimeoutBanner(`Timed out after ${requestDefaults.timeout_s}s (client-side AbortController).`);
        setRunError("Request aborted due to timeout.");
      } else {
        const message = err?.message || "Failed to run evaluation";
        setRunError(message);
      }
    } finally {
      window.clearTimeout(timer);
      setRunning(false);
    }
  };

  const testConnection = async () => {
    setPingLoading(true);
    setPingError(null);
    setPingResult(null);
    try {
      const res = await debugPing();
      setPingResult(JSON.stringify(res));
      setHealthStatus("ok");
      setToast({ message: "Connection OK", tone: "success" });
    } catch (err: any) {
      console.error("Ping failed", err);
      const message = err?.message || "Failed to fetch";
      const isUnreachable = message.toLowerCase().includes("failed to fetch");
      const hint = isUnreachable ? "Backend unreachable or CORS blocked." : message;
      setPingError(`${hint} (base: ${API_BASE_URL})`);
      setHealthStatus("error");
      setToast({ message: "Connection failed", tone: "error" });
    } finally {
      setPingLoading(false);
    }
  };

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2400);
    return () => clearTimeout(t);
  }, [toast]);

  const exportJson = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prism-eval-${result.request_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyAll = async () => {
    if (!result) return;
    const lines = [
      `# PRISM Evaluation (${result.request_id})`,
      ``,
      `Prompt: ${result.prompt}`,
      `Synthesis (${result.synthesis.method}):`,
      result.synthesis.text || "_no synthesis available_",
      ``,
      `## Per-model outputs`,
      ...result.results.map((r) => `### ${r.model} (${r.status})\n${r.text || r.error_message || "_no output_"}\n`),
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
  };

  return (
    <div className="app-shell">
      <Header
        apiBase={API_BASE_URL}
        modelsStatus={modelsStatus}
        healthStatus={healthStatus}
        onTestConnection={testConnection}
        testing={pingLoading}
        pingResult={pingResult}
        pingError={pingError}
      />

      {toast && <Toast tone={toast.tone} message={toast.message} />}

      <main className="layout">
        <section className="pane hero">
          <div className="pane-header">
            <div>
              <p className="eyebrow">Prompt</p>
              <h2>Run an evaluation</h2>
              <p className="muted">Send one prompt to multiple models and compare + synthesize the best response.</p>
            </div>
            <div className="status-row">
              <StatusBadge label="Models" state={modelsStatus} />
              <StatusBadge label="Health" state={healthStatus} />
            </div>
          </div>

          <textarea
            className="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the scenario to evaluate across models..."
          />
          {formErrors.prompt && <div className="error small">{formErrors.prompt}</div>}

          <div className="chips-row">
            <div className="chips-label">Models to run</div>
            <ModelChips models={models} selected={selected} onToggle={toggleModel} loading={modelsLoading} />
          </div>
          {formErrors.models && <div className="error small">{formErrors.models}</div>}
          {!runError && models.length === 0 && !modelsLoading && <div className="muted">No models available.</div>}

          <div className="advanced">
            <button className="ghost" onClick={() => setShowAdvanced((s) => !s)}>
              {showAdvanced ? "Hide advanced" : "Advanced"}
            </button>
            {showAdvanced && (
              <div className="advanced-grid">
                <Setting label="Temperature" value={requestDefaults.temperature} />
                <Setting label="Max tokens" value={requestDefaults.max_tokens} />
                <Setting label="Timeout (s)" value={requestDefaults.timeout_s} />
                <div className="setting">
                  <div className="muted small">Synthesis</div>
                  <select value={synthesisMethod} onChange={(e) => setSynthesisMethod(e.target.value as SynthesisMethod)}>
                    <option value="longest_nonempty">longest_nonempty</option>
                    <option value="consensus_overlap">consensus_overlap</option>
                    <option value="best_of_n">best_of_n</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          <div className="cta-row">
            <button className="primary" onClick={handleRun} disabled={running || !prompt.trim()}>
              {running ? "Running..." : "Run evaluation"}
            </button>
            <div className="switches">
              <label>
                <input type="checkbox" checked={showUsage} onChange={(e) => setShowUsage(e.target.checked)} /> show usage
              </label>
              <label>
                <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} /> show raw JSON
              </label>
            </div>
          </div>

          {runError && <div className="banner error-banner">{runError}</div>}
          {timeoutBanner && <div className="banner warn-banner">{timeoutBanner}</div>}
          {unavailableReason && <div className="banner warn-banner">Some providers unavailable: {unavailableReason}</div>}
        </section>

        <section className="pane results-pane">
          <div className="pane-header">
            <div>
              <p className="eyebrow">Results</p>
              <h2>Outputs</h2>
              {result && (
                <div className="muted small output-meta">
                  {result.results.length} models • avg latency {(result.results.reduce((s, r) => s + (r.latency_ms || 0), 0) / Math.max(result.results.length, 1) / 1000).toFixed(1)}s
                </div>
              )}
            </div>
            <div className="actions-row">
              <button className="ghost" onClick={exportJson} disabled={!result}>
                Download JSON
              </button>
              <button className="ghost" onClick={copyAll} disabled={!result}>
                Copy all outputs
              </button>
            </div>
          </div>

          {!result && (
            <div className="empty-state">
              <img src="/prism-logo.png" alt="PRISM logo" className="logo-faint" />
              <p className="muted">PRISM compares responses across models and synthesizes the best answer.</p>
            </div>
          )}

          {result && (
            <>
              <SummaryBar results={result.results} createdAt={result.created_at} requestId={result.request_id} />

              <div className="responses-grid">
                {result.results.map((r) => (
                  <ResultCard key={r.model} result={r} showUsage={showUsage} />
                ))}
              </div>

              <div className="grid two-col">
                <SynthesisCard synthesis={result.synthesis} />
                <ComparisonCard compare={result.compare} />
              </div>

              {showRaw && <pre className="raw-block">{JSON.stringify(result, null, 2)}</pre>}
            </>
          )}
        </section>
      </main>
    </div>
  );
}

function Setting({ label, value }: { label: string; value: number }) {
  return (
    <div className="setting">
      <div className="muted small">{label}</div>
      <div className="setting-value">{value}</div>
    </div>
  );
}

function SummaryBar({ results, createdAt, requestId }: { results: EvaluateResponse["results"]; createdAt?: string; requestId?: string }) {
  const successes = results.filter((r) => r.ok).length;
  const failures = results.length - successes;
  const avgLatency = results.length ? results.reduce((s, r) => s + (r.latency_ms || 0), 0) / results.length : 0;
  return (
    <div className="summary-bar">
      <div className="summary-chip">Run ID: {requestId ?? "n/a"}</div>
      <div className="summary-chip">Created: {createdAt ? new Date(createdAt).toLocaleTimeString() : "n/a"}</div>
      <div className="summary-chip">Avg latency: {avgLatency.toFixed(1)} ms</div>
      <div className="summary-chip success">Succeeded: {successes}</div>
      <div className="summary-chip warn">Failed: {failures}</div>
    </div>
  );
}

export default App;
