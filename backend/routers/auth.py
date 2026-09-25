import re
import secrets
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field

from config import VALID_PROMO_CODES, GOOGLE_CLIENT_ID
from database import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    upgrade_user_to_pro,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1)

class RedeemRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)

class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None
    access_token: Optional[str] = None

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency that extracts and verifies JWT from Bearer Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token = authorization.split("Bearer ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(req: SignupRequest):
    email = req.email.strip().lower()
    if not EMAIL_REGEX.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address."
        )

    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    pw_hash = hash_password(req.password)
    user = create_user(name=req.name, email=email, password_hash=pw_hash)
    token = create_access_token(user["id"], user["email"])
    return {
        "message": "Account created successfully.",
        "token": token,
        "user": user
    }


@router.post("/login")
async def login(req: LoginRequest):
    email = req.email.strip().lower()
    user_record = get_user_by_email(email)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(req.password, user_record.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Do not leak hash in response
    user_record.pop("password_hash", None)
    token = create_access_token(user_record["id"], user_record["email"])
    return {
        "message": "Signed in successfully.",
        "token": token,
        "user": user_record
    }


async def fetch_google_user_info(credential: Optional[str], access_token: Optional[str]) -> dict:
    """Verifies Google ID token or queries Google userinfo endpoint with OAuth2 access token."""
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        if access_token:
            resp = await http_client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Google access token."
                )
            data = resp.json()
            email = data.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email found in Google profile."
                )
            name = data.get("name") or data.get("given_name") or email.split("@")[0]
            picture = data.get("picture")
            return {"email": email, "name": name, "picture": picture}

        elif credential:
            try:
                from google.oauth2 import id_token
                from google.auth.transport import requests as google_requests

                request = google_requests.Request()
                audience = GOOGLE_CLIENT_ID.strip() if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_ID.strip() else None
                id_info = id_token.verify_oauth2_token(credential, request, audience=audience)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google credential token."
                )

            email = id_info.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email found in Google credential."
                )
            name = id_info.get("name") or id_info.get("given_name") or email.split("@")[0]
            picture = id_info.get("picture")
            return {"email": email, "name": name, "picture": picture}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'access_token' or 'credential' must be provided."
            )


@router.post("/google")
async def google_auth(req: GoogleAuthRequest):
    """Authenticates or signs up a user using verified Google credentials."""
    if not req.credential and not req.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google authentication token."
        )

    g_user = await fetch_google_user_info(req.credential, req.access_token)
    clean_email = g_user["email"].strip().lower()
    user_name = g_user.get("name") or clean_email.split("@")[0]

    user_record = get_user_by_email(clean_email)
    if not user_record:
        # Auto-provision user account with random secure password
        random_pw = secrets.token_urlsafe(32)
        pw_hash = hash_password(random_pw)
        user_record = create_user(
            name=user_name,
            email=clean_email,
            password_hash=pw_hash
        )
    else:
        user_record.pop("password_hash", None)

    token = create_access_token(user_record["id"], user_record["email"])
    return {
        "message": "Signed in with Google successfully.",
        "token": token,
        "user": user_record
    }


@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "user": current_user
    }


@router.post("/redeem")
async def redeem_promo_code(
    req: RedeemRequest,
    current_user: dict = Depends(get_current_user)
):
    code_upper = req.code.strip().upper()
    if code_upper not in VALID_PROMO_CODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired promo code. Please check the spelling and try again."
        )

    if current_user.get("is_pro"):
        return {
            "message": "Your account already has ResumeFit Pro active!",
            "user": current_user
        }

    updated_user = upgrade_user_to_pro(current_user["id"], code_upper)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update account status. Please try again."
        )

    return {
        "message": f"Congratulations! Promo code '{code_upper}' redeemed successfully. ResumeFit Pro is now active.",
        "user": updated_user
    }
