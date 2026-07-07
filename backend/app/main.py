from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models import PromptTemplate
from app.api.v1.jobs import router as jobs_router

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Content Optimizer API", version="1.0.0")

# CORS middleware to permit frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(jobs_router)

def seed_templates():
    db = SessionLocal()
    try:
        # Check if templates table is empty
        if db.query(PromptTemplate).count() == 0:
            templates = [
                PromptTemplate(
                    purpose="understanding",
                    system_prompt=(
                        "You are an expert product data analyst specializing in industrial and retail inventory data taxonomy. "
                        "Your task is to extract core attributes from messy, unvetted ERP entries.\n"
                        "Analyze the provided row variables. Populate the output schema strictly using verified properties found inside the textual payload.\n"
                        "Evaluate input clarity. If key specifications or descriptive values are missing, lower the confidence_score property to a value below 70.\n"
                        "Do not infer properties that are completely absent."
                    ),
                    user_prompt_template=(
                        "Category Input: {category}\n"
                        "Name Input: {name}\n"
                        "Description Input: {description}\n"
                        "Detailed Description Input: {detailed_description}"
                    ),
                    version="1.0",
                    is_active=True
                ),
                PromptTemplate(
                    purpose="generation",
                    system_prompt=(
                        "You are an elite eCommerce Direct Response copywriter. Transform the provided clean product properties into customer-focused descriptions.\n\n"
                        "Adhere to these formatting rules:\n"
                        "1. Short Description: Create a single sentence containing exactly 15 to 30 words. It must remain professional, highlight the product naturally, and contain zero placeholder fluff.\n"
                        "2. Detailed Description: Output text structured precisely into the following three Markdown sections:\n"
                        "   ## Product Overview\n"
                        "   [1-2 paragraphs detailing what the item is, what it achieves, and why it is essential.]\n\n"
                        "   ## Benefits\n"
                        "   [3-6 bullet points focusing entirely on real-world customer utility and practical performance advantages. Do not list raw technical parameters here.]\n\n"
                        "   ## Ideal Applications\n"
                        "   [A brief paragraph specifying target operational use cases, safe working locations, or exact end-user matches.]\n\n"
                        "CRITICAL FAULT BOUNDARY: You must never create, assume, or invent attributes that do not exist within the clean dataset. "
                        "If specific metrics like size, volume, compatibility constraints, or parts catalogs are missing, omit them completely. Do not inject placeholders."
                    ),
                    user_prompt_template=(
                        "Product Type: {product_type}\n"
                        "Category: {category}\n"
                        "Brand: {brand}\n"
                        "Key Features: {key_features}\n"
                        "Primary Purpose: {primary_purpose}\n"
                        "Target User: {target_user}\n"
                        "Original Description: {description}\n"
                        "Original Detailed Description: {detailed_description}\n"
                        "{feedback}"
                    ),
                    version="1.0",
                    is_active=True
                ),
                PromptTemplate(
                    purpose="verification",
                    system_prompt=(
                        "You are an adversarial Quality Assurance inspector evaluating compliance against strict e-commerce copywriting rules. "
                        "Compare the original raw input variables against the newly generated description output.\n\n"
                        "Evaluate compliance criteria against the following rules:\n"
                        "- Framework Compliance: Confirm that the detailed text contains exactly the 'Product Overview', 'Benefits', and 'Ideal Applications' Markdown headers.\n"
                        "- Hallucination Auditing: Ensure that no new numbers, materials, performance claims, metrics, colors, or technical dimensions were introduced that were missing from the reference data.\n\n"
                        "If any introduced facts or assumptions are present, set 'hallucination_detected' to true and specify 'REGENERATE' in the 'suggested_action' field."
                    ),
                    user_prompt_template=(
                        "Original Input:\n"
                        "Name: {name}\n"
                        "Category: {category}\n"
                        "Description: {description}\n"
                        "Detailed Description: {detailed_description}\n\n"
                        "Generated Output:\n"
                        "Short Description: {short_description}\n"
                        "Detailed Description: {detailed_description_output}"
                    ),
                    version="1.0",
                    is_active=True
                )
            ]
            db.bulk_save_objects(templates)
            db.commit()
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    seed_templates()
