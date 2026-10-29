"""Unsupported or image-based CVs are rejected with a clear message (no OCR)."""

import io

import PyPDF2
import pytest

from app.core.exceptions import CVExtractionError, UnsupportedFileTypeError
from app.services import cv_service


def _blank_pdf() -> bytes:
    """A PDF with a page but no text layer — what a scanned CV looks like to PyPDF2."""
    writer = PyPDF2.PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestExtraction:
    def test_image_only_pdf_is_rejected(self):
        with pytest.raises(CVExtractionError, match="scan or an image"):
            cv_service.extract_text("cv.pdf", _blank_pdf())

    def test_corrupted_pdf_is_rejected(self):
        with pytest.raises(CVExtractionError, match="could not be read"):
            cv_service.extract_text("cv.pdf", b"not a pdf at all")

    @pytest.mark.parametrize("name", ["cv.png", "cv.jpg", "cv.doc", "cv"])
    def test_unsupported_types(self, name):
        with pytest.raises(UnsupportedFileTypeError, match="PDF .* DOCX or TXT"):
            cv_service.extract_text(name, b"data")


class TestUploadApi:
    @pytest.mark.parametrize("name", ["photo.png", "scan.jpeg", "old.doc"])
    def test_upload_unsupported_type_message(self, client, auth_headers, name):
        resp = client.post(
            "/api/candidates",
            headers=auth_headers,
            files={"file": (name, b"data", "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]
        assert "DOCX or TXT" in resp.json()["detail"]

    def test_upload_image_only_pdf_message(self, client, auth_headers):
        resp = client.post(
            "/api/candidates",
            headers=auth_headers,
            files={"file": ("scan.pdf", _blank_pdf(), "application/pdf")},
        )
        assert resp.status_code == 422
        assert "scan or an image" in resp.json()["detail"]
