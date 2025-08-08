from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.database import get_db
from ..models.schemas import (
    BulkMatchRequest, BulkMatchResponse, JobMatchResponse,
    MatchingAnalyticsResponse
)
from ..services.intelligent_matching_service import IntelligentMatchingService
from ..routes.auth import get_current_user_dependency
from ..models.models import User, JobMatch, Job, Candidate
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matching", tags=["intelligent-matching"])

# Initialize services
matching_service = IntelligentMatchingService()

@router.post("/candidate/{candidate_id}/jobs", response_model=List[JobMatchResponse])
async def match_candidate_to_jobs(
    candidate_id: int,
    job_ids: Optional[List[int]] = None,
    min_score: float = Query(0.3, ge=0.0, le=1.0, description="Minimum match score"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of matches to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Match a candidate against jobs and return sorted matches"""
    try:
        # Verify candidate exists
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        matches = await matching_service.match_candidate_to_jobs(
            candidate_id=candidate_id,
            user_id=current_user.id,
            db=db,
            job_ids=job_ids,
            min_score=min_score,
            limit=limit
        )
        
        return matches
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error matching candidate {candidate_id} to jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match candidate to jobs"
        )

@router.post("/job/{job_id}/candidates", response_model=List[JobMatchResponse])
async def match_job_to_candidates(
    job_id: int,
    candidate_ids: Optional[List[int]] = None,
    min_score: float = Query(0.3, ge=0.0, le=1.0, description="Minimum match score"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of matches to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Match a job against candidates and return sorted matches"""
    try:
        # Verify job exists
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        matches = await matching_service.match_job_to_candidates(
            job_id=job_id,
            user_id=current_user.id,
            db=db,
            candidate_ids=candidate_ids,
            min_score=min_score,
            limit=limit
        )
        
        return matches
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error matching job {job_id} to candidates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match job to candidates"
        )

@router.post("/bulk", response_model=BulkMatchResponse)
async def bulk_matching(
    request: BulkMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Perform bulk matching between multiple jobs and candidates"""
    try:
        if not request.job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one job ID is required"
            )
        
        # Verify jobs exist
        existing_jobs = db.query(Job).filter(Job.id.in_(request.job_ids)).count()
        if existing_jobs != len(request.job_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more job IDs not found"
            )
        
        # If candidate IDs provided, verify they exist
        if request.candidate_ids:
            existing_candidates = db.query(Candidate).filter(
                Candidate.id.in_(request.candidate_ids)
            ).count()
            if existing_candidates != len(request.candidate_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more candidate IDs not found"
                )
        
        result = await matching_service.bulk_matching(
            request=request,
            user_id=current_user.id,
            db=db
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk matching: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk matching"
        )

@router.get("/history", response_model=List[JobMatchResponse])
async def get_matching_history(
    skip: int = Query(0, ge=0, description="Number of matches to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of matches to return"),
    job_id: Optional[int] = Query(None, description="Filter by specific job"),
    candidate_id: Optional[int] = Query(None, description="Filter by specific candidate"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum match score"),
    recommendation: Optional[str] = Query(None, description="Filter by recommendation (strong, consider, weak)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get matching history with filters"""
    try:
        from sqlalchemy import desc
        
        query = db.query(JobMatch).join(Job).join(Candidate)
        
        # Apply filters
        if job_id:
            query = query.filter(JobMatch.job_id == job_id)
        
        if candidate_id:
            query = query.filter(JobMatch.candidate_id == candidate_id)
        
        if min_score is not None:
            query = query.filter(JobMatch.match_score >= min_score)
        
        if recommendation:
            query = query.filter(JobMatch.recommendation == recommendation)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(JobMatch.created_at))
        
        matches = query.offset(skip).limit(limit).all()
        
        # Convert to response format
        match_responses = []
        for match in matches:
            job = db.query(Job).filter(Job.id == match.job_id).first()
            candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
            
            match_responses.append(JobMatchResponse(
                id=match.id,
                job_id=match.job_id,
                candidate_id=match.candidate_id,
                match_score=match.match_score,
                explanation=match.explanation,
                extra_skills=match.extra_skills,
                alternative_roles=match.alternative_roles,
                strengths=match.strengths,
                gaps=match.gaps,
                recommendation=match.recommendation,
                created_at=match.created_at,
                updated_at=match.updated_at,
                job={
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'remote_friendly': job.remote_friendly
                } if job else None,
                candidate={
                    'id': candidate.id,
                    'name': candidate.name,
                    'current_role': candidate.current_role,
                    'current_company': candidate.current_company,
                    'experience_years': candidate.experience_years
                } if candidate else None
            ))
        
        return match_responses
        
    except Exception as e:
        logger.error(f"Error getting matching history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matching history"
        )

@router.get("/match/{match_id}", response_model=JobMatchResponse)
async def get_match_details(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get detailed information about a specific match"""
    try:
        match = db.query(JobMatch).filter(JobMatch.id == match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found"
            )
        
        # Get related job and candidate
        job = db.query(Job).filter(Job.id == match.job_id).first()
        candidate = db.query(Candidate).filter(Candidate.id == match.candidate_id).first()
        
        return JobMatchResponse(
            id=match.id,
            job_id=match.job_id,
            candidate_id=match.candidate_id,
            match_score=match.match_score,
            explanation=match.explanation,
            extra_skills=match.extra_skills,
            alternative_roles=match.alternative_roles,
            strengths=match.strengths,
            gaps=match.gaps,
            recommendation=match.recommendation,
            created_at=match.created_at,
            updated_at=match.updated_at,
            job={
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'required_skills': job.required_skills,
                'experience_level': job.experience_level,
                'location': job.location,
                'remote_friendly': job.remote_friendly
            } if job else None,
            candidate={
                'id': candidate.id,
                'name': candidate.name,
                'current_role': candidate.current_role,
                'current_company': candidate.current_company,
                'experience_years': candidate.experience_years,
                'skills_json': candidate.skills_json,
                'professional_summary': candidate.professional_summary
            } if candidate else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting match details {match_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve match details"
        )

@router.delete("/match/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Delete a specific match"""
    try:
        match = db.query(JobMatch).filter(JobMatch.id == match_id).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found"
            )
        
        db.delete(match)
        db.commit()
        
        logger.info(f"Deleted match {match_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting match {match_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete match"
        )

@router.get("/analytics/overview", response_model=MatchingAnalyticsResponse)
async def get_matching_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get comprehensive matching analytics"""
    try:
        analytics = await matching_service.get_matching_analytics(db)
        return analytics
    except Exception as e:
        logger.error(f"Error getting matching analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matching analytics"
        )

@router.post("/rematch/{match_id}", response_model=JobMatchResponse)
async def rematch_with_latest_ai(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Re-run matching analysis with latest AI models for a specific match"""
    try:
        # Get existing match
        existing_match = db.query(JobMatch).filter(JobMatch.id == match_id).first()
        if not existing_match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found"
            )
        
        # Re-run matching for this specific job-candidate pair
        new_matches = await matching_service.match_candidate_to_jobs(
            candidate_id=existing_match.candidate_id,
            user_id=current_user.id,
            db=db,
            job_ids=[existing_match.job_id],
            min_score=0.0,  # Allow any score for re-matching
            limit=1
        )
        
        if not new_matches:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to generate new match"
            )
        
        return new_matches[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-matching {match_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-match"
        )

@router.get("/recommendations/top-candidates")
async def get_top_candidate_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Number of top candidates to return"),
    min_score: float = Query(0.7, ge=0.0, le=1.0, description="Minimum match score"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get top candidate recommendations across all jobs"""
    try:
        from sqlalchemy import func, desc
        
        # Get top candidates with highest average match scores
        top_candidates = db.query(
            Candidate.id,
            Candidate.name,
            Candidate.current_role,
            Candidate.current_company,
            Candidate.experience_years,
            func.avg(JobMatch.match_score).label('avg_score'),
            func.count(JobMatch.id).label('match_count')
        ).join(JobMatch).filter(
            JobMatch.match_score >= min_score,
            JobMatch.recommendation.in_(['strong', 'consider'])
        ).group_by(
            Candidate.id, Candidate.name, Candidate.current_role, 
            Candidate.current_company, Candidate.experience_years
        ).order_by(desc('avg_score')).limit(limit).all()
        
        recommendations = []
        for candidate_data in top_candidates:
            recommendations.append({
                'candidate_id': candidate_data.id,
                'name': candidate_data.name,
                'current_role': candidate_data.current_role,
                'current_company': candidate_data.current_company,
                'experience_years': candidate_data.experience_years,
                'avg_match_score': round(float(candidate_data.avg_score), 2),
                'total_matches': candidate_data.match_count
            })
        
        return {
            'top_candidates': recommendations,
            'criteria': {
                'min_score': min_score,
                'limit': limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting top candidate recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get candidate recommendations"
        )

@router.get("/recommendations/top-jobs")
async def get_top_job_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Number of top jobs to return"),
    min_score: float = Query(0.7, ge=0.0, le=1.0, description="Minimum match score"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get top job recommendations based on candidate matches"""
    try:
        from sqlalchemy import func, desc
        
        # Get top jobs with highest average match scores
        top_jobs = db.query(
            Job.id,
            Job.title,
            Job.company,
            Job.location,
            Job.experience_level,
            func.avg(JobMatch.match_score).label('avg_score'),
            func.count(JobMatch.id).label('match_count')
        ).join(JobMatch).filter(
            JobMatch.match_score >= min_score,
            JobMatch.recommendation.in_(['strong', 'consider']),
            Job.status == 'active'
        ).group_by(
            Job.id, Job.title, Job.company, Job.location, Job.experience_level
        ).order_by(desc('avg_score')).limit(limit).all()
        
        recommendations = []
        for job_data in top_jobs:
            recommendations.append({
                'job_id': job_data.id,
                'title': job_data.title,
                'company': job_data.company,
                'location': job_data.location,
                'experience_level': job_data.experience_level,
                'avg_match_score': round(float(job_data.avg_score), 2),
                'total_matches': job_data.match_count
            })
        
        return {
            'top_jobs': recommendations,
            'criteria': {
                'min_score': min_score,
                'limit': limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting top job recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job recommendations"
        )