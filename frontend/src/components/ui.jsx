export function ScoreBar({ value, color }) {
  return (
    <div style={{ background: "var(--surface2)", borderRadius: 4, height: 5, overflow: "hidden", flex: 1 }}>
      <div style={{ width: `${value ?? 0}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.6s ease" }} />
    </div>
  );
}

const CHIP_STYLES = {
  strong:  { background: "#22c55e15", color: "var(--green)", border: "1px solid #22c55e30" },
  partial: { background: "#f0b42915", color: "var(--gold)",  border: "1px solid #f0b42930" },
  missing: { background: "#ef444415", color: "var(--red)",   border: "1px solid #ef444430" },
  neutral: { background: "var(--surface2)", color: "var(--text-mid)", border: "1px solid var(--border)" },
};

export function Chip({ children, kind = "neutral", title }) {
  return (
    <span className="badge" title={title} style={CHIP_STYLES[kind]}>
      {children}
    </span>
  );
}

export function Toast({ toast }) {
  if (!toast) return null;
  return (
    <div style={{
      position: "fixed", bottom: 24, right: 24, zIndex: 9999,
      background: toast.type === "err" ? "#ef444418" : "#22c55e18",
      border: `1px solid ${toast.type === "err" ? "var(--red)" : "var(--green)"}`,
      color: toast.type === "err" ? "var(--red)" : "var(--green)",
      padding: "12px 18px", borderRadius: "var(--radius)",
      fontSize: 14, fontWeight: 500,
    }}>
      {toast.msg}
    </div>
  );
}
