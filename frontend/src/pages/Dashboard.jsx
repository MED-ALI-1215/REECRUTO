import { useState, useEffect, useMemo } from "react";
import { CheckCircle, XCircle, ChevronDown, ChevronUp, Search, ArrowUpDown } from "lucide-react";
import { getDashboard, acceptCandidate, rejectCandidate } from "../api/client";

const RECOMMENDATIONS = ["All", "Highly Recommended", "Recommended", "Maybe", "Not Recommended"];

const RECO_STYLE = {
  "Highly Recommended": { bg: "#22c55e18", color: "var(--green)",  border: "#22c55e30" },
  "Recommended":        { bg: "#3b82f618", color: "var(--blue)",   border: "#3b82f630" },
  "Maybe":              { bg: "#f0b42918", color: "var(--gold)",   border: "#f0b42930" },
  "Not Recommended":    { bg: "#ef444418", color: "var(--red)",    border: "#ef444430" },
};

function RecoTag({ value }) {
  const s = RECO_STYLE[value] || RECO_STYLE["Maybe"];
  return (
    <span className="badge" style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
      {value || "Maybe"}
    </span>
  );
}

function ScoreRing({ score }) {
  const color = score >= 70 ? "var(--green)" : score >= 45 ? "var(--gold)" : "var(--red)";
  return (
    <div style={{
      width: 52, height: 52, borderRadius: "50%",
      background: `conic-gradient(${color} ${score * 3.6}deg, var(--surface2) 0deg)`,
      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: "50%", background: "var(--surface)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 13, color,
      }}>
        {score?.toFixed(0)}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [results, setResults]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [acting, setActing]     = useState(null);
  const [toast, setToast]       = useState(null);

  // ── Filter / sort state ──────────────────────────────────────────────────
  const [search, setSearch]     = useState("");
  const [recoFilter, setRecoFilter] = useState("All");
  const [sortBy, setSortBy]     = useState("date_desc"); // date_desc | date_asc | score_desc | score_asc

  const showToast = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  useEffect(() => {
    getDashboard()
      .then(({ data }) => setResults(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // ── Derived list ─────────────────────────────────────────────────────────
  const displayed = useMemo(() => {
    let list = [...results];

    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(r =>
        r.candidate_name.toLowerCase().includes(q) ||
        r.candidate_email.toLowerCase().includes(q) ||
        r.job_title.toLowerCase().includes(q)
      );
    }

    // Recommendation filter
    if (recoFilter !== "All") {
      list = list.filter(r => (r.recommendation || "Maybe") === recoFilter);
    }

    // Sort
    list.sort((a, b) => {
      if (sortBy === "score_desc") return b.overall_score - a.overall_score;
      if (sortBy === "score_asc")  return a.overall_score - b.overall_score;
      if (sortBy === "date_asc")   return new Date(a.completed_at) - new Date(b.completed_at);
      return new Date(b.completed_at) - new Date(a.completed_at); // date_desc default
    });

    return list;
  }, [results, search, recoFilter, sortBy]);

  const act = async (id, action) => {
    setActing(id + action);
    try {
      if (action === "accept") await acceptCandidate(id);
      else await rejectCandidate(id);
      showToast(`Email sent — candidate ${action === "accept" ? "accepted" : "rejected"}.`);
    } catch (err) {
      showToast(err.response?.data?.detail || "Action failed.", "err");
    } finally {
      setActing(null);
    }
  };

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
      <span className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  );

  return (
    <div className="fade-in">
      <h1 style={{ fontSize: 26, marginBottom: 4 }}>Dashboard</h1>
      <p style={{ color: "var(--text-dim)", marginBottom: 24 }}>
        Completed interviews — review results and take action.
      </p>

      {/* ── Controls bar ──────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>

        {/* Search */}
        <div style={{ position: "relative", flex: "1 1 200px", minWidth: 180 }}>
          <Search size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-dim)", pointerEvents: "none" }} />
          <input
            className="input"
            placeholder="Search name, email, job…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ paddingLeft: 34 }}
          />
        </div>

        {/* Recommendation filter */}
        <select
          value={recoFilter}
          onChange={e => setRecoFilter(e.target.value)}
          style={{
            background: "var(--surface2)", border: "1px solid var(--border)",
            borderRadius: "var(--radius)", padding: "11px 14px",
            color: recoFilter === "All" ? "var(--text-dim)" : "var(--text)",
            fontSize: 14, cursor: "pointer", flex: "0 0 auto",
          }}
        >
          {RECOMMENDATIONS.map(r => (
            <option key={r} value={r}>{r === "All" ? "All recommendations" : r}</option>
          ))}
        </select>

        {/* Sort */}
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          style={{
            background: "var(--surface2)", border: "1px solid var(--border)",
            borderRadius: "var(--radius)", padding: "11px 14px",
            color: "var(--text)", fontSize: 14, cursor: "pointer", flex: "0 0 auto",
          }}
        >
          <option value="date_desc">Newest first</option>
          <option value="date_asc">Oldest first</option>
          <option value="score_desc">Highest score first</option>
          <option value="score_asc">Lowest score first</option>
        </select>

        {/* Result count */}
        <div style={{ display: "flex", alignItems: "center", color: "var(--text-dim)", fontSize: 13, paddingLeft: 4, flexShrink: 0 }}>
          {displayed.length} result{displayed.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* ── Empty state ────────────────────────────────────────────────── */}
      {displayed.length === 0 && (
        <p style={{ color: "var(--text-dim)", textAlign: "center", padding: "48px 0" }}>
          {results.length === 0 ? "No completed interviews yet." : "No results match your filters."}
        </p>
      )}

      {/* ── Result cards ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {displayed.map(r => (
          <div key={r.id} className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div
              style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 20px", cursor: "pointer" }}
              onClick={() => setExpanded(expanded === r.id ? null : r.id)}
            >
              <ScoreRing score={r.overall_score} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 600 }}>{r.candidate_name}</p>
                <p style={{ color: "var(--text-dim)", fontSize: 13 }}>{r.job_title} · {r.candidate_email}</p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
                <RecoTag value={r.recommendation} />
                <p style={{ fontSize: 12, color: "var(--text-dim)" }}>
                  {new Date(r.completed_at).toLocaleDateString()}
                </p>
                {expanded === r.id
                  ? <ChevronUp size={16} color="var(--text-dim)" />
                  : <ChevronDown size={16} color="var(--text-dim)" />}
              </div>
            </div>

            {expanded === r.id && (
              <div style={{ padding: "0 20px 20px", borderTop: "1px solid var(--border)" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, margin: "16px 0" }}>
                  {[
                    { label: "Summary",   value: r.summary },
                    { label: "Strengths", value: r.strengths },
                  ].map(({ label, value }) => value && (
                    <div key={label} style={{ background: "var(--surface2)", borderRadius: "var(--radius)", padding: "14px 16px" }}>
                      <p style={{ fontSize: 11, color: "var(--text-dim)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>{label}</p>
                      <p style={{ fontSize: 13, color: "var(--text-mid)", lineHeight: 1.6 }}>{value}</p>
                    </div>
                  ))}
                </div>

                {r.red_flags && r.red_flags.toLowerCase() !== "none" && (
                  <div style={{ background: "#ef444410", border: "1px solid #ef444430", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 16 }}>
                    <p style={{ fontSize: 11, color: "var(--red)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Red Flags</p>
                    <p style={{ fontSize: 13, color: "var(--text-mid)" }}>{r.red_flags}</p>
                  </div>
                )}

                <div style={{ display: "flex", gap: 10 }}>
                  <button className="btn-primary"
                    onClick={() => act(r.id, "accept")}
                    disabled={acting === r.id + "accept"}
                    style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {acting === r.id + "accept"
                      ? <span className="spinner" style={{ width: 14, height: 14 }} />
                      : <CheckCircle size={15} />}
                    Accept
                  </button>
                  <button className="btn-ghost"
                    onClick={() => act(r.id, "reject")}
                    disabled={acting === r.id + "reject"}
                    style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--red)", borderColor: "#ef444430" }}>
                    {acting === r.id + "reject"
                      ? <span className="spinner" style={{ width: 14, height: 14 }} />
                      : <XCircle size={15} />}
                    Reject
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", top: 24, right: 24,
          background: toast.type === "err" ? "#ef444418" : "#22c55e18",
          border: `1px solid ${toast.type === "err" ? "var(--red)" : "var(--green)"}`,
          color: toast.type === "err" ? "var(--red)" : "var(--green)",
          padding: "12px 18px", borderRadius: "var(--radius)",
          display: "flex", alignItems: "center", gap: 8,
          fontSize: 14, fontWeight: 500, zIndex: 9999,
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
