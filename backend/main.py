import logging
import uuid
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAX_UPLOAD_SIZE_BYTES,
    ALLOWED_ORIGINS,
    ALLOW_CREDENTIALS,
    IS_CORS_FALLBACK
)
from contextlib import asynccontextmanager
from pydantic import BaseModel
from presets.roles import ROLE_PRESETS
from parsers import PDFParser, DOCXParser
from agents.pipeline import AgentPipeline
from database import init_db, save_scan_file, save_scan_result, get_scan_result
from routers.auth import router as auth_router
from routers.export_router import router as export_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("resumefit")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("SQLite database initialized successfully.")
    yield

app = FastAPI(
    title="ResumeFit API",
    description="ATS Compatibility & AI Optimization Pipeline for University Resumes",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(export_router)

# CORS setup
if IS_CORS_FALLBACK:
    logger.warning(
        "⚠️ CORS WARNING: ALLOWED_ORIGINS is unset or wildcard '*'. "
        "Falling back to local dev origins %s with allow_credentials=False. "
        "For production (e.g. Render), set ALLOWED_ORIGINS to your frontend domain (e.g. https://resume-fit-peach.vercel.app).",
        ALLOWED_ORIGINS
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client if API key is provided in .env
gemini_client = None
if GEMINI_API_KEY and GEMINI_API_KEY.strip():
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY.strip())
        logger.info(f"Google GenAI client initialized successfully with GEMINI_API_KEY (key length: {len(GEMINI_API_KEY.strip())} chars, model: {GEMINI_MODEL}).")
    except Exception as e:
        logger.warning(f"Failed to initialize Google GenAI client: {e}. Fallback engine will be active.")
else:
    logger.info("No GEMINI_API_KEY found in .env. Running in rubric fallback mode.")

# Pipeline instance
pipeline = AgentPipeline(gemini_client=gemini_client)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "gemini_configured": gemini_client is not None,
        "max_upload_size_mb": 5
    }


@app.get("/api/presets")
async def get_presets():
    """Returns available job description presets."""
    return list(ROLE_PRESETS.values())


@app.post("/api/scan")
async def scan_resume(
    file: UploadFile = File(...),
    mode: str = Form("general"),  # 'general', 'preset', or 'custom'
    role_id: Optional[str] = Form(None),
    custom_jd: Optional[str] = Form(None),
):
    """
    Unified resume scanning endpoint:
    1. Validates file size (max 5MB) -> HTTP 413 if exceeded
    2. Validates format (.pdf or .docx)
    3. Parses text & inspects formatting (HTTP 422 if scanned PDF or unreadable)
    4. Runs agentic pipeline (Parser + JD -> Scoring -> Recommendations)
    5. Returns ATS score, breakdown, engine attribution, and actionable fixes
    """
    # 1. Read file bytes and enforce 5MB size limit
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        logger.warning(f"File size {file_size} exceeds limit {MAX_UPLOAD_SIZE_BYTES}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({round(file_size / (1024*1024), 2)}MB) exceeds maximum allowed limit of 5MB."
        )

    # 2. File extension check
    filename = (file.filename or "").lower()
    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file format. Please upload a PDF (.pdf) or Word document (.docx)."
        )

    # 3. Persist original uploaded file's raw bytes for in-place original-format export
    scan_id = uuid.uuid4().hex
    file_type = "docx" if filename.endswith(".docx") else "pdf"
    save_scan_file(
        scan_id=scan_id,
        filename=file.filename or f"resume.{file_type}",
        file_bytes=file_bytes,
        file_type=file_type
    )

    # 4. Resume text parsing
    if file_type == "pdf":
        resume_text, formatting_meta = PDFParser.parse(file_bytes)
    else:
        resume_text, formatting_meta = DOCXParser.parse(file_bytes)

    # 5. Resolve Job Description (if applicable)
    jd_text = None
    if mode == "preset" and role_id:
        preset = ROLE_PRESETS.get(role_id)
        if preset:
            jd_text = preset["description"]
        else:
            logger.warning(f"Unknown preset role_id: {role_id}, falling back to general mode.")
            mode = "general"
    elif mode == "custom" and custom_jd and custom_jd.strip():
        jd_text = custom_jd.strip()
    else:
        mode = "general"
        jd_text = None

    # 6. Execute Agentic Pipeline
    result = await pipeline.run(
        resume_text=resume_text,
        formatting_meta=formatting_meta,
        mode=mode,
        jd_text=jd_text
    )

    result["scan_id"] = scan_id
    result["file_type"] = file_type

    # Persist parsed_resume, parsed_jd, and scoring_result for subsequent fast recommendation regeneration
    save_scan_result(
        scan_id=scan_id,
        parsed_resume=result["parsed_resume"],
        parsed_jd=result.get("parsed_jd"),
        scoring_result=result["scoring_result"]
    )

    return JSONResponse(content=result)


class RegenerateRecommendationsRequest(BaseModel):
    scan_id: str


@app.post("/api/resume/regenerate-recommendations")
async def regenerate_recommendations(payload: RegenerateRecommendationsRequest):
    """
    Regenerates recommendation fixes for an already-scanned resume.
    Uses cached parsed_resume, parsed_jd, and scoring_result.
    Executes ONLY recommendation_agent.run() (zero re-parsing, zero JD calls, saving Gemini quota).
    """
    scan_id = payload.scan_id
    cached = get_scan_result(scan_id)
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan result not found or expired. Please upload and re-scan your resume."
        )

    parsed_resume = cached["parsed_resume"]
    parsed_jd = cached.get("parsed_jd")
    scoring_result = cached["scoring_result"]

    # Call ONLY recommendation_agent.run() - zero parser / JD agent calls
    rec_res = await pipeline.recommendation_agent.run(
        scoring_result=scoring_result,
        parsed_resume=parsed_resume,
        parsed_jd=parsed_jd
    )

    rec_used_gemini = rec_res["used_gemini"]

    # Update cached recommendations
    scoring_result["recommendations"] = rec_res["data"]
    save_scan_result(
        scan_id=scan_id,
        parsed_resume=parsed_resume,
        parsed_jd=parsed_jd,
        scoring_result=scoring_result
    )

    return JSONResponse(content={
        "scan_id": scan_id,
        "recommendations": rec_res["data"],
        "used_gemini": rec_used_gemini,
        "engine": "gemini" if rec_used_gemini else "rubric_fallback",
        "agent_engines": {
            "parser": None,
            "jd": None,
            "recommendation": rec_used_gemini
        }
    })

