import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt_handler import verify_token, create_token
from app.auth.schema import LoginRequest, LoginResponse
from app.auth.auth_service import verify_admin
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(request: Request, credentials: LoginRequest):

    logger.info(
        "Login endpoint hit",
        extra={"path": request.url.path, "username": credentials.username}
    )

    try:
        valid = verify_admin(credentials.username, credentials.password)

        if not valid:
            logger.warning(
                "Login failed — invalid credentials",
                extra={"username": credentials.username}
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_token(credentials.username)

        logger.info(
            "Login successful — token issued",
            extra={"username": credentials.username}
        )

        return LoginResponse(access_token=token)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during login",
            extra={"username": credentials.username}
        )
        raise


@router.get("/verify")
@limiter.limit("100/minute")
def verify(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):

    logger.info(
        "Token verify endpoint hit",
        extra={"path": request.url.path}
    )

    try:
        payload = verify_token(credentials.credentials)

        if not payload:
            logger.warning(
                "Token verification failed — invalid or expired token",
                extra={"path": request.url.path}
            )
            raise HTTPException(status_code=401, detail="Invalid token")

        logger.info(
            "Token verification successful",
            extra={"username": payload.get("sub")}
        )

        return {
            "authenticated": True,
            "username": payload["sub"]
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during token verification",
            extra={"path": request.url.path}
        )
        raise