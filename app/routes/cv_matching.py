from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import io
from app.models import get_db
from app.models.models import User, MatchLog, MatchResult
from app.models.schemas import MatchRequest, MatchResponse, EnhancedMatchResponse, MatchLogResponse, MatchResultResponse
from app.services.universal_cv_matching_service import universal_cv_matching_service
from app.services.user_config_service import user_config_service
from app.services.google_drive_service import google_drive_service
from app.routes.auth import get_current_user_dependency

router = APIRouter(prefix="/cv-matching", tags=["cv-matching"])

@router.post("/match")
async def match_cvs_to_job(
    match_request: MatchRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Match CVs against a job description."""
    import asyncio
    
    # Check if OpenAI is configured (minimum requirement)
    user_config = user_config_service.get_user_config(db, current_user.id)
    if not user_config or not user_config.openai_api_key:
        raise HTTPException(
            status_code=400, 
            detail="OpenAI API key not configured. Please set up your OpenAI API key first."
        )
    
    try:
        # Run the universal CV matching in a task that can be cancelled
        async def run_cv_matching():
            return await universal_cv_matching_service.process_universal_cv_matching(
                db, 
                current_user.id, 
                match_request.job_description,
                match_request.max_cvs
            )
        
        # Run universal CV matching without asyncio timeout (let other timeouts handle it)
        result = await run_cv_matching()
        return result
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[MatchLogResponse])
def get_match_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's CV matching history."""
    match_logs = db.query(MatchLog).filter(
        MatchLog.user_id == current_user.id
    ).order_by(MatchLog.created_at.desc()).limit(limit).all()
    
    return match_logs

@router.get("/history/{match_log_id}", response_model=List[MatchResultResponse])
def get_match_results(
    match_log_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get detailed results for a specific match."""
    # Verify the match log belongs to the current user
    match_log = db.query(MatchLog).filter(
        MatchLog.id == match_log_id,
        MatchLog.user_id == current_user.id
    ).first()
    
    if not match_log:
        raise HTTPException(status_code=404, detail="Match log not found")
    
    # Get match results
    match_results = db.query(MatchResult).filter(
        MatchResult.match_log_id == match_log_id
    ).order_by(MatchResult.relevance_score.desc()).all()
    
    return match_results

@router.delete("/history/{match_log_id}")
def delete_match_log(
    match_log_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete a match log and its results."""
    # Verify the match log belongs to the current user
    match_log = db.query(MatchLog).filter(
        MatchLog.id == match_log_id,
        MatchLog.user_id == current_user.id
    ).first()
    
    if not match_log:
        raise HTTPException(status_code=404, detail="Match log not found")
    
    # Delete the match log (cascade will delete results)
    db.delete(match_log)
    db.commit()
    
    return {"message": "Match log deleted successfully"}

@router.get("/export/{match_log_id}")
def export_match_results(
    match_log_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Export match results as JSON."""
    from fastapi.responses import JSONResponse
    
    # Verify the match log belongs to the current user
    match_log = db.query(MatchLog).filter(
        MatchLog.id == match_log_id,
        MatchLog.user_id == current_user.id
    ).first()
    
    if not match_log:
        raise HTTPException(status_code=404, detail="Match log not found")
    
    # Get match results
    match_results = db.query(MatchResult).filter(
        MatchResult.match_log_id == match_log_id
    ).order_by(MatchResult.relevance_score.desc()).all()
    
    # Format results for export
    export_data = {
        "match_id": match_log.id,
        "job_description": match_log.job_description,
        "created_at": match_log.created_at.isoformat(),
        "total_cvs_processed": match_log.total_cvs_processed,
        "results": []
    }
    
    for result in match_results:
        # Parse skills from JSON
        skills = []
        if result.key_skills:
            try:
                import json
                skills = json.loads(result.key_skills)
            except:
                skills = []
        
        export_data["results"].append({
            "cv_filename": result.cv_filename,
            "candidate_name": result.candidate_name,
            "candidate_summary": result.candidate_summary,
            "relevance_score": result.relevance_score,
            "is_top_match": result.is_top_match,
            "key_skills": skills,
            "match_analysis": result.match_analysis,
            "experience_years": result.experience_years,
            "download_url": result.download_url
        })
    
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=cv-match-results-{match_log_id}.json"
        }
    )

@router.get("/download-cv/{file_id}")
def download_cv(
    file_id: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Download a CV file from Google Drive."""
    print(f"📥 CV download requested for file_id: {file_id} by user {current_user.id}")
    
    try:
        # Verify user has Google Drive access
        user_config = user_config_service.get_user_config(db, current_user.id)
        if not user_config or not user_config.google_drive_token:
            raise HTTPException(status_code=400, detail="Google Drive not configured")
        
        # Download file content from Google Drive
        file_content = google_drive_service.download_file(db, current_user.id, file_id)
        if not file_content:
            raise HTTPException(status_code=404, detail="File not found or cannot be downloaded")
        
        # Get file metadata to determine filename and content type
        try:
            from googleapiclient.discovery import build
            credentials = google_drive_service.get_user_credentials(db, current_user.id)
            if credentials:
                service = build('drive', 'v3', credentials=credentials)
                file_metadata = service.files().get(fileId=file_id).execute()
                filename = file_metadata.get('name', 'cv_file')
                mime_type = file_metadata.get('mimeType', 'application/octet-stream')
                
                # Set appropriate content type for common CV formats
                if filename.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif filename.lower().endswith('.docx'):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif filename.lower().endswith('.doc'):
                    content_type = 'application/msword'
                else:
                    content_type = mime_type
            else:
                filename = f"cv_{file_id}.pdf"
                content_type = 'application/pdf'
        except Exception as e:
            print(f"⚠️ Could not get file metadata: {e}")
            filename = f"cv_{file_id}.pdf"
            content_type = 'application/pdf'
        
        print(f"📄 Downloading file: {filename} ({len(file_content)} bytes)")
        
        # Create streaming response
        file_stream = io.BytesIO(file_content)
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Content-Length": str(len(file_content)),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error downloading CV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download CV: {str(e)}")

@router.get("/stats")
def get_matching_stats(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's CV matching statistics."""
    from sqlalchemy import func
    
    # Get total matches and CVs processed
    stats = db.query(
        func.count(MatchLog.id).label('total_matches'),
        func.sum(MatchLog.total_cvs_processed).label('total_cvs_processed'),
        func.sum(MatchLog.top_matches_count).label('total_top_matches')
    ).filter(MatchLog.user_id == current_user.id).first()
    
    # Get average scores
    avg_score = db.query(
        func.avg(MatchResult.relevance_score)
    ).join(MatchLog).filter(MatchLog.user_id == current_user.id).scalar()
    
    return {
        "total_matches": stats.total_matches or 0,
        "total_cvs_processed": stats.total_cvs_processed or 0,
        "total_top_matches": stats.total_top_matches or 0,
        "average_relevance_score": round(avg_score or 0, 2)
    }
