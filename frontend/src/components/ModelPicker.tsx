import { ModelInfo } from "../types";

interface Props {
  models: ModelInfo[];
  selected: Set<string>;
  onToggle: (id: string) => void;
}

export default function ModelPicker({ models, selected, onToggle }: Props) {
  return (
    <div>
      <strong>Models</strong>
      <div className="model-list">
        {models.map((m) => (
          <label key={m.id} className={!m.available ? "disabled" : ""} title={m.reason || undefined}>
            <input
              type="checkbox"
              checked={selected.has(m.id)}
              onChange={() => onToggle(m.id)}
              disabled={!m.available}
            />
            {m.id}
            {!m.available && <span className="disabled-reason"> (disabled: {m.reason || "unavailable"})</span>}
          </label>
        ))}
      </div>
    </div>
  );
}
