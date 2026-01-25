import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "./api";
import { EvaluateResponse, ModelInfo, ModelResponse } from "./types";

const defaultRequest = {
  temperature: 0,
  max_tokens: 512,
  timeout_s: 15,
};

function App() {
  const [prompt, setPrompt] = useState("Compare the tradeoffs between unit tests and integration tests.");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EvaluateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ModelInfo[]>("/models")
      .then((data) => {
        setModels(data);
        const enabled = new Set(data.filter((m) => m.enabled).map((m) => m.id));
        setSelected(enabled);
      })
      .catch((err) => setError(err.message));
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

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body = {
        prompt,
        models: Array.from(selected),
        ...defaultRequest,
      };
      const data = await apiPost<EvaluateResponse>("/evaluate", body);
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to run evaluation");
    } finally {
      setLoading(false);
    }
  };

  const enabledModels = useMemo(() => models.filter((m) => selected.has(m.id)), [models, selected]);

  return (
    <div className="app">
      <h1>PRISM</h1>
      <p>Fan out prompts across models, view agreement, and see the synthesized answer.</p>

      <div className="card grid">
        <label>
          <strong>Prompt</strong>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Enter your prompt..." />
        </label>
        <div className="grid two-col">
          <div>
            <strong>Models</strong>
            <div className="model-list">
              {models.map((m) => (
                <label key={m.id}>
                  <input
                    type="checkbox"
                    checked={selected.has(m.id)}
                    onChange={() => toggleModel(m.id)}
                    disabled={!m.enabled}
                  />
                  {m.id} {m.enabled ? "" : `(disabled: ${m.disabled_reason || "missing key"})`}
                </label>
              ))}
            </div>
          </div>
          <div>
            <strong>Request params</strong>
            <div className="badge">temp: {defaultRequest.temperature}</div>
            <div className="badge">max_tokens: {defaultRequest.max_tokens}</div>
            <div className="badge">timeout: {defaultRequest.timeout_s}s</div>
          </div>
        </div>
        <div>
          <button onClick={handleRun} disabled={loading || !prompt.trim() || selected.size === 0}>
            {loading ? "Running..." : "Run evaluation"}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      {result && (
        <>
          <div className="card">
            <h3>Synthesized response</h3>
            <div className="badge">strategy: {result.synthesis.strategy}</div>
            <p>{result.synthesis.response}</p>
            <p style={{ color: "#475569", fontSize: 13 }}>{result.synthesis.explain}</p>
          </div>

          <div className="card">
            <h3>Metrics</h3>
            <div className="metrics">
              <Metric label="agreement" value={result.metrics.agreement.toFixed(2)} />
              <Metric label="unique_responses" value={result.metrics.unique_responses} />
              <Metric label="jaccard" value={result.metrics.similarity.toFixed(2)} />
              <Metric
                label="semantic"
                value={result.metrics.semantic_similarity !== null ? result.metrics.semantic_similarity?.toFixed(2) : "n/a"}
              />
              <Metric label="avg_length" value={result.metrics.average_length.toFixed(1)} />
            </div>
          </div>

          <div className="responses">
            {result.responses.map((r) => (
              <ResponseCard key={r.id} response={r} />
            ))}
          </div>
        </>
      )}

      {!result && enabledModels.length > 0 && (
        <div style={{ marginTop: 12, color: "#475569", fontSize: 13 }}>
          Selected models: {enabledModels.map((m) => m.id).join(", ")}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="badge">
      <strong>{label}</strong> {value}
    </div>
  );
}

function ResponseCard({ response }: { response: ModelResponse }) {
  return (
    <div className="card">
      <div className="response-header">
        <span>
          {response.id} {response.provider ? `(${response.provider})` : ""}
        </span>
        <span className="badge">{response.latency_ms.toFixed(1)} ms</span>
      </div>
      {response.error ? <div className="error">{response.error}</div> : <div>{response.text}</div>}
      <div style={{ marginTop: 8, color: "#475569", fontSize: 12 }}>
        finish: {response.finish_reason || "n/a"} | usage: {response.usage ? JSON.stringify(response.usage) : "n/a"}
      </div>
    </div>
  );
}

export default App;
