import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)
logger.info("Environment variables loaded", extra={"env_path": str(env_path)})

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL is not set or could not be loaded from environment")
    raise RuntimeError("DATABASE_URL environment variable is missing.")

try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,    # prevents stale connection issues
        pool_size=10,          # number of persistent connections in the pool
        max_overflow=20,       # extra connections allowed beyond pool_size under load
        pool_recycle=1800,     # recycle connections every 30 min to avoid DB-side timeouts
    )
    logger.info(
        "Database engine created successfully",
        extra={
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
        }
    )
except Exception:
    logger.exception("Failed to create database engine")
    raise

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
logger.info("SessionLocal factory configured successfully")