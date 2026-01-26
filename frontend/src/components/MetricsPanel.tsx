import { CompareResult, ModelResult } from "../types";

interface Props {
  results: ModelResult[];
  compare: CompareResult | null;
}

export default function MetricsPanel({ results, compare }: Props) {
  const successes = results.filter((r) => r.ok).length;
  const avgLatency = results.length ? results.reduce((s, r) => s + (r.latency_ms || 0), 0) / results.length : 0;
  const topDisagreement = compare?.pairs?.[0];

  return (
    <div className="card">
      <h3>Quick Metrics</h3>
      <div className="metrics">
        <Metric label="models" value={results.length} />
        <Metric label="success" value={successes} />
        <Metric label="failed" value={results.length - successes} />
        <Metric label="avg latency (ms)" value={avgLatency.toFixed(1)} />
        <Metric
          label="lowest jaccard"
          value={topDisagreement ? `${topDisagreement.a} vs ${topDisagreement.b}: ${topDisagreement.score.toFixed(2)}` : "n/a"}
        />
      </div>
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
