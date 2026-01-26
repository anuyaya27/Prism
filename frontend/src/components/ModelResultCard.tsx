import { useMemo, useState } from "react";
import { ModelResult } from "../types";

interface Props {
  result: ModelResult;
  showUsage?: boolean;
}

export default function ModelResultCard({ result, showUsage = false }: Props) {
  const [copied, setCopied] = useState(false);
  const statusClass = useMemo(() => {
    if (result.status === "success") return "status success";
    if (result.status === "timeout") return "status timeout";
    return "status error";
  }, [result.status]);

  const text = result.text || "";
  const errorText = result.error_message;

  const copy = async () => {
    const content = text || errorText || "";
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className="card model-card">
      <div className="response-header">
        <div className="title-group">
          <span className="title">{result.model}</span>
          {result.provider && <span className="muted small">via {result.provider}</span>}
        </div>
        <div className="chip-row">
          <span className={statusClass}>{result.status}</span>
          {typeof result.latency_ms === "number" && (
            <span className="badge">{result.latency_ms.toFixed(1)} ms</span>
          )}
        </div>
      </div>

      {errorText ? (
        <div className="error-block">
          <div className="error">{errorText}</div>
          {result.error_code && <div className="muted small">code: {result.error_code}</div>}
        </div>
      ) : (
        <pre className="response-text scrollable">{text || "No output returned."}</pre>
      )}

      {showUsage && (
        <div className="muted small usage">
          usage: {result.usage ? JSON.stringify(result.usage) : "n/a"}
        </div>
      )}

      <div className="actions">
        <button className="ghost" onClick={copy} disabled={!text && !errorText}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
