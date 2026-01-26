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
          <label key={m.id} className={!m.enabled ? "disabled" : ""}>
            <input
              type="checkbox"
              checked={selected.has(m.id)}
              onChange={() => onToggle(m.id)}
              disabled={!m.enabled}
            />
            {m.id}
            {!m.enabled && <span className="disabled-reason"> (disabled: {m.disabled_reason || "unavailable"})</span>}
          </label>
        ))}
      </div>
    </div>
  );
}
