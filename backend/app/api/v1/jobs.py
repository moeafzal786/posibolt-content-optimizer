from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
import os
import pandas as pd
from app.database import get_db
from app import models, schemas
from app.tasks.pipeline import process_excel_job

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])

REQUIRED_COLUMNS = {"Product Category", "Name", "Description", "Detailed Description"}

@router.get("", response_model=list[schemas.JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(models.Job).order_by(models.Job.created_at.desc()).limit(10).all()

@router.post("/upload", response_model=schemas.JobResponse)
def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are supported.")
    
    # Read headers to perform structural synchronous validation
    try:
        # Use openpyxl engine explicitly for reliability
        df = pd.read_excel(file.file, nrows=0)
        uploaded_cols = set(df.columns)
        if not REQUIRED_COLUMNS.issubset(uploaded_cols):
            missing = REQUIRED_COLUMNS - uploaded_cols
            raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Excel structural metadata: {str(e)}")
    
    # Re-seek file pointer after reading headers
    file.file.seek(0)
    
    # Calculate total length for queue provisioning
    try:
        full_df = pd.read_excel(file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Corrupted Excel file: {str(e)}")
        
    total_rows = len(full_df)
    
    # Save file record to state store
    db_job = models.Job(filename=file.filename, status=models.JobStatus.PENDING, total_rows=total_rows)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # Write safe upload artifact to disk
    file_path = f"/tmp/{db_job.id}.xlsx"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    full_df.to_excel(file_path, index=False)
    
    # Dispatch execution task to Celery distributed cluster
    process_excel_job.delay(str(db_job.id), file_path)
    
    return db_job

@router.get("/{job_id}/status", response_model=schemas.JobStatusResponse)
def get_job_status(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job entry not found.")
    
    progress = (job.processed_rows / job.total_rows * 100) if job.total_rows > 0 else 0.0
    return {
        "job_id": job.id,
        "status": job.status.value,
        "progress_percentage": round(progress, 2),
        "total_rows": job.total_rows,
        "processed_rows": job.processed_rows
    }

@router.get("/{job_id}/download")
def download_job_results(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job entry not found.")
        
    if job.status != models.JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Processed spreadsheet file not ready for download.")
    
    out_path = f"/tmp/{job.id}_optimized.xlsx"
    if not os.path.exists(out_path):
        raise HTTPException(status_code=404, detail="Processed output artifact was removed or is missing.")
        
    return FileResponse(
        out_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename=f"optimized_{job.filename}"
    )
