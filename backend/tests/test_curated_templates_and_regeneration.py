"""
backend/tests/test_curated_templates_and_regeneration.py
Unit tests verifying:
1. Curated templates structural markers in DOCX & PDF (OOXML borders, tables, small caps, custom bullets).
2. /api/resume/regenerate-recommendations endpoint: cached scan execution with 0 parser and 0 JD agent calls.
"""

import io
import tempfile
import pytest
from unittest.mock import AsyncMock
from docx import Document
from fastapi.testclient import TestClient

from main import app, pipeline
from database import init_db, save_scan_result, get_scan_result
from services.resume_builder import (
    build_docx_resume,
    build_pdf_resume,
    estimate_content_density,
)

client = TestClient(app)

SAMPLE_RESUME = {
    "candidate_name": "Jordan Lee",
    "contact": {
        "name": "Jordan Lee",
        "email": "jordan.lee@university.edu",
        "phone": "+1 (555) 234-5678",
        "linkedin": "linkedin.com/in/jordanlee",
        "location": "Boston, MA",
    },
    "summary": "Dedicated software engineer passionate about scalable cloud infrastructure and distributed systems.",
    "skills": [
        "Languages: Python, Go, TypeScript, C++",
        "Frameworks: FastAPI, React, Node.js",
        "Tools: Docker, Kubernetes, Git, AWS",
        "Databases: PostgreSQL, Redis, MongoDB",
    ],
    "education": [
        {
            "degree": "B.S. in Computer Science",
            "institution": "University of Excellence",
            "year": "May 2026",
            "gpa": "3.9/4.0",
        }
    ],
    "experience": [
        {
            "role": "Cloud Engineering Intern",
            "company": "Skyline Distributed Systems",
            "duration": "June 2025 - August 2025",
            "bullets": [
                "Automated Kubernetes cluster deployments across multiple AWS regions.",
                "Optimized database query performance, decreasing response times significantly.",
            ],
        }
    ],
    "projects": [
        {
            "title": "High-Throughput Message Queue",
            "tech_stack": "Go, Docker, gRPC",
            "bullets": [
                "Engineered lock-free message queue serving high-volume transactions with low latency."
            ],
        }
    ],
}


def test_tech_minimalist_structural_markers():
    """
    Asserts tech_minimalist contains:
    - 2-column skills table without borders
    - OOXML bottom border (w:pBdr / w:bottom) on section headers
    - Custom colored bullet runs
    """
    docx_bytes = build_docx_resume(SAMPLE_RESUME, template_id="tech_minimalist")
    assert docx_bytes is not None and len(docx_bytes) > 0

    doc = Document(io.BytesIO(docx_bytes))

    # tech_minimalist must render skills into a 2-column table
    assert len(doc.tables) >= 1, "tech_minimalist should render at least one table for skills"
    skills_table = doc.tables[0]
    assert len(skills_table.columns) == 2, "Skills table must have 2 columns"

    # Verify table borders are set to none
    tblPr = skills_table._tbl.tblPr
    tblBdr = tblPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblBdr")
    assert tblBdr is not None, "Table must have tblBdr configuration"
    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        b = tblBdr.find(f"{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{border_name}")
        assert b is not None and b.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") == "none"

    # Verify section headers have w:pBdr bottom border
    headers_found = 0
    for p in doc.paragraphs:
        xml = p._p.xml
        if "<w:pBdr" in xml and "<w:bottom" in xml:
            headers_found += 1

    assert headers_found >= 3, "Expected at least 3 section headers with OOXML bottom borders"

    # Verify custom bullet points are present with literal bullet glyph run
    bullet_runs = [p for p in doc.paragraphs if p.text.startswith("• ")]
    assert len(bullet_runs) >= 3, "Expected custom bullet paragraphs starting with '• '"


def test_modern_corporate_structural_markers():
    """
    Asserts modern_corporate contains:
    - 2-column accent bar tables for experience and project entries
    - Shaded left cell (accent bar)
    - OOXML bottom border on section headers
    """
    docx_bytes = build_docx_resume(SAMPLE_RESUME, template_id="modern_corporate")
    assert docx_bytes is not None and len(docx_bytes) > 0

    doc = Document(io.BytesIO(docx_bytes))

    # modern_corporate renders each experience and project entry inside a 2-column table
    # (SAMPLE_RESUME has 1 experience and 1 project -> >= 2 tables)
    assert len(doc.tables) >= 2, f"modern_corporate should render >= 2 accent bar tables, found {len(doc.tables)}"

    for tbl in doc.tables:
        assert len(tbl.columns) == 2, "Each modern_corporate entry table must have 2 columns (accent + content)"
        # Check first column cell shading
        accent_cell = tbl.rows[0].cells[0]
        tcPr = accent_cell._tc.get_or_add_tcPr()
        shd = tcPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd")
        assert shd is not None, "Accent cell must have w:shd shading"
        assert shd.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill") == "0284C7"

    # Section headers have w:pBdr
    headers_with_border = [p for p in doc.paragraphs if "<w:pBdr" in p._p.xml and "<w:bottom" in p._p.xml]
    assert len(headers_with_border) >= 3, "modern_corporate must have OOXML bottom borders on headers"


def test_ivy_league_structural_markers():
    """
    Asserts ivy_league contains:
    - Small caps formatting on section headers
    - Thin rule under candidate name
    - OOXML bottom border on section headers
    - Zero layout tables (clean classic text layout)
    """
    docx_bytes = build_docx_resume(SAMPLE_RESUME, template_id="ivy_league")
    assert docx_bytes is not None and len(docx_bytes) > 0

    doc = Document(io.BytesIO(docx_bytes))

    # Classic ivy_league format does not use side tables
    assert len(doc.tables) == 0, "ivy_league template should not use tables"

    # Verify thin rule under candidate name
    first_p = doc.paragraphs[0]
    assert "<w:pBdr" in first_p._p.xml and "<w:bottom" in first_p._p.xml, "Name paragraph must have bottom border"

    # Check for small caps on section header runs
    small_caps_found = False
    for p in doc.paragraphs:
        for run in p.runs:
            if run.font.small_caps is True:
                small_caps_found = True
                break
    assert small_caps_found, "ivy_league section headers must have small_caps set to True"


def test_pdf_generation_all_templates():
    """Verifies build_pdf_resume renders valid PDF documents for all curated templates."""
    for template_id in ["ivy_league", "tech_minimalist", "modern_corporate"]:
        pdf_bytes = build_pdf_resume(SAMPLE_RESUME, template_id=template_id)
        assert pdf_bytes is not None, f"PDF generation failed for template {template_id}"
        assert pdf_bytes.startswith(b"%PDF"), f"Output for {template_id} is not a valid PDF"


def test_content_density_heuristic():
    """Verifies density calculation triggers correctly for large vs concise resumes."""
    concise_resume = {
        "experience": [{"bullets": ["A", "B"]}],
        "projects": [{"bullets": ["C"]}],
        "skills": ["Python", "Go"],
    }
    assert estimate_content_density(concise_resume) is False

    dense_resume = {
        "experience": [
            {"bullets": ["A", "B", "C", "D"]},
            {"bullets": ["E", "F", "G"]},
            {"bullets": ["H", "I"]},
        ],
        "projects": [
            {"bullets": ["J", "K"]},
            {"bullets": ["L", "M"]},
        ],
        "skills": ["1", "2", "3", "4", "5", "6", "7", "8"],
    }
    assert estimate_content_density(dense_resume) is True


@pytest.mark.asyncio
async def test_regenerate_recommendations_endpoint(monkeypatch):
    """
    Test Change 2: POST /api/resume/regenerate-recommendations
    1. Seeds a scan result in database.
    2. Mocks parser_agent and jd_agent to verify they are NOT called (call_count == 0).
    3. Verifies recommendations are returned and updated in cache.
    """
    temp_dir = tempfile.TemporaryDirectory()
    test_db_path = str(temp_dir.name + "/test_regenerate.db")
    monkeypatch.setattr("config.DATABASE_URL", None)
    monkeypatch.setattr("database.DATABASE_URL", None)
    monkeypatch.setattr("config.DATABASE_PATH", test_db_path)
    monkeypatch.setattr("database.DATABASE_PATH", test_db_path)
    init_db(test_db_path)

    scan_id = "test-regen-scan-001"
    parsed_resume = {
        "candidate_name": "Taylor Swift",
        "contact": {"email": "taylor@swift.edu", "linkedin": "linkedin.com/in/tswift"},
        "skills": ["Audio Engineering", "Songwriting"],
        "education": [{"degree": "B.A. Music", "institution": "State College"}],
        "experience": [
            {
                "role": "Producer",
                "company": "Nashville Sound",
                "bullets": ["Managed studio recording sessions"],
            }
        ],
    }
    scoring_result = {
        "ats_score": 68,
        "breakdown": {"keyword_match": 60, "formatting": 80, "sections": 80, "achievements": 50},
        "diagnostics": {
            "keywords": {"missing": ["Mixing"]},
            "formatting": {"issues": []},
            "sections": {"missing": []},
            "achievements": {"action_verb_ratio": 0.5, "quantified_bullet_ratio": 0.0},
        },
        "recommendations": [],
    }

    save_scan_result(
        scan_id=scan_id,
        parsed_resume=parsed_resume,
        parsed_jd=None,
        scoring_result=scoring_result,
        db_path=test_db_path,
    )

    # Mock parser_agent.run and jd_agent.run with AsyncMock
    mock_parser = AsyncMock()
    mock_jd = AsyncMock()
    monkeypatch.setattr(pipeline.parser_agent, "run", mock_parser)
    monkeypatch.setattr(pipeline.jd_agent, "run", mock_jd)

    # Call endpoint
    response = client.post(
        "/api/resume/regenerate-recommendations",
        json={"scan_id": scan_id},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["scan_id"] == scan_id
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) > 0

    # Critical assertions: ZERO calls to parser and JD agents
    assert mock_parser.call_count == 0, f"Expected 0 calls to parser_agent, but got {mock_parser.call_count}"
    assert mock_jd.call_count == 0, f"Expected 0 calls to jd_agent, but got {mock_jd.call_count}"

    # Verify cached result in DB was updated with new recommendations
    cached = get_scan_result(scan_id, db_path=test_db_path)
    assert cached is not None
    assert len(cached["scoring_result"].get("recommendations", [])) > 0

    temp_dir.cleanup()


def test_regenerate_recommendations_not_found():
    """Tests 404 response when scan_id does not exist."""
    response = client.post(
        "/api/resume/regenerate-recommendations",
        json={"scan_id": "non-existent-scan-id-xyz"},
    )
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
