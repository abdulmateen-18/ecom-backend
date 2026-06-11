import logging

from app.db.session import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)


def sync_product_details() -> None:

    logger.info("Starting product details sync")

    db = SessionLocal()

    try:
        logger.info("Fetching all product IDs from database")

        products = db.execute(
            text("""
                SELECT id
                FROM products
            """)
        ).fetchall()

        logger.info(
            "Products fetched",
            extra={"count": len(products)}
        )

        if not products:
            logger.warning("No products found in database — nothing to sync")
            return

        inserted = 0

        for product in products:

            product_id = product.id

            logger.info(
                "Checking for existing product_details row",
                extra={"product_id": product_id}
            )

            existing = db.execute(
                text("""
                    SELECT product_id
                    FROM product_details
                    WHERE product_id = :product_id
                """),
                {"product_id": product_id}
            ).fetchone()

            if not existing:

                logger.info(
                    "No product_details row found — inserting pending record",
                    extra={"product_id": product_id}
                )

                db.execute(
                    text("""
                        INSERT INTO product_details (
                            product_id,
                            generation_status
                        )
                        VALUES (
                            :product_id,
                            'pending'
                        )
                    """),
                    {"product_id": product_id}
                )

                inserted += 1

                logger.info(
                    "Inserted product_details row",
                    extra={"product_id": product_id}
                )

            else:
                logger.info(
                    "product_details row already exists — skipping",
                    extra={"product_id": product_id}
                )

        db.commit()

        logger.info(
            "Product details sync completed",
            extra={"inserted": inserted, "total_products": len(products)}
        )

    except Exception:
        db.rollback()
        logger.exception("Product details sync failed — transaction rolled back")

    finally:
        db.close()
        logger.info("Database session closed")