import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from config import VALID_PROMO_CODES
from database import init_db
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Sets up an isolated SQLite database for each test."""
    temp_dir = tempfile.TemporaryDirectory()
    test_db_path = os.path.join(temp_dir.name, "test_resumefit.db")
    monkeypatch.setattr("config.DATABASE_URL", None)
    monkeypatch.setattr("database.DATABASE_URL", None)
    monkeypatch.setattr("config.DATABASE_PATH", test_db_path)
    monkeypatch.setattr("database.DATABASE_PATH", test_db_path)
    init_db(test_db_path)
    yield
    temp_dir.cleanup()


def test_signup_success():
    res = client.post(
        "/api/auth/signup",
        json={"name": "Alice Johnson", "email": "alice@university.edu", "password": "securepassword123"}
    )
    assert res.status_code == 201
    data = res.json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == "alice@university.edu"
    assert data["user"]["name"] == "Alice Johnson"
    assert data["user"]["is_pro"] is False
    assert "password_hash" not in data["user"]


def test_signup_duplicate_email():
    payload = {"name": "Bob Smith", "email": "bob@gmail.com", "password": "password123"}
    res1 = client.post("/api/auth/signup", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/signup", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_signup_invalid_email():
    res = client.post(
        "/api/auth/signup",
        json={"name": "Invalid User", "email": "notanemail", "password": "password123"}
    )
    assert res.status_code == 400
    assert "valid email" in res.json()["detail"].lower()


def test_login_success():
    # Register first
    client.post(
        "/api/auth/signup",
        json={"name": "Charlie Brown", "email": "charlie@gmail.com", "password": "mypassword456"}
    )

    # Login
    res = client.post(
        "/api/auth/login",
        json={"email": "charlie@gmail.com", "password": "mypassword456"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == "charlie@gmail.com"
    assert data["user"]["is_pro"] is False


def test_login_wrong_password():
    client.post(
        "/api/auth/signup",
        json={"name": "Dana White", "email": "dana@university.edu", "password": "correctpassword"}
    )

    res = client.post(
        "/api/auth/login",
        json={"email": "dana@university.edu", "password": "wrongpassword"}
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_login_nonexistent_user():
    res = client.post(
        "/api/auth/login",
        json={"email": "ghost@university.edu", "password": "anypassword"}
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_get_profile_authenticated():
    signup_res = client.post(
        "/api/auth/signup",
        json={"name": "Eva Green", "email": "eva@gmail.com", "password": "password123"}
    )
    token = signup_res.json()["token"]

    # Call /api/auth/me with Bearer token
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "eva@gmail.com"
    assert data["user"]["is_pro"] is False


def test_get_profile_unauthenticated():
    # No header
    res1 = client.get("/api/auth/me")
    assert res1.status_code == 401

    # Invalid header
    res2 = client.get("/api/auth/me", headers={"Authorization": "Bearer fake.jwt.token"})
    assert res2.status_code == 401


def test_redeem_invalid_promo_code():
    signup_res = client.post(
        "/api/auth/signup",
        json={"name": "Frank Castle", "email": "frank@gmail.com", "password": "password123"}
    )
    token = signup_res.json()["token"]

    res = client.post(
        "/api/auth/redeem",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "INVALID_CODE_999"}
    )
    assert res.status_code == 400
    assert "Invalid or expired promo code" in res.json()["detail"]


def test_redeem_valid_promo_code_and_persistence():
    signup_res = client.post(
        "/api/auth/signup",
        json={"name": "Professor Miller", "email": "miller@university.edu", "password": "teacherpassword"}
    )
    token = signup_res.json()["token"]

    # Redeem CAMPUS2026 (case-insensitive)
    redeem_res = client.post(
        "/api/auth/redeem",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "campus2026"}
    )
    assert redeem_res.status_code == 200
    data = redeem_res.json()
    assert data["user"]["is_pro"] is True
    assert data["user"]["pro_code_used"] == "CAMPUS2026"

    # Verify persistence: Calling /api/auth/me now shows is_pro == True
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["is_pro"] is True
    assert me_res.json()["user"]["pro_code_used"] == "CAMPUS2026"


def test_redeem_teacher_vip_code():
    signup_res = client.post(
        "/api/auth/signup",
        json={"name": "Team Dev", "email": "dev@resumefit.ai", "password": "devpassword"}
    )
    token = signup_res.json()["token"]

    redeem_res = client.post(
        "/api/auth/redeem",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "TEACHERVIP"}
    )
    assert redeem_res.status_code == 200
    assert redeem_res.json()["user"]["is_pro"] is True
