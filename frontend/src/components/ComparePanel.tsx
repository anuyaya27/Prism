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

  const pairs = [...compare.pairs].sort((a, b) => a.token_overlap_jaccard - b.token_overlap_jaccard);
  const topDisagreements = pairs.slice(0, 2);

  return (
    <div className="card">
      <div className="response-header">
        <h3 style={{ margin: 0 }}>Comparison</h3>
        {compare.summary?.notes && <span className="badge">{compare.summary.notes}</span>}
      </div>

      <div className="metrics">
        <span className="badge">
          <strong>avg similarity</strong> {compare.summary?.avg_similarity.toFixed(2)}
        </span>
        {compare.summary?.most_disagree_pair && (
          <span className="badge warn">
            <strong>most disagree</strong> {compare.summary.most_disagree_pair.a} vs {compare.summary.most_disagree_pair.b}
          </span>
        )}
      </div>

      {pairs.length === 0 ? (
        <div className="muted">Need at least two responses to show disagreement.</div>
      ) : (
        <>
          <div className="muted small">Lowest token overlap means highest disagreement.</div>
          <div className="pairs">
            {pairs.map((pair) => {
              const tone = pair.token_overlap_jaccard < 0.35 ? "warn" : pair.token_overlap_jaccard < 0.65 ? "mid" : "success";
              return (
                <div className={`pair-row ${tone}`} key={`${pair.a}-${pair.b}`}>
                  <div className="pair-label">
                    <strong>{pair.a}</strong> vs <strong>{pair.b}</strong>
                  </div>
                  <div className="pair-score">
                    jaccard {pair.token_overlap_jaccard.toFixed(2)} · len {pair.length_ratio.toFixed(2)} · kw {pair.keyword_coverage.toFixed(2)}
                  </div>
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
