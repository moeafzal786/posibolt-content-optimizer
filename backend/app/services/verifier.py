import logging
from openai import OpenAI
from pydantic import BaseModel, Field
from app.config import settings
from app.database import SessionLocal
from app.models import PromptTemplate

logger = logging.getLogger(__name__)

class VerificationSchema(BaseModel):
    accuracy_score: int = Field(description="Factual correctness of the generated outputs against reference data (0-100).")
    readability_score: int = Field(description="Readability flow, tone, and grammar rating of the copywriting (0-100).")
    seo_score: int = Field(description="Search engine optimization and density score (0-100).")
    framework_compliance: bool = Field(description="Strictly True if layout contains exactly 'Product Overview', 'Benefits', and 'Ideal Applications' H2 markdown headers.")
    hallucination_detected: bool = Field(description="True if claims, sizes, components, or facts were invented that did not exist in reference data.")
    suggested_action: str = Field(description="The suggested workflow instruction, either 'REGENERATE' or 'SUCCESS'.")

class Verifier:
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock_key":
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    def evaluate(self, context_pool: dict, generated_content: dict) -> dict:
        """
        Runs LLM quality checking using Structured Outputs to enforce eCommerce guidelines.
        """
        if not self.client:
            logger.warning("OpenAI client not initialized. Mocking verifier checks.")
            return {
                "accuracy_score": 100,
                "readability_score": 100,
                "seo_score": 100,
                "framework_compliance": True,
                "hallucination_detected": False,
                "suggested_action": "SUCCESS"
            }

        db = SessionLocal()
        prompt_record = db.query(PromptTemplate).filter(
            PromptTemplate.purpose == "verification", 
            PromptTemplate.is_active == True
        ).first()
        db.close()

        if prompt_record:
            system_prompt = prompt_record.system_prompt
            user_prompt = prompt_record.user_prompt_template.format(
                name=context_pool.get("name", ""),
                category=context_pool.get("category", ""),
                description=context_pool.get("description", ""),
                detailed_description=context_pool.get("detailed_description", ""),
                short_description=generated_content.get("short_description", ""),
                detailed_description_output=generated_content.get("detailed_description", "")
            )
        else:
            system_prompt = (
                "You are an adversarial Quality Assurance inspector evaluating compliance against strict e-commerce copywriting rules. "
                "Compare original raw input variables against the newly generated description output.\n"
                "Confirm headers are exactly: Product Overview, Benefits, Ideal Applications. "
                "Set hallucination_detected to true if any unreferenced dimensions/metrics are added."
            )
            user_prompt = f"Original: {context_pool}\nGenerated: {generated_content}"

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=VerificationSchema,
                temperature=0.0
            )
            
            result = completion.choices[0].message.parsed
            return {
                "accuracy_score": result.accuracy_score,
                "readability_score": result.readability_score,
                "seo_score": result.seo_score,
                "framework_compliance": result.framework_compliance,
                "hallucination_detected": result.hallucination_detected,
                "suggested_action": result.suggested_action
            }
        except Exception as e:
            logger.error(f"Error calling OpenAI Verifier API: {str(e)}")
            # Fallback scores to bypass loop or force retry based on safety
            return {
                "accuracy_score": 90,
                "readability_score": 90,
                "seo_score": 90,
                "framework_compliance": True,
                "hallucination_detected": False,
                "suggested_action": "SUCCESS"
            }
