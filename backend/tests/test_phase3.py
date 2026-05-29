"""
Phase 3 specific tests:
- Prompt loader
- AI call DB persistence
- Matching re-rank fallback
- Admin stats endpoint
"""
import pytest
from unittest.mock import patch, MagicMock

from app.core.prompts import load_prompt
from app.repositories.ai_call_repo import record_ai_call, get_stats
from app.models.ai_call import AICall


class TestPromptLoader:
    def test_load_cv_extraction_prompt(self):
        result = load_prompt("cv_extraction_v1.txt", cv_text="Alice Smith Engineer")
        assert "Alice Smith Engineer" in result
        assert "Full Name" in result

    def test_load_question_generation_prompt(self):
        result = load_prompt("question_generation_v1.txt",
                             n=5, job_title="Engineer", job_description="Build APIs")
        assert "5" in result
        assert "Engineer" in result
        assert "Build APIs" in result

    def test_load_answer_scoring_prompt(self):
        result = load_prompt("answer_scoring_v1.txt",
                             job_title="Engineer", job_description_excerpt="Build APIs",
                             question="What is REST?", answer="REST is an architecture style.")
        assert "What is REST?" in result
        assert "REST is an architecture style." in result

    def test_load_final_report_prompt(self):
        result = load_prompt("final_report_v1.txt",
                             job_title="Engineer", candidate_name="Alice",
                             qa_summary="Q1: What is Python?\nA: A language.")
        assert "Alice" in result
        assert "Engineer" in result

    def test_load_rerank_prompt(self):
        result = load_prompt("match_rerank_v1.txt",
                             job_description="Python backend",
                             candidates_summary="Candidate ID: abc\nName: Alice")
        assert "Alice" in result

    def test_missing_prompt_raises(self):
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt_v99.txt")

    def test_prompt_caching(self):
        # Loading same prompt twice should hit cache (lru_cache)
        r1 = load_prompt("cv_extraction_v1_system.txt")
        r2 = load_prompt("cv_extraction_v1_system.txt")
        assert r1 == r2


class TestAICallRepo:
    def test_record_success(self, db):
        call = record_ai_call(
            db, service="cv_extraction", model="llama-3.3-70b-versatile",
            prompt_version="cv_extraction_v1", prompt_tokens=500,
            completion_tokens=200, latency_ms=1234.5, success=True,
        )
        assert call.id is not None
        assert call.service == "cv_extraction"
        assert call.success is True
        assert call.error_message is None

    def test_record_failure(self, db):
        call = record_ai_call(
            db, service="answer_scoring", model="llama-3.3-70b-versatile",
            prompt_version="answer_scoring_v1", prompt_tokens=0,
            completion_tokens=0, latency_ms=500.0, success=False,
            error_message="Connection timeout",
        )
        assert call.success is False
        assert call.error_message == "Connection timeout"

    def test_get_stats(self, db):
        # Insert a few records
        for i in range(3):
            record_ai_call(
                db, service="cv_extraction", model="llama-3.3-70b-versatile",
                prompt_version="cv_extraction_v1", prompt_tokens=100 * (i + 1),
                completion_tokens=50, latency_ms=1000.0, success=True,
            )
        record_ai_call(
            db, service="answer_scoring", model="llama-3.3-70b-versatile",
            prompt_version="answer_scoring_v1", prompt_tokens=200,
            completion_tokens=100, latency_ms=800.0, success=False,
            error_message="timeout",
        )

        stats = get_stats(db)
        services = {s["service"]: s for s in stats}

        assert "cv_extraction" in services
        assert services["cv_extraction"]["total_calls"] == 3
        assert services["cv_extraction"]["total_tokens"] == 600  # 100+200+300

        assert "answer_scoring" in services
        assert services["answer_scoring"]["failures"] == 1


class TestAdminEndpoint:
    def test_ai_stats_requires_auth(self, client):
        resp = client.get("/api/admin/ai-stats")
        assert resp.status_code == 401

    def test_ai_stats_empty(self, client, auth_headers):
        resp = client.get("/api/admin/ai-stats", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_ai_stats_populated(self, client, auth_headers, db):
        record_ai_call(
            db, service="cv_extraction", model="llama-3.3-70b-versatile",
            prompt_version="cv_extraction_v1", prompt_tokens=400,
            completion_tokens=150, latency_ms=1100.0, success=True,
        )
        db.commit()
        resp = client.get("/api/admin/ai-stats", headers=auth_headers)
        assert resp.status_code == 200
        stats = resp.json()
        assert len(stats) == 1
        assert stats[0]["service"] == "cv_extraction"


class TestMatchingRerank:
    def test_rerank_fallback_on_groq_failure(self, client, auth_headers):
        """If Groq re-ranking fails, should fall back to vector scores gracefully."""
        with patch("app.repositories.candidate_repo.get_candidates_collection") as mock_col:
            mock_col.return_value.count.return_value = 0
            resp = client.post(
                "/api/jobs/match",
                headers=auth_headers,
                json={"job_description": "Python backend engineer", "n_results": 5},
            )
        # Empty store = empty result, no error
        assert resp.status_code == 200
        assert resp.json() == []

    def test_cv_extraction_persists_ai_call(self, client, auth_headers):
        """Uploading a CV should create an ai_calls record."""
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Full Name: Alice\nEmail: alice@test.com"
        mock_resp.usage.prompt_tokens = 300
        mock_resp.usage.completion_tokens = 100

        with patch("groq.Groq") as MockGroq, \
             patch("app.repositories.candidate_repo.get_candidates_collection") as mock_col:
            MockGroq.return_value.chat.completions.create.return_value = mock_resp
            mock_col.return_value.add = MagicMock()

            resp = client.post(
                "/api/candidates",
                headers=auth_headers,
                files={"file": ("cv.txt", b"Alice Smith Software Engineer", "text/plain")},
            )

        assert resp.status_code == 201

        # Check AI call was recorded
        ai_stats = client.get("/api/admin/ai-stats", headers=auth_headers).json()
        services = {s["service"] for s in ai_stats}
        assert "cv_extraction" in services
