import React, { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, debugPing, getModels, postEvaluate } from "./api/client";
import ComparePanel from "./components/ComparePanel";
import ModelPicker from "./components/ModelPicker";
import ModelResultCard from "./components/ModelResultCard";
import SynthesisCard from "./components/SynthesisCard";
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
  const [lastModelsStatus, setLastModelsStatus] = useState<"idle" | "success" | "error">("idle");
  const [lastModelsError, setLastModelsError] = useState<string | null>(null);
  const [pingResult, setPingResult] = useState<string | null>(null);
  const [pingError, setPingError] = useState<string | null>(null);
  const [pingLoading, setPingLoading] = useState(false);
  const [formErrors, setFormErrors] = useState<{ prompt?: string; models?: string }>({});
  const [showUsage, setShowUsage] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null);

  useEffect(() => {
    const loadModels = async () => {
      setModelsLoading(true);
      try {
        const data = await getModels();
        const safeModels = Array.isArray((data as any)?.models) ? (data as any).models : Array.isArray(data) ? data : [];
        setModels(safeModels);
        const defaults = ["mock:echo", "mock:pseudo"].filter((id) => safeModels.some((m: ModelInfo) => m.id === id && m.available));
        const enabledFallback = safeModels.filter((m: ModelInfo) => m.available).map((m: ModelInfo) => m.id);
        const initial = new Set(defaults.length ? defaults : enabledFallback);
        setSelected(initial);
        const unavailable = safeModels.find((m: ModelInfo) => !m.available && m.reason);
        setUnavailableReason(unavailable ? unavailable.reason || "Some providers are unavailable." : null);
        setRunError(null);
        setLastModelsStatus("success");
        setLastModelsError(null);
      } catch (err: any) {
        console.error("Failed to load models", err);
        const message = err?.message || "Failed to load models";
        const isUnreachable = message.toLowerCase().includes("failed to fetch");
        const reason = isUnreachable ? "Backend unreachable or blocked by CORS" : message;
        setRunError(`Failed to load models from ${API_BASE_URL}. ${reason}. Check backend is running at ${API_BASE_URL} and CORS allows localhost:5173.`);
        setLastModelsStatus("error");
        setLastModelsError(message);
        setModels([]);
        setSelected(new Set());
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
      return next;
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
    } catch (err: any) {
      console.error("Ping failed", err);
      const message = err?.message || "Failed to fetch";
      const isUnreachable = message.toLowerCase().includes("failed to fetch");
      const hint = isUnreachable ? "Backend unreachable or CORS blocked." : message;
      setPingError(`${hint} (base: ${API_BASE_URL})`);
    } finally {
      setPingLoading(false);
    }
  };

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
    <div className="app">
      <header>
        <div>
          <h1>PRISM</h1>
          <p>Multi-LLM Evaluation &amp; Response Synthesis</p>
        </div>
        <div className="connection">
          <div className="muted">Connection</div>
          <div className="connection-row">
            <span className="badge">API: {API_BASE_URL}</span>
          </div>
          <div className="connection-row">
            <span className={`badge ${lastModelsStatus === "success" ? "success" : lastModelsStatus === "error" ? "warn" : ""}`}>
              /models: {lastModelsStatus === "idle" ? "pending" : lastModelsStatus}
            </span>
            {pingResult && <span className="badge success">ping ok</span>}
            {pingError && <span className="badge warn">ping failed</span>}
            <button className="ghost" onClick={testConnection} disabled={pingLoading}>
              {pingLoading ? "Testing..." : "Test connection"}
            </button>
          </div>
          {lastModelsError && <span className="muted small">models error: {lastModelsError}</span>}
          {pingResult && <div className="muted small">ping: {pingResult}</div>}
          {pingError && <div className="error small">ping error: {pingError}</div>}
        </div>
      </header>

      {modelsLoading && <div className="spinner">Loading models...</div>}

      {runError && (
        <div className="banner error-banner">
          <span>{runError}</span>
          <button className="ghost" onClick={() => setRunError(null)}>
            x
          </button>
        </div>
      )}

      {timeoutBanner && (
        <div className="banner warn-banner">
          <span>{timeoutBanner}</span>
          <button className="ghost" onClick={() => setTimeoutBanner(null)}>
            x
          </button>
        </div>
      )}

      {unavailableReason && (
        <div className="banner warn-banner">
          <span>Some providers unavailable: {unavailableReason}</span>
        </div>
      )}

      <div className="card grid">
        <label>
          <strong>Prompt</strong>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter a prompt to evaluate across models..."
            required
          />
          {formErrors.prompt && <div className="error small">{formErrors.prompt}</div>}
        </label>

        <ModelPicker models={models} selected={selected} onToggle={toggleModel} />
        {formErrors.models && <div className="error small">{formErrors.models}</div>}
        {!runError && models.length === 0 && !modelsLoading && <div className="muted">No models available.</div>}

        <div className="controls">
          <button onClick={handleRun} disabled={running}>
            {running ? "Running..." : "Run"}
          </button>
          <div className="badges">
            <span className="badge">temp: {requestDefaults.temperature}</span>
            <span className="badge">max_tokens: {requestDefaults.max_tokens}</span>
            <span className="badge">timeout: {requestDefaults.timeout_s}s</span>
            <select value={synthesisMethod} onChange={(e) => setSynthesisMethod(e.target.value as SynthesisMethod)}>
              <option value="longest_nonempty">longest_nonempty</option>
              <option value="consensus_overlap">consensus_overlap</option>
              <option value="best_of_n">best_of_n</option>
            </select>
          </div>
        </div>
      </div>

      <section className="results-section">
        <div className="section-header">
          <h2>Results</h2>
          {running && <span className="badge">Running...</span>}
          {result && <span className="badge">request_id: {result.request_id}</span>}
          <div className="chip-row">
            <label className="muted small">
              <input type="checkbox" checked={showUsage} onChange={(e) => setShowUsage(e.target.checked)} /> show usage
            </label>
            <label className="muted small">
              <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} /> show raw JSON
            </label>
            <button className="ghost" onClick={exportJson} disabled={!result}>
              Export JSON
            </button>
            <button className="ghost" onClick={copyAll} disabled={!result}>
              Copy all
            </button>
          </div>
        </div>

        {!result && (
          <div className="card muted">
            {runError ? "Backend offline or failed request. Adjust settings and retry." : "Run an evaluation to see model outputs."}
          </div>
        )}

        {result && (
          <>
            <SummaryBar results={result.results} createdAt={result.created_at} />

            <div className="responses">
              {result.results.map((r) => (
                <ModelResultCard key={r.model} result={r} showUsage={showUsage} />
              ))}
            </div>

            <div className="grid two-col">
              <SynthesisCard synthesis={result.synthesis} />
              <ComparePanel compare={result.compare} />
            </div>

            {showRaw && (
              <pre className="response-text scrollable raw-block">{JSON.stringify(result, null, 2)}</pre>
            )}
          </>
        )}
      </section>
    </div>
  );
}

function SummaryBar({ results, createdAt }: { results: EvaluateResponse["results"]; createdAt?: string }) {
  const successes = results.filter((r) => r.ok).length;
  const failures = results.length - successes;
  const avgLatency = results.length ? results.reduce((s, r) => s + (r.latency_ms || 0), 0) / results.length : 0;
  return (
    <div className="card summary">
      <div className="badge">created: {createdAt ? new Date(createdAt).toLocaleTimeString() : "n/a"}</div>
      <div className="badge">avg latency: {avgLatency.toFixed(1)} ms</div>
      <div className="badge success">success: {successes}</div>
      <div className="badge warn">failed: {failures}</div>
    </div>
  );
}

export default App;
