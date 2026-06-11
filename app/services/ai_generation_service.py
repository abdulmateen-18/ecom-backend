import json
import logging
import re

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.openai_service import generate_completion

logger = logging.getLogger(__name__)


def extract_json(raw: str) -> dict:
    """
    Safely extracts JSON from LLM response even if it includes markdown or extra text.
    """
    # remove markdown fences if any
    raw = raw.replace("```json", "").replace("```", "").strip()

    # extract JSON block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logger.warning(
            "No JSON block found in LLM response",
            extra={"response_preview": raw[:200]}
        )
        raise ValueError(f"No JSON found in response: {raw}")

    return json.loads(match.group())


def generate_product_content() -> None:

    logger.info("Starting product content generation batch")

    db = SessionLocal()

    try:
        logger.info("Fetching pending products from database")

        pending_products = db.execute(
            text("""
                SELECT
                    p.id,
                    p.name
                FROM products p
                JOIN product_details pd
                    ON p.id = pd.product_id
                WHERE pd.generation_status = 'pending'
            """)
        ).fetchall()

        logger.info(
            "Pending products fetched",
            extra={"count": len(pending_products)}
        )

        if not pending_products:
            logger.info("No pending products found. Exiting batch.")
            return

        for product in pending_products:

            product_id = product.id
            product_name = product.name

            logger.info(
                "Generating content for product",
                extra={"product_id": product_id, "product_name": product_name}
            )

            try:
                prompt = f"""
Generate scientific metadata for the peptide:

{product_name}

Return ONLY valid JSON.

Required JSON structure:

{{
  "overview_text": "",
  "mechanism_text": "",
  "amino_acids": "",
  "total_studies": "",
  "origin": "",
  "category": "",
  "structure_type": "",
  "research_status": "",
  "administration_route": "",
  "tags": []
}}

Requirements:
- Professional scientific tone
- Research-focused
- No marketing language
- No medical claims
- overview_text should be 1 paragraph
- mechanism_text should be 2 paragraphs
- tags should contain 3-5 concise scientific keywords
- amino_acids should be a number if known
- total_studies should be an estimated count
"""

                logger.info(
                    "Sending prompt to OpenAI",
                    extra={"product_id": product_id}
                )

                response = generate_completion(prompt)

                logger.info(
                    "Received response from OpenAI",
                    extra={"product_id": product_id}
                )

                data = extract_json(response)

                logger.info(
                    "Successfully parsed JSON from LLM response",
                    extra={"product_id": product_id}
                )

                logger.info(
                    "Updating product details in database",
                    extra={"product_id": product_id}
                )

                db.execute(
                    text("""
                        UPDATE product_details
                        SET
                            overview_text = :overview_text,
                            mechanism_text = :mechanism_text,
                            amino_acids = :amino_acids,
                            total_studies = :total_studies,
                            origin = :origin,
                            category = :category,
                            structure_type = :structure_type,
                            research_status = :research_status,
                            administration_route = :administration_route,
                            tags = :tags,
                            generation_status = 'completed'
                        WHERE product_id = :product_id
                    """),
                    {
                        "overview_text": data["overview_text"],
                        "mechanism_text": data["mechanism_text"],
                        "amino_acids": data["amino_acids"],
                        "total_studies": data["total_studies"],
                        "origin": data["origin"],
                        "category": data["category"],
                        "structure_type": data["structure_type"],
                        "research_status": data["research_status"],
                        "administration_route": data["administration_route"],
                        "tags": data["tags"],
                        "product_id": product_id,
                    }
                )

                db.commit()

                logger.info(
                    "Product content generation completed",
                    extra={"product_id": product_id, "product_name": product_name}
                )

            except ValueError as e:
                db.rollback()
                logger.warning(
                    "Failed to parse LLM response as JSON — skipping product",
                    extra={"product_id": product_id, "product_name": product_name, "error": str(e)}
                )

            except KeyError as e:
                db.rollback()
                logger.warning(
                    "LLM response JSON is missing expected field — skipping product",
                    extra={"product_id": product_id, "product_name": product_name, "missing_key": str(e)}
                )

            except Exception:
                db.rollback()
                logger.exception(
                    "Unexpected error while processing product — skipping product",
                    extra={"product_id": product_id, "product_name": product_name}
                )

    except Exception:
        logger.exception("Fatal error during product content generation batch")
        db.rollback()

    finally:
        db.close()
        logger.info("Database session closed")