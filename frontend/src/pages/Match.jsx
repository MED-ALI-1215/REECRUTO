import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, X, Users, Sparkles } from "lucide-react";
import { listJobs, createJob } from "../api/client";
import { Chip, Toast } from "../components/ui";
import { errorMessage, scoreColor, useToast } from "../lib/ui";

function NewJobForm({ onCancel, onCreated, showToast }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      const { data } = await createJob(title.trim(), description);
      onCreated(data);
    } catch (err) {
      showToast(errorMessage(err, "Could not create the job."), "err");
      setSaving(false);
    }
  };

  return (
    <div className="card fade-in" style={{ marginBottom: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h3 style={{ fontSize: 17 }}>New job</h3>
        <button className="btn-ghost" onClick={onCancel} disabled={saving} aria-label="Cancel"
          style={{ padding: 6, display: "flex" }}>
          <X size={16} />
        </button>
      </div>
      <input className="input" placeholder="Job title (optional — extracted from the description)"
        value={title} onChange={e => setTitle(e.target.value)} style={{ marginBottom: 12 }} />
      <textarea className="input" placeholder="Paste the full job description here…"
        value={description} onChange={e => setDescription(e.target.value)}
        rows={8} style={{ resize: "vertical", marginBottom: 14 }} />
      <button className="btn-primary" onClick={submit}
        disabled={saving || description.trim().length < 20}
        style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {saving ? <span className="spinner" style={{ width: 16, height: 16 }} /> : <Sparkles size={15} />}
        {saving ? "Extracting skills & scoring CVs…" : "Save & find candidates"}
      </button>
    </div>
  );
}

function JobCard({ job, onOpen }) {
  return (
    <button onClick={onOpen} className="card" style={{
      textAlign: "left", color: "inherit", display: "flex", flexDirection: "column", gap: 12,
      cursor: "pointer", border: "1px solid var(--border)", transition: "border-color 0.2s",
    }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--border2)")}
      onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <h3 style={{ fontSize: 16, lineHeight: 1.3 }}>{job.title}</h3>
        {job.best_score != null && (
          <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 18, color: scoreColor(job.best_score), flexShrink: 0 }}
            title="Best candidate score">
            {job.best_score.toFixed(0)}%
          </span>
        )}
      </div>
      <p style={{ fontSize: 13, color: "var(--text-dim)", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
        {job.description_preview}
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {job.required_skills.slice(0, 6).map(s => <Chip key={s}>{s}</Chip>)}
        {job.required_skills.length > 6 && <Chip>+{job.required_skills.length - 6}</Chip>}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, color: "var(--text-dim)", marginTop: "auto" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Users size={13} /> {job.candidates_count} candidate{job.candidates_count !== 1 ? "s" : ""}
        </span>
        {job.pending_count > 0
          ? <span style={{ color: "var(--gold)" }}>{job.pending_count} new CV{job.pending_count !== 1 ? "s" : ""}</span>
          : <span>{new Date(job.created_at).toLocaleDateString()}</span>}
      </div>
    </button>
  );
}

export default function MatchPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [toast, showToast] = useToast();

  useEffect(() => {
    listJobs()
      .then(({ data }) => setJobs(data))
      .catch(err => showToast(errorMessage(err, "Could not load jobs."), "err"))
      .finally(() => setLoading(false));
  }, [showToast]);

  return (
    <div className="fade-in">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 28, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: 26, marginBottom: 4 }}>Job Matcher</h1>
          <p style={{ color: "var(--text-dim)" }}>Saved job descriptions and their best candidates.</p>
        </div>
        {!creating && (
          <button className="btn-primary" onClick={() => setCreating(true)}
            style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Plus size={16} /> New job
          </button>
        )}
      </div>

      {creating && (
        <NewJobForm
          showToast={showToast}
          onCancel={() => setCreating(false)}
          onCreated={job => navigate(`/match/${job.id}`)}
        />
      )}

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", paddingTop: 60 }}>
          <span className="spinner" style={{ width: 32, height: 32 }} />
        </div>
      ) : jobs.length === 0 && !creating ? (
        <p style={{ color: "var(--text-dim)", textAlign: "center", padding: "48px 0" }}>
          No saved jobs yet — click “New job” to add one.
        </p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {jobs.map(job => <JobCard key={job.id} job={job} onOpen={() => navigate(`/match/${job.id}`)} />)}
        </div>
      )}

      <Toast toast={toast} />
    </div>
  );
}
