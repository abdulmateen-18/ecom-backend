import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER")
if not WHATSAPP_NUMBER:
    logger.warning(
        "WHATSAPP_NUMBER is not set in environment — WhatsApp integration may not work"
    )

logger.info(
    "Environment file loaded",
    extra={"env_path": str(env_path)}
)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

if not JWT_ALGORITHM:
    logger.warning(
        "JWT_ALGORITHM is not set in environment — downstream JWT operations may fail"
    )

_jwt_expire_raw = os.getenv("JWT_EXPIRE_DAYS", "3")

try:
    JWT_EXPIRE_DAYS = int(_jwt_expire_raw)
    if _jwt_expire_raw == "3" and os.getenv("JWT_EXPIRE_DAYS") is None:
        logger.warning(
            "JWT_EXPIRE_DAYS not set in environment — defaulting to 3 days"
        )
except ValueError:
    logger.error(
        "JWT_EXPIRE_DAYS is not a valid integer — check your .env configuration",
        extra={"raw_value": _jwt_expire_raw}
    )
    raise

# Optional validation
if not ADMIN_USERNAME:
    logger.error("ADMIN_USERNAME is not set or empty in environment configuration")
    raise ValueError("ADMIN_USERNAME not found in .env")

if not ADMIN_PASSWORD_HASH:
    logger.error("ADMIN_PASSWORD_HASH is not set or empty in environment configuration")
    raise ValueError("ADMIN_PASSWORD_HASH not found in .env")

if not JWT_SECRET_KEY:
    logger.error("JWT_SECRET_KEY is not set or empty in environment configuration")
    raise ValueError("JWT_SECRET_KEY not found in .env")

logger.info(
    "Application configuration loaded successfully",
    extra={
        "admin_username_set": bool(ADMIN_USERNAME),
        "admin_password_hash_set": bool(ADMIN_PASSWORD_HASH),
        "jwt_secret_key_set": bool(JWT_SECRET_KEY),
        "jwt_algorithm_set": bool(JWT_ALGORITHM),
        "jwt_expire_days": JWT_EXPIRE_DAYS,
    }
)