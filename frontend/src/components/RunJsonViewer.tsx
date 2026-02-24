import React, { useEffect, useState } from "react";
import { EvaluateResponse } from "../types";
import { API_BASE_URL } from "../api/client";

interface Props {
  runId: string | null;
}

export default function RunJsonViewer({ runId }: Props) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !runId) return;
    const fetchRun = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE_URL}/runs/${runId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setData(await res.json());
      } catch (err: any) {
        setError(err?.message || "Failed to load run");
      } finally {
        setLoading(false);
      }
    };
    fetchRun();
  }, [open, runId]);

  return (
    <div className="card">
      <div className="response-header">
        <h3 style={{ margin: 0 }}>Run JSON</h3>
        <button className="ghost" disabled={!runId} onClick={() => setOpen((v) => !v)}>
          {open ? "Hide" : "View"}
        </button>
      </div>
      {!runId && <div className="muted">Run ID missing.</div>}
      {runId && open && (
        <div className="run-json">
          {loading && <div className="muted">Loading…</div>}
          {error && <div className="error-block">{error}</div>}
          {!loading && !error && <pre className="scrollable" style={{ maxHeight: 280 }}>{JSON.stringify(data, null, 2)}</pre>}
        </div>
      )}
    </div>
  );
}
