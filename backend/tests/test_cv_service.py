import pytest
from unittest.mock import patch, MagicMock

from app.core.exceptions import UnsupportedFileTypeError, CVExtractionError, GroqAPIError
from app.services import cv_service


class TestExtractText:
    def test_txt_file(self):
        data = b"Alice Smith\nSoftware Engineer\nalice@example.com"
        result = cv_service.extract_text("cv.txt", data)
        assert "Alice Smith" in result

    def test_empty_txt_raises(self):
        with pytest.raises(CVExtractionError):
            cv_service.extract_text("cv.txt", b"   ")

    def test_unsupported_extension_raises(self):
        with pytest.raises(UnsupportedFileTypeError):
            cv_service.extract_text("cv.xyz", b"some content")

    def test_no_extension_raises(self):
        with pytest.raises(UnsupportedFileTypeError):
            cv_service.extract_text("cv", b"some content")


class TestHelpers:
    def test_extract_email_from_text(self):
        assert cv_service.extract_email_from_text("contact: foo@bar.com") == "foo@bar.com"
        assert cv_service.extract_email_from_text("no email here") is None
        assert cv_service.extract_email_from_text("") is None

    def test_extract_name_from_structured(self):
        assert cv_service.extract_name_from_structured("Full Name: John Doe") == "John Doe"
        assert cv_service.extract_name_from_structured("1. Full Name: Jane Smith") == "Jane Smith"
        assert cv_service.extract_name_from_structured("Name: N/A") is None
        assert cv_service.extract_name_from_structured("") is None

    def test_extract_email_from_structured(self):
        info = "Full Name: Alice\nEmail: alice@example.com\nSkills: Python"
        assert cv_service.extract_email_from_structured(info) == "alice@example.com"

    def test_generate_candidate_id_is_32_chars(self):
        cid = cv_service.generate_candidate_id()
        assert len(cid) == 32
        assert cid != cv_service.generate_candidate_id()  # unique


class TestAIExtraction:
    def test_groq_success(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Full Name: Alice\nEmail: alice@example.com"
        mock_response.usage.prompt_tokens = 100

        with patch("groq.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.return_value = mock_response
            result = cv_service.extract_cv_info_with_ai("Alice Smith CV text here")

        assert "Full Name: Alice" in result

    def test_groq_failure_raises_groq_api_error(self):
        with patch("groq.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.side_effect = Exception("connection error")
            with pytest.raises(GroqAPIError):
                cv_service.extract_cv_info_with_ai("some cv text")
