import os
import io
import tempfile
import pytest
from fastapi.testclient import TestClient
from docx import Document

from config import VALID_PROMO_CODES
from database import init_db
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    temp_dir = tempfile.TemporaryDirectory()
    test_db_path = os.path.join(temp_dir.name, "test_resumefit_export.db")
    monkeypatch.setattr("config.DATABASE_URL", None)
    monkeypatch.setattr("database.DATABASE_URL", None)
    monkeypatch.setattr("config.DATABASE_PATH", test_db_path)
    monkeypatch.setattr("database.DATABASE_PATH", test_db_path)
    init_db(test_db_path)
    yield
    temp_dir.cleanup()


SAMPLE_PARSED_RESUME = {
    "contact": {
        "name": "Sarah Chen",
        "email": "sarah.chen@university.edu",
        "phone": "(555) 345-6789",
        "linkedin": "linkedin.com/in/sarahchen"
    },
    "education": [
        {
            "degree": "B.S. in Computer Science",
            "institution": "Tech State University",
            "year": "2024"
        }
    ],
    "skills": ["Python", "SQL", "Tableau", "Git"],
    "experience": [
        {
            "role": "Data Analyst Intern",
            "company": "Apex Analytics",
            "duration": "Summer 2023",
            "bullets": [
                "Responsible for analyzing user engagement data",
                "Automated weekly reporting pipelines in Python"
            ]
        }
    ]
}

SAMPLE_REWRITES = [
    {
        "original_bullet": "Responsible for analyzing user engagement data",
        "rewrite_bullet": "Spearheaded user engagement analysis across 45,000 active accounts in SQL, identifying retention patterns that boosted 30-day conversion by 18%.",
        "role": "Data Analyst Intern"
    }
]


def test_get_templates():
    res = client.get("/api/resume/templates")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
    ids = [t["id"] for t in data]
    assert "original" in ids
    assert "ivy_league" in ids
    assert "tech_minimalist" in ids
    assert "modern_corporate" in ids


def test_export_forbidden_without_pro():
    res_signup = client.post(
        "/api/auth/signup",
        json={"name": "Free User", "email": "free@test.com", "password": "password123"}
    )
    token = res_signup.json()["token"]

    res = client.post(
        "/api/resume/export",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "format": "docx",
            "parsed_resume": SAMPLE_PARSED_RESUME,
            "applied_rewrites": SAMPLE_REWRITES
        }
    )
    assert res.status_code == 403
    assert "ResumeFit Pro feature" in res.json()["detail"]


def test_export_docx_success_for_pro_user():
    res_signup = client.post(
        "/api/auth/signup",
        json={"name": "Pro Student", "email": "pro@test.com", "password": "password123"}
    )
    token = res_signup.json()["token"]

    client.post(
        "/api/auth/redeem",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "CAMPUS2026"}
    )

    res = client.post(
        "/api/resume/export",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "format": "docx",
            "template_id": "ivy_league",
            "parsed_resume": SAMPLE_PARSED_RESUME,
            "applied_rewrites": SAMPLE_REWRITES
        }
    )
    assert res.status_code == 200
    assert "wordprocessingml.document" in res.headers["content-type"]
    assert "attachment" in res.headers["content-disposition"]
    assert "Sarah_Chen" in res.headers["content-disposition"]
    assert ".docx" in res.headers["content-disposition"]

    doc = Document(io.BytesIO(res.content))
    all_text = " ".join([p.text for p in doc.paragraphs])
    assert "SARAH CHEN" in all_text
    assert "boosted 30-day conversion by 18%" in all_text
    assert "Responsible for analyzing user engagement data" not in all_text


def test_export_pdf_success_for_pro_user():
    res_signup = client.post(
        "/api/auth/signup",
        json={"name": "Pro Student 2", "email": "pro2@test.com", "password": "password123"}
    )
    token = res_signup.json()["token"]

    client.post(
        "/api/auth/redeem",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "TEACHERVIP"}
    )

    res = client.post(
        "/api/resume/export",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "format": "pdf",
            "template_id": "tech_minimalist",
            "parsed_resume": SAMPLE_PARSED_RESUME,
            "applied_rewrites": SAMPLE_REWRITES
        }
    )
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert res.content.startswith(b"%PDF")
