import pytest
from unittest.mock import patch, MagicMock

from app.core.exceptions import GroqAPIError, GroqParseError
from app.services import interview_service


def _mock_groq_response(content: str, prompt_tokens: int = 50):
    mock = MagicMock()
    mock.choices[0].message.content = content
    mock.usage.prompt_tokens = prompt_tokens
    return mock


class TestGenerateQuestions:
    def test_returns_list_of_questions(self):
        content = "1. What is Python?\n2. Explain REST APIs.\n3. Describe your experience with FastAPI."
        with patch("app.services.interview_service._groq_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = _mock_groq_response(content)
            questions = interview_service.generate_questions("Backend Engineer", "Build APIs", n=3)
        assert len(questions) == 3
        assert "What is Python?" in questions[0]

    def test_groq_failure_raises(self):
        with patch("app.services.interview_service._groq_client") as mock_client:
            mock_client.return_value.chat.completions.create.side_effect = Exception("timeout")
            with pytest.raises(GroqAPIError):
                interview_service.generate_questions("Engineer", "description")

    def test_empty_answer_returns_zero_score(self):
        result = interview_service.score_answer("Q?", "", "Engineer", "desc")
        assert result["score"] == 0
        assert "No answer" in result["feedback"]


class TestScoreAnswer:
    def test_valid_json_response(self):
        content = '{"score": 85, "feedback": "Good answer.", "keywords": ["Python", "REST"]}'
        with patch("app.services.interview_service._groq_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = _mock_groq_response(content)
            result = interview_service.score_answer("What is REST?", "REST is...", "Engineer", "desc")
        assert result["score"] == 85
        assert "Python" in result["keywords"]

    def test_invalid_json_raises_parse_error(self):
        with patch("app.services.interview_service._groq_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = _mock_groq_response("not json at all")
            with pytest.raises(GroqParseError):
                interview_service.score_answer("Q?", "some answer", "Engineer", "desc")


class TestGenerateFinalReport:
    def test_valid_report(self):
        content = (
            '{"overall_score": 78, "summary": "Good candidate.", '
            '"strengths": "Python", "red_flags": "None", "recommendation": "Recommended"}'
        )
        with patch("app.services.interview_service._groq_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = _mock_groq_response(content)
            report = interview_service.generate_final_report(
                "Alice", "Engineer", ["Q1"], ["A1"], [{"score": 78}]
            )
        assert report["overall_score"] == 78
        assert report["recommendation"] == "Recommended"

    def test_groq_failure_raises(self):
        with patch("app.services.interview_service._groq_client") as mock_client:
            mock_client.return_value.chat.completions.create.side_effect = Exception("API down")
            with pytest.raises(GroqAPIError):
                interview_service.generate_final_report("Alice", "Engineer", ["Q1"], ["A1"], [{"score": 0}])
