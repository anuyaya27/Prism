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
  return (
    <header className="topbar">
      <div className="brand">
        <img
          src="/prism-logo.png"
          alt="PRISM logo"
          className="brand-logo"
          style={{ width: 32, height: 32, borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.25)", objectFit: "cover" }}
        />
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
