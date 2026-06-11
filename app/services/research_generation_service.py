import json
import logging
import re

from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.openai_service import generate_completion

logger = logging.getLogger(__name__)


def extract_json(raw: str) -> dict:
    raw = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logger.warning(
            "No JSON block found in LLM response",
            extra={"response_preview": raw[:200]}
        )
        raise ValueError("No JSON found")
    return json.loads(match.group())


def generate_research_studies() -> None:

    logger.info("Starting research studies generation batch")

    db = SessionLocal()

    try:
        logger.info("Fetching pending products for research generation")

        products = db.execute(
            text("""
                SELECT p.id, p.name
                FROM products p
                JOIN product_details pd
                ON p.id = pd.product_id
                WHERE pd.research_generation_status = 'pending'
                AND pd.generation_status = 'completed'
            """)
        ).fetchall()

        logger.info(
            "Pending products fetched for research generation",
            extra={"count": len(products)}
        )

        if not products:
            logger.info("No pending products found for research generation. Exiting batch.")
            return

        for product in products:

            product_id = product.id
            product_name = product.name

            logger.info(
                "Generating research studies for product",
                extra={"product_id": product_id, "product_name": product_name}
            )

            try:
                prompt = f"""
You are a biomedical research data generator.

Generate EXACTLY 4 scientific research studies for the compound: {product_name}

Return ONLY valid JSON in this format:

{{
  "studies": [
    {{
      "study_area": "",
      "model_type": "",
      "outcome": "",
      "study_year": ""
    }}
  ]
}}

Rules:
- Must be scientifically realistic but NOT real clinical claims
- No marketing language
- Use plausible preclinical research domains
- Exactly 4 entries only
- study_year must be between 2018–2025
- model_type must be one of:
  "In vitro", "Preclinical", "Cell culture", "Animal model"
"""

                logger.info(
                    "Sending research generation prompt to OpenAI",
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

                studies = data["studies"]

                logger.info(
                    "Inserting research studies into database",
                    extra={"product_id": product_id, "study_count": len(studies)}
                )

                for i, s in enumerate(studies):
                    db.execute(
                        text("""
                            INSERT INTO research_studies (
                                product_id,
                                study_area,
                                model_type,
                                outcome,
                                study_year,
                                study_order
                            )
                            VALUES (
                                :product_id,
                                :study_area,
                                :model_type,
                                :outcome,
                                :study_year,
                                :study_order
                            )
                        """),
                        {
                            "product_id": product_id,
                            "study_area": s["study_area"],
                            "model_type": s["model_type"],
                            "outcome": s["outcome"],
                            "study_year": s["study_year"],
                            "study_order": i
                        }
                    )

                logger.info(
                    "Research studies inserted successfully",
                    extra={"product_id": product_id, "study_count": len(studies)}
                )

                db.execute(
                    text("""
                        UPDATE product_details
                        SET research_generation_status = 'completed'
                        WHERE product_id = :product_id
                    """),
                    {"product_id": product_id}
                )

                db.commit()

                logger.info(
                    "Research generation completed for product",
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
                    "Unexpected error while generating research for product — skipping product",
                    extra={"product_id": product_id, "product_name": product_name}
                )

    except Exception:
        db.rollback()
        logger.exception("Fatal error during research studies generation batch")

    finally:
        db.close()
        logger.info("Database session closed")