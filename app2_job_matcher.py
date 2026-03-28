import streamlit as st
import sys
import os
import re
import sqlite3
import secrets
from datetime import datetime
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import CandidateDatabase
from utils.email_sender import send_email, generate_acceptance_email, generate_rejection_email
from groq import Groq
from dotenv import load_dotenv

# ── Interview session helper (creates token in interview DB) ─────────────────
_INTERVIEW_DB = os.getenv("INTERVIEW_DB_PATH", "./interview_sessions.db")
_APP_BASE_URL  = os.getenv("APP_BASE_URL", "http://localhost:8502")

def _create_interview_session(candidate_name, candidate_email, job_title, job_description):
    """Insert a session token into interview_sessions.db and return the full link."""
    os.makedirs(os.path.dirname(_INTERVIEW_DB) if os.path.dirname(_INTERVIEW_DB) else ".", exist_ok=True)
    token = secrets.token_urlsafe(32)
    conn  = sqlite3.connect(_INTERVIEW_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, candidate_name TEXT, candidate_email TEXT,
            job_title TEXT, job_description TEXT, created_at TEXT, used INTEGER DEFAULT 0
        )
    """)
    conn.execute(
        "INSERT INTO sessions VALUES (?,?,?,?,?,?,0)",
        (token, candidate_name, candidate_email, job_title, job_description, datetime.now().isoformat())
    )
    conn.commit(); conn.close()
    return f"{_APP_BASE_URL}?token={token}"

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_email_from_text(text: str) -> Optional[str]:
    """Return the first valid email found in any block of text."""
    if not text:
        return None
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None


def resolve_email(metadata: dict, cv_document: str) -> Optional[str]:
    """
    Try to find the candidate's email in this order:
      1. metadata['email']  (direct field, if stored)
      2. metadata['structured_info']  (AI-extracted block)
      3. raw CV document text
    """
    # 1 — direct metadata field
    direct = metadata.get("email", "").strip()
    if direct:
        return direct

    # 2 — AI structured block (labelled line first, then any email)
    structured = metadata.get("structured_info", "") or ""
    for line in structured.splitlines():
        m = re.match(r"(?:\d+\.\s*)?e[-\s]?mail\s*[:\-]\s*(.+)", line, re.IGNORECASE)
        if m:
            found = extract_email_from_text(m.group(1))
            if found:
                return found
    fallback = extract_email_from_text(structured)
    if fallback:
        return fallback

    # 3 — raw CV text
    return extract_email_from_text(cv_document or "")


def resolve_name(metadata: dict) -> str:
    """
    Return the best available candidate name:
      1. metadata['name']  (if not empty / 'Unknown')
      2. Parse from metadata['structured_info']
      3. Fall back to 'Unknown'
    """
    raw_name = (metadata.get("name") or "").strip()
    if raw_name and raw_name.lower() not in ("unknown", "n/a", ""):
        return raw_name

    structured = metadata.get("structured_info", "") or ""
    for line in structured.splitlines():
        m = re.match(
            r"(?:\d+\.\s*)?(?:full\s*name|name)\s*[:\-]\s*(.+)",
            line.strip(),
            re.IGNORECASE,
        )
        if m:
            name = m.group(1).strip().strip("*").strip()
            if name and name.lower() not in ("unknown", "n/a", "not provided", ""):
                return name

    return "Unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Matcher — RECRUTO",
    page_icon="🎯",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS  — obsidian / amber / electric-teal, editorial brutalist tone
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Epilogue:wght@400;500;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
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
.block-container { padding: 2.2rem 3rem 5rem; max-width: 1160px; }

/* ── Hero ── */
.hero {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: end;
    gap: 2rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid #161c2a;
    margin-bottom: 2.2rem;
}
.hero-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #14b8a6;
    border: 1px solid rgba(20,184,166,0.25);
    background: rgba(20,184,166,0.05);
    display: inline-block;
    padding: 0.22rem 0.7rem;
    border-radius: 3px;
    margin-bottom: 0.8rem;
}
.hero-title {
    font-family: 'Instrument Serif', serif;
    font-size: 3.8rem;
    font-weight: 400;
    font-style: italic;
    line-height: 1.0;
    color: #f1f5f9;
    margin: 0 0 0.35rem 0;
    letter-spacing: -0.01em;
}
.hero-title strong {
    font-style: normal;
    font-weight: 400;
    color: #fbbf24;
    font-family: 'Epilogue', sans-serif;
    font-weight: 900;
}
.hero-sub {
    font-size: 0.8rem;
    color: #3d4f6b;
    letter-spacing: 0.04em;
    line-height: 1.5;
}
.hero-right { text-align: right; }
.groq-chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.25);
    background: rgba(251,191,36,0.05);
    padding: 0.3rem 0.8rem;
    border-radius: 4px;
    letter-spacing: 0.1em;
    display: inline-block;
    margin-bottom: 0.5rem;
}
.hero-count {
    font-family: 'Epilogue', sans-serif;
    font-size: 3rem;
    font-weight: 900;
    color: #fbbf24;
    line-height: 1;
}
.hero-count-lbl {
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #1e2d42;
}

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
}

/* ── Divider ── */
.rdiv { border:none; border-top: 1px solid #161c2a; margin: 2rem 0; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea,
.stNumberInput > div > div > input {
    background: #0f1420 !important;
    border: 1px solid #1c2640 !important;
    border-radius: 7px !important;
    color: #dce4f0 !important;
    font-family: 'Epilogue', sans-serif !important;
    font-size: 0.87rem !important;
    transition: border-color .15s, box-shadow .15s;
}
.stTextInput > div > div > input:focus,
.stTextArea  > div > div > textarea:focus {
    border-color: #fbbf24 !important;
    box-shadow: 0 0 0 3px rgba(251,191,36,0.08) !important;
}
.stTextInput    > label,
.stTextArea     > label,
.stNumberInput  > label { color: #2d3f58 !important; font-size: 0.74rem !important; }

/* ── Select ── */
.stSelectbox > div > div {
    background: #0f1420 !important;
    border: 1px solid #1c2640 !important;
    border-radius: 7px !important;
    color: #dce4f0 !important;
}
.stSelectbox > label { color: #2d3f58 !important; font-size: 0.74rem !important; }

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
    transition: opacity .18s, box-shadow .18s !important;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.82 !important;
    box-shadow: 0 0 22px rgba(251,191,36,0.3) !important;
}

/* ── Default buttons ── */
.stButton > button {
    background: #0f1420 !important;
    color: #5a7299 !important;
    border: 1px solid #1c2640 !important;
    border-radius: 7px !important;
    font-family: 'Epilogue', sans-serif !important;
    font-size: 0.82rem !important;
    transition: border-color .15s, color .15s !important;
}
.stButton > button:hover {
    border-color: #fbbf24 !important;
    color: #fbbf24 !important;
}
div[data-testid="column"] .stButton > button {
    width: 100%;
    padding: 0.45rem 0.5rem !important;
    font-size: 0.78rem !important;
}

/* ── Candidate card ── */
.ccard {
    background: #0f1420;
    border: 1px solid #1c2640;
    border-radius: 10px;
    padding: 1.2rem 1.5rem 0.85rem;
    margin: 0.9rem 0 0;
    position: relative;
    overflow: hidden;
    transition: border-color .18s, box-shadow .18s;
}
.ccard::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, #fbbf24 0%, #14b8a6 100%);
    border-radius: 3px 0 0 3px;
}
.ccard:hover {
    border-color: #263554;
    box-shadow: 0 6px 26px rgba(251,191,36,0.07);
}
.ctop {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 0.5rem;
}
.rank-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    color: #090b10;
    background: #fbbf24;
    padding: 0.15rem 0.55rem;
    border-radius: 4px;
}
.score-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #14b8a6;
    background: rgba(20,184,166,0.08);
    border: 1px solid rgba(20,184,166,0.2);
    padding: 0.12rem 0.55rem;
    border-radius: 20px;
}
.cname {
    font-family: 'Epilogue', sans-serif;
    font-size: 1.1rem;
    font-weight: 800;
    color: #f1f5f9;
}
.cmeta {
    font-size: 0.74rem;
    color: #2d3f58;
    margin-top: 0.1rem;
}
.cemail-auto {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #14b8a6;
    background: rgba(20,184,166,0.06);
    border: 1px solid rgba(20,184,166,0.15);
    border-radius: 4px;
    padding: 0.18rem 0.6rem;
    display: inline-block;
    margin-top: 0.25rem;
}
.cemail-missing {
    font-size: 0.72rem;
    color: #c0392b;
    margin-top: 0.25rem;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #070912 !important;
    border-right: 1px solid #161c2a !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #dce4f0 !important; }
[data-testid="stSidebar"] .stTextInput  > label,
[data-testid="stSidebar"] .stSelectbox > label { color: #2d3f58 !important; }
.sb-brand {
    font-family: 'Epilogue', sans-serif;
    font-size: 1.7rem;
    font-weight: 900;
    color: #f1f5f9;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.sb-brand span { color: #fbbf24; }
.sb-tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: #2d3f58;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.sb-stat {
    background: #0f1420;
    border: 1px solid #1c2640;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-top: 0.4rem;
}
.sb-stat-lbl { font-size: 0.62rem; letter-spacing: 0.16em; text-transform: uppercase; color: #2d3f58; }
.sb-stat-val { font-family:'Epilogue',sans-serif; font-size:1.9rem; font-weight:900; color:#fbbf24; line-height:1.1; }

/* ── Alerts ── */
.stAlert { background:#0f1420 !important; border:1px solid #1c2640 !important; border-radius:7px !important; color:#dce4f0 !important; }
.stSuccess { background:rgba(20,184,166,0.05) !important;  border-left-color:#14b8a6 !important; }
.stError   { background:rgba(220,38,38,0.05) !important;   border-left-color:#dc2626 !important; }
.stWarning { background:rgba(251,191,36,0.05) !important;  border-left-color:#fbbf24 !important; }

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

/* ── Number input ── */
.stNumberInput div[data-baseweb="input"] { background:#0f1420 !important; border-color:#1c2640 !important; }

/* ── Footer ── */
.rfooter {
    text-align: center; color: #161c2a; font-size: 0.65rem;
    letter-spacing: 0.2em; text-transform: uppercase;
    margin-top: 4rem; padding-top: 1.5rem; border-top: 1px solid #161c2a;
}
.rfooter span { color: #fbbf24; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DB init
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_database():
    return CandidateDatabase(os.getenv("CHROMA_DB_PATH", "./chroma_db"))

db = get_database()

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
for key in ("matched_candidates", "ranked_candidates"):
    if key not in st.session_state:
        st.session_state[key] = None

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sb-brand">REC<span>R</span>UTO</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-tagline">Job Matcher · Groq Edition</div>', unsafe_allow_html=True)

    st.markdown('<div class="slabel">Groq Config</div>', unsafe_allow_html=True)
    api_key = st.text_input(
        "Groq API Key",
        type="password",
        value=os.getenv("GROQ_API_KEY", ""),
        help="Free key at console.groq.com",
    )
    groq_model = st.selectbox(
        "Model",
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        index=0,
        help="llama-3.3-70b-versatile recommended",
    )

    st.markdown("---")
    st.markdown('<div class="slabel">Email Settings</div>', unsafe_allow_html=True)
    sender_email    = st.text_input("Sender Email",      value=os.getenv("EMAIL_ADDRESS", ""))
    sender_password = st.text_input("Email App Password", type="password", value=os.getenv("EMAIL_PASSWORD", ""),
                                    help="Gmail App Password — not your regular password")

    st.markdown("---")
    st.markdown(f"""
        <div class="sb-stat">
            <div class="sb-stat-lbl">Candidates in DB</div>
            <div class="sb-stat-val">{db.get_candidate_count()}</div>
        </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-tag">⚡ Groq · Ultra-low latency inference</div>
    <div class="hero-title"><strong>Spot Talent,</strong><br><em>Build Success.</em></div>
    <div class="hero-sub">Job Matcher · Semantic search via ChromaDB · AI ranking via Groq</div>
  </div>
  <div class="hero-right">
    <div class="groq-chip">⚡ GROQ POWERED</div>
    <div class="hero-count">{db.get_candidate_count()}</div>
    <div class="hero-count-lbl">Candidates in pool</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Job description form
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="slabel">Job Description</div>', unsafe_allow_html=True)

c1, c2 = st.columns([3, 1])
with c1:
    job_title = st.text_input("Job Title", placeholder="e.g. Senior Python Developer",
                               label_visibility="collapsed")
with c2:
    num_candidates = st.number_input("Top N", min_value=1, max_value=20, value=5,
                                      help="How many top candidates to retrieve")

job_description = st.text_area(
    "JD",
    height=170,
    placeholder="Paste the full job description here — required skills, responsibilities, qualifications…",
    label_visibility="collapsed",
)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🔍  Find Matching Candidates", type="primary"):
    if not job_title or not job_description:
        st.error("Please enter both a job title and description.")
    elif not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
    else:
        with st.spinner("Scanning candidate pool…"):
            results = db.search_candidates(job_description, n_results=num_candidates)

            if results and results.get("ids") and len(results["ids"][0]) > 0:
                st.session_state.ranked_candidates  = None
                st.session_state.matched_candidates = {
                    "job_title":       job_title,
                    "job_description": job_description,
                    "candidates":      [],
                }

                # Fetch full documents so we can mine emails from raw CV text
                all_ids = results["ids"][0]
                docs_fetched = {}
                try:
                    fetched = db.collection.get(ids=all_ids, include=["documents", "metadatas"])
                    for cid, doc, meta in zip(fetched["ids"], fetched["documents"], fetched["metadatas"]):
                        docs_fetched[cid] = {"doc": doc, "meta": meta}
                except Exception:
                    pass

                for i, (cid, metadata, distance) in enumerate(zip(
                    results["ids"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )):
                    match_score = round(max(0, min(100, 100 - distance * 50)), 1)

                    # Resolve name & email
                    full_doc = docs_fetched.get(cid, {}).get("doc", "")
                    name  = resolve_name(metadata)
                    email = resolve_email(metadata, full_doc)

                    st.session_state.matched_candidates["candidates"].append({
                        "id":          cid,
                        "name":        name,
                        "email":       email,          # auto-resolved, may be None
                        "file_name":   metadata.get("file_name", "N/A"),
                        "upload_date": metadata.get("upload_date", "N/A"),
                        "match_score": match_score,
                        "rank":        i + 1,
                    })

                count = len(results["ids"][0])
                emails_found = sum(1 for c in st.session_state.matched_candidates["candidates"] if c["email"])
                st.success(f"✅  {count} candidates matched · {emails_found}/{count} emails auto-detected.")
            else:
                st.warning("No candidates found. Upload CVs first via the CV Parser.")

# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.matched_candidates:
    st.markdown('<hr class="rdiv">', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Matched Candidates</div>', unsafe_allow_html=True)

    # Groq ranking button
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("⚡  Rank with Groq AI"):
            if not api_key:
                st.error("Enter your Groq API key in the sidebar.")
            else:
                with st.spinner(f"Groq ({groq_model}) is analysing candidates…"):
                    try:
                        client = Groq(api_key=api_key)
                        info = "\n\n".join(
                            f"Candidate {i+1}: {c['name']}\nMatch Score: {c['match_score']}%"
                            for i, c in enumerate(st.session_state.matched_candidates["candidates"])
                        )
                        prompt = f"""You are an expert recruitment consultant. Rank these candidates for:

Job Title: {st.session_state.matched_candidates['job_title']}
Job Description: {st.session_state.matched_candidates['job_description']}

Candidates:
{info}

Rank from best to worst. Format:
1. [Name] — <1-2 sentence justification>
2. [Name] — ...
"""
                        resp = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": "You are a professional recruitment expert. Be concise and objective."},
                                {"role": "user",   "content": prompt},
                            ],
                            model=groq_model,
                            temperature=0.3,
                            max_tokens=1024,
                        )
                        st.session_state.ranked_candidates = resp.choices[0].message.content.strip()
                        st.success("⚡ Ranking complete!")
                    except Exception as e:
                        st.error(f"Groq API error: {e}")

    if st.session_state.ranked_candidates:
        with st.expander("⚡  Groq AI Ranking Analysis", expanded=True):
            st.markdown(st.session_state.ranked_candidates)

    # ── Candidate cards ──────────────────────────────────────────────────────
    for candidate in st.session_state.matched_candidates["candidates"]:
        auto_email   = candidate["email"]
        email_display = (
            f'<div class="cemail-auto">✉ {auto_email}</div>'
            if auto_email
            else '<div class="cemail-missing">⚠ No email found in CV — enter manually below</div>'
        )

        st.markdown(f"""
            <div class="ccard">
                <div class="ctop">
                    <span class="rank-badge">#{candidate['rank']}</span>
                    <span class="score-badge">{candidate['match_score']}% match</span>
                    <span class="cname">{candidate['name']}</span>
                </div>
                <div class="cmeta">📄 {candidate['file_name']}</div>
                {email_display}
            </div>
        """, unsafe_allow_html=True)

        # Email override + action buttons
        col_email, col_accept, col_reject = st.columns([4, 1, 1])
        with col_email:
            manual_email = st.text_input(
                "Override email",
                value=auto_email or "",
                key=f"email_{candidate['id']}",
                placeholder="auto-detected or type manually",
                label_visibility="collapsed",
            )
            # Use manual override if provided, else auto-detected
            final_email = manual_email.strip() or auto_email

        with col_accept:
            if st.button("✅  Accept", key=f"accept_{candidate['id']}"):
                if not final_email:
                    st.error("No email — enter it above.")
                elif not sender_email or not sender_password:
                    st.error("Configure sender email in sidebar.")
                else:
                    interview_link = _create_interview_session(
                        candidate["name"],
                        final_email,
                        st.session_state.matched_candidates["job_title"],
                        st.session_state.matched_candidates["job_description"],
                    )
                    subject, body = generate_acceptance_email(
                        candidate["name"],
                        st.session_state.matched_candidates["job_title"],
                        interview_link=interview_link,
                    )
                    ok, msg = send_email(final_email, subject, body, sender_email, sender_password)
                    if ok:
                        st.success(f"✅ Acceptance + interview link sent to {candidate['name']} ({final_email})")
                    else:
                        st.error(f"❌ {msg}")

        with col_reject:
            if st.button("❌  Reject", key=f"reject_{candidate['id']}"):
                if not final_email:
                    st.error("No email — enter it above.")
                elif not sender_email or not sender_password:
                    st.error("Configure sender email in sidebar.")
                else:
                    subject, body = generate_rejection_email(
                        candidate["name"],
                        st.session_state.matched_candidates["job_title"],
                    )
                    ok, msg = send_email(final_email, subject, body, sender_email, sender_password)
                    if ok:
                        st.success(f"Rejection sent to {candidate['name']}.")
                    else:
                        st.error(f"❌ {msg}")

        st.markdown("<div style='margin-bottom:0.4rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rfooter">
    <span>RECRUTO</span> · Job Matcher · Powered by <span>Groq AI</span> &amp; ChromaDB
</div>
""", unsafe_allow_html=True)