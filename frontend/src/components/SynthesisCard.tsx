import { useMemo, useState } from "react";
import { SynthesisPayload } from "../types";

export default function SynthesisCard({ synthesis }: { synthesis: SynthesisPayload }) {
  const [copied, setCopied] = useState(false);
  const text = synthesis.text || "";
  const hasContent = synthesis.ok && !!text;
  const badgeClass = useMemo(() => (synthesis.ok ? "badge success" : "badge warn"), [synthesis.ok]);

  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className="card">
      <div className="response-header">
        <h3 style={{ margin: 0 }}>Synthesis</h3>
        <div className="chip-row">
          <span className={badgeClass}>{synthesis.method}</span>
          {synthesis.rationale && <span className="badge">{synthesis.rationale}</span>}
        </div>
      </div>
      <pre className="response-text scrollable">{hasContent ? text : "Synthesis unavailable (no usable responses)."}</pre>
      <div className="actions">
        <button className="ghost" onClick={copy} disabled={!hasContent}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
