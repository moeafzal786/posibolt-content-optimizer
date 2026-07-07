from pydantic import BaseModel, model_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

class JobResponse(BaseModel):
    job_id: UUID
    status: str
    filename: str
    total_rows: int
    processed_rows: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def map_id_to_job_id(cls, data):
        # Handle SQLAlchemy model object
        if hasattr(data, "id") and not hasattr(data, "job_id"):
            # We set job_id so pydantic can read it
            data.job_id = data.id
        # Handle dictionary
        elif isinstance(data, dict) and "id" in data and "job_id" not in data:
            data["job_id"] = data["id"]
        return data

    class Config:
        from_attributes = True

class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    progress_percentage: float
    total_rows: int
    processed_rows: int

    @model_validator(mode="before")
    @classmethod
    def map_id_to_job_id(cls, data):
        if hasattr(data, "id") and not hasattr(data, "job_id"):
            data.job_id = data.id
        elif isinstance(data, dict) and "id" in data and "job_id" not in data:
            data["job_id"] = data["id"]
        return data

    class Config:
        from_attributes = True
