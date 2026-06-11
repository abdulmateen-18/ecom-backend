import logging

from fastapi import Request, HTTPException
from app.core.security import verify_token

logger = logging.getLogger(__name__)


def get_current_user(request: Request):

    try:
        token = request.cookies.get("token")

        if not token:
            logger.warning(
                "Authentication failed — no token cookie present",
                extra={"path": request.url.path}
            )
            raise HTTPException(status_code=401, detail="Not logged in")

        payload = verify_token(token)

        if not payload:
            logger.warning(
                "Authentication failed — token is invalid or expired",
                extra={"path": request.url.path}
            )
            raise HTTPException(status_code=401, detail="Invalid token")

        logger.info(
            "User authenticated successfully",
            extra={"username": payload.get("sub"), "path": request.url.path}
        )

        return payload

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during authentication",
            extra={"path": request.url.path}
        )
        raise