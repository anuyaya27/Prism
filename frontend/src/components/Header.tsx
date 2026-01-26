import { useState } from "react";
import StatusBadge from "./StatusBadge";

type Props = {
  apiBase: string;
  modelsStatus: "idle" | "ok" | "error";
  healthStatus: "idle" | "ok" | "error";
  onTestConnection: () => void;
  testing: boolean;
  pingResult?: string | null;
  pingError?: string | null;
};

export default function Header({ apiBase, modelsStatus, healthStatus, onTestConnection, testing, pingResult, pingError }: Props) {
  const [logoOk, setLogoOk] = useState(true);

  const logoSize = "clamp(36px, 6vw, 44px)";
  const logoStyle = {
    width: logoSize,
    height: logoSize,
    borderRadius: 12,
    boxShadow: "0 10px 28px rgba(0,0,0,0.35)",
    objectFit: "cover" as const,
  };

  return (
    <header className="topbar">
      <div className="brand" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {logoOk ? (
          <img
            src="/prism-logo.png"
            alt="PRISM logo"
            className="brand-logo"
            style={logoStyle}
            onError={() => setLogoOk(false)}
          />
        ) : (
          <div
            aria-label="PRISM logo fallback"
            style={{
              ...logoStyle,
              background: "#111827",
              color: "#f9fafb",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 14,
              boxShadow: "0 10px 28px rgba(0,0,0,0.35)",
            }}
          >
            P
          </div>
        )}
        <div>
          <div className="brand-title">PRISM</div>
          <div className="brand-sub">Multi-LLM Evaluation &amp; Response Synthesis</div>
        </div>
      </div>
      <div className="connection-card">
        <div className="muted small">API</div>
        <div className="endpoint">{apiBase}</div>
        <div className="badge-row">
          <StatusBadge label="Models" state={modelsStatus} />
          <StatusBadge label="Health" state={healthStatus} />
        </div>
        <div className="badge-row">
          {pingResult && <span className="chip success">ping ok</span>}
          {pingError && <span className="chip warn">ping failed</span>}
          <button className="ghost" onClick={onTestConnection} disabled={testing}>
            {testing ? "Checking..." : "Check API"}
          </button>
        </div>
      </div>
    </header>
  );
}
