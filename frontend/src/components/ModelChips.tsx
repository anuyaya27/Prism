import { ModelInfo } from "../types";
import { formatModelLabel } from "../utils/modelLabels";

interface Props {
  models: ModelInfo[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  loading?: boolean;
}

type Group = { provider: string; items: ModelInfo[] };

function groupByProvider(models: ModelInfo[]): Group[] {
  const groups: Record<string, ModelInfo[]> = {};
  models.forEach((m) => {
    const key = m.provider || m.id.split(":")[0] || "Other";
    if (!groups[key]) groups[key] = [];
    groups[key].push(m);
  });
  return Object.entries(groups).map(([provider, items]) => ({ provider, items }));
}

export default function ModelChips({ models, selected, onToggle, loading }: Props) {
  if (loading) {
    return (
      <div className="chip-list">
        {Array.from({ length: 4 }).map((_, idx) => (
          <div key={idx} className="chip skeleton" />
        ))}
      </div>
    );
  }

  if (!models.length) {
    return <div className="muted">No models detected.</div>;
  }

  const grouped = groupByProvider(models);

  return (
    <div className="chip-list">
      {grouped.map((group) => (
        <div key={group.provider} className="chip-group">
          <div className="chip-group-label">{group.provider}</div>
          <div className="chip-group-row">
            {group.items.map((model) => {
              const active = selected.has(model.id) && model.available;
              const friendly = formatModelLabel(model.id);
              const title = model.reason ? `${friendly} • ${model.reason}` : friendly;
              return (
                <button
                  key={model.id}
                  className={`chip ${active ? "active" : ""} ${!model.available ? "disabled" : ""}`}
                  onClick={() => onToggle(model.id)}
                  disabled={!model.available}
                  title={title}
                >
                  <span className="chip-label">
                    {active && <span className="chip-check">&#10003;</span>}
                    {friendly}
                  </span>
                  <span className="chip-sub">ID: {model.id}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
