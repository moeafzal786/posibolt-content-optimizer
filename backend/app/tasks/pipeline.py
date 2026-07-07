import os
import pandas as pd
from celery import Celery
from app.config import settings
from app.database import SessionLocal
from app.models import Job, JobItem, JobStatus, ItemStatus
from app.services.ai_orchestrator import AIOrchestrator
import logging

logger = logging.getLogger(__name__)

# Initialize Celery using dynamic URL config settings
celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

@celery_app.task(bind=True, max_retries=3)
def process_excel_job(self, job_id: str, file_path: str):
    logger.info(f"Starting execution of Excel job {job_id} on file {file_path}")
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found in database.")
        db.close()
        return
    
    job.status = JobStatus.PROCESSING
    db.commit()
    
    # Delete any existing job items for this job to avoid duplicates in case of retries
    try:
        db.query(JobItem).filter(JobItem.job_id == job.id).delete()
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to clear old job items: {e}")
        db.rollback()
    
    try:
        df = pd.read_excel(file_path)
        orchestrator = AIOrchestrator()
        
        short_descriptions = []
        detailed_descriptions = []
        
        for index, row in df.iterrows():
            # Extract strict source properties with NaN protection
            def clean_cell(col_name):
                val = row.get(col_name, "")
                if pd.isna(val):
                    return ""
                return str(val).strip()

            row_data = {
                "category": clean_cell("Product Category"),
                "name": clean_cell("Name"),
                "description": clean_cell("Description"),
                "detailed_description": clean_cell("Detailed Description")
            }
            
            # Execute Core Logic Isolation Stack via Orchestrator
            logger.info(f"Processing row {index + 1}/{len(df)}: '{row_data['name']}'")
            result = orchestrator.process_product_row(row_data)
            
            # Commit processing state atomicity
            db_item = JobItem(
                job_id=job.id,
                row_index=index,
                category_input=row_data["category"],
                name_input=row_data["name"],
                description_input=row_data["description"],
                detailed_desc_input=row_data["detailed_description"],
                short_desc_output=result["short_description"],
                detailed_desc_output=result["detailed_description"],
                confidence_score=result["confidence_score"],
                accuracy_score=result["scores"]["accuracy"],
                readability_score=result["scores"]["readability"],
                seo_score=result["scores"]["seo"],
                overall_score=result["scores"]["overall"],
                status=ItemStatus.SUCCESS if result["status"] == "SUCCESS" else (
                    ItemStatus.REGENERATED if result["status"] == "REGENERATED" else ItemStatus.FAILED
                ),
                error_log=result.get("error")
            )
            db.add(db_item)
            
            short_descriptions.append(result["short_description"])
            detailed_descriptions.append(result["detailed_description"])
            
            # Realtime progress update
            job.processed_rows = index + 1
            db.commit()
        
        # Build target export sheet without overriding raw properties
        df["Short Description Webstore"] = short_descriptions
        df["Optimized Detailed Description"] = detailed_descriptions
        
        output_path = f"/tmp/{job.id}_optimized.xlsx"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_excel(output_path, index=False)
        
        job.status = JobStatus.COMPLETED
        job.completed_at = pd.Timestamp.now(tz="UTC")
        db.commit()
        logger.info(f"Excel job {job_id} successfully completed. Export written to {output_path}")
        
    except Exception as exc:
        logger.error(f"Execution error on job {job_id}: {str(exc)}")
        job.status = JobStatus.FAILED
        db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
