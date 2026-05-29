import { useState } from "react";
import { Search, Send, ChevronDown, ChevronUp, Zap } from "lucide-react";
import { matchCandidates, createInterview } from "../api/client";

function ScoreBar({ value, color }) {
  return (
    <div style={{ background: "var(--surface2)", borderRadius: 4, height: 5, overflow: "hidden", flex: 1 }}>
      <div style={{ width: `${value}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.6s ease" }} />
    </div>
  );
}

function ScoreColor(score) {
  return score >= 70 ? "var(--green)" : score >= 45 ? "var(--gold)" : "var(--red)";
}

export default function MatchPage() {
  const [jd, setJd] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [inviting, setInviting] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const search = async () => {
    if (!jd.trim()) return;
    setLoading(true); setResults([]);
    try {
      const { data } = await matchCandidates(jd, 5, false);
      setResults(data);
    } catch (err) {
      showToast(err.response?.data?.detail || "Matching failed.", "err");
    } finally {
      setLoading(false);
    }
  };

  const invite = async (c) => {
    if (!jobTitle.trim()) { showToast("Enter a job title first.", "err"); return; }
    setInviting(c.id);
    try {
      await createInterview({
        candidate_name: c.name,
        candidate_email: c.email || "",
        job_title: jobTitle,
        job_description: jd,
      });
      showToast(`Interview invite sent to ${c.name}.`);
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to send invite.", "err");
    } finally {
      setInviting(null);
    }
  };

  return (
    <div className="fade-in">
      <h1 style={{ fontSize: 26, marginBottom: 4 }}>Job Matcher</h1>
      <p style={{ color: "var(--text-dim)", marginBottom: 28 }}>
        Paste a job description to find the best matching candidates.
      </p>

      {/* Input section */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
          <input className="input" placeholder="Job title (e.g. Backend Engineer)"
            value={jobTitle} onChange={e => setJobTitle(e.target.value)}
            style={{ flex: "0 0 260px" }} />
        </div>
        <textarea className="input" placeholder="Paste the full job description here…"
          value={jd} onChange={e => setJd(e.target.value)}
          rows={5} style={{ resize: "vertical", marginBottom: 14 }} />
        <button className="btn-primary" onClick={search} disabled={loading || !jd.trim()}
          style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : <Search size={15} />}
          {loading ? "Matching…" : "Find Candidates"}
        </button>
      </div>

      {/* Results */}
      {results.length === 0 && !loading && (
        <p style={{ color: "var(--text-dim)", textAlign: "center", padding: "24px 0" }}>
          {jd ? "No matching candidates found." : "Enter a job description to begin."}
        </p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {results.map((c, i) => (
          <div key={c.id} className="card" style={{ padding: 0, overflow: "hidden" }}>
            {/* Header row */}
            <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "18px 20px", cursor: "pointer" }}
              onClick={() => setExpanded(expanded === c.id ? null : c.id)}>
              {/* Rank */}
              <span style={{
                width: 28, height: 28, borderRadius: "50%", background: i === 0 ? "var(--gold)" : "var(--surface2)",
                color: i === 0 ? "#0a0d13" : "var(--text-mid)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 13, flexShrink: 0,
              }}>{i + 1}</span>

              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 600 }}>{c.name}</p>
                <p style={{ color: "var(--text-dim)", fontSize: 13 }}>{c.email || "No email"}</p>
              </div>

              {/* Score */}
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <p style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 22,
                  color: ScoreColor(c.match_score) }}>
                  {c.match_score?.toFixed(0)}<span style={{ fontSize: 14, fontWeight: 400 }}>%</span>
                </p>
                <p style={{ fontSize: 11, color: "var(--text-dim)" }}>match</p>
              </div>

              {expanded === c.id ? <ChevronUp size={16} color="var(--text-dim)" /> : <ChevronDown size={16} color="var(--text-dim)" />}
            </div>

            {/* Expanded detail */}
            {expanded === c.id && (
              <div style={{ padding: "0 20px 20px", borderTop: "1px solid var(--border)" }}>
                {/* Score breakdown */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "16px 0" }}>
                  {[
                    { label: "Skills match", value: c.skills_score, color: "var(--blue)" },
                    { label: "Vector similarity", value: c.vector_score, color: "var(--gold)" },
                    { label: "Certifications", value: c.cert_score, color: "var(--green)" },
                  ].map(({ label, value, color }) => (
                    <div key={label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span style={{ fontSize: 12, color: "var(--text-dim)", width: 120, flexShrink: 0 }}>{label}</span>
                      <ScoreBar value={value} color={color} />
                      <span style={{ fontSize: 12, color, fontWeight: 600, width: 36, textAlign: "right" }}>
                        {value?.toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>

                {/* Matched / missing skills */}
                {c.matched_skills?.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 6 }}>Matched skills</p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {c.matched_skills.map(s => (
                        <span key={s} className="badge" style={{ background: "#22c55e15", color: "var(--green)", border: "1px solid #22c55e30" }}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {c.missing_skills?.length > 0 && (
                  <div style={{ marginBottom: 14 }}>
                    <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 6 }}>Missing skills</p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {c.missing_skills.map(s => (
                        <span key={s} className="badge" style={{ background: "#ef444415", color: "var(--red)", border: "1px solid #ef444430" }}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}

                {c.reasoning && (
                  <p style={{ fontSize: 13, color: "var(--text-mid)", background: "var(--surface2)",
                    padding: "10px 14px", borderRadius: "var(--radius)", marginBottom: 14,
                    borderLeft: "3px solid var(--border2)" }}>
                    {c.reasoning}
                  </p>
                )}

                <button className="btn-primary" onClick={() => invite(c)}
                  disabled={inviting === c.id || !c.email}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {inviting === c.id ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Send size={14} />}
                  {c.email ? "Send Interview Invite" : "No email on file"}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {toast && (
        <div style={{
          position: "fixed", bottom: 24, right: 24,
          background: toast.type === "err" ? "#ef444418" : "#22c55e18",
          border: `1px solid ${toast.type === "err" ? "var(--red)" : "var(--green)"}`,
          color: toast.type === "err" ? "var(--red)" : "var(--green)",
          padding: "12px 18px", borderRadius: "var(--radius)",
          display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500,
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
