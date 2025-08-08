from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.database import get_db
from ..models.schemas import (
    JobCreate, JobUpdate, JobResponse, JobAnalyticsResponse,
    BulkMatchRequest, BulkMatchResponse
)
from ..services.job_management_service import JobManagementService
from ..services.intelligent_matching_service import IntelligentMatchingService
from ..routes.auth import get_current_user_dependency
from ..models.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Initialize services
job_service = JobManagementService()
matching_service = IntelligentMatchingService()

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Create a new job posting"""
    try:
        job = await job_service.create_job(job_data, db)
        return job
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    skip: int = Query(0, ge=0, description="Number of jobs to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of jobs to return"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    experience_level: Optional[str] = Query(None, description="Filter by experience level"),
    remote_only: Optional[bool] = Query(None, description="Show only remote jobs"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    search_term: Optional[str] = Query(None, description="Search in title, description, or company"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get jobs with advanced filtering and search"""
    try:
        jobs, total_count = await job_service.get_jobs(
            db=db,
            skip=skip,
            limit=limit,
            company=company,
            location=location,
            experience_level=experience_level,
            remote_only=remote_only,
            status=status,
            search_term=search_term,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Add total count to response headers for pagination
        return jobs
        
    except Exception as e:
        logger.error(f"Error getting jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve jobs"
        )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get a specific job by ID"""
    try:
        job = await job_service.get_job(job_id, db)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job"
        )

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Update an existing job"""
    try:
        job = await job_service.update_job(job_id, job_update, db)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job"
        )

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    soft_delete: bool = Query(True, description="Perform soft delete (recommended)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Delete a job (soft delete by default)"""
    try:
        success = await job_service.delete_job(job_id, db, soft_delete)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete job"
        )

@router.get("/{job_id}/similar", response_model=List[JobResponse])
async def get_similar_jobs(
    job_id: int,
    limit: int = Query(5, ge=1, le=20, description="Number of similar jobs to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Find similar jobs based on title, company, and skills"""
    try:
        similar_jobs = await job_service.get_similar_jobs(job_id, db, limit)
        return similar_jobs
    except Exception as e:
        logger.error(f"Error finding similar jobs for {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find similar jobs"
        )

@router.get("/{job_id}/matches", response_model=List)
async def get_job_matches(
    job_id: int,
    limit: int = Query(20, ge=1, le=100, description="Number of candidate matches to return"),
    min_score: float = Query(0.3, ge=0.0, le=1.0, description="Minimum match score"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Find candidates that match this job"""
    try:
        matches = await matching_service.match_job_to_candidates(
            job_id=job_id,
            user_id=current_user.id,
            db=db,
            min_score=min_score,
            limit=limit
        )
        return matches
    except Exception as e:
        logger.error(f"Error finding matches for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find job matches"
        )

@router.post("/bulk-update-status")
async def bulk_update_job_status(
    job_ids: List[int],
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Bulk update job status"""
    try:
        if not job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No job IDs provided"
            )
        
        result = await job_service.bulk_update_job_status(job_ids, status, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk updating job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job status"
        )

@router.get("/analytics/overview", response_model=JobAnalyticsResponse)
async def get_job_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get comprehensive job analytics"""
    try:
        analytics = await job_service.get_job_analytics(db, days)
        return analytics
    except Exception as e:
        logger.error(f"Error getting job analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job analytics"
        )