import logging
import uuid
import re

from sqlalchemy import text
from app.db.session import SessionLocal

from app.services.ai_generation_service import generate_product_content
from app.services.research_generation_service import generate_research_studies
from app.services.product_sync_service import sync_product_details

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """BPC-157 → bpc-157"""
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")


# ─── Existing Service Functions ───────────────────────────────────────────────

def get_product(id: str):

    logger.info(
        "Fetching product by ID",
        extra={"product_id": id}
    )

    db = SessionLocal()

    try:
        product = db.execute(
            text("SELECT * FROM products WHERE id = :id"),
            {"id": id}
        ).fetchone()

        if not product:
            logger.warning(
                "Product not found",
                extra={"product_id": id}
            )
            return None

        logger.info(
            "Fetching product details, variants, research and tags",
            extra={"product_id": id}
        )

        details = db.execute(
            text("SELECT * FROM product_details WHERE product_id = :id"),
            {"id": id}
        ).fetchone()

        variants = db.execute(
            text("""
                SELECT id, label, price
                FROM product_variants
                WHERE product_id = :id
                ORDER BY created_at ASC
            """),
            {"id": id}
        ).fetchall()

        research = db.execute(
            text("""
                SELECT study_area, model_type, outcome, study_year
                FROM research_studies
                WHERE product_id = :id
                ORDER BY study_order ASC
            """),
            {"id": id}
        ).fetchall()

        tags = db.execute(
            text("""
                SELECT tag_name
                FROM product_tags
                WHERE product_id = :id
                ORDER BY tag_order ASC
            """),
            {"id": id}
        ).fetchall()

        related_products = db.execute(
            text("""
                SELECT p.id, p.name, p.image_url
                FROM related_products rp
                JOIN products p ON rp.related_product_id = p.id
                WHERE rp.product_id = :id
                ORDER BY rp.relationship_order ASC
            """),
            {"id": id}
        ).fetchall()

        logger.info(
            "Product fetched successfully",
            extra={
                "product_id": id,
                "variant_count": len(variants),
                "research_count": len(research),
                "tag_count": len(tags),
                "related_count": len(related_products),
            }
        )

        return {
            "product": {
                "id": product.id,
                "name": product.name,
                "subtitle": product.subtitle,
                "description": product.description,
                "image_url": product.image_url,
                "tag": product.tag,
                "min_price": product.min_price,
            },
            "details": {
                "overview_text": details.overview_text if details else None,
                "mechanism_text": details.mechanism_text if details else None,
                "amino_acids": details.amino_acids if details else None,
                "total_studies": details.total_studies if details else None,
                "origin": details.origin if details else None,
                "category": details.category if details else None,
                "structure_type": details.structure_type if details else None,
                "research_status": details.research_status if details else None,
                "administration_route": details.administration_route if details else None,
                "tags": details.tags if details else [],
            },
            "variants": [
                {"id": v.id, "label": v.label, "price": v.price}
                for v in variants
            ],
            "research_studies": [
                {
                    "study_area": r.study_area,
                    "model_type": r.model_type,
                    "outcome": r.outcome,
                    "study_year": r.study_year,
                }
                for r in research
            ],
            "tags": [t.tag_name for t in tags],
            "related_products": [
                {"id": rp.id, "name": rp.name, "image_url": rp.image_url}
                for rp in related_products
            ],
        }

    except Exception:
        logger.exception(
            "Unexpected error fetching product",
            extra={"product_id": id}
        )
        raise

    finally:
        db.close()


def get_products():

    logger.info("Fetching all products")

    db = SessionLocal()

    try:
        products = db.execute(
            text("SELECT id, name, subtitle, min_price, tag FROM products")
        ).fetchall()

        logger.info(
            "Products fetched successfully",
            extra={"product_count": len(products)}
        )

        return [
            {
                "id": p.id,
                "name": p.name,
                "subtitle": p.subtitle,
                "minprice": p.min_price,
                "tag": p.tag,
            }
            for p in products
        ]

    except Exception:
        logger.exception("Unexpected error fetching products list")
        raise

    finally:
        db.close()


def get_cart_details(items: list):

    logger.info(
        "Fetching cart details",
        extra={"item_count": len(items)}
    )

    db = SessionLocal()

    try:
        result = []

        for item in items:
            product_id = item["product_id"]
            variant_id = item["variant_id"]
            quantity = item["quantity"]

            logger.info(
                "Fetching cart item",
                extra={"product_id": product_id, "variant_id": variant_id}
            )

            row = db.execute(
                text("""
                    SELECT
                        p.id AS product_id,
                        p.name,
                        p.subtitle,
                        p.image_url,
                        pv.id AS variant_id,
                        pv.label AS variant,
                        pv.price
                    FROM products p
                    JOIN product_variants pv ON pv.product_id = p.id
                    WHERE p.id = :product_id AND pv.id = :variant_id
                """),
                {"product_id": product_id, "variant_id": variant_id},
            ).fetchone()

            if not row:
                logger.warning(
                    "Cart item not found — skipping",
                    extra={"product_id": product_id, "variant_id": variant_id}
                )
                continue

            result.append({
                "product_id": row.product_id,
                "name": row.name,
                "subtitle": row.subtitle,
                "image_url": row.image_url,
                "variant_id": row.variant_id,
                "variant": row.variant,
                "price": row.price,
                "quantity": quantity,
                "subtotal": row.price * quantity,
            })

        logger.info(
            "Cart details fetched successfully",
            extra={"requested": len(items), "resolved": len(result)}
        )

        return result

    except Exception:
        logger.exception(
            "Unexpected error fetching cart details",
            extra={"item_count": len(items)}
        )
        raise

    finally:
        db.close()


# ─── New Admin Service Functions ──────────────────────────────────────────────

def create_product(data):
    """
    Inserts into products, product_variants, and product_details (pending).
    All in one transaction — rolls back everything if anything fails.
    """

    product_id = slugify(data.name)

    logger.info(
        "Creating new product",
        extra={"product_id": product_id, "product_name": data.name}
    )

    db = SessionLocal()

    try:
        # 1. Insert product
        db.execute(
            text("""
                INSERT INTO products (id, name, subtitle, description, image_url, tag, min_price)
                VALUES (:id, :name, :subtitle, :description, :image_url, :tag, :min_price)
            """),
            {
                "id": product_id,
                "name": data.name,
                "subtitle": data.subtitle,
                "description": data.description,
                "image_url": data.image_url,
                "tag": data.tag,
                "min_price": data.min_price,
            },
        )

        logger.info(
            "Product row inserted",
            extra={"product_id": product_id}
        )

        # 2. Insert variants
        for variant in data.variants:
            variant_id = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO product_variants (id, product_id, label, price)
                    VALUES (:id, :product_id, :label, :price)
                """),
                {
                    "id": variant_id,
                    "product_id": product_id,
                    "label": variant.label,
                    "price": variant.price,
                },
            )

        logger.info(
            "Product variants inserted",
            extra={"product_id": product_id, "variant_count": len(data.variants)}
        )

        # 3. Create pending product_details row
        db.execute(
            text("""
                INSERT INTO product_details (product_id, generation_status, research_generation_status)
                VALUES (:product_id, 'pending', 'pending')
            """),
            {"product_id": product_id},
        )

        logger.info(
            "Product details row inserted with pending status",
            extra={"product_id": product_id}
        )

        db.commit()

        logger.info(
            "Product created successfully",
            extra={"product_id": product_id, "product_name": data.name}
        )

        return {"id": product_id, "name": data.name, "message": "Product created successfully"}

    except Exception:
        db.rollback()
        logger.error(
            "Failed to create product — transaction rolled back",
            extra={"product_id": product_id, "product_name": data.name},
            exc_info=True
        )
        raise

    finally:
        db.close()


def delete_product(product_id: str):
    """
    Deletes product — cascades to product_details, product_variants,
    research_studies automatically via FK constraints.
    """

    logger.info(
        "Deleting product",
        extra={"product_id": product_id}
    )

    db = SessionLocal()

    try:
        result = db.execute(
            text("DELETE FROM products WHERE id = :id"),
            {"id": product_id},
        )

        db.commit()

        if result.rowcount == 0:
            logger.warning(
                "Delete attempted but product not found",
                extra={"product_id": product_id}
            )
            return False

        logger.info(
            "Product deleted successfully",
            extra={"product_id": product_id}
        )

        return True

    except Exception:
        db.rollback()
        logger.error(
            "Failed to delete product — transaction rolled back",
            extra={"product_id": product_id},
            exc_info=True
        )
        raise

    finally:
        db.close()


def run_generation(product_id: str):
    """
    Runs the full AI generation pipeline for a product:
    1. sync_product_details  → creates product_details row if missing
    2. generate_product_content → fills AI columns in product_details
    3. generate_research_studies → fills research_studies table
    """

    logger.info(
        "Starting AI generation pipeline",
        extra={"product_id": product_id}
    )

    try:
        logger.info(
            "Running step 1: sync_product_details",
            extra={"product_id": product_id}
        )
        sync_product_details()

        logger.info(
            "Running step 2: generate_product_content",
            extra={"product_id": product_id}
        )
        generate_product_content()

        logger.info(
            "Running step 3: generate_research_studies",
            extra={"product_id": product_id}
        )
        generate_research_studies()

        logger.info(
            "AI generation pipeline completed successfully",
            extra={"product_id": product_id}
        )

    except Exception:
        logger.exception(
            "AI generation pipeline failed",
            extra={"product_id": product_id}
        )
        raise