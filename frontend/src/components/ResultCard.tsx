import { useState } from "react";
import { ModelResult } from "../types";
import { formatModelLabel } from "../utils/modelLabels";

interface Props {
  result: ModelResult;
  showUsage?: boolean;
}

export default function ResultCard({ result, showUsage }: Props) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(result.text || result.error_message || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const label = formatModelLabel(result.model);

  return (
    <div className="card result-card" title={`ID: ${result.model}`}>
      <div className="card-top">
        <div>
          <div className="title">{label}</div>
          <div className="muted small">ID: {result.model}</div>
        </div>
        <div className="chip-row">
          <span className={`chip ${result.ok ? "success" : "warn"}`}>{result.status}</span>
          <span className="chip">{(result.latency_ms ?? 0).toFixed(1)} ms</span>
        </div>
      </div>
      <div className="body">
        {result.error_message ? (
          <div className="error-block">{result.error_message}</div>
        ) : (
          <pre className="code-block">{result.text || "No output returned."}</pre>
        )}
      </div>
      {showUsage && <div className="muted small">usage: {result.usage ? JSON.stringify(result.usage) : "n/a"}</div>}
      <div className="actions">
        <button className="ghost" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
