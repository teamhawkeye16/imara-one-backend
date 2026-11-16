"""
Documents Metadata & Content Endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.document import Document
from backend.app.schemas.document import DocumentResponse

router = APIRouter(tags=["Documents"])


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str = Path(..., description="Unique document ID"),
    db: Session = Depends(get_db),
):
    """
    Retrieve indexed document details by ID.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    domain_name = doc.domain.domain_name if doc.domain else ""
    return DocumentResponse(
        id=doc.id,
        url=doc.url,
        title=doc.title,
        meta_description=doc.meta_description,
        clean_text=doc.clean_text,
        domain_name=domain_name,
        content_hash=doc.content_hash,
        language=doc.language,
        http_status=doc.http_status,
        word_count=doc.word_count,
        indexed_at=doc.indexed_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )

