"""
API integration tests — uses TestClient with an in-memory SQLite DB.
All Groq and SMTP calls are mocked.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAuth:
    def test_login_success(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "reecruto-admin"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_wrong_username(self, client):
        resp = client.post("/api/auth/login", json={"username": "hacker", "password": "reecruto-admin"})
        assert resp.status_code == 401


class TestCandidates:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/candidates", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"total": 0, "candidates": []}

    def test_list_requires_auth(self, client):
        resp = client.get("/api/candidates")
        assert resp.status_code == 401

    def test_upload_candidate(self, client, auth_headers):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Full Name: Alice Smith\nEmail: alice@example.com"
        mock_resp.usage.prompt_tokens = 100

        with patch("groq.Groq") as MockGroq, \
             patch("app.repositories.candidate_repo.get_candidates_collection") as mock_col:
            MockGroq.return_value.chat.completions.create.return_value = mock_resp
            mock_col.return_value.add = MagicMock()

            resp = client.post(
                "/api/candidates",
                headers=auth_headers,
                files={"file": ("test_cv.txt", b"Alice Smith\nSoftware Engineer\nalice@example.com", "text/plain")},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Alice Smith"
        assert data["email"] == "alice@example.com"

    def test_upload_unsupported_type(self, client, auth_headers):
        resp = client.post(
            "/api/candidates",
            headers=auth_headers,
            files={"file": ("malware.exe", b"MZ binary", "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]

    def test_upload_empty_file(self, client, auth_headers):
        resp = client.post(
            "/api/candidates",
            headers=auth_headers,
            files={"file": ("empty.txt", b"   ", "text/plain")},
        )
        assert resp.status_code == 422  # CVExtractionError

    def test_delete_nonexistent_candidate(self, client, auth_headers):
        resp = client.delete("/api/candidates/does-not-exist", headers=auth_headers)
        assert resp.status_code == 404


class TestJobs:
    def test_match_empty_store(self, client, auth_headers):
        with patch("app.repositories.candidate_repo.get_candidates_collection") as mock_col:
            mock_col.return_value.count.return_value = 0
            resp = client.post(
                "/api/jobs/match",
                headers=auth_headers,
                json={"job_description": "Python backend engineer", "n_results": 5},
            )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_match_requires_auth(self, client):
        resp = client.post("/api/jobs/match", json={"job_description": "Python dev"})
        assert resp.status_code == 401


class TestInterviews:
    def test_create_interview_session(self, client, auth_headers):
        with patch("app.services.email_service.send_email"):
            resp = client.post(
                "/api/interviews",
                headers=auth_headers,
                json={
                    "candidate_name": "Alice",
                    "candidate_email": "alice@test.com",
                    "job_title": "Engineer",
                    "job_description": "Build APIs",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["token"]
        assert not data["used"]
        # token returned for use in other tests if needed

    def test_get_session_by_token(self, client, auth_headers):
        with patch("app.services.email_service.send_email"):
            create_resp = client.post(
                "/api/interviews",
                headers=auth_headers,
                json={
                    "candidate_name": "Bob",
                    "candidate_email": "bob@test.com",
                    "job_title": "Engineer",
                    "job_description": "Build APIs",
                },
            )
        token = create_resp.json()["token"]
        resp = client.get(f"/api/interviews/{token}")
        assert resp.status_code == 200
        assert resp.json()["candidate_name"] == "Bob"

    def test_get_nonexistent_session(self, client):
        resp = client.get("/api/interviews/nonexistent-token")
        assert resp.status_code == 404

    def test_used_session_returns_410(self, client, auth_headers):
        with patch("app.services.email_service.send_email"):
            token = client.post(
                "/api/interviews",
                headers=auth_headers,
                json={"candidate_name": "X", "candidate_email": "x@t.com",
                      "job_title": "Eng", "job_description": "desc"},
            ).json()["token"]

        # Manually mark as used via finish endpoint
        with patch("app.services.interview_service.generate_final_report") as mock_report:
            mock_report.return_value = {
                "overall_score": 70, "summary": "ok", "strengths": "x",
                "red_flags": "none", "recommendation": "Maybe"
            }
            client.post(f"/api/interviews/{token}/finish",
                        json={"questions": ["Q1"], "answers": ["A1"], "scores": [{"score": 70}]})

        # Now the session is used — should return 410
        resp = client.get(f"/api/interviews/{token}")
        assert resp.status_code == 410


class TestDashboard:
    def test_list_results_empty(self, client, auth_headers):
        resp = client.get("/api/dashboard/results", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_accept_nonexistent_result(self, client, auth_headers):
        resp = client.post("/api/dashboard/results/9999/accept", headers=auth_headers)
        assert resp.status_code == 404

    def test_reject_nonexistent_result(self, client, auth_headers):
        resp = client.post("/api/dashboard/results/9999/reject", headers=auth_headers)
        assert resp.status_code == 404


class TestErrorHandling:
    def test_groq_error_returns_502(self, client, auth_headers):
        """Groq failure on upload should return 502, not a raw traceback."""
        with patch("groq.Groq") as MockGroq, \
             patch("app.repositories.candidate_repo.get_candidates_collection"):
            MockGroq.return_value.chat.completions.create.side_effect = Exception("Groq is down")
            resp = client.post(
                "/api/candidates",
                headers=auth_headers,
                files={"file": ("cv.txt", b"Alice Smith Engineer", "text/plain")},
            )
        assert resp.status_code == 502
        # Must be a clean JSON error, not a traceback
        assert "detail" in resp.json()
        assert "traceback" not in resp.text.lower()
