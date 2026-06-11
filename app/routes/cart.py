import logging
import os
from pathlib import Path    
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from app.modules.products.schema import CartDetailsRequest
from app.modules.products.service import get_cart_details
from app.core.rate_limit import limiter


logger = logging.getLogger(__name__)
router = APIRouter()
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER")

@router.post("/details")
@limiter.limit("200/minute")
def cart_details(request: Request, data: CartDetailsRequest):

    logger.info(
        "Cart details endpoint hit",
        extra={"path": request.url.path, "item_count": len(data.items)}
    )

    try:
        items = [item.dict() for item in data.items]

        logger.info(
            "Processing cart details request",
            extra={"item_count": len(items)}
        )

        result = get_cart_details(items)

        logger.info(
            "Cart details response ready",
            extra={"path": request.url.path, "item_count": len(items)}
        )

        return {
            "items": result,
            "whatsapp_number": WHATSAPP_NUMBER
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error processing cart details",
            extra={"path": request.url.path, "item_count": len(data.items)}
        )
        raise