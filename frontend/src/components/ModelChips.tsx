import { ModelInfo } from "../types";
import { formatModelLabel } from "../utils/modelLabels";

interface Props {
  models: ModelInfo[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  loading?: boolean;
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

  return (
    <div className="chip-list">
      {models.map((model) => {
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
            <span className="chip-label">{friendly}</span>
            <span className="chip-sub">ID: {model.id}</span>
          </button>
        );
      })}
    </div>
  );
}
