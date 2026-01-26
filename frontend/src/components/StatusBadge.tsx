interface Props {
  label: string;
  state: "idle" | "ok" | "error";
}

const stateLabel: Record<Props["state"], string> = {
  idle: "Checking",
  ok: "Connected",
  error: "Offline",
};

export default function StatusBadge({ label, state }: Props) {
  const tone = state === "ok" ? "success" : state === "error" ? "warn" : "idle";
  return <span className={`chip ${tone}`}>{label}: {stateLabel[state]}</span>;
}
