import base64
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Response, Header
from pydantic import BaseModel, Field

from services.resume_builder import (
    build_docx_resume,
    build_pdf_resume,
    apply_rewrites_to_custom_docx,
    convert_docx_to_pdf_via_libreoffice,
    CURATED_TEMPLATES
)
from database import decode_access_token, get_user_by_id, get_scan_file, get_latest_scan_file

router = APIRouter(prefix="/api/resume", tags=["resume"])

class ExportRequest(BaseModel):
    format: str = Field(default="docx", pattern="^(docx|pdf)$")
    template_id: str = Field(default="original")
    scan_id: Optional[str] = None
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
    - When template_id == 'original' or custom_template_base64 is provided:
      Edits the real document in place at the Run level (preserving 100% of formatting, layout, and margins).
    - When template_id is one of the 3 curated templates ('ivy_league', 'tech_minimalist', 'modern_corporate'):
      Freshly lays out the resume in the chosen target design.
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

    # Branch 1: "original" or custom template -> ALWAYS edit original bytes in place at run level
    if req.custom_template_base64 or tmpl_id == "original":
        source_docx_bytes = None
        template_label = "OriginalFormat"

        if req.custom_template_base64:
            try:
                source_docx_bytes = base64.b64decode(req.custom_template_base64)
                template_label = "CustomTemplate"
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid custom template data: {str(e)}"
                )
        elif req.scan_id:
            scan_record = get_scan_file(req.scan_id)
            if not scan_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Original uploaded resume file not found for this scan session. Please re-upload your .docx file or select a curated template."
                )
            if scan_record.get("file_type") != "docx":
                if req.format == "pdf":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Your resume was originally uploaded as a PDF. Directly editing and preserving compiled PDF documents in-place is not supported. To export with 100% layout preservation, please upload your resume in Word (.docx) format or select one of our curated ATS templates (Ivy League, Tech Minimalist, Modern Corporate) for PDF export."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Your resume was originally uploaded as a PDF. To keep your original format byte-for-byte as DOCX, please upload your resume in .docx format or choose one of our curated templates."
                    )
            source_docx_bytes = scan_record["file_bytes"]
        else:
            # Fallback to the latest scan file in memory/DB if available
            latest_scan = get_latest_scan_file()
            if latest_scan and latest_scan.get("file_type") == "docx":
                source_docx_bytes = latest_scan["file_bytes"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Original resume document (.docx) is required for 'Keep Original Format'. Please provide a scan_id or upload your .docx template, or select one of our curated templates (Ivy League, Tech Minimalist, Modern Corporate)."
                )

        # Apply rewrites strictly at the Run level in place
        try:
            edited_docx_bytes = apply_rewrites_to_custom_docx(source_docx_bytes, req.applied_rewrites)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not apply rewrites to original document: {str(e)}"
            )

        if req.format == "docx":
            filename = f"{safe_name}_{template_label}_Optimized.docx"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return Response(
                content=edited_docx_bytes,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )
        else:
            # Format is PDF for original / custom template
            pdf_bytes = convert_docx_to_pdf_via_libreoffice(edited_docx_bytes)
            if pdf_bytes:
                filename = f"{safe_name}_{template_label}_Optimized.pdf"
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Access-Control-Expose-Headers": "Content-Disposition"
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF export is not supported for custom or original-format templates because preserving 100% of your exact document fonts, spacing, margins, and formatting requires Word (.docx). Please download as DOCX, or select one of our curated ATS templates (Ivy League, Tech Minimalist, Modern Corporate) for PDF export."
                )

    # Branch 2: Curated templates ('ivy_league', 'tech_minimalist', 'modern_corporate')
    if req.format == "pdf":
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

