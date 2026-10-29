"""LLM token usage tracking and cost estimate (GET /api/admin/usage)."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models.ai_call import AICall
from app.repositories.ai_call_repo import get_usage, record_ai_call


def _call(db, service="cv_extraction", prompt=1000, completion=500, success=True, days_ago=0):
    call = record_ai_call(
        db,
        service=service,
        model="openai/gpt-oss-120b",
        prompt_version="v",
        prompt_tokens=prompt,
        completion_tokens=completion,
        latency_ms=100.0,
        success=success,
    )
    if days_ago:
        call.created_at = datetime.now(UTC) - timedelta(days=days_ago)
        db.commit()
    return call


class TestUsageAggregation:
    def test_totals_cost_and_services(self, db):
        _call(db, "cv_extraction", 1_000_000, 0)
        _call(db, "cv_extraction", 0, 1_000_000)
        _call(db, "answer_scoring", 100, 50, success=False)

        usage = get_usage(db)
        totals = usage["totals"]
        assert totals["calls"] == 3 and totals["failures"] == 1
        assert totals["prompt_tokens"] == 1_000_100
        assert totals["completion_tokens"] == 1_000_050
        # default prices: $0.15 / 1M input, $0.60 / 1M output
        assert totals["estimated_cost_usd"] == pytest.approx(0.15 + 0.60, abs=1e-3)

        cv = next(s for s in usage["by_service"] if s["service"] == "cv_extraction")
        assert cv["total_calls"] == 2
        assert cv["avg_tokens_per_call"] == 1_000_000
        assert cv["avg_cost_per_call_usd"] == pytest.approx(0.375)
        assert usage["by_service"][0]["service"] == "cv_extraction"  # biggest first

    def test_period_filter_and_daily_breakdown(self, db):
        _call(db, days_ago=40)
        _call(db, days_ago=2)
        _call(db)
        recent = get_usage(db, days=30)
        assert recent["totals"]["calls"] == 2
        assert len(recent["by_day"]) == 2
        assert get_usage(db)["totals"]["calls"] == 3  # all time

    def test_empty(self, db):
        usage = get_usage(db, days=7)
        assert usage["totals"]["calls"] == 0 and usage["by_day"] == []


class TestUsageApi:
    def test_requires_auth(self, client):
        assert client.get("/api/admin/usage").status_code == 401

    def test_endpoint(self, client, auth_headers, db):
        _call(db)
        _call(db, days_ago=100)
        resp = client.get("/api/admin/usage?days=30", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["totals"]["calls"] == 1
        everything = client.get("/api/admin/usage?days=0", headers=auth_headers).json()
        assert everything["totals"]["calls"] == 2

    def test_every_llm_feature_is_tracked(self, db):
        """Job extraction (and the other services) record their tokens."""
        from app.services.job_service import extract_job_skills

        resp = MagicMock()
        resp.choices[0].message.content = json.dumps({"title": "Dev", "required_skills": ["Go"]})
        resp.usage.prompt_tokens = 321
        resp.usage.completion_tokens = 123
        with patch("groq.Groq") as groq:
            groq.return_value.chat.completions.create.return_value = resp
            extract_job_skills("", "We need a Go developer for our team.", db=db)
        call = db.query(AICall).one()
        assert (call.service, call.prompt_tokens, call.completion_tokens) == (
            "job_extraction",
            321,
            123,
        )
