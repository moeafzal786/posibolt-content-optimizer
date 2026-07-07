import uuid
import enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, Uuid
from sqlalchemy.sql import func
from app.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ItemStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    REGENERATED = "REGENERATED"
    FAILED = "FAILED"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    status = Column(SQLEnum(JobStatus, name="job_status"), nullable=False, default=JobStatus.PENDING)
    total_rows = Column(Integer, nullable=False, default=0)
    processed_rows = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class JobItem(Base):
    __tablename__ = "job_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id = Column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    row_index = Column(Integer, nullable=False)
    category_input = Column(Text, nullable=True)
    name_input = Column(Text, nullable=False)
    description_input = Column(Text, nullable=True)
    detailed_desc_input = Column(Text, nullable=True)
    short_desc_output = Column(Text, nullable=True)
    detailed_desc_output = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=False, default=0)
    accuracy_score = Column(Integer, nullable=False, default=0)
    readability_score = Column(Integer, nullable=False, default=0)
    seo_score = Column(Integer, nullable=False, default=0)
    overall_score = Column(Integer, nullable=False, default=0)
    status = Column(SQLEnum(ItemStatus, name="item_status"), nullable=False, default=ItemStatus.SUCCESS)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    purpose = Column(String(50), nullable=False, unique=True)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    version = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
