import { useState } from "react";
import { ModelResult } from "../types";
import { formatModelLabel } from "../utils/modelLabels";

interface Props {
  response: ModelResult;
}

export default function ResponseCard({ response }: Props) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(response.text || response.error_message || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const label = formatModelLabel(response.model);

  return (
    <div className="card" title={`ID: ${response.model}`}>
      <div className="response-header">
        <span className="title">{label}</span>
        <span className="badge">{(response.latency_ms ?? 0).toFixed(1)} ms</span>
      </div>
      <div className="meta">
        <span>ID: {response.model}</span>
        <span>status: {response.status}</span>
      </div>
      {response.error_message ? <div className="error">{response.error_message}</div> : <pre className="response-text">{response.text}</pre>}
      <div className="actions">
        <button className="ghost" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
