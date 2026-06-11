from app.core.logging_config import setup_logging
setup_logging()  # must be first, before any other app imports

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.rate_limit import limiter
from app.modules.products.routes import router as product_router
from app.routes.auth import router as auth_router
from app.routes.cart import router as cart_router

logger = logging.getLogger(__name__)


app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # for now (later restrict)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_router, prefix="/products", tags=["Products"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(cart_router, prefix="/cart", tags=["Cart"])

logger.info("Application startup complete — routers registered and middleware configured")