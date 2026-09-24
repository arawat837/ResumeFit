import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field

from config import VALID_PROMO_CODES
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
