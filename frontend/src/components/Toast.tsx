import { useEffect, useRef } from "react";

interface Props {
  message: string;
  tone?: "success" | "error" | "info" | "warning";
  duration?: number;
  onClose?: () => void;
}

export default function Toast({ message, tone = "info", duration = 4000, onClose }: Props) {
  const timeoutRef = useRef<number | undefined>();

  useEffect(() => {
    if (!duration) return;

    timeoutRef.current = window.setTimeout(() => {
      onClose?.();
    }, duration);

    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, [duration, onClose]);

  return (
    <div
      role="status"
      aria-live="polite"
      className={`toast toast-${tone}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.75rem 1rem",
        borderRadius: "8px",
        color: "#0f172a",
        backgroundColor:
          tone === "success"
            ? "#dcfce7"
            : tone === "error"
            ? "#fee2e2"
            : tone === "warning"
            ? "#fef3c7"
            : "#e0f2fe",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.08)",
        minWidth: "240px",
      }}
    >
      <strong style={{ textTransform: "capitalize" }}>{tone}</strong>
      <span style={{ flex: 1 }}>{message}</span>
      {onClose && (
        <button
          type="button"
          aria-label="Dismiss"
          onClick={onClose}
          style={{
            appearance: "none",
            border: "none",
            background: "transparent",
            cursor: "pointer",
            fontSize: "1rem",
            color: "inherit",
            padding: 0,
          }}
        >
          x
        </button>
      )}
    </div>
  );
}