import { CompareResult } from "../types";
import { formatModelLabel } from "../utils/modelLabels";

export default function ComparisonCard({ compare }: { compare: CompareResult }) {
  const pairs = [...(compare?.pairs || [])].sort((a, b) => a.token_overlap_jaccard - b.token_overlap_jaccard);
  const top = pairs[0];
  return (
    <div className="card">
      <div className="card-top">
        <div className="title">Comparison</div>
        <div className="chip">avg sim {compare?.summary?.avg_similarity?.toFixed(2) ?? "n/a"}</div>
      </div>
      {top && (
        <div className="muted small">Most disagree: {formatModelLabel(top.a)} vs {formatModelLabel(top.b)} (jaccard {top.token_overlap_jaccard.toFixed(2)})</div>
      )}
      <div className="pairs">
        {pairs.map((pair) => (
          <div key={`${pair.a}-${pair.b}`} className="pair-row" title={`IDs: ${pair.a} vs ${pair.b}`}>
            <div>
              <strong>{formatModelLabel(pair.a)}</strong> vs <strong>{formatModelLabel(pair.b)}</strong>
            </div>
            <div className="muted small">
              j {pair.token_overlap_jaccard.toFixed(2)} | len {pair.length_ratio.toFixed(2)} | kw {pair.keyword_coverage.toFixed(2)}
            </div>
          </div>
        ))}
        {!pairs.length && <div className="muted">Not enough responses to compare.</div>}
      </div>
    </div>
  );
}
