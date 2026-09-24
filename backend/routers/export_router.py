import base64
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Response, Header
from pydantic import BaseModel, Field

from services.resume_builder import (
    build_docx_resume,
    build_pdf_resume,
    apply_rewrites_to_custom_docx,
    CURATED_TEMPLATES
)
from database import decode_access_token, get_user_by_id

router = APIRouter(prefix="/api/resume", tags=["resume"])

class ExportRequest(BaseModel):
    format: str = Field(default="docx", pattern="^(docx|pdf)$")
    template_id: str = Field(default="original")
    parsed_resume: Dict[str, Any]
    applied_rewrites: List[Dict[str, Any]] = Field(default_factory=list)
    custom_template_base64: Optional[str] = None


@router.get("/templates")
async def get_templates():
    """Returns curated student resume templates."""
    return list(CURATED_TEMPLATES.values())


@router.post("/export")
async def export_optimized_resume(
    req: ExportRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Generates and returns an ATS-optimized resume in DOCX or PDF format.
    Entitlement check: Verifies active Pro access.
    """
    # Verify user token
    is_pro = False
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user = get_user_by_id(int(payload["sub"]))
            if user and user.get("is_pro"):
                is_pro = True

    if not is_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resume export with AI bullet rewrites is a ResumeFit Pro feature. Please redeem your campus/team promo code."
        )

    contact = req.parsed_resume.get("contact", {})
    raw_name = contact.get("name") or req.parsed_resume.get("candidate_name") or "Candidate"
    safe_name = "".join(c for c in raw_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    tmpl_id = req.template_id if req.template_id in CURATED_TEMPLATES else "original"

    # Handle custom user-uploaded DOCX template
    if req.custom_template_base64:
        try:
            custom_bytes = base64.b64decode(req.custom_template_base64)
            if req.format == "docx":
                file_bytes = apply_rewrites_to_custom_docx(custom_bytes, req.applied_rewrites)
                filename = f"{safe_name}_CustomTemplate_Optimized.docx"
                media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                file_bytes = build_pdf_resume(req.parsed_resume, req.applied_rewrites, template_id=tmpl_id)
                filename = f"{safe_name}_CustomTemplate_Optimized.pdf"
                media_type = "application/pdf"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse custom template: {str(e)}"
            )
    elif req.format == "pdf":
        file_bytes = build_pdf_resume(req.parsed_resume, req.applied_rewrites, template_id=tmpl_id)
        filename = f"{safe_name}_{tmpl_id}_Optimized.pdf"
        media_type = "application/pdf"
    else:
        file_bytes = build_docx_resume(req.parsed_resume, req.applied_rewrites, template_id=tmpl_id)
        filename = f"{safe_name}_{tmpl_id}_Optimized.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
