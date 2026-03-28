"""
RECRUTO — app3_interview.py
AI Interview Module  ·  Candidate-facing only
────────────────────────────────────────────────────────────────────────────────
Flow:
  1. Candidate opens unique token link  (?token=xxx)
  2. App loads job context from SQLite via token
  3. Groq generates 5 tailored interview questions
  4. Candidate answers each question via text input
  5. Groq scores each answer in real time
  6. Final report (score + summary) saved to SQLite
  7. Recruiter views results in the Dashboard (index.html iframe → app4_dashboard.py)
────────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import sqlite3
import os
import json
import re
from datetime import datetime
from typing import Optional
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH       = os.getenv("INTERVIEW_DB_PATH", "./interview_sessions.db")
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
NUM_QUESTIONS = 5

st.set_page_config(
    page_title="AI Interview — RECRUTO",
    page_icon="🤖",
    layout="centered",          # centered — candidate doesn't need wide layout
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — same obsidian / amber / teal theme, no sidebar needed
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Epilogue:wght@400;500;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Epilogue', sans-serif;
    background-color: #090b10 !important;
    color: #dce4f0 !important;
}
.stApp {
    background:
        radial-gradient(ellipse 55% 35% at 5%   5%,  rgba(251,191,36,0.07)  0%, transparent 55%),
        radial-gradient(ellipse 40% 30% at 95% 95%,  rgba(20,184,166,0.06)  0%, transparent 55%),
        #090b10;
    min-height: 100vh;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 2.5rem 2rem 5rem; max-width: 760px; margin: 0 auto; }

/* ── Brand bar ── */
.brand-bar {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 2rem;
    padding-bottom: 1.2rem;
    border-bottom: 1px solid #161c2a;
}
.brand-name {
    font-family: 'Epilogue', sans-serif;
    font-size: 1.3rem;
    font-weight: 900;
    color: #f1f5f9;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.brand-name span { color: #fbbf24; }
.brand-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    color: #14b8a6;
    border: 1px solid rgba(20,184,166,0.25);
    background: rgba(20,184,166,0.05);
    padding: 0.18rem 0.55rem;
    border-radius: 3px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

/* ── Hero ── */
.hero { padding-bottom: 1.5rem; margin-bottom: 1.8rem; }
.hero-title {
    font-family: 'Instrument Serif', serif;
    font-size: 2.8rem;
    font-weight: 400;
    font-style: italic;
    line-height: 1.0;
    color: #f1f5f9;
    margin: 0 0 0.3rem 0;
}
.hero-title strong {
    font-style: normal;
    font-weight: 900;
    color: #fbbf24;
    font-family: 'Epilogue', sans-serif;
}
.hero-sub { font-size: 0.8rem; color: #3d4f6b; letter-spacing: 0.04em; }

/* ── Section label ── */
.slabel {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    font-weight: 500;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: #3d4f6b;
    padding-left: 0.55rem;
    border-left: 2px solid #fbbf24;
    margin-bottom: 0.55rem;
    display: block;
}

/* ── Cards ── */
.card {
    background: #0f1420;
    border: 1px solid #1c2640;
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
}
.card-accent {
    background: #0f1420;
    border: 1px solid #1c2640;
    border-left: 3px solid #fbbf24;
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}
.card-teal {
    background: rgba(20,184,166,0.05);
    border: 1px solid rgba(20,184,166,0.2);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.card-done {
    background: rgba(20,184,166,0.05);
    border: 1px solid rgba(20,184,166,0.25);
    border-left: 3px solid #14b8a6;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}

/* ── Question box ── */
.q-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #fbbf24;
    margin-bottom: 0.4rem;
}
.q-text { font-size: 1.05rem; font-weight: 500; color: #f1f5f9; line-height: 1.5; }

/* ── Score display ── */
.score-big {
    font-family: 'Epilogue', sans-serif;
    font-size: 2.8rem;
    font-weight: 900;
    line-height: 1;
}
.score-big.good  { color: #14b8a6; }
.score-big.ok    { color: #fbbf24; }
.score-big.low   { color: #f87171; }

/* ── Progress bar ── */
.prog-wrap { width: 100%; background: #1c2640; border-radius: 4px; height: 6px; margin: 0.6rem 0; }
.prog-fill { height: 6px; border-radius: 4px; background: linear-gradient(90deg, #fbbf24, #14b8a6); transition: width 0.4s; }

/* ── Info pill ── */
.info-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(251,191,36,0.07);
    border: 1px solid rgba(251,191,36,0.2);
    border-radius: 6px;
    padding: 0.35rem 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #fbbf24;
    margin: 0.2rem 0.3rem 0.2rem 0;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea {
    background: #0f1420 !important;
    border: 1px solid #1c2640 !important;
    border-radius: 7px !important;
    color: #dce4f0 !important;
    font-family: 'Epilogue', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color .15s, box-shadow .15s;
}
.stTextInput > div > div > input:focus,
.stTextArea  > div > div > textarea:focus {
    border-color: #fbbf24 !important;
    box-shadow: 0 0 0 3px rgba(251,191,36,0.08) !important;
}
.stTextInput > label, .stTextArea > label { color: #2d3f58 !important; font-size: 0.74rem !important; }

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: #fbbf24 !important;
    color: #090b10 !important;
    font-family: 'Epilogue', sans-serif !important;
    font-weight: 900 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 7px !important;
    padding: 0.65rem 2rem !important;
    width: 100%;
    transition: opacity .18s, box-shadow .18s !important;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.82 !important;
    box-shadow: 0 0 22px rgba(251,191,36,0.3) !important;
}
.stButton > button {
    background: #0f1420 !important;
    color: #5a7299 !important;
    border: 1px solid #1c2640 !important;
    border-radius: 7px !important;
    font-family: 'Epilogue', sans-serif !important;
    font-size: 0.82rem !important;
    transition: border-color .15s, color .15s !important;
}
.stButton > button:hover { border-color: #fbbf24 !important; color: #fbbf24 !important; }

/* ── Alerts ── */
.stAlert   { background: #0f1420 !important; border: 1px solid #1c2640 !important; border-radius: 7px !important; }
.stSuccess { background: rgba(20,184,166,0.05) !important;  border-left-color: #14b8a6 !important; }
.stError   { background: rgba(220,38,38,0.05) !important;   border-left-color: #dc2626 !important; }
.stWarning { background: rgba(251,191,36,0.05) !important;  border-left-color: #f59e0b !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #0f1420 !important; color: #dce4f0 !important;
    border: 1px solid #1c2640 !important; border-radius: 7px !important;
    font-family: 'Epilogue', sans-serif !important;
}
.streamlit-expanderContent {
    background: #0b0f1a !important; border: 1px solid #1c2640 !important;
    border-top: none !important; color: #dce4f0 !important;
}

/* ── Misc ── */
.rdiv { border: none; border-top: 1px solid #161c2a; margin: 2rem 0; }
code {
    background: #0f1420 !important; color: #14b8a6 !important;
    border: 1px solid #1c2640 !important; border-radius: 4px !important;
    padding: 0.1rem 0.4rem !important; font-size: 0.8rem !important;
}
p { color: #5a7299 !important; }
strong { color: #dce4f0 !important; }
.rfooter {
    text-align: center; color: #161c2a; font-size: 0.65rem;
    letter-spacing: 0.2em; text-transform: uppercase;
    margin-top: 4rem; padding-top: 1.5rem; border-top: 1px solid #161c2a;
}
.rfooter span { color: #fbbf24; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                token           TEXT PRIMARY KEY,
                candidate_name  TEXT NOT NULL,
                candidate_email TEXT NOT NULL,
                job_title       TEXT NOT NULL,
                job_description TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                used            INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS interviews (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                token           TEXT NOT NULL,
                candidate_name  TEXT NOT NULL,
                candidate_email TEXT NOT NULL,
                job_title       TEXT NOT NULL,
                questions_json  TEXT NOT NULL,
                answers_json    TEXT NOT NULL,
                scores_json     TEXT NOT NULL,
                overall_score   REAL NOT NULL,
                summary         TEXT NOT NULL,
                strengths       TEXT NOT NULL,
                red_flags       TEXT NOT NULL,
                recommendation  TEXT NOT NULL,
                completed_at    TEXT NOT NULL
            );
        """)


def get_session(token: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token=?", (token,)
        ).fetchone()
        return dict(row) if row else None


def mark_session_used(token: str):
    with get_conn() as conn:
        conn.execute("UPDATE sessions SET used=1 WHERE token=?", (token,))


def save_interview(token, candidate_name, candidate_email, job_title,
                   questions, answers, scores, overall_score,
                   summary, strengths, red_flags, recommendation):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO interviews
            (token, candidate_name, candidate_email, job_title,
             questions_json, answers_json, scores_json,
             overall_score, summary, strengths, red_flags,
             recommendation, completed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            token, candidate_name, candidate_email, job_title,
            json.dumps(questions), json.dumps(answers), json.dumps(scores),
            overall_score, summary, strengths, red_flags,
            recommendation, datetime.now().isoformat()
        ))


init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Groq helpers
# ─────────────────────────────────────────────────────────────────────────────

def groq_client() -> Groq:
    key = st.session_state.get("groq_key") or GROQ_API_KEY
    if not key:
        st.error("❌ Groq API key not configured. Please contact the recruiter.")
        st.stop()
    return Groq(api_key=key)


def generate_questions(job_title, job_description, candidate_name) -> list:
    prompt = f"""You are a senior technical recruiter conducting a job interview.

Candidate name: {candidate_name}
Job title: {job_title}
Job description:
{job_description}

Generate exactly {NUM_QUESTIONS} interview questions for this candidate.
The questions should:
- Be specific to the job description above
- Mix technical knowledge, situational, and behavioural questions
- Progressively increase in depth (start easy, end challenging)
- Be open-ended so the candidate must explain their thinking

Return ONLY a JSON array of strings, no extra text. Example:
["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""

    resp = groq_client().chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.6,
        max_tokens=800,
    )
    raw = resp.choices[0].message.content.strip()
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    return json.loads(match.group()) if match else json.loads(raw)


def score_answer(question, answer, job_title, job_description) -> dict:
    if not answer.strip():
        return {"score": 0, "feedback": "No answer provided.", "keywords": []}

    prompt = f"""You are evaluating a candidate's answer in a job interview.

Job title: {job_title}
Job description (summary): {job_description[:600]}

Question: {question}
Candidate answer: {answer}

Evaluate and respond ONLY with a JSON object:
{{
  "score": <integer 0-100>,
  "feedback": "<2-3 sentences: what was good, what was missing>",
  "keywords": ["<key concept mentioned>", "<another>"]
}}

Scoring guide:
- 85-100: Excellent, detailed, directly relevant
- 65-84 : Good, mostly relevant, minor gaps
- 40-64 : Partial, vague or missing key points
- 0-39  : Off-topic, too short, or incorrect"""

    resp = groq_client().chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=400,
    )
    raw = resp.choices[0].message.content.strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group()) if match else {"score": 50, "feedback": raw, "keywords": []}


def generate_final_report(candidate_name, job_title, questions, answers, scores) -> dict:
    qa_block = "\n\n".join([
        f"Q{i+1}: {q}\nA: {a}\nScore: {s.get('score', 0)}/100"
        for i, (q, a, s) in enumerate(zip(questions, answers, scores))
    ])
    prompt = f"""You are a recruitment expert writing a final interview assessment.

Candidate: {candidate_name}
Role: {job_title}

Interview transcript:
{qa_block}

Respond ONLY with this JSON:
{{
  "overall_score": <weighted average 0-100, integer>,
  "summary": "<3-4 sentence overall assessment>",
  "strengths": "<2-3 key strengths demonstrated>",
  "red_flags": "<1-2 concerns, or 'None identified' if none>",
  "recommendation": "<one of: Strong Hire | Hire | Maybe | No Hire>"
}}"""

    resp = groq_client().chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        max_tokens=600,
    )
    raw = resp.choices[0].message.content.strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {
        "overall_score": int(sum(s.get("score", 0) for s in scores) / max(len(scores), 1)),
        "summary": raw,
        "strengths": "See transcript",
        "red_flags": "None identified",
        "recommendation": "Maybe",
    }

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def score_class(score: float) -> str:
    if score >= 75: return "good"
    if score >= 50: return "ok"
    return "low"

# ─────────────────────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────────────────────
defaults = {
    "interview_stage":  "waiting",   # waiting | intro | questions | complete
    "session_data":     None,
    "questions":        [],
    "answers":          [],
    "scores":           [],
    "current_q":        0,
    "token":            "",
    "groq_key":         GROQ_API_KEY,
    "current_answer":   "",
    "report":           None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# Parse token from URL  (?token=xxx)
# ─────────────────────────────────────────────────────────────────────────────
params    = st.query_params
url_token = params.get("token", "")

if url_token and st.session_state.interview_stage == "waiting":
    sess = get_session(url_token)
    if sess and not sess["used"]:
        st.session_state.session_data    = sess
        st.session_state.token           = url_token
        st.session_state.interview_stage = "intro"

# ─────────────────────────────────────────────────────────────────────────────
# Brand bar (always visible)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-bar">
    <div class="brand-name">REC<span>R</span>UTO</div>
    <div class="brand-tag">AI Interview</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# STAGE: WAITING — no token or invalid token
# ─────────────────────────────────────────────────────────────────────────────
stage = st.session_state.interview_stage

if stage == "waiting":
    st.markdown("""
    <div class="hero">
        <div class="hero-title"><strong>Your Interview</strong></div>
        <div class="hero-sub">Enter the token from your invitation email to begin.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Enter your interview token</div>', unsafe_allow_html=True)
    st.markdown("""
    <p>You should have received an interview link by email from RECRUTO.
    Open that link directly, or paste your token below.</p>
    """, unsafe_allow_html=True)

    manual_token = st.text_input(
        "Interview Token",
        placeholder="Paste your token here…",
        label_visibility="collapsed",
    )
    if st.button("🚀  Start Interview", type="primary"):
        if manual_token.strip():
            sess = get_session(manual_token.strip())
            if sess and not sess["used"]:
                st.session_state.session_data    = sess
                st.session_state.token           = manual_token.strip()
                st.session_state.interview_stage = "intro"
                st.rerun()
            elif sess and sess["used"]:
                st.error("❌ This interview token has already been used.")
            else:
                st.error("❌ Invalid token. Please check your invitation email.")
        else:
            st.warning("Please enter your token.")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# STAGE: INTRO — confirm identity, show instructions
# ─────────────────────────────────────────────────────────────────────────────
elif stage == "intro":
    sess = st.session_state.session_data

    st.markdown(f"""
    <div class="hero">
        <div class="hero-title"><strong>Welcome,</strong><br><em>{sess['candidate_name']}!</em></div>
        <div class="hero-sub">AI-Powered Interview · Groq · RECRUTO</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="card-teal">
        <div class="slabel">Your session</div>
        <span class="info-pill">👤 {sess['candidate_name']}</span>
        <span class="info-pill">💼 {sess['job_title']}</span>
        <span class="info-pill">📅 {datetime.now().strftime('%B %d, %Y')}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="card-accent">
        <div class="slabel">Before you begin</div>
        <p style="color:#dce4f0;font-size:0.95rem;line-height:1.8;margin:0;">
        You are about to start your AI-powered interview for the
        <strong>{sess['job_title']}</strong> position.<br><br>
        • You will be asked <strong>{NUM_QUESTIONS} questions</strong> tailored to this role.<br>
        • Type your answer in the text box — quality matters more than speed.<br>
        • Each answer is scored immediately by AI.<br>
        • Your results are sent to the recruiter after you finish.<br>
        • Complete it in one session — the interview cannot be paused.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("✅  I'm Ready — Begin Interview", type="primary"):
        with st.spinner("⚡ Generating your interview questions…"):
            try:
                qs = generate_questions(
                    sess["job_title"],
                    sess["job_description"],
                    sess["candidate_name"],
                )
                st.session_state.questions       = qs
                st.session_state.answers         = [""] * len(qs)
                st.session_state.scores          = [{}]  * len(qs)
                st.session_state.current_q       = 0
                st.session_state.interview_stage = "questions"
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error generating questions: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE: QUESTIONS — one question at a time
# ─────────────────────────────────────────────────────────────────────────────
elif stage == "questions":
    sess  = st.session_state.session_data
    qs    = st.session_state.questions
    idx   = st.session_state.current_q
    total = len(qs)

    # Progress bar
    pct = int((idx / total) * 100)
    st.markdown(f"""
    <div style="margin-bottom:1.5rem;">
        <div style="display:flex;justify-content:space-between;margin-bottom:0.3rem;">
            <span class="slabel" style="margin:0;">Progress</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
                         color:#3d4f6b;">{idx}/{total} answered</span>
        </div>
        <div class="prog-wrap">
            <div class="prog-fill" style="width:{pct}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Answered questions summary (collapsible)
    if idx > 0:
        with st.expander(f"✅ Answered questions ({idx})", expanded=False):
            for i in range(idx):
                sc        = st.session_state.scores[i]
                score_val = sc.get("score", 0)
                cls       = score_class(score_val)
                st.markdown(f"""
                <div class="card-done">
                    <div class="q-number">Question {i+1}</div>
                    <div class="q-text" style="font-size:0.9rem;margin-bottom:0.5rem;">{qs[i]}</div>
                    <div style="font-size:0.82rem;color:#5a7299;margin-bottom:0.4rem;font-style:italic;">
                        {st.session_state.answers[i][:200]}{'…' if len(st.session_state.answers[i]) > 200 else ''}
                    </div>
                    <span class="score-big {cls}" style="font-size:1.4rem;">{score_val}</span>
                    <span style="font-size:0.7rem;color:#3d4f6b;margin-left:0.3rem;">/100</span>
                    <p style="font-size:0.8rem;color:#5a7299;margin:0.3rem 0 0;">{sc.get('feedback', '')}</p>
                </div>
                """, unsafe_allow_html=True)

    # Current question
    st.markdown(f"""
    <div class="card-accent">
        <div class="q-number">Question {idx + 1} of {total}</div>
        <div class="q-text">{qs[idx]}</div>
    </div>
    """, unsafe_allow_html=True)

    answer = st.text_area(
        "Your answer",
        value=st.session_state.current_answer,
        height=160,
        placeholder="Type your answer here… Be specific and use examples where possible.",
        key=f"answer_input_{idx}",
        label_visibility="collapsed",
    )

    word_count = len(answer.strip().split()) if answer.strip() else 0
    wc_color   = "#14b8a6" if word_count >= 30 else "#fbbf24" if word_count >= 10 else "#f87171"
    st.markdown(f"""
    <div style="text-align:right;margin-top:-0.5rem;margin-bottom:0.8rem;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:{wc_color};">
            {word_count} words {'✓' if word_count >= 30 else '— aim for 30+'}
        </span>
    </div>
    """, unsafe_allow_html=True)

    btn_label = (
        "⚡  Submit & Next Question"
        if idx < total - 1
        else "⚡  Submit & Finish Interview"
    )

    if st.button(btn_label, type="primary"):
        if not answer.strip():
            st.warning("Please write an answer before continuing.")
        else:
            with st.spinner("⚡ Scoring your answer…"):
                try:
                    result = score_answer(
                        qs[idx], answer,
                        sess["job_title"], sess["job_description"]
                    )
                    st.session_state.answers[idx] = answer
                    st.session_state.scores[idx]  = result
                    st.session_state.current_answer = ""

                    if idx + 1 < total:
                        st.session_state.current_q = idx + 1
                        st.rerun()
                    else:
                        # All questions done → generate report
                        with st.spinner("⚡ Generating your final assessment…"):
                            report = generate_final_report(
                                sess["candidate_name"],
                                sess["job_title"],
                                st.session_state.questions,
                                st.session_state.answers,
                                st.session_state.scores,
                            )
                            st.session_state.report = report
                            save_interview(
                                token           = st.session_state.token,
                                candidate_name  = sess["candidate_name"],
                                candidate_email = sess["candidate_email"],
                                job_title       = sess["job_title"],
                                questions       = st.session_state.questions,
                                answers         = st.session_state.answers,
                                scores          = st.session_state.scores,
                                overall_score   = report["overall_score"],
                                summary         = report["summary"],
                                strengths       = report["strengths"],
                                red_flags       = report["red_flags"],
                                recommendation  = report["recommendation"],
                            )
                            mark_session_used(st.session_state.token)
                            st.session_state.interview_stage = "complete"
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE: COMPLETE — show candidate their results
# ─────────────────────────────────────────────────────────────────────────────
elif stage == "complete":
    sess   = st.session_state.session_data
    report = st.session_state.report
    score  = report.get("overall_score", 0)
    cls    = score_class(score)

    st.markdown(f"""
    <div class="card" style="text-align:center;padding:2.5rem;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
                    letter-spacing:0.2em;color:#14b8a6;margin-bottom:0.8rem;">
            ✅ INTERVIEW COMPLETE
        </div>
        <div class="hero-title" style="font-size:2rem;">
            Well done, <strong>{sess['candidate_name']}</strong>!
        </div>
        <p style="color:#5a7299;margin:0.5rem 0 1.5rem;">
            Your interview for <strong style="color:#dce4f0;">{sess['job_title']}</strong>
            has been submitted successfully.
        </p>
        <div class="score-big {cls}" style="font-size:5rem;">{score}</div>
        <div style="font-size:0.65rem;letter-spacing:0.2em;text-transform:uppercase;color:#3d4f6b;">
            Overall score / 100
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="card-accent" style="margin-top:1rem;">
        <div class="slabel">Assessment summary</div>
        <p style="color:#dce4f0;font-size:0.95rem;line-height:1.7;">{report.get('summary', '')}</p>
        <div style="margin-top:1rem;display:flex;gap:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
                <div class="slabel">Strengths</div>
                <p style="color:#14b8a6;font-size:0.88rem;">{report.get('strengths', '')}</p>
            </div>
            <div style="flex:1;min-width:200px;">
                <div class="slabel">Areas to improve</div>
                <p style="color:#fbbf24;font-size:0.88rem;">{report.get('red_flags', '')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="margin-top:1rem;text-align:center;">
        <p style="color:#5a7299;font-size:0.88rem;">
            The recruiter will review your results and contact you within a few business days.
            You may now close this window.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Per-question breakdown
    with st.expander("📋 View detailed question breakdown"):
        for i, (q, a, s) in enumerate(zip(
            st.session_state.questions,
            st.session_state.answers,
            st.session_state.scores,
        )):
            sv  = s.get("score", 0)
            cls_q = score_class(sv)
            st.markdown(f"""
            <div class="card-done" style="margin-bottom:0.8rem;">
                <div class="q-number">Question {i+1}</div>
                <div class="q-text" style="font-size:0.9rem;margin-bottom:0.5rem;">{q}</div>
                <div style="font-size:0.85rem;color:#5a7299;margin-bottom:0.6rem;
                            background:#090b10;padding:0.6rem 0.8rem;border-radius:6px;">
                    {a}
                </div>
                <span class="score-big {cls_q}" style="font-size:1.4rem;">{sv}</span>
                <span style="font-size:0.7rem;color:#3d4f6b;margin-left:0.3rem;">/100</span>
                <p style="font-size:0.82rem;color:#5a7299;margin:0.4rem 0 0;">
                    {s.get('feedback', '')}
                </p>
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rfooter">
    <span>RECRUTO</span> · AI Interview · Powered by <span>Groq AI</span>
</div>
""", unsafe_allow_html=True)