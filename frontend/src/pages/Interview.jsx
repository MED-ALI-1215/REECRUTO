import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { getSession, getQuestions, scoreAnswer, finishInterview } from "../api/client";

function ProgressBar({ current, total }) {
  return (
    <div style={{ background: "var(--surface2)", borderRadius: 4, height: 4, marginBottom: 32, overflow: "hidden" }}>
      <div style={{ width: `${(current / total) * 100}%`, height: "100%", background: "var(--gold)", borderRadius: 4, transition: "width 0.5s ease" }} />
    </div>
  );
}

function ScoreDisplay({ score, feedback, keywords }) {
  const color = score >= 70 ? "var(--green)" : score >= 45 ? "var(--gold)" : "var(--red)";
  return (
    <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: 20, marginTop: 16 }} className="fade-in">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 28, color }}>
          {score}<span style={{ fontSize: 16, fontWeight: 400 }}>/100</span>
        </span>
        <div style={{ flex: 1, background: "var(--border)", borderRadius: 4, height: 6, overflow: "hidden" }}>
          <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.6s ease" }} />
        </div>
      </div>
      <p style={{ fontSize: 14, color: "var(--text-mid)", lineHeight: 1.6, marginBottom: 10 }}>{feedback}</p>
      {keywords?.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {keywords.map(k => (
            <span key={k} className="badge" style={{ background: "var(--blue-dim)", color: "var(--blue)", border: "1px solid #3b82f630", fontSize: 11 }}>{k}</span>
          ))}
        </div>
      )}
    </div>
  );
}

const STATES = { loading: "loading", ready: "ready", answering: "answering", scoring: "scoring", done: "done", error: "error" };

export default function Interview() {
  const [params] = useSearchParams();
  const token = params.get("token");

  const [state, setState] = useState(STATES.loading);
  const [session, setSession] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [current, setCurrent] = useState(0);
  const [answer, setAnswer] = useState("");
  const [scores, setScores] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [lastScore, setLastScore] = useState(null);
  const [finalResult, setFinalResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [loadingQs, setLoadingQs] = useState(false);

  useEffect(() => {
    if (!token) { setState(STATES.error); setErrorMsg("No interview token provided."); return; }
    getSession(token)
      .then(({ data }) => { setSession(data); setState(STATES.ready); })
      .catch(err => { setState(STATES.error); setErrorMsg(err.response?.data?.detail || "Invalid or expired link."); });
  }, [token]);

  const start = async () => {
    setLoadingQs(true);
    try {
      const { data } = await getQuestions(token);
      setQuestions(data.questions);
      setCurrent(0); setScores([]); setAnswers([]); setLastScore(null);
      setState(STATES.answering);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Failed to load questions.");
      setState(STATES.error);
    } finally {
      setLoadingQs(false);
    }
  };

  const submit = async () => {
    if (!answer.trim()) return;
    setState(STATES.scoring);
    try {
      const { data } = await scoreAnswer(token, questions[current], answer);
      setLastScore(data);
      setScores(s => [...s, data]);
      setAnswers(a => [...a, answer]);
    } catch {
      setLastScore({ score: 0, feedback: "Could not score this answer.", keywords: [] });
      setScores(s => [...s, { score: 0, feedback: "", keywords: [] }]);
      setAnswers(a => [...a, answer]);
    }
  };

  const next = async () => {
    if (current + 1 < questions.length) {
      setCurrent(c => c + 1);
      setAnswer(""); setLastScore(null);
      setState(STATES.answering);
    } else {
      // Finish
      setState(STATES.loading);
      try {
        const { data } = await finishInterview(token, {
          questions, answers: [...answers], scores: [...scores],
        });
        setFinalResult(data);
        setState(STATES.done);
      } catch {
        setState(STATES.done);
      }
    }
  };

  // ── Error ──
  if (state === STATES.error) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div className="card" style={{ maxWidth: 420, textAlign: "center" }}>
        <p style={{ fontSize: 40, marginBottom: 12 }}>⚠️</p>
        <h2 style={{ marginBottom: 8 }}>Link unavailable</h2>
        <p style={{ color: "var(--text-dim)" }}>{errorMsg}</p>
      </div>
    </div>
  );

  // ── Loading ──
  if (state === STATES.loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)", flexDirection: "column", gap: 16 }}>
      <span className="spinner" style={{ width: 36, height: 36 }} />
      <p style={{ color: "var(--text-dim)" }}>Loading your interview…</p>
    </div>
  );

  // ── Done ──
  if (state === STATES.done) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div className="card fade-in" style={{ maxWidth: 480, width: "90%", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
        <h2 style={{ marginBottom: 8 }}>Interview complete!</h2>
        {finalResult && (
          <>
            <p style={{ color: "var(--text-dim)", marginBottom: 20 }}>
              Your overall score
            </p>
            <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 52,
              color: finalResult.overall_score >= 70 ? "var(--green)" : finalResult.overall_score >= 45 ? "var(--gold)" : "var(--red)",
              marginBottom: 16 }}>
              {finalResult.overall_score?.toFixed(0)}%
            </div>
            {finalResult.summary && <p style={{ color: "var(--text-mid)", lineHeight: 1.7, fontSize: 14 }}>{finalResult.summary}</p>}
          </>
        )}
        <p style={{ color: "var(--text-dim)", fontSize: 13, marginTop: 20 }}>
          The recruiter will review your results and be in touch.
        </p>
      </div>
    </div>
  );

  // ── Ready (start screen) ──
  if (state === STATES.ready) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div className="card fade-in" style={{ maxWidth: 480, width: "90%" }}>
        <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 20, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 20 }}>
          REECRUTO
        </div>
        <h2 style={{ marginBottom: 8 }}>Hello, {session?.candidate_name} 👋</h2>
        <p style={{ color: "var(--text-dim)", marginBottom: 6 }}>
          You're interviewing for <strong style={{ color: "var(--text)" }}>{session?.job_title}</strong>
        </p>
        <p style={{ color: "var(--text-dim)", fontSize: 13, marginBottom: 28, lineHeight: 1.6 }}>
          You'll be asked a series of questions. Take your time to answer each one thoroughly.
          Your answers will be scored by AI.
        </p>
        <button className="btn-primary" onClick={start} disabled={loadingQs}
          style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {loadingQs ? <span className="spinner" style={{ width: 16, height: 16 }} /> : null}
          {loadingQs ? "Loading questions…" : "Begin Interview"}
        </button>
      </div>
    </div>
  );

  // ── Answering / Scoring ──
  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "48px 20px" }}>
      <div style={{ width: "100%", maxWidth: 600 }}>
        {/* Header */}
        <div style={{ marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 16, letterSpacing: "0.1em", color: "var(--gold)" }}>REECRUTO</span>
          <span style={{ fontSize: 13, color: "var(--text-dim)" }}>Question {current + 1} of {questions.length}</span>
        </div>

        <ProgressBar current={current + (state === STATES.scoring ? 1 : 0)} total={questions.length} />

        <div className="card fade-in" key={current}>
          <p style={{ fontSize: 12, color: "var(--text-dim)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>
            Question {current + 1}
          </p>
          <h2 style={{ fontSize: 19, marginBottom: 20, lineHeight: 1.4 }}>{questions[current]}</h2>

          {state === STATES.answering && (
            <>
              <textarea className="input" placeholder="Type your answer here…"
                value={answer} onChange={e => setAnswer(e.target.value)}
                rows={5} style={{ resize: "vertical", marginBottom: 14 }} />
              <button className="btn-primary" onClick={submit} disabled={!answer.trim()}>
                Submit Answer
              </button>
            </>
          )}

          {state === STATES.scoring && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, padding: "16px 0" }}>
              <span className="spinner" style={{ width: 28, height: 28 }} />
              <p style={{ color: "var(--text-dim)" }}>Scoring your answer…</p>
            </div>
          )}

          {lastScore && (
            <>
              <ScoreDisplay {...lastScore} />
              <button className="btn-primary" onClick={next} style={{ marginTop: 16 }}>
                {current + 1 < questions.length ? "Next Question →" : "Finish Interview"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
