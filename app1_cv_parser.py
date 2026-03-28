import streamlit as st
import sys
import os
import re
import uuid
from datetime import datetime
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cv_parser import parse_cv, extract_cv_info_with_ai
from utils.database import CandidateDatabase
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — extract name & email from AI structured output
# ─────────────────────────────────────────────────────────────────────────────

def extract_name_from_structured(structured_info: str) -> Optional[str]:
    """
    Parse the candidate name from the AI-generated structured block.
    Looks for lines like:
        Full Name: John Doe
        1. Full Name: John Doe
        Name: John Doe
    """
    if not structured_info:
        return None
    for line in structured_info.splitlines():
        line = line.strip()
        m = re.match(
            r"(?:\d+\.\s*)?(?:full\s*name|name)\s*[:\-]\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if m:
            name = m.group(1).strip().strip("*").strip()
            if name and name.lower() not in ("n/a", "unknown", "not provided", "not found", ""):
                return name
    return None


def extract_email_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CV Parser — RECRUTO",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — matches Job Matcher obsidian/amber theme
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
.block-container { padding: 2.2rem 3rem 5rem; max-width: 1160px; }

/* ── Hero ── */
.hero {
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
}
.hero-title strong {
    font-style: normal;
    font-weight: 900;
    color: #fbbf24;
    font-family: 'Epilogue', sans-serif;
}
.hero-sub {
    font-size: 0.8rem;
    color: #3d4f6b;
    letter-spacing: 0.04em;
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
    display: block;
}

/* ── Panel card ── */
.panel-card {
    background: #0f1420;
    border: 1px solid #1c2640;
    border-radius: 10px;
    padding: 1.5rem 1.6rem;
    margin-bottom: 1.2rem;
}
.panel-title {
    font-family: 'Epilogue', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #5a7299;
    margin-bottom: 1rem;
}

/* ── Candidate card ── */
.ccard {
    background: #0f1420;
    border: 1px solid #1c2640;
    border-left: 3px solid #fbbf24;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin: 0.8rem 0;
    transition: border-color .18s, box-shadow .18s;
}
.ccard:hover {
    border-color: #263554;
    box-shadow: 0 6px 26px rgba(251,191,36,0.07);
}

/* ── Name resolved banner ── */
.name-resolved {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(20,184,166,0.08);
    border: 1px solid rgba(20,184,166,0.2);
    border-radius: 5px;
    padding: 0.3rem 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #14b8a6;
    margin-top: 0.5rem;
}
.name-fallback {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(251,191,36,0.06);
    border: 1px solid rgba(251,191,36,0.2);
    border-radius: 5px;
    padding: 0.3rem 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #fbbf24;
    margin-top: 0.5rem;
}

/* ── Divider ── */
.rdiv { border: none; border-top: 1px solid #161c2a; margin: 2rem 0; }
hr { border: none !important; border-top: 1px solid #161c2a !important; margin: 2rem 0 !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea {
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
.stTextInput > label,
.stTextArea  > label { color: #2d3f58 !important; font-size: 0.74rem !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] > div {
    background: #0f1420 !important;
    border: 2px dashed #1c2640 !important;
    border-radius: 10px !important;
    transition: border-color .2s;
}
[data-testid="stFileUploader"] > div:hover { border-color: #fbbf24 !important; }
[data-testid="stFileUploader"] label { color: #3d4f6b !important; }

/* ── Checkboxes ── */
.stCheckbox > label       { color: #dce4f0 !important; font-size: 0.88rem !important; }
.stCheckbox span          { color: #dce4f0 !important; }

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

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #0f1420 !important; color: #dce4f0 !important;
    border: 1px solid #1c2640 !important; border-radius: 7px !important;
    font-family: 'Epilogue', sans-serif !important; font-size: 0.88rem !important;
}
.streamlit-expanderHeader:hover { border-color: #fbbf24 !important; }
.streamlit-expanderContent {
    background: #0b0f1a !important; border: 1px solid #1c2640 !important;
    border-top: none !important; color: #dce4f0 !important;
}

/* ── Alerts ── */
.stAlert   { background: #0f1420 !important; border: 1px solid #1c2640 !important; border-radius: 7px !important; }
.stSuccess { background: rgba(20,184,166,0.05) !important;  border-left-color: #14b8a6 !important; }
.stError   { background: rgba(220,38,38,0.05) !important;   border-left-color: #dc2626 !important; }
.stInfo    { background: rgba(251,191,36,0.04) !important;  border-left-color: #fbbf24 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #070912 !important;
    border-right: 1px solid #161c2a !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] label { color: #3d4f6b !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3   { color: #dce4f0 !important; }
.sb-brand {
    font-family: 'Epilogue', sans-serif;
    font-size: 1.7rem; font-weight: 900;
    color: #f1f5f9; letter-spacing: 0.05em; text-transform: uppercase;
}
.sb-brand span { color: #fbbf24; }
.sb-tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem; color: #2d3f58;
    letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 1rem;
}
.sb-stat {
    background: #0f1420; border: 1px solid #1c2640;
    border-radius: 8px; padding: 0.75rem 1rem; margin-top: 0.4rem;
}
.sb-stat-lbl { font-size: 0.62rem; letter-spacing: 0.16em; text-transform: uppercase; color: #2d3f58; }
.sb-stat-val { font-family:'Epilogue',sans-serif; font-size:1.9rem; font-weight:900; color:#fbbf24; line-height:1.1; }

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
# DB init
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_database():
    return CandidateDatabase(os.getenv("CHROMA_DB_PATH", "./chroma_db"))

db = get_database()

# ─────────────────────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">📄 CV Ingestion Pipeline</div>
    <div class="hero-title"><strong>CV Parser</strong></div>
    <div class="hero-sub">Upload &amp; parse candidate CVs with Groq AI — RECRUTO</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sb-brand">REC<span>R</span>UTO</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-tagline">CV Parser · Groq Edition</div>', unsafe_allow_html=True)

    st.markdown(f"""
        <div class="sb-stat">
            <div class="sb-stat-lbl">Candidates in DB</div>
            <div class="sb-stat-val">{db.get_candidate_count()}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="slabel">Supported Formats</div>', unsafe_allow_html=True)
    st.markdown("""
- PDF (.pdf)
- Word (.docx, .doc)
- Images (.png, .jpg, .jpeg)
- Text (.txt)
    """)

    st.markdown("---")
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
    ) if "selectbox" in dir(st) else "llama-3.3-70b-versatile"

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;font-size:0.72rem;color:#1c2640;letter-spacing:0.1em;">'
        'Powered by <span style="color:#fbbf24">GROQ AI</span> &amp; '
        '<span style="color:#14b8a6">CHROMADB</span></div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Upload + Options
# ─────────────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1.2, 1], gap="large")

with col1:
    st.markdown('<div class="panel-card"><div class="panel-title">📤 Upload CV</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Choose a CV file",
        type=["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"],
        help="Drag and drop or click to upload",
        label_visibility="collapsed",
    )
    candidate_name_input = st.text_input(
        "Candidate Name (optional — AI will extract if left blank)",
        placeholder="e.g. John Doe",
        help="Leave blank to let AI extract the name automatically from the CV",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="panel-card"><div class="panel-title">⚡ Options</div>', unsafe_allow_html=True)
    use_ai = st.checkbox(
        "🤖 AI Extraction (Groq)",
        value=True,
        help="Extract structured info using Groq AI — enables automatic name & email detection",
    )
    save_to_db = st.checkbox(
        "💾 Save to Database",
        value=True,
        help="Store parsed CV in ChromaDB for job matching",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Parse button + logic
# ─────────────────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚀  Parse CV", type="primary"):
        with st.spinner("Extracting text from CV…"):
            raw_text = parse_cv(uploaded_file)

        with st.expander("📝 Raw Extracted Text"):
            st.text_area("Raw Text", raw_text, height=200, label_visibility="collapsed")

        structured_info = ""

        if use_ai and api_key:
            with st.spinner("⚡ Groq AI extracting structured information…"):
                structured_info = extract_cv_info_with_ai(raw_text, api_key)

            st.success("✅ CV Parsed Successfully!")
            st.markdown('<div class="slabel">Structured Information</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ccard">{structured_info}</div>', unsafe_allow_html=True)

        elif use_ai and not api_key:
            st.warning("⚠️ Groq API key not set — falling back to raw text. Enter your key in the sidebar.")
            structured_info = raw_text
        else:
            structured_info = raw_text
            st.success("✅ Text Extracted Successfully!")

        # ── Name resolution (THE FIX) ─────────────────────────────────────
        # Priority: 1) recruiter typed a name  2) AI extracted  3) filename fallback
        final_name = None

        if candidate_name_input.strip():
            # Recruiter provided a name explicitly
            final_name = candidate_name_input.strip()
            name_source = "manual"
        else:
            # Try to extract from AI structured output
            final_name = extract_name_from_structured(structured_info)
            if final_name:
                name_source = "ai"
            else:
                # Last resort: use filename without extension
                base = os.path.splitext(uploaded_file.name)[0]
                final_name = base.replace("_", " ").replace("-", " ").title()
                name_source = "filename"

        # Show which source was used
        if name_source == "manual":
            st.markdown(
                f'<div class="name-resolved">✏️ Name (manual): <strong>{final_name}</strong></div>',
                unsafe_allow_html=True,
            )
        elif name_source == "ai":
            st.markdown(
                f'<div class="name-resolved">🤖 Name auto-extracted: <strong>{final_name}</strong></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="name-fallback">📄 Name from filename: <strong>{final_name}</strong></div>',
                unsafe_allow_html=True,
            )

        # ── Save to DB ────────────────────────────────────────────────────
        if save_to_db:
            try:
                candidate_id = str(uuid.uuid4())

                db.add_candidate(
                    candidate_id=candidate_id,
                    name=final_name,                  # ← always a real name now
                    cv_text=raw_text,
                    structured_info=structured_info,
                    file_name=uploaded_file.name,
                )

                st.success(f"✅ **{final_name}** saved to database!  Total candidates: {db.get_candidate_count()}")
                st.info(f"🆔 Candidate ID: `{candidate_id}`")

            except Exception as e:
                st.error(f"❌ Error saving to database: {str(e)}")

# ─────────────────────────────────────────────────────────────────────────────
# Candidate database viewer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<hr class="rdiv">', unsafe_allow_html=True)
st.markdown('<div class="slabel">Candidate Database</div>', unsafe_allow_html=True)

if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

col_btn1, col_btn2, _ = st.columns([1, 1, 4])
with col_btn1:
    if st.button("🔄  Load Candidates", type="primary"):
        st.session_state.refresh_counter += 1
with col_btn2:
    if st.button("♻️  Refresh"):
        st.cache_resource.clear()
        st.session_state.refresh_counter += 1
        st.rerun()

if st.session_state.refresh_counter > 0:
    with st.spinner("Loading candidates…"):
        db_fresh = CandidateDatabase(os.getenv("CHROMA_DB_PATH", "./chroma_db"))
        all_candidates = db_fresh.get_all_candidates()

        if "error" in all_candidates:
            st.error(f"❌ Error: {all_candidates['error']}")

        elif all_candidates and all_candidates.get("ids") and len(all_candidates["ids"]) > 0:
            total = len(all_candidates["ids"])
            st.markdown(f"""
                <div class="sb-stat" style="margin-bottom:1rem;">
                    <div class="sb-stat-lbl">Total Candidates</div>
                    <div class="sb-stat-val">{total}</div>
                </div>
            """, unsafe_allow_html=True)

            for candidate_id, metadata in zip(all_candidates["ids"], all_candidates["metadatas"]):
                display_name = metadata.get("name", "Unknown")
                file_name    = metadata.get("file_name", "N/A")

                with st.expander(f"👤 {display_name}  ·  {file_name}"):
                    col_info, col_action = st.columns([3, 1])

                    with col_info:
                        st.markdown(f"**🆔 ID:** `{candidate_id}`")
                        st.markdown(f"**📅 Uploaded:** {metadata.get('upload_date', 'N/A')}")

                        # Show extracted email if present in structured_info
                        si = metadata.get("structured_info", "")
                        email = extract_email_from_text(si)
                        if email:
                            st.markdown(f"**✉️ Email:** `{email}`")

                    with col_action:
                        delete_key = f"delete_{candidate_id}_{st.session_state.refresh_counter}"
                        if st.button("🗑️  Delete", key=delete_key):
                            try:
                                db_del = CandidateDatabase(os.getenv("CHROMA_DB_PATH", "./chroma_db"))
                                db_del.delete_candidate(candidate_id)
                                st.cache_resource.clear()
                                st.session_state.refresh_counter += 1
                                st.success(f"✅ Deleted {display_name}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        else:
            st.info("📭 No candidates found. Upload some CVs to get started!")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rfooter">
    <span>RECRUTO</span> · CV Parser · Powered by <span>Groq AI</span> &amp; ChromaDB
</div>
""", unsafe_allow_html=True)