from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import date
from enum import Enum


class JobAnalytics(BaseModel):
    total_jobs: int
    jobs_by_status: Dict[str, int]
    total_workers: int
    workers_by_role: Dict[str, int]


class WorkerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    job_id: Optional[int] = None

class WorkerCreate(WorkerBase):
    pass

class WorkerResponse(WorkerBase):
    id: int

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Job name (required)")
    customer: str = Field(..., min_length=1, max_length=100, description="Customer name (required)")
    start_date: Optional[date] = Field(None, description="Job start date")
    end_date: Optional[date] = Field(None, description="Job end date")
    status: Optional[str] = Field(None, pattern="^(In Progress|Completed|Cancelled)$", description="Job status")

    @validator('end_date')
    def validate_dates(cls, end_date, values):
        start_date = values.get('start_date')
        if start_date and end_date and end_date < start_date:
            raise ValueError('end_date must be after start_date')
        return end_date

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    workers: List[WorkerResponse] = []

    class Config:
        from_attributes = True 



class SortField(str, Enum):
    name = "name"
    start_date = "start_date"
    customer = "customer"
    status = "status"