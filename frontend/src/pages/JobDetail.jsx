import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, RefreshCw, Search, Pencil, Trash2, Send, ChevronDown, ChevronUp, AlertTriangle,
} from "lucide-react";
import { getJob, updateJob, deleteJob, runJobMatch, createInterview } from "../api/client";
import { Chip, ScoreBar, SecurityBadge, Toast } from "../components/ui";
import { errorMessage, scoreColor, useToast } from "../lib/ui";

const SOURCE_LABEL = {
  experience: "Experience",
  project: "Project",
  certification: "Certification",
};

const CATEGORIES = [
  { key: "required", label: "Required" },
  { key: "nice", label: "Nice to have" },
  { key: "soft", label: "Soft skills" },
];

// "Project: REECRUTO (≈ torch, 86%)" — "≈" marks a semantic match found by ChromaDB
function sourceText(src) {
  const base = src.type === "skills" ? src.label : `${SOURCE_LABEL[src.type] || src.type}: ${src.label}`;
  return src.via ? `${base} (≈ ${src.via}, ${Math.round(src.similarity * 100)}%)` : base;
}

const toList = (text) => text.split(",").map(s => s.trim()).filter(Boolean);

function chipKind(score) {
  if (score >= 0.8) return "strong";
  if (score > 0) return "partial";
  return "missing";
}

// ── Skills (view + edit) ──────────────────────────────────────────────────────
function JobEditor({ job, onSave, onCancel, saving }) {
  const [title, setTitle] = useState(job.title);
  const [description, setDescription] = useState(job.description);
  const [skills, setSkills] = useState({
    required: job.skills.required.join(", "),
    nice: job.skills.nice.join(", "),
    soft: job.skills.soft.join(", "),
  });

  const save = () => {
    const payload = {};
    if (title.trim() !== job.title) payload.title = title.trim();
    const newSkills = {
      required: toList(skills.required), nice: toList(skills.nice), soft: toList(skills.soft),
    };
    const skillsChanged = CATEGORIES.some(
      ({ key }) => newSkills[key].join(",") !== job.skills[key].join(",")
    );
    if (skillsChanged) payload.skills = newSkills;
    // A new description re-extracts the skills on the server (unless edited by hand)
    if (description !== job.description) payload.description = description;
    onSave(payload);
  };

  return (
    <div className="card fade-in" style={{ marginBottom: 20 }}>
      <input className="input" value={title} onChange={e => setTitle(e.target.value)} style={{ marginBottom: 12 }} />
      <textarea className="input" value={description} onChange={e => setDescription(e.target.value)}
        rows={6} style={{ resize: "vertical", marginBottom: 12 }} />
      {CATEGORIES.map(({ key, label }) => (
        <label key={key} style={{ display: "block", marginBottom: 10 }}>
          <span style={{ fontSize: 12, color: "var(--text-dim)" }}>{label} (comma separated)</span>
          <input className="input" value={skills[key]}
            onChange={e => setSkills(s => ({ ...s, [key]: e.target.value }))} />
        </label>
      ))}
      <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 14 }}>
        Saving new skills or a new description rescores every CV.
      </p>
      <div style={{ display: "flex", gap: 10 }}>
        <button className="btn-primary" onClick={save} disabled={saving || description.trim().length < 20}
          style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {saving && <span className="spinner" style={{ width: 14, height: 14 }} />} Save
        </button>
        <button className="btn-ghost" onClick={onCancel} disabled={saving}>Cancel</button>
      </div>
    </div>
  );
}

function JobSummary({ job }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card" style={{ marginBottom: 20 }}>
      {CATEGORIES.map(({ key, label }) => job.skills[key].length > 0 && (
        <div key={key} style={{ marginBottom: 12 }}>
          <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 6 }}>{label}</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {job.skills[key].map(s => <Chip key={s}>{s}</Chip>)}
          </div>
        </div>
      ))}
      {job.interview_questions.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 6 }}>
            Interview questions (shared by every candidate, + 1 personal question from each CV)
          </p>
          <ol style={{ paddingLeft: 20, fontSize: 13, color: "var(--text-mid)", lineHeight: 1.7 }}>
            {job.interview_questions.map(q => <li key={q}>{q}</li>)}
          </ol>
        </div>
      )}
      <button className="btn-ghost" onClick={() => setOpen(o => !o)}
        style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, padding: "6px 10px" }}>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {open ? "Hide description" : "Show description"}
      </button>
      {open && (
        <p style={{ whiteSpace: "pre-wrap", fontSize: 14, color: "var(--text-mid)", marginTop: 12, lineHeight: 1.7 }}>
          {job.description}
        </p>
      )}
    </div>
  );
}

// ── One candidate ─────────────────────────────────────────────────────────────
function CandidateRow({ match, rank, job, showToast }) {
  const [expanded, setExpanded] = useState(false);
  const [inviting, setInviting] = useState(false);

  const invite = async () => {
    setInviting(true);
    try {
      await createInterview({
        candidate_name: match.name,
        candidate_email: match.email,
        job_id: job.id,              // shared interview questions for this job
        candidate_id: match.candidate_id, // + a personal question built from the CV
      });
      showToast(`Interview invite sent to ${match.name}.`);
    } catch (err) {
      showToast(errorMessage(err, "Failed to send invite."), "err");
    } finally {
      setInviting(false);
    }
  };

  const bars = [
    { label: "Required", value: match.required_score, color: "var(--blue)" },
    { label: "Nice to have", value: match.nice_score, color: "var(--gold)" },
    { label: "Soft skills", value: match.soft_score, color: "var(--green)" },
  ].filter(b => b.value != null);

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 20px", cursor: "pointer" }}
        onClick={() => setExpanded(e => !e)}>
        <span style={{
          width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
          background: rank === 1 ? "var(--gold)" : "var(--surface2)",
          color: rank === 1 ? "#0a0d13" : "var(--text-mid)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 13,
        }}>{rank}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontWeight: 600 }}>{match.name}</p>
          <p style={{ color: "var(--text-dim)", fontSize: 13 }}>{match.email || "No email"}</p>
        </div>
        {match.flagged && <SecurityBadge reasons={["The CV contains text that tries to instruct the AI — review it."]} />}
        {match.legacy_profile && (
          <span className="badge" title="Extracted with the old format — re-upload this CV"
            style={{ background: "#f0b42915", color: "var(--gold)", border: "1px solid #f0b42930", display: "flex", alignItems: "center", gap: 4 }}>
            <AlertTriangle size={12} /> Re-upload CV
          </span>
        )}
        <p style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 22, color: scoreColor(match.score), flexShrink: 0 }}>
          {match.score.toFixed(0)}<span style={{ fontSize: 14, fontWeight: 400 }}>%</span>
        </p>
        {expanded ? <ChevronUp size={16} color="var(--text-dim)" /> : <ChevronDown size={16} color="var(--text-dim)" />}
      </div>

      {expanded && (
        <div style={{ padding: "0 20px 20px", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "16px 0" }}>
            {bars.map(({ label, value, color }) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 12, color: "var(--text-dim)", width: 100, flexShrink: 0 }}>{label}</span>
                <ScoreBar value={value} color={color} />
                <span style={{ fontSize: 12, color, fontWeight: 600, width: 40, textAlign: "right" }}>{value.toFixed(0)}%</span>
              </div>
            ))}
          </div>

          {/* Evidence per skill */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
            {match.breakdown.map(s => (
              <div key={`${s.category}-${s.skill}`} style={{ display: "flex", alignItems: "baseline", gap: 10, fontSize: 13 }}>
                <span style={{ width: 150, flexShrink: 0 }}>
                  <Chip kind={chipKind(s.score)}>{s.skill}</Chip>
                </span>
                <span style={{ color: "var(--text-dim)", width: 40, flexShrink: 0 }}>{Math.round(s.score * 100)}%</span>
                <span style={{ color: "var(--text-mid)" }}>
                  {s.sources.length
                    ? s.sources.map(sourceText).join(" · ")
                    : "No evidence in the CV"}
                </span>
              </div>
            ))}
          </div>

          {match.reasoning && (
            <p style={{ fontSize: 13, color: "var(--text-mid)", background: "var(--surface2)", padding: "10px 14px",
              borderRadius: "var(--radius)", marginBottom: 14, borderLeft: "3px solid var(--border2)" }}>
              {match.reasoning}
            </p>
          )}

          <button className="btn-primary" onClick={invite} disabled={inviting || !match.email}
            style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {inviting ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Send size={14} />}
            {match.email ? "Send Interview Invite" : "No email on file"}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function JobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null); // "match" | "rescore" | "save" | "delete"
  const [editing, setEditing] = useState(false);
  const [toast, showToast] = useToast();

  useEffect(() => {
    let active = true;
    getJob(jobId)
      .then(({ data }) => active && setJob(data))
      .catch(err => active && showToast(errorMessage(err, "Could not load the job."), "err"))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [jobId, showToast]);

  const match = async (rescoreAll) => {
    setBusy(rescoreAll ? "rescore" : "match");
    try {
      const { data } = await runJobMatch(jobId, rescoreAll);
      setJob(data.job);
      const total = data.scored + data.filtered_out;
      showToast(total === 0 ? "No new CVs to score."
        : `${data.scored} CV${data.scored > 1 ? "s" : ""} scored`
          + (data.filtered_out ? `, ${data.filtered_out} not pre-selected.` : "."));
    } catch (err) {
      showToast(errorMessage(err, "Matching failed."), "err");
    } finally {
      setBusy(null);
    }
  };

  const save = async (payload) => {
    if (Object.keys(payload).length === 0) { setEditing(false); return; }
    setBusy("save");
    try {
      const { data } = await updateJob(jobId, payload);
      setJob(data);
      setEditing(false);
      showToast("Job updated.");
    } catch (err) {
      showToast(errorMessage(err, "Could not update the job."), "err");
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete “${job.title}” and its results?`)) return;
    setBusy("delete");
    try {
      await deleteJob(jobId);
      navigate("/match");
    } catch (err) {
      showToast(errorMessage(err, "Could not delete the job."), "err");
      setBusy(null);
    }
  };

  if (loading && !job) return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
      <span className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  );
  if (!job) return (
    <div>
      <Link to="/match" style={{ color: "var(--text-dim)", display: "inline-flex", alignItems: "center", gap: 6 }}>
        <ArrowLeft size={14} /> Back to jobs
      </Link>
      <Toast toast={toast} />
    </div>
  );

  return (
    <div className="fade-in">
      <Link to="/match" style={{ color: "var(--text-dim)", fontSize: 13, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 14 }}>
        <ArrowLeft size={14} /> All jobs
      </Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: 26, marginBottom: 4 }}>{job.title}</h1>
          <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
            {job.matches.length} candidate{job.matches.length !== 1 ? "s" : ""}
            {job.filtered_out_count > 0 && ` · ${job.filtered_out_count} not pre-selected by semantic search`}
            {" · "}created {new Date(job.created_at).toLocaleDateString()}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn-primary" onClick={() => match(false)} disabled={!!busy || job.pending_count === 0}
            style={{ display: "flex", alignItems: "center", gap: 8 }}
            title="Score only the CVs uploaded since the last search">
            {busy === "match" ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Search size={14} />}
            {job.pending_count > 0 ? `Search ${job.pending_count} new CV${job.pending_count > 1 ? "s" : ""}` : "No new CVs"}
          </button>
          <button className="btn-ghost" onClick={() => match(true)} disabled={!!busy}
            style={{ display: "flex", alignItems: "center", gap: 8 }} title="Rescore every CV">
            {busy === "rescore" ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <RefreshCw size={14} />}
            Rescore all
          </button>
          <button className="btn-ghost" onClick={() => setEditing(e => !e)} disabled={!!busy}
            style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Pencil size={14} /> Edit
          </button>
          <button className="btn-ghost" onClick={remove} disabled={!!busy} aria-label="Delete job"
            style={{ display: "flex", alignItems: "center", color: "var(--red)", borderColor: "#ef444430" }}>
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {editing
        ? <JobEditor job={job} saving={busy === "save"} onSave={save} onCancel={() => setEditing(false)} />
        : <JobSummary job={job} />}

      {job.matches.length === 0 ? (
        <p style={{ color: "var(--text-dim)", textAlign: "center", padding: "32px 0" }}>
          No CVs scored yet — upload CVs, then search.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {job.matches.map((m, i) => (
            <CandidateRow key={m.candidate_id} match={m} rank={i + 1} job={job} showToast={showToast} />
          ))}
        </div>
      )}

      <Toast toast={toast} />
    </div>
  );
}
