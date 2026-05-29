from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_auth
from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.core.logging import get_logger
from app.db.session import get_db
from app.repositories import candidate_repo
from app.schemas.candidate import CandidateListOut, CandidateOut
from app.services import cv_service
from app.services.extraction_service import parse_structured_info

logger = get_logger(__name__)
router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
async def upload_candidate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    settings = get_settings()
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"File type .{ext} is not allowed.")

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise FileTooLargeError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

    # Extract raw text then AI-structured info
    cv_text = cv_service.extract_text(file.filename, data)
    structured_info = cv_service.extract_cv_info_with_ai(cv_text, db=db)

    # Parse structured info into semantic fields (no extra API call)
    parsed = parse_structured_info(structured_info)

    name = cv_service.extract_name_from_structured(structured_info) or file.filename
    email = cv_service.extract_email_from_structured(structured_info)
    candidate_id = cv_service.generate_candidate_id()

    # Save full data to PostgreSQL
    candidate = candidate_repo.create_candidate(
        db,
        id=candidate_id,
        name=name,
        email=email,
        file_name=file.filename,
        structured_info=structured_info,
        cv_text=cv_text,
        skills_text=parsed.skills_text,
        experience_text=parsed.experience_text,
        certifications_text=parsed.certifications_text,
    )

    # Embed compact semantic document in ChromaDB (not raw CV text)
    candidate_repo.add_to_vector_store(candidate_id, parsed.chroma_document)

    logger.info(
        "Candidate created: id=%s name=%s skills=%d chars chroma_doc=%d chars",
        candidate_id,
        name,
        len(parsed.skills_text),
        len(parsed.chroma_document),
    )
    return candidate


@router.get("", response_model=CandidateListOut)
def list_candidates(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    candidates = candidate_repo.list_candidates(db)
    return CandidateListOut(total=len(candidates), candidates=candidates)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: str, db: Session = Depends(get_db), _: str = Depends(require_auth)
):
    from app.core.exceptions import CandidateNotFoundError

    if not candidate_repo.delete_candidate(db, candidate_id):
        raise CandidateNotFoundError()
    candidate_repo.remove_from_vector_store(candidate_id)
