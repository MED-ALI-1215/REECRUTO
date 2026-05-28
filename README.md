# REECRUTO

AI-powered recruitment platform. Automates CV parsing, semantic candidate matching, and AI-conducted interviews — from upload to hiring decision.

---

## What it does

| Step | Who | What happens |
|---|---|---|
| 1 | Recruiter | Uploads candidate CVs (PDF, DOCX, TXT, image) |
| 2 | System | AI extracts structured profile — name, email, skills, experience, certifications |
| 3 | Recruiter | Pastes a job description → ranked candidates with match scores |
| 4 | Recruiter | Sends interview invite — candidate receives a one-time link by email |
| 5 | Candidate | Completes AI interview — questions generated per role, each answer scored in real time |
| 6 | Recruiter | Reviews completed interviews on dashboard — accepts or rejects with one click |
| 7 | Candidate | Receives acceptance (face-to-face scheduled) or rejection email automatically |

---

## Project structure

```
REECRUTO/
├── backend/                  FastAPI backend
│   ├── app/
│   │   ├── api/routes/       candidates, jobs, interviews, dashboard, auth, admin
│   │   ├── core/             config, logging, security, exceptions, prompts
│   │   ├── db/               SQLAlchemy session, ChromaDB client
│   │   ├── models/           ORM models (candidates, interview_sessions, interview_results, ai_calls)
│   │   ├── repositories/     all DB access (candidate_repo, interview_repo, ai_call_repo)
│   │   ├── schemas/          Pydantic request/response schemas
│   │   └── services/         business logic (cv, matching, scoring, interview, email, extraction)
│   ├── prompts/              versioned AI prompt templates
│   ├── alembic/              database migrations
│   ├── tests/                86 tests — services, repositories, API, security, scoring
│   ├── requirements.txt      pinned dependencies
│   ├── Dockerfile
│   └── .env.example
├── reecruto-frontend/        React + Vite frontend
│   └── src/
│       ├── pages/            Login, Upload, Match, Dashboard, Interview
│       ├── components/       Layout (sidebar nav)
│       └── api/              axios client + all API calls
├── docker-compose.yml        PostgreSQL + ChromaDB + backend
├── .github/workflows/ci.yml  lint + format check + tests on every push
└── .gitignore
```

---

## Tech stack

**Backend**
- FastAPI + Uvicorn
- SQLAlchemy 2.0 + Alembic (PostgreSQL in production, SQLite for local dev)
- ChromaDB — vector embeddings for semantic candidate search
- Groq API (llama-3.3-70b-versatile) — CV extraction, question generation, answer scoring
- JWT authentication (python-jose)
- Tenacity — automatic retry with exponential backoff on all Groq calls

**Frontend**
- React 18 + Vite
- React Router v6
- Axios
- Lucide React (icons)

**Infrastructure**
- Docker + Docker Compose
- GitHub Actions CI (ruff + black + pytest)

---

## Local development setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Clone
```bash
git clone https://github.com/MED-ALI-1215/REECRUTO.git
cd REECRUTO
```

### 2. Backend
```bash
cd backend
cp .env.example .env
# Fill in .env — see Environment variables section below
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

Health check: `http://localhost:8000/health`

### 3. Frontend
```bash
cd reecruto-frontend
cp .env.example .env   # set VITE_API_URL=http://localhost:8000
npm install
npm run dev            # runs on http://localhost:3000
```

### 4. Login
```
Username: admin
Password: reecruto-admin
```

---

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | From console.groq.com |
| `EMAIL_ADDRESS` | ✅ | Gmail address used to send emails |
| `EMAIL_PASSWORD` | ✅ | Gmail App Password (16 chars, not your login password) |
| `SECRET_KEY` | ✅ | Random 64-char string — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `APP_BASE_URL` | ✅ | Base URL for candidate interview links — `http://localhost:3000/interview` for local dev |
| `DATABASE_URL` | ✅ | `sqlite:///./reecruto.db` for local dev, PostgreSQL URL for production |
| `GROQ_MODEL` | — | Default: `llama-3.3-70b-versatile` |
| `CHROMA_USE_SERVER` | — | `false` for local file mode, `true` for Docker server mode |
| `MAX_UPLOAD_SIZE_MB` | — | Default: 10 |

---

## Running with Docker

```bash
# Make sure backend/.env exists with real values first
docker compose up --build
```

Services started:
- `postgres` on port 5432
- `chromadb` on port 8001
- `backend` on port 8000

The backend container automatically points to the Docker service names for PostgreSQL and ChromaDB — no manual URL changes needed.

### Run database migrations
```bash
cd backend
DATABASE_URL=postgresql+psycopg2://reecruto:reecruto@localhost:5432/reecruto \
  python -m alembic upgrade head
```

---

## Running tests

```bash
cd backend
GROQ_API_KEY=test EMAIL_ADDRESS=test@test.com EMAIL_PASSWORD=pass \
DATABASE_URL=sqlite:///:memory: SECRET_KEY=any-long-string-here \
python -m pytest tests/ -v
```

86 tests covering: JWT security, CV parsing, interview service, repositories, all API endpoints, scoring formula, AI call logging.

All external calls (Groq, SMTP) are mocked — tests run without real credentials.

---

## Matching algorithm

Candidate scoring uses a 3-signal formula with no mandatory Groq API call:

```
final_score = (vector_similarity × 0.40) + (skills_overlap × 0.40) + (cert_bonus × 0.20)
```

**Vector similarity** — ChromaDB semantic search on a compact embedding document built from skills, experience titles, and projects only (not raw CV noise).

**Skills overlap** — job description is matched against a curated vocabulary of ~120 tech skills. Only recognized terms are compared — French words, stopwords, and sentence fragments are ignored. Matched and missing skills are returned per candidate.

**Certification bonus** — 100 if job requires certs and candidate has matching ones, 75 if certs not required, 50 if required but missing.

**Deep mode** (optional, one Groq call) — recruiter can request a Groq re-ranking pass on top of the formula for a second opinion on close calls.

---

## AI prompt versioning

All Groq prompts live in `backend/prompts/` as versioned text files:

```
cv_extraction_v1.txt
question_generation_v1.txt
answer_scoring_v1.txt
final_report_v1.txt
match_rerank_v1.txt
```

To update a prompt, edit the `.txt` file — no code changes needed. Every Groq call is logged to the `ai_calls` table (service, model, tokens, latency, success/failure). View stats at `GET /api/admin/ai-stats`.

---

## API reference

Full interactive docs at `http://localhost:8000/docs` when the backend is running.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | — | Get JWT token |
| POST | `/api/candidates` | ✅ | Upload and parse a CV |
| GET | `/api/candidates` | ✅ | List all candidates |
| DELETE | `/api/candidates/{id}` | ✅ | Remove a candidate |
| POST | `/api/jobs/match` | ✅ | Match candidates to a job description |
| POST | `/api/interviews` | ✅ | Create session + send invite email |
| GET | `/api/interviews/{token}` | — | Load interview session (candidate) |
| POST | `/api/interviews/{token}/questions` | — | Generate interview questions |
| POST | `/api/interviews/{token}/score` | — | Score a single answer |
| POST | `/api/interviews/{token}/finish` | — | Save completed interview |
| GET | `/api/dashboard/results` | ✅ | List completed interviews |
| POST | `/api/dashboard/results/{id}/accept` | ✅ | Send acceptance email |
| POST | `/api/dashboard/results/{id}/reject` | ✅ | Send rejection email |
| GET | `/api/admin/ai-stats` | ✅ | AI call usage statistics |
| GET | `/health` | — | Service health check |

---

## CV format recommendations

For best matching results:
- CVs should use English skill names (Python, FastAPI, Docker — not French equivalents)
- Section headers in English (Skills, Work Experience, Certifications)
- PDF with a text layer, DOCX, or TXT — scanned image PDFs are not supported
- Multi-page PDFs are fully supported

---

## CI/CD

GitHub Actions runs on every push to `main`/`dev` and every pull request:

1. `ruff check app/` — linting
2. `black --check app/` — formatting
3. `pytest tests/` — full test suite

No secrets needed for CI — all external calls are mocked in tests.
