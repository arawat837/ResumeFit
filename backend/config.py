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

# CORS Origins
raw_origins = os.getenv("ALLOWED_ORIGINS")
if raw_origins:
    ALLOWED_ORIGINS = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",
        "*"
    ]

