import { useState, useEffect, useRef } from "react";
import { Upload as UploadIcon, Trash2, FileText, CheckCircle, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { getCandidates, uploadCandidate, deleteCandidate } from "../api/client";

export default function UploadPage() {
  const [candidates, setCandidates] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const inputRef = useRef();

  const showToast = (msg, type = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const load = async () => {
    try {
      const { data } = await getCandidates();
      setCandidates(data.candidates);
    } catch { /* silent */ }
  };

  useEffect(() => { load(); }, []);

  const handleFiles = async (files) => {
    const file = files[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadCandidate(file);
      showToast("CV uploaded and parsed successfully.");
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || "Upload failed.", "err");
    } finally {
      setUploading(false);
    }
  };

  const remove = async (id, name) => {
    if (!confirm(`Remove ${name}?`)) return;
    try {
      await deleteCandidate(id);
      setCandidates(c => c.filter(x => x.id !== id));
      showToast("Candidate removed.");
    } catch {
      showToast("Failed to remove candidate.", "err");
    }
  };

  return (
    <div className="fade-in">
      <h1 style={{ fontSize: 26, marginBottom: 4 }}>CV Upload</h1>
      <p style={{ color: "var(--text-dim)", marginBottom: 28 }}>
        Upload candidate CVs — AI extracts their profile automatically.
      </p>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        style={{
          border: `2px dashed ${dragging ? "var(--gold)" : "var(--border2)"}`,
          borderRadius: "var(--radius-lg)", padding: "40px 24px",
          textAlign: "center", cursor: "pointer", marginBottom: 28,
          background: dragging ? "var(--gold-dim)" : "var(--surface)",
          transition: "all 0.2s",
        }}
      >
        <input ref={inputRef} type="file" hidden
          accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
          onChange={e => handleFiles(e.target.files)} />

        {uploading ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <span className="spinner" style={{ width: 28, height: 28 }} />
            <p style={{ color: "var(--text-mid)" }}>Parsing CV with AI…</p>
          </div>
        ) : (
          <>
            <UploadIcon size={32} color="var(--text-dim)" style={{ marginBottom: 12 }} />
            <p style={{ fontWeight: 600, marginBottom: 4 }}>Drop a CV here or click to browse</p>
            <p style={{ color: "var(--text-dim)", fontSize: 13 }}>PDF, DOCX, TXT, PNG, JPG — max 10MB</p>
          </>
        )}
      </div>

      {/* Candidate list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {candidates.length === 0 && (
          <p style={{ color: "var(--text-dim)", textAlign: "center", padding: "24px 0" }}>
            No candidates yet.
          </p>
        )}

        {candidates.map(c => (
          <div key={c.id} className="card" style={{ padding: 0, overflow: "hidden" }}>
            {/* Header row */}
            <div
              style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 20px", cursor: "pointer" }}
              onClick={() => setExpanded(expanded === c.id ? null : c.id)}
            >
              <FileText size={18} color="var(--text-dim)" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 600, fontSize: 15 }}>{c.name}</p>
                <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
                  {c.email || "No email"} · {c.file_name}
                </p>
              </div>
              <p style={{ color: "var(--text-dim)", fontSize: 12, flexShrink: 0 }}>
                {new Date(c.uploaded_at).toLocaleDateString()}
              </p>
              {/* Expand toggle */}
              <span style={{ color: "var(--text-dim)" }}>
                {expanded === c.id ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}
              </span>
              {/* Delete */}
              <button
                onClick={e => { e.stopPropagation(); remove(c.id, c.name); }}
                style={{ background: "transparent", color: "var(--text-dim)", padding: 6, borderRadius: 6, transition: "color 0.15s", flexShrink: 0 }}
                onMouseOver={e => e.currentTarget.style.color = "var(--red)"}
                onMouseOut={e => e.currentTarget.style.color = "var(--text-dim)"}
              >
                <Trash2 size={16} />
              </button>
            </div>

            {/* Expanded: extracted CV info */}
            {expanded === c.id && (
              <div style={{ borderTop: "1px solid var(--border)", padding: "16px 20px" }} className="fade-in">
                {c.structured_info ? (
                  <pre style={{
                    fontFamily: "DM Sans, sans-serif", fontSize: 13,
                    color: "var(--text-mid)", lineHeight: 1.7,
                    whiteSpace: "pre-wrap", wordBreak: "break-word",
                    margin: 0,
                  }}>
                    {c.structured_info}
                  </pre>
                ) : (
                  <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
                    No extracted info available.
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Toast — top right, doesn't overlap candidates */}
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
          {toast.type === "err" ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
          {toast.msg}
        </div>
      )}
    </div>
  );
}
