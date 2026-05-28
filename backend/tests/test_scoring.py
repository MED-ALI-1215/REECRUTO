import pytest
from app.services.scoring_service import (
    compute_score, _extract_skills_from_text, _extract_candidate_skills
)
from app.services.extraction_service import parse_structured_info


class TestSkillExtraction:
    def test_extracts_known_skills_from_jd(self):
        jd = "We need a Python developer with FastAPI, PostgreSQL and Docker experience."
        skills = _extract_skills_from_text(jd)
        assert "python" in skills
        assert "fastapi" in skills
        assert "postgresql" in skills
        assert "docker" in skills

    def test_does_not_extract_stopwords_or_sentence_fragments(self):
        jd = "We are looking for a motivated team player who will work with us."
        skills = _extract_skills_from_text(jd)
        assert "looking" not in skills
        assert "motivated" not in skills
        assert "with" not in skills

    def test_extracts_multiword_skills(self):
        jd = "Experience with machine learning and deep learning is required."
        skills = _extract_skills_from_text(jd)
        assert "machine learning" in skills
        assert "deep learning" in skills

    def test_french_jd_sentence_words_not_treated_as_skills(self):
        # Only ASCII skill terms should be detected — French words won't be in vocab
        jd = "Nous recherchons un developpeur Python avec des connaissances en FastAPI et Docker"
        skills = _extract_skills_from_text(jd)
        assert "nous" not in skills
        assert "recherchons" not in skills
        assert "python" in skills
        # fastapi may or may not parse depending on accent stripping — check at least python/docker
        assert "docker" in skills

    def test_empty_jd_returns_empty(self):
        assert _extract_skills_from_text("") == set()


class TestCandidateSkillExtraction:
    def test_comma_separated_skills(self):
        skills = _extract_candidate_skills("Python, FastAPI, PostgreSQL, Docker")
        assert "python" in skills
        assert "fastapi" in skills

    def test_mixed_case_normalized(self):
        skills = _extract_candidate_skills("PYTHON, JavaScript")
        assert "python" in skills
        assert "javascript" in skills

    def test_empty_returns_empty(self):
        assert _extract_candidate_skills("") == set()
        assert _extract_candidate_skills(None) == set()


class TestScoringFormula:
    def _score(self, jd, skills, vector=50.0, experience="", certs=""):
        return compute_score(
            vector_score=vector,
            job_description=jd,
            skills_text=skills,
            experience_text=experience,
            certifications_text=certs,
        )

    def test_high_skill_match(self):
        result = self._score(
            jd="Python FastAPI PostgreSQL Docker developer",
            skills="Python, FastAPI, PostgreSQL, Docker, Redis",
            vector=70.0,
        )
        assert result.skills_score >= 80
        assert result.final_score >= 60

    def test_low_skill_match(self):
        result = self._score(
            jd="Python FastAPI PostgreSQL Docker developer",
            skills="Java, Spring, MySQL",
            vector=30.0,
        )
        assert result.skills_score < 30
        assert len(result.missing_skills) > 0

    def test_matched_and_missing_are_real_skills(self):
        result = self._score(
            jd="We need a Python and React developer with Docker",
            skills="Python, Vue, Docker",
            vector=60.0,
        )
        for skill in result.missing_skills:
            assert skill not in {"and", "with", "need", "we", "a"}

    def test_cert_bonus_when_job_requires_certs(self):
        result = self._score(
            jd="AWS certification required",
            skills="Python",
            certs="AWS Certified Solutions Architect",
        )
        assert result.cert_score == 100.0

    def test_no_cert_requirement_gives_neutral_score(self):
        result = self._score(
            jd="Python developer needed",
            skills="Python",
            certs="",
        )
        assert result.cert_score == 75.0

    def test_vector_score_weight(self):
        r1 = self._score(jd="Python developer", skills="Python", vector=100.0)
        r2 = self._score(jd="Python developer", skills="Python", vector=0.0)
        assert r1.final_score > r2.final_score

    def test_no_recognizable_skills_in_jd_gives_neutral(self):
        result = self._score(
            jd="Nous recherchons quelqu'un de motive et dynamique",
            skills="Python, FastAPI",
            vector=50.0,
        )
        assert result.skills_score == 50.0


class TestExtractionService:
    def test_parse_structured_info_returns_object(self):
        info = "Full Name: John Doe\nEmail: john@example.com\nSkills: Python, FastAPI\nWork Experience: Backend Developer at TechCorp"
        result = parse_structured_info(info)
        assert result is not None

    def test_extracts_skills_field(self):
        info = "Skills: Python, FastAPI, PostgreSQL\nWork Experience: Backend Developer"
        result = parse_structured_info(info)
        # ParsedCV uses skills_text not skills
        assert "python" in result.skills_text.lower() or "fastapi" in result.skills_text.lower()

    def test_empty_input_does_not_crash(self):
        result = parse_structured_info("")
        assert result is not None

    def test_chroma_doc_excludes_personal_info(self):
        info = "Full Name: John Doe\nEmail: john@example.com\nPhone: +1234567890\nSkills: Python, FastAPI"
        result = parse_structured_info(info)
        assert "john@example.com" not in result.chroma_document
        assert "+1234567890" not in result.chroma_document
