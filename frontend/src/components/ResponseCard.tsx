import { useState } from "react";
import { ModelResponse } from "../types";

interface Props {
  response: ModelResponse;
}

export default function ResponseCard({ response }: Props) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(response.text || response.error || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="card">
      <div className="response-header">
        <span className="title">
          {response.id} {response.provider ? `(${response.provider})` : ""}
        </span>
        <span className="badge">{response.latency_ms.toFixed(1)} ms</span>
      </div>
      <div className="meta">
        <span>finish: {response.finish_reason || "n/a"}</span>
        <span>usage: {response.usage ? JSON.stringify(response.usage) : "n/a"}</span>
      </div>
      {response.error ? <div className="error">{response.error}</div> : <pre className="response-text">{response.text}</pre>}
      <div className="actions">
        <button className="ghost" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
