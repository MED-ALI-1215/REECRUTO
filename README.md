# REECRUTO

AI-powered recruitment platform. Automates CV parsing, semantic candidate matching, and AI-conducted interviews — from upload to hiring decision.

---

## What it does

| Step | Who | What happens |
|---|---|---|
| 1 | Recruiter | Uploads candidate CVs (PDF, DOCX, TXT, image) |
| 2 | System | AI extracts a structured JSON profile — skills, experience (with technologies used), projects, certifications |
| 3 | Recruiter | Saves a job description → its skills are extracted once, every CV is ranked with per-skill evidence |
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
│   │   ├── models/           ORM models (candidates, jobs, job_matches, interview_sessions, interview_results, ai_calls)
│   │   ├── repositories/     all DB access (candidate_repo, job_repo, interview_repo, ai_call_repo)
│   │   ├── schemas/          Pydantic request/response schemas
│   │   └── services/         business logic (cv, extraction, job, scoring, skills, semantic, interview, email)
│   ├── prompts/              versioned AI prompt templates
│   ├── alembic/              database migrations
│   ├── scripts/              skill_similarity.py — tune the semantic-matching threshold
│   ├── tests/                98 tests — services, repositories, API, security, scoring, jobs
│   ├── requirements.txt      pinned dependencies
│   ├── Dockerfile
│   └── .env.example
├── frontend/                 React + Vite frontend
│   └── src/
│       ├── pages/            Login, Upload, Match (jobs grid), JobDetail, Dashboard, Interview
│       ├── components/       Layout (sidebar nav), shared UI (chips, score bars, toast)
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
- ChromaDB — semantic retrieval of CVs and semantic skill matching
- Groq API (`openai/gpt-oss-120b`, JSON mode) — CV & job extraction, question generation, answer scoring
- JWT authentication (python-jose)
- Tenacity — automatic retry with exponential backoff on all Groq calls

**Frontend**
- React 19 + Vite
- React Router v7
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
cd frontend
npm install
npm run dev            # runs on http://localhost:3000
```

The API URL defaults to `http://localhost:8000`; set `VITE_API_URL` in `frontend/.env` to change it.

### 4. Login
```
Username: admin
Password: reecruto-admin
```

Override them with `RECRUITER_USERNAME` / `RECRUITER_PASSWORD` in `backend/.env`.

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
| `RECRUITER_USERNAME` / `RECRUITER_PASSWORD` | — | Recruiter login. Default: `admin` / `reecruto-admin` |
| `GROQ_MODEL` | — | Default: `openai/gpt-oss-120b` |
| `CHROMA_USE_SERVER` | — | `false` for local file mode, `true` for Docker server mode |
| `MATCH_PREFILTER_MIN_CVS` | — | Number of CVs from which ChromaDB pre-selects before scoring. Below it, every CV is scored. Default: 500 |
| `MATCH_RETRIEVE_TOP_K` | — | How many CVs ChromaDB keeps per search when pre-selecting. Default: 100 |
| `SEMANTIC_SKILLS_ENABLED` | — | Semantic skill matching ("Torch" ≈ "PyTorch"). Default: `true` |
| `SKILL_SIMILARITY_THRESHOLD` | — | Minimum similarity (0–1) for two skill names to count as the same. Default: 0.80 |
| `SEMANTIC_MATCH_FACTOR` | — | Weight of a similar-skill match vs an exact one. Default: 0.8 |
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

98 tests covering: JWT security, CV parsing, interview service, repositories, all API endpoints, evidence scoring, skill normalisation, saved jobs, ChromaDB retrieve → rank, AI call logging.

All external calls (Groq, SMTP) are mocked — tests run without real credentials.

---

## Matching algorithm

Matching is a two-stage **retrieve → rank** pipeline. No LLM call happens per CV:
the job's skills are extracted once (one Groq call) when the job is saved.

### 1. Retrieve (ChromaDB, recall)

Every CV is embedded in ChromaDB as a compact document (summary, skills, job titles,
projects, certifications — no contact details). Once there are at least
`MATCH_PREFILTER_MIN_CVS` CVs, ChromaDB pre-selects the `MATCH_RETRIEVE_TOP_K` CVs
closest to the job; the others are marked "not pre-selected". Below that threshold
every CV is scored.

### 2. Rank (evidence-based scoring, precision)

For each skill the job asks for, the matcher looks for **proof** in the CV's JSON profile:

| Evidence | Value |
|---|---|
| Only listed in "skills" | 0.4 |
| Used in a project | 0.8 |
| Used in professional experience | 1.0 |
| Covered by a certification | +0.2 (max 1.0) |

```
score = 0.70 × required skills + 0.20 × nice-to-have skills + 0.10 × soft skills
```

Categories the job doesn't mention are dropped and the weights re-normalised
(e.g. no nice-to-have skills → 0.90 / 0.10).

- **Skill normalisation** — aliases (`Postgres` = `PostgreSQL`, `K8s` = `Kubernetes`) and
  implied skills (`PostgreSQL` ⇒ `SQL`, `PyTorch` ⇒ `Deep Learning` ⇒ `Machine Learning`).
- **Semantic skill matching** — ChromaDB keeps a vocabulary of every skill name seen in CVs.
  A job skill with no exact match can be proven by a similar one (cosine similarity ≥
  `SKILL_SIMILARITY_THRESHOLD`), worth `SEMANTIC_MATCH_FACTOR` of the evidence.
- **Explainability** — every skill keeps its sources ("Experience: Generative AI Intern @ Talan",
  "Project: REECRUTO (≈ torch, 86%)"), shown on the job page.

### Saved jobs

Jobs are stored with their extracted skills (editable by the recruiter). The Job Matcher shows
a grid of jobs; "Search new CVs" scores only the CVs uploaded since the last search, and
"Rescore all" recomputes every match (also needed after the scoring formula changes —
matches carry a `scoring_version`).

Tune the semantic threshold with:

```bash
cd backend
python -m scripts.skill_similarity                    # built-in examples
python -m scripts.skill_similarity "torch" "pytorch"  # your own pair
```

---

## AI prompt versioning

All Groq prompts live in `backend/prompts/` as versioned text files:

```
cv_extraction_v2.txt        JSON profile (v1 kept for reference)
job_extraction_v1.txt       required / nice-to-have / soft skills of a job
question_generation_v1.txt
answer_scoring_v1.txt
final_report_v1.txt
```

To update a prompt, edit the `.txt` file — no code changes needed (restart the backend: prompts are cached). Every Groq call is logged to the `ai_calls` table (service, model, tokens, latency, success/failure). View stats at `GET /api/admin/ai-stats`.

---

## API reference

Full interactive docs at `http://localhost:8000/docs` when the backend is running.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | — | Get JWT token |
| POST | `/api/candidates` | ✅ | Upload and parse a CV |
| GET | `/api/candidates` | ✅ | List all candidates |
| DELETE | `/api/candidates/{id}` | ✅ | Remove a candidate |
| GET | `/api/jobs` | ✅ | Saved jobs (grid) with best score and new CVs count |
| POST | `/api/jobs` | ✅ | Save a job, extract its skills, score every CV |
| GET | `/api/jobs/{id}` | ✅ | Job, skills and ranked candidates with evidence |
| PATCH | `/api/jobs/{id}` | ✅ | Edit title, description or skills (rescores) |
| POST | `/api/jobs/{id}/match` | ✅ | Score new CVs (`?rescore_all=true` for all) |
| DELETE | `/api/jobs/{id}` | ✅ | Delete a job and its matches |
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
- PDF with a text layer, DOCX, or TXT — scanned image PDFs are not supported (`.doc` is not supported either)
- CVs in other languages work: the extraction prompt translates the profile to English
- CVs uploaded before the JSON extraction (v2) must be re-uploaded — they are flagged "Re-upload CV"
- Multi-page PDFs are fully supported

---

## CI/CD

GitHub Actions runs on every push to `main`/`dev` and every pull request:

1. `ruff check app/` — linting
2. `black --check app/` — formatting
3. `pytest tests/` — full test suite

No secrets needed for CI — all external calls are mocked in tests.
