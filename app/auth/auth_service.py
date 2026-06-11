import logging

import bcrypt

from app.core.config import (
    ADMIN_USERNAME,
    ADMIN_PASSWORD_HASH
)

logger = logging.getLogger(__name__)


def verify_admin(
    username: str,
    password: str
) -> bool:

    if username != ADMIN_USERNAME:
        logger.warning(
            "Admin authentication failed — unknown username",
            extra={"attempted_username": username}
        )
        return False

    try:
        result = bcrypt.checkpw(
            password.encode(),
            ADMIN_PASSWORD_HASH.encode()
        )
    except Exception:
        logger.exception(
            "Unexpected error during bcrypt password verification — possible misconfigured hash"
        )
        return False

    if not result:
        logger.warning(
            "Admin authentication failed — incorrect password",
            extra={"username": username}
        )
    else:
        logger.info(
            "Admin authentication successful",
            extra={"username": username}
        )

    return result