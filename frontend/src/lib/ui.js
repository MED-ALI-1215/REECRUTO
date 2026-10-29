import { useCallback, useState } from "react";

export function scoreColor(score) {
  if (score == null) return "var(--text-dim)";
  return score >= 70 ? "var(--green)" : score >= 45 ? "var(--gold)" : "var(--red)";
}

export function errorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map(d => d.msg).join(", ");
  return detail || fallback;
}

// const [toast, showToast] = useToast();  …  <Toast toast={toast} />
export function useToast() {
  const [toast, setToast] = useState(null);
  const show = useCallback((msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  }, []);
  return [toast, show];
}
