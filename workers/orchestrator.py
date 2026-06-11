from app.services.product_sync_service import sync_product_details
from app.services.ai_generation_service import generate_product_content
from app.services.research_generation_service import generate_research_studies


def run_workers():

    print("Starting workers...")

    # 1. Ensure product_details rows exist
    print("Syncing product_details...")
    sync_product_details()

    # 2. Fill product_details using LLM
    print("Generating product details...")
    generate_product_content()

    # 3. Fill research_studies using LLM
    print("Generating research studies...")
    generate_research_studies()

    print("Workers completed.")


if __name__ == "__main__":
    run_workers()