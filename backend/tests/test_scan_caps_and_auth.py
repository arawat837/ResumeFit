import io
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from docx import Document

from main import app, pipeline
import database
from database import (
    init_db,
    create_user,
    get_user_by_id,
    upgrade_user_to_pro,
    create_access_token,
    save_scan_result,
    check_and_increment_scan_count
)

client = TestClient(app)

def create_sample_docx(text: str = "Test candidate resume content with enough text to parse successfully.") -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


@pytest.fixture(autouse=True)
def setup_isolated_db(monkeypatch):
    """Ensures each test runs in an isolated SQLite database."""
    temp_dir = tempfile.TemporaryDirectory()
    test_db_path = f"{temp_dir.name}/test_caps.db"

    monkeypatch.setattr("config.DATABASE_URL", None)
    monkeypatch.setattr("database.DATABASE_URL", None)
    monkeypatch.setattr("config.DATABASE_PATH", test_db_path)
    monkeypatch.setattr("database.DATABASE_PATH", test_db_path)

    init_db(test_db_path)
    yield test_db_path
    temp_dir.cleanup()


def test_scan_without_authorization_header_returns_401():
    """Requirement (a): /api/scan without an Authorization header returns 401."""
    docx_bytes = create_sample_docx()
    res = client.post(
        "/api/scan",
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "Authentication required" in res.json()["detail"]


def test_daily_scan_caps_free_user_and_pro_user(monkeypatch):
    """
    Requirement (b): A free user's 3rd scan in one UTC day returns 429;
    a Pro user's 8th scan in one UTC day returns 429.
    """
    docx_bytes = create_sample_docx()

    # Fast pipeline mock so scans complete instantly without Gemini API calls
    mock_run = AsyncMock(return_value={
        "ats_score": 85,
        "breakdown": {"keyword_match": 80, "formatting": 90, "sections": 85, "achievements": 85},
        "parsed_resume": {"candidate_name": "Test User"},
        "parsed_jd": None,
        "scoring_result": {"ats_score": 85, "recommendations": []},
        "recommendations": [],
        "engine": "rubric_fallback",
        "agent_engines": {"parser": False, "jd": None, "recommendation": False}
    })
    monkeypatch.setattr(pipeline, "run", mock_run)

    # 1. Test Free User Cap (2/day)
    free_user = create_user("Free User", "free@resumefit.ai", "hash123")
    free_token = create_access_token(free_user["id"], free_user["email"])
    free_headers = {"Authorization": f"Bearer {free_token}"}

    # 1st scan -> 200
    res1 = client.post(
        "/api/scan",
        headers=free_headers,
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res1.status_code == 200, f"Scan 1 failed: {res1.text}"

    # 2nd scan -> 200
    res2 = client.post(
        "/api/scan",
        headers=free_headers,
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res2.status_code == 200, f"Scan 2 failed: {res2.text}"

    # 3rd scan -> 429 Too Many Requests
    res3 = client.post(
        "/api/scan",
        headers=free_headers,
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res3.status_code == 429, f"Expected 429 on 3rd scan, got {res3.status_code}: {res3.text}"
    detail_lower = res3.json()["detail"].lower()
    assert "daily scan limit reached" in detail_lower
    assert "2 scans per day" in detail_lower

    # 2. Test Pro User Cap (7/day)
    pro_user = create_user("Pro User", "pro@resumefit.ai", "hash123")
    upgrade_user_to_pro(pro_user["id"], "CAMPUS2026")
    pro_token = create_access_token(pro_user["id"], pro_user["email"])
    pro_headers = {"Authorization": f"Bearer {pro_token}"}

    # Perform scans 1 through 7 for Pro user -> all return 200
    for i in range(1, 8):
        res = client.post(
            "/api/scan",
            headers=pro_headers,
            files={"file": (f"resume_pro_{i}.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"mode": "general"}
        )
        assert res.status_code == 200, f"Pro scan {i} failed: {res.text}"

    # 8th scan for Pro user -> 429 Too Many Requests
    res8 = client.post(
        "/api/scan",
        headers=pro_headers,
        files={"file": ("resume_pro_8.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"mode": "general"}
    )
    assert res8.status_code == 429, f"Expected 429 on Pro 8th scan, got {res8.status_code}: {res8.text}"
    pro_detail_lower = res8.json()["detail"].lower()
    assert "daily scan limit reached" in pro_detail_lower
    assert "7 scans per day" in pro_detail_lower


def test_regenerate_recommendations_auth_and_pro_only(monkeypatch):
    """
    Requirement (c): /api/resume/regenerate-recommendations returns 403 for a
    non-Pro authenticated user and 401 for no auth.
    """
    scan_id = "test-auth-regen-123"
    save_scan_result(
        scan_id=scan_id,
        parsed_resume={"candidate_name": "Test"},
        parsed_jd=None,
        scoring_result={"ats_score": 75, "recommendations": []}
    )

    # 1. No Authorization header -> 401 Unauthorized
    res_no_auth = client.post(
        "/api/resume/regenerate-recommendations",
        json={"scan_id": scan_id}
    )
    assert res_no_auth.status_code == 401
    assert "Authentication required" in res_no_auth.json()["detail"]

    # 2. Authenticated Free User -> 403 Forbidden
    free_user = create_user("Free User 2", "free2@resumefit.ai", "hash123")
    free_token = create_access_token(free_user["id"], free_user["email"])
    res_free = client.post(
        "/api/resume/regenerate-recommendations",
        headers={"Authorization": f"Bearer {free_token}"},
        json={"scan_id": scan_id}
    )
    assert res_free.status_code == 403
    assert "Pro" in res_free.json()["detail"]

    # 3. Authenticated Pro User -> 200 OK
    pro_user = create_user("Pro User 2", "pro2@resumefit.ai", "hash123")
    upgrade_user_to_pro(pro_user["id"], "CAMPUS2026")
    pro_token = create_access_token(pro_user["id"], pro_user["email"])

    mock_rec_run = AsyncMock(return_value={
        "data": [{"id": "fix1", "message": "Add metrics to bullet points"}],
        "used_gemini": False
    })
    monkeypatch.setattr(pipeline.recommendation_agent, "run", mock_rec_run)

    res_pro = client.post(
        "/api/resume/regenerate-recommendations",
        headers={"Authorization": f"Bearer {pro_token}"},
        json={"scan_id": scan_id}
    )
    assert res_pro.status_code == 200
    assert "recommendations" in res_pro.json()


def test_scans_today_resets_after_last_scan_date_rolls_to_new_day(monkeypatch):
    """
    Requirement (d): scans_today correctly resets after last_scan_date rolls to a new day (mock the date).
    """
    user = create_user("Daily Reset User", "dailyreset@resumefit.ai", "hash123")
    user_id = user["id"]

    # Day 1: 2026-09-20
    class FakeDay1:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 20, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(database, "datetime", FakeDay1)

    # Use up all 2 scans on Day 1
    assert check_and_increment_scan_count(user_id, is_pro=False) is True
    assert check_and_increment_scan_count(user_id, is_pro=False) is True
    assert check_and_increment_scan_count(user_id, is_pro=False) is False  # Cap reached on Day 1

    # Verify user state at end of Day 1
    u1 = get_user_by_id(user_id)
    assert u1["scans_today"] == 2
    assert u1["last_scan_date"] == "2026-09-20"

    # Day 2: 2026-09-21 (Mock date rolls over to next day)
    class FakeDay2:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 21, 9, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(database, "datetime", FakeDay2)

    # Prior to scanning on Day 2, user's formatted scans_today should reflect 0 for today
    u2_before = get_user_by_id(user_id)
    assert u2_before["scans_today"] == 0

    # User attempts scan on Day 2 -> Should succeed and reset scans_today to 1 for the new day
    allowed = check_and_increment_scan_count(user_id, is_pro=False)
    assert allowed is True

    u2_after = get_user_by_id(user_id)
    assert u2_after["scans_today"] == 1
    assert u2_after["last_scan_date"] == "2026-09-21"

    # Second scan on Day 2 succeeds
    assert check_and_increment_scan_count(user_id, is_pro=False) is True
    # Third scan on Day 2 is blocked (cap reached)
    assert check_and_increment_scan_count(user_id, is_pro=False) is False
