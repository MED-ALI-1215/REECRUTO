import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/client";

export default function Login() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const { data } = await login(form.username, form.password);
      localStorage.setItem("token", data.access_token);
      navigate("/upload");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--bg)",
    }}>
      <div className="card fade-in" style={{ width: 380 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 28,
            letterSpacing: "0.12em", textTransform: "uppercase",
          }}>
            REC<span style={{ color: "var(--gold)" }}>R</span>UTO
          </div>
          <p style={{ color: "var(--text-dim)", fontSize: 13, marginTop: 6 }}>
            Recruiter portal
          </p>
        </div>

        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-mid)", fontWeight: 600, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Username
            </label>
            <input
              className="input"
              placeholder="admin"
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              autoFocus
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "var(--text-mid)", fontWeight: 600, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Password
            </label>
            <input
              className="input"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            />
          </div>

          {error && (
            <p style={{ color: "var(--red)", fontSize: 13, background: "#ef444415", padding: "8px 12px", borderRadius: "var(--radius)", border: "1px solid #ef444430" }}>
              {error}
            </p>
          )}

          <button className="btn-primary" type="submit" disabled={loading} style={{ marginTop: 4 }}>
            {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
