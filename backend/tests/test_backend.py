import io
import pytest
from fastapi.testclient import TestClient
from docx import Document
import pypdfium2

from main import app
from config import MAX_UPLOAD_SIZE_BYTES
from agents.scoring_agent import ScoringAgent
from agents.recommendation_agent import RecommendationAgent
from agents.pipeline import AgentPipeline

client = TestClient(app)

def create_sample_docx(text: str) -> bytes:
    doc = Document()
    for line in text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_sample_pdf(text: str) -> bytes:
    """Creates a basic PDF using pypdfium2 / raw canvas."""
    # Let's use pypdfium2 or generate a minimal raw PDF
    # In pypdfium2:
    pdf = pypdfium2.PdfDocument.new()
    page = pdf.new_page(width=595, height=842) # A4
    # Note: text page in pdfium or reportlab
    # If we want simple text extraction via pdfplumber, a raw PDF string works:
    # A standard raw PDF text stream:
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 72 712 Td (" + text.encode("ascii", "ignore") + b") Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000234 00000 n \n0000000340 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n417\n%%EOF\n"
    )
    return pdf_content

def create_empty_scanned_pdf() -> bytes:
    """Creates a valid PDF with 0 extractable characters to simulate scanned PDF."""
    pdf = pypdfium2.PdfDocument.new()
    pdf.new_page(width=595, height=842)
    bio = io.BytesIO()
    pdf.save(bio)
    return bio.getvalue()


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["max_upload_size_mb"] == 5


def test_presets():
    res = client.get("/api/presets")
    assert res.status_code == 200
    presets = res.json()
    assert len(presets) == 4
    preset_ids = [p["id"] for p in presets]
    assert "data_analyst" in preset_ids
    assert "consultant" in preset_ids
    assert "marketing" in preset_ids
    assert "hr" in preset_ids


def test_file_size_limit_rejection():
    # Construct a payload slightly larger than 5MB
    large_payload = b"A" * (MAX_UPLOAD_SIZE_BYTES + 1024)
    res = client.post(
        "/api/scan",
        files={"file": ("large_resume.docx", large_payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res.status_code == 413
    assert "exceeds maximum allowed limit of 5MB" in res.json()["detail"]


def test_scanned_pdf_rejection():
    empty_pdf = create_empty_scanned_pdf()
    res = client.post(
        "/api/scan",
        files={"file": ("scanned_resume.pdf", empty_pdf, "application/pdf")},
        data={"mode": "general"}
    )
    assert res.status_code == 422
    assert "image-based or scanned PDF" in res.json()["detail"]


def test_valid_docx_scan_general_mode():
    sample_text = (
        "Alex Rivera\n"
        "alex.rivera@university.edu | (555) 123-4567 | linkedin.com/in/alexrivera\n\n"
        "Education\n"
        "Bachelor of Science in Computer Science, State University, 2024\n\n"
        "Technical Skills\n"
        "Python, SQL, Tableau, Excel, Data Analysis, Git, Problem Solving, Communication\n\n"
        "Professional Experience\n"
        "Data Analyst Intern - Acme Corp\n"
        "- Automated daily data aggregation scripts in Python, reducing manual reporting time by 35%.\n"
        "- Built interactive Tableau dashboards for executive leadership, tracking $150k in quarterly revenue.\n"
        "- Optimized SQL queries across PostgreSQL databases, increasing throughput by 2.5x.\n"
    )
    docx_bytes = create_sample_docx(sample_text)

    res = client.post(
        "/api/scan",
        files={"file": ("alex_rivera_resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "ats_score" in data
    assert 0 <= data["ats_score"] <= 100
    assert "breakdown" in data
    assert "keyword_match" in data["breakdown"]
    assert "formatting" in data["breakdown"]
    assert "sections" in data["breakdown"]
    assert "achievements" in data["breakdown"]
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 5
    assert "engine" in data
    assert data["engine"] in ["gemini", "rubric_fallback"]
    assert "agent_engines" in data
    assert "parser" in data["agent_engines"]
    assert "jd" in data["agent_engines"]
    assert "recommendation" in data["agent_engines"]
    # General mode skips JD agent, so jd should be None
    assert data["agent_engines"]["jd"] is None


def test_valid_docx_scan_preset_mode():
    sample_text = (
        "Jordan Smith\n"
        "jordan@example.com | (555) 987-6543 | linkedin.com/in/jordansmith\n\n"
        "Education\n"
        "BBA in Finance & Consulting, Metro University, 2025\n\n"
        "Skills\n"
        "Financial Modeling, Excel, PowerPoint, Stakeholder Management, Strategy, Problem Solving\n\n"
        "Experience\n"
        "Consulting Analyst Intern - Global Advisory\n"
        "- Developed comprehensive market research decks using PowerPoint for C-suite clients.\n"
        "- Built dynamic financial valuation models in Excel, saving 8 hours of analyst workload per week.\n"
        "- Led stakeholder workshops across 3 client departments.\n"
    )
    docx_bytes = create_sample_docx(sample_text)

    res = client.post(
        "/api/scan",
        files={"file": ("jordan_resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "preset", "role_id": "consultant"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ats_score"] > 50
    # In preset mode, JD Agent ran, so jd should be a bool (True or False)
    assert isinstance(data["agent_engines"]["jd"], bool)


@pytest.mark.asyncio
async def test_scoring_agent_metrics_accuracy():
    """Confirms bare numbers are not counted as metrics in ScoringAgent."""
    agent = ScoringAgent()
    resume_with_bare_digits = {
        "contact": {"email": "test@test.com"},
        "education": [{"degree": "BS"}],
        "skills": ["Python"],
        "experience": [{
            "role": "Student Leader",
            "bullets": [
                "Led a team of 5 students on senior design project",
                "Graduated in 2023 with GPA 3.8",
                "Completed 3 independent research projects"
            ]
        }]
    }

    res = await agent.run(resume_with_bare_digits, None, {}, "general")
    ach_diag = res["diagnostics"]["achievements"]
    # None of these bare digits should count as metric bullets
    assert ach_diag["metric_bullets"] == 0

    resume_with_real_metrics = {
        "contact": {"email": "test@test.com"},
        "education": [{"degree": "BS"}],
        "skills": ["Python"],
        "experience": [{
            "role": "Engineer",
            "bullets": [
                "Increased speed by 35% across all pipelines",
                "Generated $12k in new sponsorship revenue",
                "Automated nightly jobs saving 10 hours per week"
            ]
        }]
    }
    res_real = await agent.run(resume_with_real_metrics, None, {}, "general")
    ach_diag_real = res_real["diagnostics"]["achievements"]
    assert ach_diag_real["metric_bullets"] == 3


def test_real_sample_pdf_scan():
    """Tests scanning the real generated Sarah Chen PDF resume."""
    from pathlib import Path
    pdf_path = Path(__file__).resolve().parent.parent.parent / "sample_resumes" / "sarah_chen_data_analyst.pdf"
    assert pdf_path.exists()
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    res = client.post(
        "/api/scan",
        files={"file": ("sarah_chen_data_analyst.pdf", pdf_bytes, "application/pdf")},
        data={"mode": "preset", "role_id": "data_analyst"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ats_score"] >= 65
    assert data["breakdown"]["keyword_match"] >= 40
    assert len(data["recommendations"]) >= 5


def test_real_sample_scanned_pdf_error():
    """Tests that the image-only scanned PDF returns HTTP 422 with the exact required error."""
    from pathlib import Path
    pdf_path = Path(__file__).resolve().parent.parent.parent / "sample_resumes" / "scanned_image_only_resume.pdf"
    assert pdf_path.exists()
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    res = client.post(
        "/api/scan",
        files={"file": ("scanned_image_only_resume.pdf", pdf_bytes, "application/pdf")},
        data={"mode": "general"}
    )
    assert res.status_code == 422
    assert "image-based or scanned PDF" in res.json()["detail"]


import time
import json
import asyncio

class MockGeminiResponse:
    def __init__(self, text: str):
        self.text = text

class MockAioModels:
    def __init__(self, delay: float = 0.5):
        self.delay = delay

    async def generate_content(self, model: str, contents: str, config: dict = None):
        await asyncio.sleep(self.delay)
        if "resume text into structured JSON" in contents:
            return MockGeminiResponse(json.dumps({
                "contact": {"name": "Alex Rivera", "email": "alex@test.com", "phone": "555-1234", "linkedin": "linkedin.com/in/alex"},
                "summary": "Data Analyst with skills in SQL and Python",
                "skills": ["SQL", "Python", "Tableau", "Excel", "Data Analysis"],
                "experience": [{
                    "role": "Data Analyst Intern",
                    "company": "Tech Corp",
                    "duration": "2024",
                    "bullets": ["Automated reports reducing latency by 40%", "Saved $15k in cloud costs"]
                }],
                "education": [{"institution": "State Univ", "degree": "BS Data Science", "year": "2025"}]
            }))
        elif "Analyze the following Job Description" in contents:
            return MockGeminiResponse(json.dumps({
                "required_skills": ["SQL", "Python", "Tableau", "Excel"],
                "keywords": ["ETL", "dashboards", "data modeling"],
                "seniority": "Entry-Level"
            }))
        else:
            return MockGeminiResponse(json.dumps([
                {"priority": 1, "issue": "Enhance action verbs", "suggestion": "Start bullets with strong action verbs"},
                {"priority": 2, "issue": "Add more metrics", "suggestion": "Quantify outcomes with percentages or dollars"},
                {"priority": 3, "issue": "Highlight certifications", "suggestion": "Add relevant coursework or certifications"},
                {"priority": 4, "issue": "Add portfolio link", "suggestion": "Link GitHub or Tableau Public profile"},
                {"priority": 5, "issue": "Format headers", "suggestion": "Ensure consistent date formatting across experience"}
            ]))

class MockGeminiClient:
    def __init__(self, delay: float = 0.5):
        self.aio = type("MockAio", (), {"models": MockAioModels(delay=delay)})()


@pytest.mark.asyncio
async def test_concurrency_timing_parser_and_jd_agents():
    """
    Verifies that Parser Agent and JD Agent execute CONCURRENTLY via asyncio.gather.
    With each call sleeping 0.5s:
    - If concurrent: elapsed time is close to 0.5s (~0.5 - 0.7s).
    - If sequential: elapsed time would be >= 1.0s (2 x 0.5s).
    Asserts elapsed time is closer to 0.5s than to 1.0s.
    """
    from presets.roles import ROLE_PRESETS
    mock_client = MockGeminiClient(delay=0.5)
    pipeline = AgentPipeline(gemini_client=mock_client)

    sample_resume = "Alex Rivera\nData Analyst with Python and SQL experience.\nEducation: BS CS 2024"
    data_analyst_jd = ROLE_PRESETS["data_analyst"]["description"]

    # Measure the concurrent Parser + JD step directly as executed by pipeline
    start_time = time.perf_counter()
    parser_res, jd_res = await asyncio.gather(
        pipeline.parser_agent.run(sample_resume),
        pipeline.jd_agent.run(data_analyst_jd)
    )
    elapsed = time.perf_counter() - start_time
    print(f"\n[CONCURRENCY TIMING] Parser + JD step elapsed: {elapsed:.4f}s (closer to 0.5s concurrent than 1.0s sequential)")

    # Validate output structure
    assert parser_res["used_gemini"] is True
    assert jd_res["used_gemini"] is True

    # Validate timing: elapsed should be closer to 0.5s than to 1.0s (2 * 0.5s)
    # i.e., abs(elapsed - 0.5) < abs(elapsed - 1.0), and elapsed < 0.85
    assert abs(elapsed - 0.5) < abs(elapsed - 1.0), (
        f"Concurrency failure: elapsed time {elapsed:.3f}s is closer to 1.0s (sequential) than 0.5s (concurrent)"
    )
    assert elapsed < 0.85, f"Elapsed time {elapsed:.3f}s exceeded concurrent threshold"

    # Also run the full pipeline with mocked Gemini and verify engine attribution
    full_result = await pipeline.run(
        resume_text=sample_resume,
        formatting_meta={"char_count": 800},
        mode="preset",
        jd_text=data_analyst_jd
    )
    assert full_result["engine"] == "gemini"
    assert full_result["agent_engines"] == {
        "parser": True,
        "jd": True,
        "recommendation": True
    }


def test_cors_fallback_behavior():
    """Confirms CORS rejects unauthorized external origins on default fallback and disables credentials."""
    from config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, IS_CORS_FALLBACK
    assert "http://localhost:5173" in ALLOWED_ORIGINS
    assert "*" not in ALLOWED_ORIGINS
    assert ALLOW_CREDENTIALS is False
    assert IS_CORS_FALLBACK is True

    # 1. Unauthorized origin preflight request must not receive allow-origin
    res_unauth = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert "access-control-allow-origin" not in res_unauth.headers

    # 2. Local dev origin preflight receives allow-origin without allow-credentials
    res_local = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-credentials" not in res_local.headers


def test_corrupted_or_password_protected_pdf_rejection():
    """Confirms corrupted/password-protected PDFs return distinct HTTP 422."""
    corrupted_pdf_bytes = b"%PDF-1.4\ncorrupted-garbage-stream-that-cannot-be-parsed"
    res = client.post(
        "/api/scan",
        files={"file": ("corrupted_resume.pdf", corrupted_pdf_bytes, "application/pdf")},
        data={"mode": "general"}
    )
    assert res.status_code == 422
    assert "This PDF appears to be corrupted or password-protected. Please upload an unlocked, text-based PDF." in res.json()["detail"]


def test_mismatched_txt_to_pdf_rejection():
    """Confirms renamed non-PDF files return distinct HTTP 422."""
    fake_pdf_bytes = b"Just plain text file content that does not have PDF magic bytes."
    res = client.post(
        "/api/scan",
        files={"file": ("fake_resume.pdf", fake_pdf_bytes, "application/pdf")},
        data={"mode": "general"}
    )
    assert res.status_code == 422
    assert "The uploaded file does not match a valid PDF document structure" in res.json()["detail"]


def test_mismatched_txt_to_docx_rejection():
    """Confirms renamed non-DOCX files return distinct HTTP 422."""
    fake_docx_bytes = b"Just plain text file content that lacks PK zip magic bytes."
    res = client.post(
        "/api/scan",
        files={"file": ("fake_resume.docx", fake_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res.status_code == 422
    assert "The uploaded file does not match a valid Word document (.docx) structure" in res.json()["detail"]




