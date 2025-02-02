from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, or_, func
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from typing import Optional, List
import os
from contextlib import contextmanager

from .models import Base, Job, Worker
from .schemas import JobCreate, JobResponse, WorkerCreate, WorkerResponse, SortField, JobAnalytics

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI()

try:
    with engine.connect() as conn:
        pass
    print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        ) from e
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.post("/jobs/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(job: JobCreate):
    with get_db() as db:
        try:
            db_job = Job(**job.model_dump())
            db.add(db_job)
            db.commit()
            db.refresh(db_job)
            return db.query(Job).options(joinedload(Job.workers)).filter(Job.id == db_job.id).first()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

@app.get("/jobs/", response_model=List[JobResponse])
def get_jobs(
    keyword: Optional[str] = Query(None, min_length=1, max_length=100),
    status: Optional[str] = Query(
        None,
        pattern="^(Pending|In Progress|Completed|Cancelled)$"
    ),
    start_after: Optional[date] = Query(None),
    end_before: Optional[date] = Query(None),
    sort_by: Optional[SortField] = Query(None),
    desc: bool = Query(False)
):
    with get_db() as db:
        query = db.query(Job).options(joinedload(Job.workers))

        if start_after and end_before and start_after > end_before:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_after date must be before end_before date"
            )

        if keyword:
            query = query.filter(
                or_(
                    Job.name.ilike(f"%{keyword}%"),
                    Job.customer.ilike(f"%{keyword}%")
                )
            )

        if status:
            query = query.filter(Job.status == status)

        if start_after:
            query = query.filter(Job.start_date >= start_after)
        if end_before:
            query = query.filter(Job.end_date <= end_before)

        if sort_by:
            order_field = getattr(Job, sort_by.value)
            if desc:
                order_field = order_field.desc()
            query = query.order_by(order_field)

        return query.all()

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: int):
    with get_db() as db:
        job = db.query(Job).options(joinedload(Job.workers)).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found"
            )
        return job

@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int):
    with get_db() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found"
            )
        db.delete(job)
        db.commit()


@app.post("/workers/", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
def create_worker(worker: WorkerCreate):
    with get_db() as db:
        if worker.job_id:
            job = db.query(Job).filter(Job.id == worker.job_id).first()
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job with id {worker.job_id} not found"
                )
        
        db_worker = Worker(**worker.model_dump())
        db.add(db_worker)
        db.commit()
        db.refresh(db_worker)
        return db_worker

@app.get("/workers/", response_model=List[WorkerResponse])
def get_workers(
    name: Optional[str] = Query(None, description="Search by worker name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    job_id: Optional[int] = Query(None, description="Filter by job ID")
):
    with get_db() as db:
        query = db.query(Worker)
        
        if name:
            query = query.filter(Worker.name.ilike(f"%{name}%"))
        if role:
            query = query.filter(Worker.role.ilike(f"%{role}%"))
        if job_id:
            query = query.filter(Worker.job_id == job_id)
            
        return query.all()

@app.get("/jobs/{job_id}/workers/", response_model=List[WorkerResponse])
def get_job_workers(job_id: int):
    with get_db() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found"
            )
        return job.workers

@app.put("/workers/{worker_id}/assign/{job_id}", response_model=WorkerResponse)
def assign_worker_to_job(worker_id: int, job_id: int):
    with get_db() as db:
        worker = db.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with id {worker_id} not found"
            )
            
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found"
            )
            
        worker.job_id = job_id
        db.commit()
        db.refresh(worker)
        return worker


@app.get("/analytics/", response_model=JobAnalytics)
def get_analytics():
    with get_db() as db:
        total_jobs = db.query(func.count(Job.id)).scalar()

        status_counts = db.query(
            Job.status,
            func.count(Job.id)
        ).group_by(Job.status).all()
        jobs_by_status = {
            status if status else "Unspecified": count 
            for status, count in status_counts
        }

        total_workers = db.query(func.count(Worker.id)).scalar()

        role_counts = db.query(
            Worker.role,
            func.count(Worker.id)
        ).group_by(Worker.role).all()
        workers_by_role = dict(role_counts)

        return {
            "total_jobs": total_jobs,
            "jobs_by_status": jobs_by_status,
            "total_workers": total_workers,
            "workers_by_role": workers_by_role
        }
