import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.jwt_handler import verify_token
from app.modules.products.schema import CreateProductRequest, CreateProductResponse
from app.modules.products.service import (
    get_product,
    get_products,
    create_product,
    delete_product,
    run_generation,
)
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()
bearer_scheme = HTTPBearer()


# ─── Auth Dependency ──────────────────────────────────────────────────────────

def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    payload = verify_token(credentials.credentials)

    if not payload:
        logger.warning(
            "Admin authentication failed — invalid or expired token"
        )
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    logger.info(
        "Admin authenticated via token",
        extra={"username": payload["sub"]}
    )

    return payload["sub"]


# ─── Public Routes ────────────────────────────────────────────────────────────

@router.get("/")
@limiter.limit("200/minute")
def read_products(request: Request):

    logger.info(
        "Read products endpoint hit",
        extra={"path": request.url.path}
    )

    try:
        result = get_products()

        logger.info(
            "Products fetched successfully",
            extra={"product_count": len(result) if result else 0}
        )

        return result

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error fetching products",
            extra={"path": request.url.path}
        )
        raise


@router.get("/{id}")
@limiter.limit("200/minute")
def read_product(request: Request, id: str):

    logger.info(
        "Read product endpoint hit",
        extra={"path": request.url.path, "product_id": id}
    )

    try:
        product = get_product(id)

        if not product:
            logger.warning(
                "Product not found",
                extra={"product_id": id}
            )
            raise HTTPException(status_code=404, detail="Product not found")

        logger.info(
            "Product fetched successfully",
            extra={"product_id": id}
        )

        return product

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error fetching product",
            extra={"product_id": id}
        )
        raise


# ─── Protected Admin Routes ───────────────────────────────────────────────────

@router.post("/", response_model=CreateProductResponse)
@limiter.limit("30/minute")
def add_product(
    request: Request,
    data: CreateProductRequest,
    admin: str = Depends(require_admin),
):
    logger.info(
        "Add product endpoint hit",
        extra={"path": request.url.path, "admin": admin}
    )

    try:
        result = create_product(data)

        logger.info(
            "Product created successfully",
            extra={"admin": admin}
        )

        return result

    except HTTPException:
        raise

    except Exception as e:                          # FIX: was `except Exception:`
        logger.error(
            "Failed to create product",
            extra={"admin": admin},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}")
@limiter.limit("30/minute")
def remove_product(
    request: Request,
    id: str,
    admin: str = Depends(require_admin),
):
    logger.info(
        "Delete product endpoint hit",
        extra={"path": request.url.path, "product_id": id, "admin": admin}
    )

    try:
        found = delete_product(id)

        if not found:
            logger.warning(
                "Delete failed — product not found",
                extra={"product_id": id, "admin": admin}
            )
            raise HTTPException(status_code=404, detail="Product not found")

        logger.info(
            "Product deleted successfully",
            extra={"product_id": id, "admin": admin}
        )

        return {"message": f"Product '{id}' deleted successfully"}

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error deleting product",
            extra={"product_id": id, "admin": admin}
        )
        raise


@router.post("/{id}/generate")
@limiter.limit("30/minute")
def generate_product(
    request: Request,
    id: str,
    admin: str = Depends(require_admin),
):
    logger.info(
        "Generate product endpoint hit",
        extra={"path": request.url.path, "product_id": id, "admin": admin}
    )

    try:
        product = get_product(id)

        if not product:
            logger.warning(
                "Generation failed — product not found",
                extra={"product_id": id, "admin": admin}
            )
            raise HTTPException(status_code=404, detail="Product not found")

        logger.info(
            "Starting generation for product",
            extra={"product_id": id, "admin": admin}
        )

        run_generation(id)

        logger.info(
            "Generation completed successfully",
            extra={"product_id": id, "admin": admin}
        )

        return {"message": f"Generation completed for '{id}'"}

    except HTTPException:
        raise

    except Exception as e:                          # FIX: was `except Exception:`
        logger.error(
            "Generation failed for product",
            extra={"product_id": id, "admin": admin},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))