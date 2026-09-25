import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables strictly from .env file
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

# Gemini API configuration (loaded ONLY from environment/.env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Maximum upload size: 5MB
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5,242,880 bytes

# Minimum text characters required for a valid resume (scanned PDF threshold)
MIN_TEXT_CHARS = 50

# CORS Configuration
# Safe local development origins
LOCAL_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

raw_origins = os.getenv("ALLOWED_ORIGINS")
parsed_origins = [
    orig.strip()
    for orig in (raw_origins.split(",") if raw_origins else [])
    if orig.strip()
]

# Only treat as explicitly configured if there is at least one non-wildcard origin
has_explicit_domains = bool(parsed_origins) and any(o != "*" for o in parsed_origins)

if has_explicit_domains:
    # Explicit real domain(s) configured: allow credentials, strip any accidental wildcard
    ALLOWED_ORIGINS = [o for o in parsed_origins if o != "*"]
    ALLOW_CREDENTIALS = True
    IS_CORS_FALLBACK = False
else:
    # Safe default: local dev only, disable credentials, never wildcard
    ALLOWED_ORIGINS = LOCAL_DEV_ORIGINS
    ALLOW_CREDENTIALS = False
    IS_CORS_FALLBACK = True

# Database Configuration (Supabase PostgreSQL or Local SQLite)
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "resumefit.db"))

# JWT Authentication Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "resumefit-super-secret-jwt-key-2026-university-student-ats")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 30  # 30-day persistent sessions

# Valid Pro Promo Codes
raw_promo_codes = os.getenv("PROMO_CODES", "CAMPUS2026,TEACHERVIP,TEAMPRO,RESUMEFIT_PRO,STUDENTVIP")
VALID_PROMO_CODES = [c.strip().upper() for c in raw_promo_codes.split(",") if c.strip()]

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


