"""
Tests for the evidence-based scoring, skill normalisation, JSON profiles
and the saved-jobs API.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.api.dependencies import require_auth
from app.main import app
from app.models.candidate import Candidate
from app.models.job import JobMatch
from app.services.extraction_service import load_profile, parse_structured_info
from app.services.scoring_service import compute_match
from app.services.skills import normalize_skill, skill_in_set, skill_in_text

PROFILE = {
    "full_name": "Mohamed Amine",
    "email": "amine@example.com",
    "summary": "AI engineer with strong teamwork and communication.",
    "skills": ["Python", "SQL", "PyTorch", "Docker", "Git", "Kafka"],
    "soft_skills": ["Teamwork", "Problem-solving"],
    "experience": [
        {
            "title": "Generative AI Intern",
            "company": "Talan",
            "duration": "2026",
            "technologies": ["Python", "LangGraph", "FastAPI", "ChromaDB"],
            "highlights": ["Built a RAG assistant for institutional services."],
        },
        {
            "title": "Database Intern",
            "company": "Oradist",
            "technologies": ["PostgreSQL"],
            "highlights": ["Optimized SQL queries."],
        },
    ],
    "projects": [
        {"name": "Image generation", "technologies": ["PyTorch", "Diffusers"], "description": ""}
    ],
    "certifications": [
        {"name": "IBM Data Science", "skills": ["Machine Learning", "Python", "Statistics"]}
    ],
}


# ── Skill normalisation ───────────────────────────────────────────────────────


class TestSkills:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Postgres", "postgresql"),
            ("  PostgreSQL ", "postgresql"),
            ("Retrieval‑Augmented Generation (RAG)", "rag"),
            ("K8s", "kubernetes"),
            ("Python 3.11", "python"),
            ("REST APIs", "rest api"),
        ],
    )
    def test_normalize(self, raw, expected):
        assert normalize_skill(raw) == expected

    def test_containment_whole_word_only(self):
        assert skill_in_set("docker", {"docker compose"})
        assert not skill_in_set("java", {"javascript"})
        assert not skill_in_set("c", {"c++"})

    def test_text_search(self):
        assert skill_in_text("sql", "Optimized SQL queries")
        assert not skill_in_text("sql", "Worked with PostgreSQL")
        assert skill_in_text("rest api", "Designed REST APIs")


# ── Evidence scoring ──────────────────────────────────────────────────────────


class TestEvidenceScoring:
    def _evidence(self, result, skill):
        return next(s for s in result.skills if s.skill == skill)

    def test_evidence_levels(self):
        result = compute_match(
            {"required": ["fastapi", "pytorch", "kafka", "statistics", "rust"]}, PROFILE
        )
        assert self._evidence(result, "fastapi").score == 1.0  # experience
        assert self._evidence(result, "pytorch").score == 0.8  # project
        assert self._evidence(result, "kafka").score == 0.4  # listed only
        assert self._evidence(result, "statistics").score == 0.2  # certification only
        assert self._evidence(result, "rust").score == 0.0
        assert result.missing_skills == ["rust"]
        assert "fastapi" in result.matched_skills

    def test_certification_bonus_is_capped(self):
        result = compute_match({"required": ["python"]}, PROFILE)
        assert self._evidence(result, "python").score == 1.0

    def test_implied_and_text_evidence(self):
        result = compute_match({"required": ["sql", "rag", "vector databases"]}, PROFILE)
        assert self._evidence(result, "sql").score == 1.0  # PostgreSQL in experience
        assert self._evidence(result, "rag").score == 1.0  # found in a highlight
        assert self._evidence(result, "vector databases").score == 1.0  # ChromaDB implies it

    def test_transitive_implication(self):
        # PyTorch (project) -> deep learning -> machine learning, plus the certification bonus
        result = compute_match({"required": ["machine learning"]}, PROFILE)
        assert self._evidence(result, "machine learning").score == 1.0

    def test_weights_without_nice_to_have(self):
        result = compute_match(
            {"required": ["fastapi"], "soft": ["teamwork", "leadership"]}, PROFILE
        )
        # 0.70 / 0.10 re-normalised → required 100, soft 50
        assert result.final_score == pytest.approx((100 * 0.7 + 50 * 0.1) / 0.8, abs=0.1)

    def test_full_weights(self):
        result = compute_match(
            {"required": ["fastapi"], "nice": ["rust"], "soft": ["teamwork"]}, PROFILE
        )
        assert result.final_score == pytest.approx(0.7 * 100 + 0.2 * 0 + 0.1 * 100)

    def test_legacy_profile_scores_zero(self):
        result = compute_match({"required": ["python"]}, None)
        assert result.final_score == 0
        assert result.legacy_profile

    def test_no_job_skills(self):
        assert compute_match({}, PROFILE).final_score == 0


# ── JSON profile parsing ──────────────────────────────────────────────────────


class TestProfileParsing:
    def test_load_profile_from_json(self):
        profile = load_profile(json.dumps(PROFILE))
        assert profile["full_name"] == "Mohamed Amine"
        assert profile["experience"][0]["technologies"][0] == "Python"

    def test_legacy_markdown_returns_none(self):
        assert load_profile("**Full Name:** Bob\n### Skills\nPython") is None

    def test_tolerates_bad_shapes(self):
        profile = load_profile(json.dumps({"skills": "Python, SQL", "experience": ["Dev"]}))
        assert profile["skills"] == ["Python", "SQL"]
        assert profile["experience"][0]["title"] == "Dev"

    def test_chroma_document_has_no_contact_info(self):
        parsed = parse_structured_info(json.dumps({**PROFILE, "phone": "+216 00 000 000"}))
        assert "amine@example.com" not in parsed.chroma_document
        assert "+216" not in parsed.chroma_document
        assert "Python" in parsed.skills_text


# ── Jobs API ──────────────────────────────────────────────────────────────────

JOB_SKILLS = {"required": ["fastapi", "python", "rust"], "nice": ["kafka"], "soft": ["teamwork"]}


@pytest.fixture
def api(client):
    app.dependency_overrides[require_auth] = lambda: "admin"
    yield client
    app.dependency_overrides.pop(require_auth, None)


def _add_candidate(db, cid: str, profile: dict | None):
    db.add(
        Candidate(
            id=cid,
            name=f"Candidate {cid}",
            email=f"{cid}@test.com",
            structured_info=json.dumps(profile) if profile is not None else "**Full Name:** X",
        )
    )
    db.commit()


def _create_job(api):
    with patch(
        "app.services.job_service.extract_job_skills",
        return_value=("Backend Engineer", JOB_SKILLS),
    ):
        resp = api.post(
            "/api/jobs",
            json={"title": "", "description": "We need a Python FastAPI engineer, Rust a must."},
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestJobsApi:
    def test_requires_auth(self, client):
        assert client.get("/api/jobs").status_code in (401, 403)

    def test_create_scores_existing_cvs(self, api, db):
        _add_candidate(db, "good", PROFILE)
        _add_candidate(db, "legacy", None)
        job = _create_job(api)

        assert job["title"] == "Backend Engineer"
        assert job["skills"]["required"] == ["fastapi", "python", "rust"]
        assert [m["candidate_id"] for m in job["matches"]] == ["good", "legacy"]
        best = job["matches"][0]
        assert best["score"] > 50
        assert best["missing_skills"] == ["rust"]
        assert job["matches"][1]["legacy_profile"] is True
        assert job["pending_count"] == 0

    def test_grid_and_match_only_new_cvs(self, api, db):
        _add_candidate(db, "first", PROFILE)
        job = _create_job(api)

        _add_candidate(db, "second", PROFILE)
        grid = api.get("/api/jobs").json()
        assert grid[0]["candidates_count"] == 1
        assert grid[0]["pending_count"] == 1

        run = api.post(f"/api/jobs/{job['id']}/match").json()
        assert run["scored"] == 1  # only the new CV
        assert len(run["job"]["matches"]) == 2

        again = api.post(f"/api/jobs/{job['id']}/match").json()
        assert again["scored"] == 0
        assert api.post(f"/api/jobs/{job['id']}/match?rescore_all=true").json()["scored"] == 2

    def test_edit_skills_rescores(self, api, db):
        _add_candidate(db, "c1", PROFILE)
        job = _create_job(api)
        resp = api.patch(
            f"/api/jobs/{job['id']}",
            json={"skills": {"required": ["FastAPI"], "nice": [], "soft": []}},
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["skills"]["required"] == ["fastapi"]
        assert updated["matches"][0]["score"] == 100

    def test_delete_job_and_candidate_cleanup(self, api, db):
        _add_candidate(db, "c1", PROFILE)
        job = _create_job(api)

        with patch("app.repositories.candidate_repo.get_candidates_collection"):
            assert api.delete("/api/candidates/c1").status_code == 204
        # matches of a deleted candidate never linger
        assert db.query(JobMatch).count() == 0

        assert api.delete(f"/api/jobs/{job['id']}").status_code == 204
        assert api.get(f"/api/jobs/{job['id']}").status_code == 404

    def test_unknown_job_404(self, api):
        assert api.get("/api/jobs/999").status_code == 404
        assert api.post("/api/jobs/999/match").status_code == 404

    def test_description_too_short(self, api):
        assert api.post("/api/jobs", json={"description": "short"}).status_code == 422


class TestJobExtraction:
    def test_extract_job_skills_parses_and_normalises(self):
        from unittest.mock import MagicMock

        from app.services.job_service import extract_job_skills

        resp = MagicMock()
        resp.choices[0].message.content = json.dumps(
            {
                "title": "ML Engineer",
                "required_skills": ["Python", "Postgres", "Python"],
                "nice_to_have_skills": ["python", "K8s"],
                "soft_skills": ["Communication"],
            }
        )
        with patch("groq.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.return_value = resp
            title, skills = extract_job_skills("", "We need someone good at Python.")

        assert title == "ML Engineer"
        assert skills == {
            "required": ["python", "postgresql"],
            "nice": ["kubernetes"],
            "soft": ["communication"],
        }


# ── ChromaDB: semantic skills + retrieve -> rank ──────────────────────────────


class TestSemanticSkills:
    def test_similar_skill_proves_with_discount(self):
        # "torch-lightning" is unknown to the alias list; ChromaDB says it is close to pytorch
        result = compute_match(
            {"required": ["lightning"]},
            PROFILE,
            similar={"lightning": [("pytorch", 0.86)]},
            semantic_factor=0.8,
        )
        evidence = result.skills[0]
        assert evidence.score == pytest.approx(0.64)  # project evidence 0.8 x 0.8
        assert evidence.sources[0]["via"] == "pytorch"

    def test_exact_evidence_wins_over_similar(self):
        result = compute_match(
            {"required": ["fastapi"]}, PROFILE, similar={"fastapi": [("kafka", 0.81)]}
        )
        assert result.skills[0].score == 1.0
        assert "via" not in result.skills[0].sources[0]

    def test_similar_skills_threshold(self):
        from app.core.config import get_settings
        from app.services import semantic_service

        settings = get_settings().model_copy(
            update={"SEMANTIC_SKILLS_ENABLED": True, "SKILL_SIMILARITY_THRESHOLD": 0.8}
        )
        collection = MagicMock()
        collection.count.return_value = 3
        collection.query.return_value = {
            "ids": [["pytorch", "torch", "tensorflow"]],
            "distances": [[0.0, 0.1, 0.35]],
        }
        with (
            patch.object(semantic_service, "get_settings", return_value=settings),
            patch.object(semantic_service, "get_skills_collection", return_value=collection),
        ):
            out = semantic_service.similar_skills(["pytorch"])
        assert out == {"pytorch": [("torch", 0.9)]}  # itself excluded, tensorflow too far

    def test_profile_skill_names(self):
        from app.services.scoring_service import profile_skill_names

        names = profile_skill_names(PROFILE)
        assert {"python", "langgraph", "postgresql", "diffusers", "statistics"} <= names


class TestRetrieveThenRank:
    def test_prefilter_keeps_top_k(self, api, db):
        from app.core.config import get_settings
        from app.services import semantic_service

        for cid in ("a", "b", "c"):
            _add_candidate(db, cid, PROFILE)
        settings = get_settings().model_copy(
            update={"MATCH_PREFILTER_MIN_CVS": 2, "MATCH_RETRIEVE_TOP_K": 2}
        )
        collection = MagicMock()
        collection.query.return_value = {"ids": [["c", "a"]]}
        with (
            patch.object(semantic_service, "get_settings", return_value=settings),
            patch.object(semantic_service, "get_candidates_collection", return_value=collection),
        ):
            job = _create_job(api)

        assert sorted(m["candidate_id"] for m in job["matches"]) == ["a", "c"]
        assert job["filtered_out_count"] == 1
        assert job["pending_count"] == 0  # "b" was handled, not pending forever
        _, kwargs = collection.query.call_args
        assert kwargs["n_results"] == 2
        assert kwargs["where"] == {"candidate_id": {"$in": ["a", "b", "c"]}}

    def test_below_threshold_scores_everything(self, api, db):
        for cid in ("a", "b"):
            _add_candidate(db, cid, PROFILE)
        job = _create_job(api)  # default MATCH_PREFILTER_MIN_CVS=500
        assert len(job["matches"]) == 2
        assert job["filtered_out_count"] == 0

    def test_retrieval_failure_falls_back_to_all(self, api, db):
        from app.core.config import get_settings
        from app.services import semantic_service

        for cid in ("a", "b"):
            _add_candidate(db, cid, PROFILE)
        settings = get_settings().model_copy(update={"MATCH_PREFILTER_MIN_CVS": 1})
        collection = MagicMock()
        collection.query.side_effect = RuntimeError("chroma down")
        with (
            patch.object(semantic_service, "get_settings", return_value=settings),
            patch.object(semantic_service, "get_candidates_collection", return_value=collection),
        ):
            job = _create_job(api)
        assert len(job["matches"]) == 2
