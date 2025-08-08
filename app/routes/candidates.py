from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.database import get_db
from ..models.schemas import (
    CandidateCreate, CandidateUpdate, CandidateResponse, 
    CandidateAnalyticsResponse, IntelligentSearchRequest, IntelligentSearchResponse
)
from ..services.enhanced_candidate_service import EnhancedCandidateService
from ..services.intelligent_matching_service import IntelligentMatchingService
from ..routes.auth import get_current_user_dependency
from ..models.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidates", tags=["candidates"])

# Initialize services
candidate_service = EnhancedCandidateService()
matching_service = IntelligentMatchingService()

@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate_data: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Create a new candidate profile"""
    try:
        # If Google Drive file ID is provided, create from CV
        if candidate_data.google_drive_file_id:
            candidate = await candidate_service.create_candidate_from_cv(
                cv_filename=candidate_data.cv_filename,
                google_drive_file_id=candidate_data.google_drive_file_id,
                user_id=current_user.id,
                db=db
            )
        else:
            # Manual candidate creation would need a different implementation
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google Drive file ID is required for candidate creation"
            )
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create candidate profile"
            )
        
        return candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating candidate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create candidate"
        )

@router.get("/", response_model=List[CandidateResponse])
async def get_candidates(
    skip: int = Query(0, ge=0, description="Number of candidates to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candidates to return"),
    search_term: Optional[str] = Query(None, description="Search in name, summary, role, or company"),
    skills: Optional[List[str]] = Query(None, description="Filter by skills"),
    min_experience: Optional[int] = Query(None, ge=0, description="Minimum years of experience"),
    max_experience: Optional[int] = Query(None, ge=0, description="Maximum years of experience"),
    availability_status: Optional[str] = Query(None, description="Filter by availability status"),
    remote_preference: Optional[bool] = Query(None, description="Filter by remote work preference"),
    location: Optional[str] = Query(None, description="Filter by preferred location"),
    sort_by: str = Query("last_updated", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get candidates with advanced filtering and search"""
    try:
        candidates, total_count = await candidate_service.get_candidates(
            db=db,
            skip=skip,
            limit=limit,
            search_term=search_term,
            skills=skills or [],
            min_experience=min_experience,
            max_experience=max_experience,
            availability_status=availability_status,
            remote_preference=remote_preference,
            location=location,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return candidates
        
    except Exception as e:
        logger.error(f"Error getting candidates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve candidates"
        )

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get a specific candidate by ID"""
    try:
        candidate = await candidate_service.get_candidate(candidate_id, db)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        return candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve candidate"
        )

@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: int,
    candidate_update: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Update an existing candidate"""
    try:
        candidate = await candidate_service.update_candidate(candidate_id, candidate_update, db)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        return candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update candidate"
        )

@router.post("/{candidate_id}/reanalyze", response_model=CandidateResponse)
async def reanalyze_candidate_cv(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Re-analyze candidate's CV with latest AI models"""
    try:
        # Get candidate
        candidate = await candidate_service.get_candidate(candidate_id, db)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Re-analyze CV
        updated_candidate = await candidate_service.create_candidate_from_cv(
            cv_filename=candidate.cv_filename,
            google_drive_file_id=candidate.google_drive_file_id,
            user_id=current_user.id,
            db=db,
            force_reanalyze=True
        )
        
        if not updated_candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to re-analyze candidate CV"
            )
        
        return updated_candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-analyzing candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-analyze candidate"
        )

@router.get("/{candidate_id}/matches", response_model=List)
async def get_candidate_matches(
    candidate_id: int,
    limit: int = Query(10, ge=1, le=50, description="Number of job matches to return"),
    min_score: float = Query(0.3, ge=0.0, le=1.0, description="Minimum match score"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Find jobs that match this candidate"""
    try:
        matches = await matching_service.match_candidate_to_jobs(
            candidate_id=candidate_id,
            user_id=current_user.id,
            db=db,
            min_score=min_score,
            limit=limit
        )
        return matches
    except Exception as e:
        logger.error(f"Error finding matches for candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find candidate matches"
        )

@router.post("/search", response_model=IntelligentSearchResponse)
async def intelligent_candidate_search(
    search_request: IntelligentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """AI-powered intelligent candidate search using natural language"""
    try:
        search_result = await candidate_service.intelligent_candidate_search(
            search_request=search_request,
            user_id=current_user.id,
            db=db
        )
        
        return IntelligentSearchResponse(
            query=search_request.query,
            results=search_result.get('results', []),
            total_results=search_result.get('total_results', 0),
            search_time=search_result.get('search_time', 0),
            suggestions=search_result.get('suggestions', []),
            filters_applied=search_result.get('criteria_used', {}),
            session_id=search_request.session_id or "default"
        )
    except Exception as e:
        logger.error(f"Error in intelligent candidate search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform intelligent search"
        )

@router.post("/bulk-import")
async def bulk_import_candidates_from_drive(
    folder_name: str = Query("CVs", description="Google Drive folder name to import CVs from"),
    force_reanalyze: bool = Query(False, description="Re-analyze existing candidates"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Bulk import candidates from Google Drive folder"""
    try:
        results = await candidate_service.bulk_import_candidates_from_folder(
            folder_name=folder_name,
            user_id=current_user.id,
            db=db,
            force_reanalyze=force_reanalyze
        )
        
        return {
            "message": f"Bulk import completed from folder '{folder_name}'",
            "status": "completed",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in bulk import: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk import"
        )

@router.post("/regenerate-summaries")
async def regenerate_professional_summaries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Regenerate professional summaries for all candidates with missing or poor summaries"""
    try:
        updated_count = await candidate_service.regenerate_professional_summaries(db)
        
        return {
            "message": f"Successfully regenerated professional summaries for {updated_count} candidates",
            "updated_candidates": updated_count,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error regenerating summaries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate professional summaries"
        )

@router.get("/analytics/overview", response_model=CandidateAnalyticsResponse)
async def get_candidate_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get comprehensive candidate analytics"""
    try:
        analytics = await candidate_service.get_candidate_analytics(db)
        return analytics
    except Exception as e:
        logger.error(f"Error getting candidate analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve candidate analytics"
        )

@router.get("/skills/trending")
async def get_trending_skills(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(20, ge=1, le=100, description="Number of skills to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Get trending skills from recent candidate profiles"""
    try:
        # This would analyze recent candidate skills and identify trends
        # For now, return a placeholder response
        return {
            "message": "Trending skills analysis would be implemented here",
            "days_analyzed": days,
            "top_skills": []
        }
    except Exception as e:
        logger.error(f"Error getting trending skills: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trending skills"
        )

@router.post("/{candidate_id}/download-cv")
async def download_candidate_cv(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Download candidate's CV from Google Drive"""
    try:
        # Get candidate
        candidate = await candidate_service.get_candidate(candidate_id, db)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # This would integrate with Google Drive service to provide download link
        return {
            "candidate_id": candidate_id,
            "cv_filename": candidate.cv_filename,
            "google_drive_file_id": candidate.google_drive_file_id,
            "download_url": f"https://drive.google.com/file/d/{candidate.google_drive_file_id}/view"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading CV for candidate {candidate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download CV"
        )