import pytest
from datetime import datetime, timezone

from app.repositories import candidate_repo, interview_repo
from app.core.exceptions import SessionNotFoundError


class TestCandidateRepo:
    def test_create_and_get(self, db):
        c = candidate_repo.create_candidate(
            db, id="abc123", name="Bob", email="bob@test.com",
            file_name="bob.pdf",
            structured_info="Full Name: Bob\n" + "x" * 2000,  # long — must not be truncated
            cv_text="Bob is a developer.",
        )
        assert c.id == "abc123"
        assert len(c.structured_info) > 1000  # no truncation

        fetched = candidate_repo.get_candidate(db, "abc123")
        assert fetched is not None
        assert fetched.name == "Bob"

    def test_get_nonexistent_returns_none(self, db):
        assert candidate_repo.get_candidate(db, "does-not-exist") is None

    def test_list_candidates(self, db):
        candidate_repo.create_candidate(db, id="c1", name="Alice", email=None,
            file_name="a.pdf", structured_info="x", cv_text="x",
            skills_text='', experience_text='', certifications_text='')
        candidate_repo.create_candidate(db, id="c2", name="Bob", email=None,
            file_name="b.pdf", structured_info="x", cv_text="x",
            skills_text='', experience_text='', certifications_text='')
        all_candidates = candidate_repo.list_candidates(db)
        assert len(all_candidates) == 2

    def test_delete_candidate(self, db):
        candidate_repo.create_candidate(db, id="del1", name="Delete Me", email=None,
            file_name="d.pdf", structured_info="x", cv_text="x",
            skills_text='', experience_text='', certifications_text='')
        assert candidate_repo.delete_candidate(db, "del1") is True
        assert candidate_repo.get_candidate(db, "del1") is None

    def test_delete_nonexistent_returns_false(self, db):
        assert candidate_repo.delete_candidate(db, "ghost") is False


class TestInterviewRepo:
    def test_create_session(self, db):
        sess = interview_repo.create_session(
            db, candidate_name="Alice", candidate_email="alice@test.com",
            job_title="Engineer", job_description="Build stuff",
        )
        assert sess.token
        assert not sess.used
        assert sess.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)

    def test_session_validity(self, db):
        sess = interview_repo.create_session(
            db, candidate_name="Alice", candidate_email="alice@test.com",
            job_title="Engineer", job_description="Build stuff",
        )
        valid, reason = interview_repo.is_session_valid(sess)
        assert valid
        assert reason == ""

    def test_mark_session_used(self, db):
        sess = interview_repo.create_session(
            db, candidate_name="Alice", candidate_email="alice@test.com",
            job_title="Engineer", job_description="Build stuff",
        )
        interview_repo.mark_session_used(db, sess.token)
        updated = interview_repo.get_session(db, sess.token)
        valid, reason = interview_repo.is_session_valid(updated)
        assert not valid
        assert "already been used" in reason

    def test_save_and_list_results(self, db):
        sess = interview_repo.create_session(
            db, candidate_name="Alice", candidate_email="alice@test.com",
            job_title="Engineer", job_description="Build stuff",
        )
        interview_repo.mark_session_used(db, sess.token)
        r = interview_repo.save_result(
            db, token=sess.token, candidate_name="Alice", candidate_email="alice@test.com",
            job_title="Engineer", questions=["Q1", "Q2"], answers=["A1", "A2"],
            scores=[{"score": 80}, {"score": 90}], overall_score=85.0,
            summary="Strong candidate", strengths="Python", red_flags="None",
            recommendation="Recommended",
        )
        assert r.overall_score == 85.0
        assert r.recommendation == "Recommended"
        results = interview_repo.list_results(db)
        assert len(results) == 1
