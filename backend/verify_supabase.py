"""
ResumeFit - Supabase PostgreSQL Connection Verification Utility
Usage:
    python verify_supabase.py [optional_connection_string]
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from config import DATABASE_URL
from database import is_using_postgres, get_postgres_connection, init_db

def test_connection():
    target_url = sys.argv[1] if len(sys.argv) > 1 else DATABASE_URL

    print("=" * 60)
    print("ResumeFit - Supabase Connection Health Check")
    print("=" * 60)

    if not target_url or not target_url.strip():
        print("[!] No DATABASE_URL found in backend/.env or passed via CLI.")
        print("    ResumeFit is currently operating in offline SQLite mode (resumefit.db).")
        print("\nTo connect Supabase:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Project Settings -> Database -> Connection string -> URI")
        print("3. Add to backend/.env: DATABASE_URL=\"your_connection_string\"")
        print("4. Re-run: python verify_supabase.py")
        sys.exit(1)

    # Sanitize URL for display
    safe_display = target_url
    if "@" in safe_display:
        parts = safe_display.split("@")
        safe_display = f"{parts[0].split(':')[0]}://****:****@{parts[1]}"

    print(f"[*] Testing connection to: {safe_display}")

    try:
        # 1. Initialize tables (users table + indexes)
        print("[*] Running init_db() on Supabase...")
        init_db(db_url=target_url)

        # 2. Query users table
        conn = get_postgres_connection(db_url=target_url)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM users;")
            res = cur.fetchone()
            user_count = res["total"] if isinstance(res, dict) else res[0]
            print(f"[+] SUCCESS! Connected to Supabase PostgreSQL.")
            print(f"[+] Schema initialized: 'users' table is ready (Current users: {user_count}).")

        # 3. Live Round-trip Verification (Insert -> Promo Upgrade -> Cleanup)
        print("[*] Performing live Auth & Pro promo roundtrip check on Supabase...")
        test_email = "_healthcheck_test@resumefit.test"
        from database import create_user, upgrade_user_to_pro, hash_password
        
        # Clean any prior leftover test row
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s;", (test_email,))
            
        test_user = create_user("Health Check", test_email, hash_password("Test12345!"), db_url=target_url)
        assert test_user["is_pro"] is False, "Initial user should not be Pro"
        
        upgraded = upgrade_user_to_pro(test_user["id"], "CAMPUS2026", db_url=target_url)
        assert upgraded["is_pro"] is True, "User should be Pro after promo redemption"
        assert upgraded["pro_code_used"] == "CAMPUS2026", "Promo code should be recorded"

        # Cleanup test user
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s;", (test_user["id"],))

        print("[+] Live Roundtrip Passed: Account creation, PBKDF2 hashing, and Pro promo code upgrade verified!")
        print("=" * 60)
        print("Your ResumeFit database is fully linked with persistent Supabase cloud storage!")
        print("=" * 60)
        conn.close()
    except Exception as e:
        print(f"\n[-] CONNECTION ERROR: {e}")
        print("\nTroubleshooting tips:")
        print("1. Password: Make sure you replaced [YOUR-PASSWORD] with the real database password you set during project creation.")
        print("2. Pooler vs Direct: In Supabase Database Settings, try the 'Session' connection pooler (port 5432) or 'Transaction' pooler (port 6543).")
        print("3. Special Characters: If your password contains special characters like '@', '#', '%', ensure they are URL-encoded or reset to an alphanumeric password.")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
