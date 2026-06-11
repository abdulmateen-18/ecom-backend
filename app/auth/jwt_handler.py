import logging
import os
from datetime import datetime, timedelta

from jose import jwt, JWTError

from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_DAYS

logger = logging.getLogger(__name__)


def create_token(username: str) -> str:

    try:
        payload = {
            "sub": username,
            "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        logger.info(
            "JWT token created successfully",
            extra={"username": username, "expires_days": JWT_EXPIRE_DAYS}
        )

        return token

    except Exception:
        logger.exception(
            "Unexpected error while creating JWT token",
            extra={"username": username}
        )
        raise


def verify_token(token: str) -> dict | None:

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        logger.info(
            "JWT token verified successfully",
            extra={"username": payload.get("sub")}
        )

        return payload

    except JWTError:
        logger.warning(
            "JWT token verification failed — invalid or expired token"
        )
        return None

    except Exception:
        logger.exception(
            "Unexpected error during JWT token verification"
        )
        return None