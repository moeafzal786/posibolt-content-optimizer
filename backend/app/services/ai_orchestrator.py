import logging
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
from app.config import settings
from app.database import SessionLocal
from app.models import PromptTemplate
from app.services.research_engine import ResearchEngine
from app.services.verifier import Verifier

logger = logging.getLogger(__name__)

class UnderstandingSchema(BaseModel):
    product_type: str = Field(description="Generic product type classification.")
    category: str = Field(description="Target taxonomy category.")
    brand: str = Field(description="Extracted brand name or OEM.")
    key_features: List[str] = Field(description="List of verified product attributes and specs.")
    primary_purpose: str = Field(description="Main application or problem solved.")
    target_user: str = Field(description="Intended customer profile.")
    confidence_score: int = Field(description="Confidence rating of inputs (0-100). Lower if specs are missing.")

class GenerationSchema(BaseModel):
    short_description: str = Field(description="A single sentence containing exactly 15 to 30 words.")
    detailed_description: str = Field(description="Structured markdown description detailing Overview, Benefits, and Applications.")

class AIOrchestrator:
    def __init__(self):
        self.research_engine = ResearchEngine()
        self.verifier = Verifier()
        self.client = None
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock_key":
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.mini_model = "gpt-4o-mini"
        self.copy_model = "gpt-4o"

    def process_product_row(self, row_data: dict) -> dict:
        """
        Main pipeline logic per row: Preprocess -> Understand -> [Research] -> Generate -> Verify -> [Loop Retry]
        """
        # Step 1: Preprocess text patterns and extract baseline traits
        cleaned_input = self._preprocess(row_data)
        
        # Step 2: Parse traits & verify input confidence using structured output
        understanding = self._call_llm_understanding(cleaned_input)
        
        context_pool = {
            "name": cleaned_input.get("name", ""),
            "category": cleaned_input.get("category", "") or understanding.get("category", ""),
            "description": cleaned_input.get("description", ""),
            "detailed_description": cleaned_input.get("detailed_description", ""),
            "product_type": understanding.get("product_type", ""),
            "brand": understanding.get("brand", ""),
            "key_features": ", ".join(understanding.get("key_features", [])),
            "primary_purpose": understanding.get("primary_purpose", ""),
            "target_user": understanding.get("target_user", ""),
            "feedback": ""
        }

        # Step 3: Conditional verification research activation when information is scarce
        if understanding.get("confidence_score", 100) < 70:
            logger.info(f"Confidence score ({understanding.get('confidence_score')}) is low. Triggering Tavily Search.")
            external_context = self.research_engine.search_trusted_sources(cleaned_input["name"])
            context_pool["description"] = (
                f"{context_pool['description']}\n\n"
                f"[Verified Research Specifications]:\n{external_context}"
            )

        # Step 4: Generative optimization with localized state correction retry loop
        max_attempts = 3
        current_attempt = 0
        
        while current_attempt < max_attempts:
            generated_content = self._call_llm_generation(context_pool)
            eval_results = self.verifier.evaluate(context_pool, generated_content)
            
            # Calculate overall score metric based on system weights:
            # Score_overall = 0.40 * Score_accuracy + 0.30 * Score_readability + 0.30 * Score_seo
            overall_score = int(
                (0.40 * eval_results["accuracy_score"]) + 
                (0.30 * eval_results["readability_score"]) + 
                (0.30 * eval_results["seo_score"])
            )
            
            is_valid = (
                overall_score >= 90 and 
                not eval_results["hallucination_detected"] and 
                eval_results["framework_compliance"]
            )
            
            if is_valid:
                logger.info(f"Row optimization succeeded on attempt {current_attempt + 1}.")
                return {
                    "status": "SUCCESS" if current_attempt == 0 else "REGENERATED",
                    "short_description": generated_content["short_description"],
                    "detailed_description": generated_content["detailed_description"],
                    "confidence_score": understanding["confidence_score"],
                    "scores": {
                        "accuracy": eval_results["accuracy_score"],
                        "readability": eval_results["readability_score"],
                        "seo": eval_results["seo_score"],
                        "overall": overall_score
                    }
                }
                
            current_attempt += 1
            # Inject correction variables for the next attempt
            context_pool["feedback"] = (
                f"\n[CRITICAL QUALITY INSTRUCTION (Attempt {current_attempt + 1}/3)]:\n"
                f"Your previous attempt was rejected due to quality check failure:\n"
                f"- Framework Compliance: {eval_results['framework_compliance']} (Must use exactly ## Product Overview, ## Benefits, ## Ideal Applications headers)\n"
                f"- Hallucination Detected: {eval_results['hallucination_detected']} (Must NOT invent features/dimensions/colors not found in the reference inputs)\n"
                f"- Overall Weighted Score: {overall_score}/100 (Accuracy: {eval_results['accuracy_score']}, Readability: {eval_results['readability_score']}, SEO: {eval_results['seo_score']})\n"
                f"Refine your output: exclude placeholders, keep short description strictly 15-30 words, maintain strict fact-alignment."
            )
            logger.warning(f"Quality checks failed for row '{cleaned_input['name']}'. Attempt {current_attempt} failed. Re-trying...")
            
        logger.error(f"Failed to optimize description for row '{cleaned_input['name']}' after {max_attempts} attempts.")
        return {
            "status": "FAILED",
            "short_description": "",
            "detailed_description": "Processing execution failed quality guardrail constraints.",
            "confidence_score": understanding["confidence_score"],
            "scores": {"accuracy": 0, "readability": 0, "seo": 0, "overall": 0},
            "error": "Failed to clear verification scoring matrix after maximum iterations."
        }

    def _preprocess(self, data: dict) -> dict:
        """
        Normalizes spacing and targets text inconsistencies.
        """
        cleaned = {}
        for key in ["category", "name", "description", "detailed_description"]:
            val = data.get(key, "")
            text = str(val) if val is not None and not (isinstance(val, float) and pd_isna(val)) else ""
            text = text.strip()
            text = " ".join(text.split())
            cleaned[key] = text
        return cleaned

    def _call_llm_understanding(self, cleaned_input: dict) -> dict:
        if not self.client:
            return {
                "product_type": "Product",
                "category": cleaned_input.get("category") or "Uncategorized",
                "brand": "Generic",
                "key_features": ["Standard model"],
                "primary_purpose": "Utility",
                "target_user": "Professional",
                "confidence_score": 80
            }

        db = SessionLocal()
        prompt_record = db.query(PromptTemplate).filter(
            PromptTemplate.purpose == "understanding", 
            PromptTemplate.is_active == True
        ).first()
        db.close()

        if prompt_record:
            system_prompt = prompt_record.system_prompt
            user_prompt = prompt_record.user_prompt_template.format(
                category=cleaned_input.get("category", ""),
                name=cleaned_input.get("name", ""),
                description=cleaned_input.get("description", ""),
                detailed_description=cleaned_input.get("detailed_description", "")
            )
        else:
            system_prompt = "Extract product attributes from messy data."
            user_prompt = f"Data: {cleaned_input}"

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.mini_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=UnderstandingSchema,
                temperature=0.0
            )
            res = completion.choices[0].message.parsed
            return {
                "product_type": res.product_type,
                "category": res.category,
                "brand": res.brand,
                "key_features": res.key_features,
                "primary_purpose": res.primary_purpose,
                "target_user": res.target_user,
                "confidence_score": res.confidence_score
            }
        except Exception as e:
            logger.error(f"Error calling OpenAI Understanding API: {str(e)}")
            return {
                "product_type": "Product",
                "category": cleaned_input.get("category", ""),
                "brand": "Generic",
                "key_features": [],
                "primary_purpose": "Utility",
                "target_user": "Commercial",
                "confidence_score": 60
            }

    def _call_llm_generation(self, context_pool: dict) -> dict:
        if not self.client:
            return {
                "short_description": f"The premium {context_pool['name']} delivers excellent performance and industrial quality.",
                "detailed_description": "## Product Overview\nDetailed overview.\n\n## Benefits\n- High quality\n- Durable finish\n\n## Ideal Applications\nCommercial environments."
            }

        db = SessionLocal()
        prompt_record = db.query(PromptTemplate).filter(
            PromptTemplate.purpose == "generation", 
            PromptTemplate.is_active == True
        ).first()
        db.close()

        if prompt_record:
            system_prompt = prompt_record.system_prompt
            user_prompt = prompt_record.user_prompt_template.format(
                product_type=context_pool.get("product_type", ""),
                category=context_pool.get("category", ""),
                brand=context_pool.get("brand", ""),
                key_features=context_pool.get("key_features", ""),
                primary_purpose=context_pool.get("primary_purpose", ""),
                target_user=context_pool.get("target_user", ""),
                description=context_pool.get("description", ""),
                detailed_description=context_pool.get("detailed_description", ""),
                feedback=context_pool.get("feedback", "")
            )
        else:
            system_prompt = "Create eCommerce short and detailed descriptions."
            user_prompt = f"Product data: {context_pool}"

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.copy_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=GenerationSchema,
                temperature=0.7
            )
            res = completion.choices[0].message.parsed
            return {
                "short_description": res.short_description,
                "detailed_description": res.detailed_description
            }
        except Exception as e:
            logger.error(f"Error calling OpenAI Generation API: {str(e)}")
            return {
                "short_description": "Premium industrial grade product optimized for maximum operational uptime.",
                "detailed_description": "## Product Overview\nDefault item overview.\n\n## Benefits\n- Verified build\n- Consistent service\n\n## Ideal Applications\nStandard workshop environments."
            }

def pd_isna(val):
    """
    Safely check if val is NaN (pandas style) to avoid pandas import dependencies.
    """
    try:
        import pandas as pd
        return pd.isna(val)
    except Exception:
        # Fallback numeric NaN check
        return val != val
