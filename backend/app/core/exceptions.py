"""
Custom exception hierarchy for REECRUTO.
All domain errors inherit from AppError so the global handler can catch them cleanly.
"""
from fastapi import HTTPException, status


class AppError(Exception):
    """Base class for all application errors."""
    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)

    def as_http(self) -> HTTPException:
        return HTTPException(status_code=self.status_code, detail=self.detail)


# ── CV / file errors ──────────────────────────────────────────────────────────
class UnsupportedFileTypeError(AppError):
    status_code = 400
    detail = "Unsupported file type."

class FileTooLargeError(AppError):
    status_code = 400
    detail = "File exceeds maximum allowed size."

class CVExtractionError(AppError):
    status_code = 422
    detail = "Could not extract text from the uploaded file."


# ── AI errors ─────────────────────────────────────────────────────────────────
class GroqAPIError(AppError):
    status_code = 502
    detail = "AI service is temporarily unavailable. Please try again."

class GroqParseError(AppError):
    status_code = 502
    detail = "AI returned an unexpected response format."


# ── Candidate errors ──────────────────────────────────────────────────────────
class CandidateNotFoundError(AppError):
    status_code = 404
    detail = "Candidate not found."


# ── Interview errors ──────────────────────────────────────────────────────────
class SessionNotFoundError(AppError):
    status_code = 404
    detail = "Interview session not found."

class SessionAlreadyUsedError(AppError):
    status_code = 410
    detail = "This interview link has already been used."

class SessionExpiredError(AppError):
    status_code = 410
    detail = "This interview link has expired."


# ── Email errors ──────────────────────────────────────────────────────────────
class EmailDeliveryError(AppError):
    status_code = 502
    detail = "Failed to deliver email."
