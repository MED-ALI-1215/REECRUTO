"""
RECRUTO — app4_dashboard.py
Recruiter Dashboard  ·  Recruiter-facing only
────────────────────────────────────────────────────────────────────────────────
Reads completed interviews from SQLite and displays:
  - Summary stats (total, avg score, hire/no-hire counts)
  - Per-candidate cards with full Q&A breakdown
  - Sort and filter controls
  - Post-interview actions: send human interview invite or final rejection
────────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import sqlite3
import os
import json
import re
from datetime import datetime
from utils.email_sender import send_email
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("INTERVIEW_DB_PATH", "./interview_sessions.db")

st.set_page_config(
    page_title="Dashboard — RECRUTO",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — same obsidian / amber / teal theme
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
.block-container { padding: 2.2rem 3rem 5rem; max-width: 1160px; }

/* ── Hero ── */
.hero { padding-bottom: 2rem; border-bottom: 1px solid #161c2a; margin-bottom: 2.2rem; }
.hero-tag {
    font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; font-weight: 500;
    letter-spacing: 0.22em; text-transform: uppercase; color: #14b8a6;
    border: 1px solid rgba(20,184,166,0.25); background: rgba(20,184,166,0.05);
    display: inline-block; padding: 0.22rem 0.7rem; border-radius: 3px; margin-bottom: 0.8rem;
}
.hero-title {
    font-family: 'Instrument Serif', serif; font-size: 3rem; font-weight: 400;
    font-style: italic; line-height: 1.0; color: #f1f5f9; margin: 0 0 0.35rem 0;
}
.hero-title strong {
    font-style: normal; font-weight: 900; color: #fbbf24; font-family: 'Epilogue', sans-serif;
}
.hero-sub { font-size: 0.8rem; color: #3d4f6b; letter-spacing: 0.04em; }

/* ── Section label ── */
.slabel {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500;
    letter-spacing: 0.28em; text-transform: uppercase; color: #3d4f6b;
    padding-left: 0.55rem; border-left: 2px solid #fbbf24;
    margin-bottom: 0.55rem; display: block;
}

/* ── Stat card ── */
.stat-card {
    background: #0f1420; border: 1px solid #1c2640; border-radius: 10px;
    padding: 1rem 1.2rem; text-align: center;
}
.stat-lbl { font-size: 0.58rem; letter-spacing: 0.2em; text-transform: uppercase; color: #2d3f58; margin-bottom: 0.2rem; }
.stat-val { font-family: 'Epilogue', sans-serif; font-size: 2rem; font-weight: 900; line-height: 1; }

/* ── Cards ── */
.card {
    background: #0f1420; border: 1px solid #1c2640; border-radius: 10px;
    padding: 1.4rem 1.6rem; margin-bottom: 1.2rem;
}
.card-accent {
    background: #0f1420; border: 1px solid #1c2640; border-left: 3px solid #fbbf24;
    border-radius: 10px; padding: 1.4rem 1.6rem; margin-bottom: 1rem;
}
.card-teal {
    background: rgba(20,184,166,0.05); border: 1px solid rgba(20,184,166,0.2);
    border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 1rem;
}
.card-done {
    background: rgba(20,184,166,0.05); border: 1px solid rgba(20,184,166,0.25);
    border-left: 3px solid #14b8a6; border-radius: 10px;
    padding: 1.2rem 1.5rem; margin-bottom: 1rem;
}

/* ── Score ── */
.score-big { font-family: 'Epilogue', sans-serif; font-size: 2.8rem; font-weight: 900; line-height: 1; }
.score-big.good { color: #14b8a6; }
.score-big.ok   { color: #fbbf24; }
.score-big.low  { color: #f87171; }
.q-number {
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 500;
    letter-spacing: 0.2em; text-transform: uppercase; color: #fbbf24; margin-bottom: 0.4rem;
}
.q-text { font-size: 1.05rem; font-weight: 500; color: #f1f5f9; line-height: 1.5; }

/* ── Progress bar ── */
.prog-wrap { width: 100%; background: #1c2640; border-radius: 4px; height: 6px; margin: 0.6rem 0; }
.prog-fill { height: 6px; border-radius: 4px; background: linear-gradient(90deg, #fbbf24, #14b8a6); }

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: #fbbf24 !important; color: #090b10 !important;
    font-family: 'Epilogue', sans-serif !important; font-weight: 900 !important;
    font-size: 0.88rem !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important; border: none !important;
    border-radius: 7px !important; padding: 0.65rem 2rem !important;
    width: 100%; transition: opacity .18s, box-shadow .18s !important;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.82 !important; box-shadow: 0 0 22px rgba(251,191,36,0.3) !important;
}
.stButton > button {
    background: #0f1420 !important; color: #5a7299 !important;
    border: 1px solid #1c2640 !important; border-radius: 7px !important;
    font-family: 'Epilogue', sans-serif !important; font-size: 0.82rem !important;
    transition: border-color .15s, color .15s !important; width: 100%;
}
.stButton > button:hover { border-color: #fbbf24 !important; color: #fbbf24 !important; }

/* ── Inputs ── */
.stTextInput > div > div > input, .stSelectbox > div > div {
    background: #0f1420 !important; border: 1px solid #1c2640 !important;
    border-radius: 7px !important; color: #dce4f0 !important;
    font-family: 'Epilogue', sans-serif !important; font-size: 0.87rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #fbbf24 !important; box-shadow: 0 0 0 3px rgba(251,191,36,0.08) !important;
}
.stTextInput > label, .stSelectbox > label { color: #2d3f58 !important; font-size: 0.74rem !important; }

/* ── Email settings panel ── */
.email-panel {
    background: #0a0d16; border: 1px solid #1c2640; border-radius: 10px;
    padding: 1.2rem 1.5rem; margin-bottom: 1.5rem;
}

/* ── Alerts ── */
.stAlert   { background: #0f1420 !important; border: 1px solid #1c2640 !important; border-radius: 7px !important; }
.stSuccess { background: rgba(20,184,166,0.05) !important;  border-left-color: #14b8a6 !important; }
.stError   { background: rgba(220,38,38,0.05) !important;   border-left-color: #dc2626 !important; }
.stWarning { background: rgba(251,191,36,0.05) !important;  border-left-color: #f59e0b !important; }
.stInfo    { background: rgba(251,191,36,0.04) !important;  border-left-color: #fbbf24 !important; }

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
p { color: #5a7299 !important; }
strong { color: #dce4f0 !important; }
code {
    background: #0f1420 !important; color: #14b8a6 !important;
    border: 1px solid #1c2640 !important; border-radius: 4px !important;
    padding: 0.1rem 0.4rem !important; font-size: 0.8rem !important;
}
.rfooter {
    text-align: center; color: #161c2a; font-size: 0.65rem;
    letter-spacing: 0.2em; text-transform: uppercase;
    margin-top: 4rem; padding-top: 1.5rem; border-top: 1px solid #161c2a;
}
.rfooter span { color: #fbbf24; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
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
            CREATE TABLE IF NOT EXISTS post_actions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                interview_id    INTEGER NOT NULL,
                action          TEXT NOT NULL,
                sent_at         TEXT NOT NULL,
                FOREIGN KEY (interview_id) REFERENCES interviews(id)
            );
        """)


def get_all_interviews() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM interviews ORDER BY completed_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_actions_for(interview_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM post_actions WHERE interview_id=? ORDER BY sent_at DESC",
            (interview_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def log_action(interview_id: int, action: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO post_actions (interview_id, action, sent_at) VALUES (?,?,?)",
            (interview_id, action, datetime.now().isoformat())
        )


init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def score_class(score: float) -> str:
    if score >= 75: return "good"
    if score >= 50: return "ok"
    return "low"


def recommendation_color(rec: str) -> str:
    return {
        "Strong Hire": "#14b8a6",
        "Hire":        "#a3e635",
        "Maybe":       "#fbbf24",
        "No Hire":     "#f87171",
    }.get(rec, "#fbbf24")


# ─────────────────────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">📊 Recruiter Dashboard</div>
    <div class="hero-title"><strong>Interview</strong> Results</div>
    <div class="hero-sub">All completed AI interviews · scores · recommendations · post-interview actions</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Email settings (collapsed panel — recruiter fills once)
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("⚙️  Email Settings (required for post-interview actions)", expanded=False):
    ec1, ec2 = st.columns(2)
    with ec1:
        sender_email = st.text_input(
            "Sender Email", value=os.getenv("EMAIL_ADDRESS", ""),
            placeholder="your@gmail.com"
        )
    with ec2:
        sender_password = st.text_input(
            "Email App Password", type="password",
            value=os.getenv("EMAIL_PASSWORD", ""),
            help="Gmail App Password — not your regular password"
        )

st.markdown('<hr class="rdiv">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Load interviews
# ─────────────────────────────────────────────────────────────────────────────
interviews = get_all_interviews()

if not interviews:
    st.info("📭 No completed interviews yet. Send interview links to candidates via the Job Matcher.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Summary stats
# ─────────────────────────────────────────────────────────────────────────────
avg_score = sum(r["overall_score"] for r in interviews) / len(interviews)
strong    = sum(1 for r in interviews if r["recommendation"] in ("Strong Hire", "Hire"))
maybe     = sum(1 for r in interviews if r["recommendation"] == "Maybe")
no_hire   = sum(1 for r in interviews if r["recommendation"] == "No Hire")

s1, s2, s3, s4 = st.columns(4)
for col, label, value, color in [
    (s1, "Total interviews",  len(interviews),        "#fbbf24"),
    (s2, "Avg score",         f"{avg_score:.0f}/100", "#14b8a6"),
    (s3, "Hire / Strong",     strong,                 "#a3e635"),
    (s4, "No Hire",           no_hire,                "#f87171"),
]:
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-lbl">{label}</div>
            <div class="stat-val" style="color:{color};">{value}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sort + filter controls
# ─────────────────────────────────────────────────────────────────────────────
ctrl1, ctrl2 = st.columns(2)
with ctrl1:
    sort_by = st.selectbox(
        "Sort by",
        ["Score ↓", "Score ↑", "Date ↓", "Recommendation"],
    )
with ctrl2:
    rec_filter = st.selectbox(
        "Filter recommendation",
        ["All", "Strong Hire", "Hire", "Maybe", "No Hire"],
    )

filtered = interviews
if rec_filter != "All":
    filtered = [r for r in filtered if r["recommendation"] == rec_filter]

sort_map = {
    "Score ↓":        lambda x: -x["overall_score"],
    "Score ↑":        lambda x:  x["overall_score"],
    "Date ↓":         lambda x:  x["completed_at"],
    "Recommendation": lambda x:  ["Strong Hire", "Hire", "Maybe", "No Hire"].index(
                                      x.get("recommendation", "Maybe")),
}
filtered = sorted(filtered, key=sort_map.get(sort_by, lambda x: -x["overall_score"]))

st.markdown('<hr class="rdiv">', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Candidate cards
# ─────────────────────────────────────────────────────────────────────────────
for rec in filtered:
    score     = rec["overall_score"]
    rec_label = rec["recommendation"]
    cls       = score_class(score)
    rec_color = recommendation_color(rec_label)
    pct_bar   = int(score)
    actions   = get_actions_for(rec["id"])
    action_labels = [a["action"] for a in actions]

    with st.expander(
        f"👤 {rec['candidate_name']}  ·  {rec['job_title']}  ·  "
        f"Score: {score:.0f}/100  ·  {rec_label}"
    ):
        info_col, score_col = st.columns([3, 1])

        with info_col:
            st.markdown(f"""
            <div class="slabel">Candidate info</div>
            <p style="margin:0;font-size:0.88rem;color:#dce4f0;">
                <strong>Email:</strong> {rec['candidate_email']}<br>
                <strong>Role:</strong>  {rec['job_title']}<br>
                <strong>Completed:</strong> {rec['completed_at'][:16].replace('T', ' ')}
            </p>
            """, unsafe_allow_html=True)

        with score_col:
            st.markdown(f"""
            <div style="text-align:center;background:#090b10;border-radius:10px;padding:1rem;">
                <div class="score-big {cls}">{score:.0f}</div>
                <div style="font-size:0.6rem;letter-spacing:0.2em;text-transform:uppercase;color:#3d4f6b;">/ 100</div>
                <div style="margin-top:0.5rem;background:{rec_color};color:#090b10;
                            font-family:'Epilogue',sans-serif;font-weight:900;
                            font-size:0.72rem;padding:0.3rem 0.6rem;border-radius:4px;
                            letter-spacing:0.08em;">
                    {rec_label}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Score bar
        st.markdown(f"""
        <div class="prog-wrap" style="margin:0.8rem 0;">
            <div class="prog-fill" style="width:{pct_bar}%"></div>
        </div>
        """, unsafe_allow_html=True)

        # AI assessment
        st.markdown(f"""
        <div class="card" style="margin-bottom:0.6rem;">
            <div class="slabel">AI Assessment</div>
            <p style="color:#dce4f0;font-size:0.9rem;line-height:1.7;margin:0;">
                {rec['summary']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        st_col, rf_col = st.columns(2)
        with st_col:
            st.markdown(f"""
            <div class="card-teal">
                <div class="slabel">Strengths</div>
                <p style="color:#14b8a6;font-size:0.85rem;margin:0;">{rec['strengths']}</p>
            </div>
            """, unsafe_allow_html=True)
        with rf_col:
            st.markdown(f"""
            <div class="card-accent">
                <div class="slabel">Red flags</div>
                <p style="color:#fbbf24;font-size:0.85rem;margin:0;">{rec['red_flags']}</p>
            </div>
            """, unsafe_allow_html=True)

        # ── Post-interview actions ────────────────────────────────────────
        st.markdown('<div class="slabel" style="margin-top:1rem;">Post-Interview Actions</div>', unsafe_allow_html=True)

        # Show history of sent actions
        if action_labels:
            for al in action_labels:
                icon = "✅" if "invite" in al.lower() else "❌"
                st.markdown(
                    f'<p style="font-size:0.78rem;color:#3d4f6b;margin:0;">'
                    f'{icon} {al}</p>',
                    unsafe_allow_html=True
                )
            st.markdown("<br>", unsafe_allow_html=True)

        act1, act2 = st.columns(2)

        with act1:
            # Invite to human interview
            invite_sent = any("invite" in a.lower() for a in action_labels)
            btn_label   = "✅  Invite Sent" if invite_sent else "📅  Invite to Human Interview"
            if st.button(btn_label, key=f"invite_{rec['id']}", disabled=invite_sent):
                if not sender_email or not sender_password:
                    st.error("Configure sender email above first.")
                else:
                    subject = f"You've advanced! Next steps for {rec['job_title']} — RECRUTO"
                    body = f"""
                    <html><head><meta charset="utf-8"></head>
                    <body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
                      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
                        <tr><td align="center">
                          <table width="600" cellpadding="0" cellspacing="0"
                                 style="background:#161b27;border-radius:12px;overflow:hidden;border:1px solid #1e2a3a;">
                            <tr><td style="background:linear-gradient(90deg,#fbbf24,#f59e0b);padding:4px 0;"></td></tr>
                            <tr><td style="padding:32px 40px;">
                              <h1 style="color:#f1f5f9;font-size:22px;">Congratulations, {rec['candidate_name']}!</h1>
                              <p style="color:#64748b;font-size:15px;line-height:1.7;">
                                You have successfully completed your AI interview for
                                <strong style="color:#fbbf24;">{rec['job_title']}</strong>.
                                We are impressed with your performance and would like to invite you
                                to a <strong style="color:#f1f5f9;">human interview</strong> with our team.
                              </p>
                              <p style="color:#64748b;font-size:14px;">
                                Our recruitment team will contact you shortly to schedule a convenient time.
                              </p>
                              <p style="color:#f1f5f9;font-size:14px;font-weight:700;margin-top:24px;">
                                The RECRUTO Team
                              </p>
                            </td></tr>
                            <tr><td style="background:linear-gradient(90deg,#fbbf24,#f59e0b);padding:3px 0;"></td></tr>
                          </table>
                        </td></tr>
                      </table>
                    </body></html>
                    """
                    ok, msg = send_email(
                        rec["candidate_email"], subject, body,
                        sender_email, sender_password
                    )
                    if ok:
                        log_action(rec["id"], f"Human interview invite sent to {rec['candidate_email']}")
                        st.success(f"✅ Invite sent to {rec['candidate_name']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        with act2:
            # Final rejection
            reject_sent = any("rejection" in a.lower() for a in action_labels)
            btn_label2  = "❌  Rejection Sent" if reject_sent else "❌  Send Final Rejection"
            if st.button(btn_label2, key=f"final_reject_{rec['id']}", disabled=reject_sent):
                if not sender_email or not sender_password:
                    st.error("Configure sender email above first.")
                else:
                    subject = f"Your application for {rec['job_title']} — RECRUTO"
                    body = f"""
                    <html><head><meta charset="utf-8"></head>
                    <body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
                      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
                        <tr><td align="center">
                          <table width="600" cellpadding="0" cellspacing="0"
                                 style="background:#161b27;border-radius:12px;overflow:hidden;border:1px solid #1e2a3a;">
                            <tr><td style="background:#1e2a3a;padding:3px 0;"></td></tr>
                            <tr><td style="padding:32px 40px 28px 40px;">
                              <h1 style="color:#f1f5f9;font-size:22px;">Dear {rec['candidate_name']},</h1>
                              <p style="color:#64748b;font-size:15px;line-height:1.7;">
                                Thank you for completing the AI interview for
                                <strong style="color:#94a3b8;">{rec['job_title']}</strong>.
                                After careful consideration, we have decided to move forward with other candidates.
                                We genuinely appreciate the time you invested in the process.
                              </p>
                              <p style="color:#64748b;font-size:14px;">
                                We wish you every success in your career journey.
                              </p>
                              <p style="color:#f1f5f9;font-size:14px;font-weight:700;margin-top:24px;">
                                The RECRUTO Team
                              </p>
                            </td></tr>
                            <tr><td style="background:#1e2a3a;padding:3px 0;"></td></tr>
                          </table>
                        </td></tr>
                      </table>
                    </body></html>
                    """
                    ok, msg = send_email(
                        rec["candidate_email"], subject, body,
                        sender_email, sender_password
                    )
                    if ok:
                        log_action(rec["id"], f"Final rejection sent to {rec['candidate_email']}")
                        st.success(f"Rejection sent to {rec['candidate_name']}.")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        # ── Full Q&A breakdown ────────────────────────────────────────────
        with st.expander("📋 Full Q&A breakdown"):
            qs  = json.loads(rec["questions_json"])
            ans = json.loads(rec["answers_json"])
            scs = json.loads(rec["scores_json"])
            for i, (q, a, s) in enumerate(zip(qs, ans, scs)):
                sv  = s.get("score", 0)
                clq = score_class(sv)
                st.markdown(f"""
                <div class="card-done" style="margin-bottom:0.7rem;">
                    <div class="q-number">Question {i+1}</div>
                    <div class="q-text" style="font-size:0.88rem;margin-bottom:0.4rem;">{q}</div>
                    <div style="font-size:0.83rem;color:#5a7299;background:#090b10;
                                padding:0.5rem 0.8rem;border-radius:6px;margin-bottom:0.5rem;">
                        {a}
                    </div>
                    <span class="score-big {clq}" style="font-size:1.2rem;">{sv}</span>
                    <span style="font-size:0.68rem;color:#3d4f6b;">/100</span>
                    <p style="font-size:0.8rem;color:#5a7299;margin:0.3rem 0 0;">
                        {s.get('feedback', '')}
                    </p>
                </div>
                """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rfooter">
    <span>RECRUTO</span> · Recruiter Dashboard · Powered by <span>Groq AI</span>
</div>
""", unsafe_allow_html=True)