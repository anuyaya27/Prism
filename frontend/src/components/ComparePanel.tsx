import { CompareResult } from "../types";

interface Props {
  compare: CompareResult | null;
}

export default function ComparePanel({ compare }: Props) {
  if (!compare) {
    return (
      <div className="card">
        <h3>Comparison</h3>
        <div className="muted">No comparison available.</div>
      </div>
    );
  }

  const pairs = [...compare.pairs].sort((a, b) => a.score - b.score);
  const topDisagreements = pairs.slice(0, 2);

  return (
    <div className="card">
      <div className="response-header">
        <h3 style={{ margin: 0 }}>Comparison</h3>
        {compare.note && <span className="badge">{compare.note}</span>}
      </div>

      {pairs.length === 0 ? (
        <div className="muted">Need at least two responses to show disagreement.</div>
      ) : (
        <>
          <div className="muted small">Lowest scores mean highest disagreement.</div>
          <div className="pairs">
            {pairs.map((pair) => {
              const tone = pair.score < 0.35 ? "warn" : pair.score < 0.65 ? "mid" : "success";
              return (
                <div className={`pair-row ${tone}`} key={`${pair.a}-${pair.b}`}>
                  <div className="pair-label">
                    <strong>{pair.a}</strong> vs <strong>{pair.b}</strong>
                  </div>
                  <div className="pair-score">{pair.score.toFixed(2)}</div>
                </div>
              );
            })}
          </div>

          <div className="muted small" style={{ marginTop: 8 }}>
            Highlighted disagreements:{" "}
            {topDisagreements.map((pair) => `${pair.a} vs ${pair.b}`).join(", ") || "n/a"}
          </div>
        </>
      )}
    </div>
  );
}
