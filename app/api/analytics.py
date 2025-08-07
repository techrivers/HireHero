from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app.models import get_db
from app.models.models import MatchLog, MatchResult, User
from app.routes.auth import get_current_user_dependency

router = APIRouter()

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get dashboard statistics for the current user."""
    
    try:
        # Get date ranges
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Total matches
        total_matches = db.query(MatchLog).filter(
            MatchLog.user_id == current_user.id
        ).count()
        
        # Matches this week
        matches_this_week = db.query(MatchLog).filter(
            MatchLog.user_id == current_user.id,
            func.date(MatchLog.created_at) >= week_ago
        ).count()
        
        # Matches this month
        matches_this_month = db.query(MatchLog).filter(
            MatchLog.user_id == current_user.id,
            func.date(MatchLog.created_at) >= month_ago
        ).count()
        
        # Total candidates evaluated
        total_candidates = db.query(MatchResult).join(MatchLog).filter(
            MatchLog.user_id == current_user.id
        ).count()
        
        # Average match score (using relevance_score field)
        avg_score_result = db.query(func.avg(MatchResult.relevance_score)).join(MatchLog).filter(
            MatchLog.user_id == current_user.id
        ).scalar()
        avg_match_score = round(float(avg_score_result or 0), 1)
        
        # Top skills from recent matches (using key_skills field)
        top_skills = []
        skills_results = db.query(MatchResult.key_skills).join(MatchLog).filter(
            MatchLog.user_id == current_user.id,
            func.date(MatchLog.created_at) >= month_ago,
            MatchResult.key_skills.isnot(None)
        ).all()
        
        skill_counts = {}
        for result in skills_results:
            if result.key_skills:
                try:
                    # Handle both comma-separated and JSON formats
                    if result.key_skills.startswith('['):
                        import json
                        skills_list = json.loads(result.key_skills)
                    else:
                        skills_list = result.key_skills.split(',')
                    
                    for skill in skills_list:
                        skill_clean = str(skill).strip().strip('"\'')
                        if skill_clean:
                            skill_counts[skill_clean] = skill_counts.get(skill_clean, 0) + 1
                except:
                    continue
        
        top_skills = [
            {"skill": skill, "count": count}
            for skill, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Match success rate (scores >= 70)
        high_score_matches = db.query(MatchResult).join(MatchLog).filter(
            MatchLog.user_id == current_user.id,
            MatchResult.relevance_score >= 70
        ).count()
        
        success_rate = round((high_score_matches / max(total_candidates, 1)) * 100, 1)
        
        # Recent activity (last 7 days)
        recent_matches = db.query(MatchLog).filter(
            MatchLog.user_id == current_user.id,
            func.date(MatchLog.created_at) >= week_ago
        ).order_by(desc(MatchLog.created_at)).limit(5).all()
        
        recent_activity = []
        for match in recent_matches:
            results_count = len(match.match_results) if match.match_results else 0
            recent_activity.append({
                "id": match.id,
                "job_title": f"Match #{match.id}",  # Use ID since we don't have job_title field
                "candidates_found": results_count,
                "created_at": match.created_at.isoformat(),
                "status": "completed" if results_count > 0 else "no_matches"
            })
        
        return {
            "total_matches": total_matches,
            "matches_this_week": matches_this_week,
            "matches_this_month": matches_this_month,
            "total_candidates": total_candidates,
            "avg_match_score": avg_match_score,
            "success_rate": success_rate,
            "top_skills": top_skills[:5],
            "recent_activity": recent_activity,
            "week_over_week_change": calculate_week_over_week_change(db, current_user.id),
            "month_over_month_change": calculate_month_over_month_change(db, current_user.id)
        }
        
    except Exception as e:
        import traceback
        print(f"Error in dashboard stats: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")

@router.get("/match-trends")
async def get_match_trends(
    days: int = 30,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get matching trends over time."""
    
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Daily match counts
        daily_matches = db.query(
            func.date(MatchLog.created_at).label('date'),
            func.count(MatchLog.id).label('matches'),
            func.count(MatchResult.id).label('candidates')
        ).outerjoin(MatchResult, MatchResult.match_log_id == MatchLog.id).filter(
            MatchLog.user_id == current_user.id,
            func.date(MatchLog.created_at) >= start_date
        ).group_by(func.date(MatchLog.created_at)).order_by(func.date(MatchLog.created_at)).all()
        
        # Format data for charts
        trend_data = []
        for row in daily_matches:
            trend_data.append({
                "date": row.date.isoformat(),
                "matches": row.matches,
                "candidates": row.candidates or 0
            })
        
        return {
            "trend_data": trend_data,
            "period_days": days,
            "total_matches": sum([d["matches"] for d in trend_data]),
            "total_candidates": sum([d["candidates"] for d in trend_data])
        }
        
    except Exception as e:
        import traceback
        print(f"Error in match trends: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching match trends: {str(e)}")

@router.get("/skill-analysis")
async def get_skill_analysis(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get skill analysis from recent matches."""
    
    try:
        # Get skills from last 30 days
        month_ago = datetime.now().date() - timedelta(days=30)
        
        # Most demanded skills from candidate profiles (since we don't have job requirements stored)
        skills_results = db.query(MatchResult.key_skills).join(MatchLog).filter(
            MatchLog.user_id == current_user.id,
            func.date(MatchLog.created_at) >= month_ago,
            MatchResult.key_skills.isnot(None)
        ).all()
        
        skill_demand = {}
        for result in skills_results:
            if result.key_skills:
                try:
                    # Handle both comma-separated and JSON formats
                    if result.key_skills.startswith('['):
                        import json
                        skills_list = json.loads(result.key_skills)
                    else:
                        skills_list = result.key_skills.split(',')
                    
                    for skill in skills_list:
                        skill_clean = str(skill).strip().strip('"\'')
                        if skill_clean:
                            skill_demand[skill_clean] = skill_demand.get(skill_clean, 0) + 1
                except:
                    continue
        
        most_demanded_skills = [
            {"skill": skill, "demand": count}
            for skill, count in sorted(skill_demand.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # For skill gaps, we'll use the same data but identify less common skills
        candidate_skills = skill_demand
        
        # Calculate skill gaps
        skill_gaps = []
        for skill_data in most_demanded_skills[:10]:
            skill = skill_data["skill"]
            demand = skill_data["demand"]
            supply = candidate_skills.get(skill, 0)
            gap_ratio = demand / max(supply, 1)  # Avoid division by zero
            
            if gap_ratio > 1.5:  # Significant gap
                skill_gaps.append({
                    "skill": skill,
                    "demand": demand,
                    "supply": supply,
                    "gap_ratio": round(gap_ratio, 2)
                })
        
        return {
            "most_demanded_skills": most_demanded_skills,
            "skill_gaps": sorted(skill_gaps, key=lambda x: x["gap_ratio"], reverse=True)[:5],
            "total_unique_skills": len(set([s["skill"] for s in most_demanded_skills] + list(candidate_skills.keys())))
        }
        
    except Exception as e:
        import traceback
        print(f"Error in skill analysis: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching skill analysis: {str(e)}")

def calculate_week_over_week_change(db: Session, user_id: int) -> float:
    """Calculate week over week change in matches."""
    today = datetime.now().date()
    this_week_start = today - timedelta(days=7)
    last_week_start = today - timedelta(days=14)
    
    this_week_matches = db.query(MatchLog).filter(
        MatchLog.user_id == user_id,
        func.date(MatchLog.created_at) >= this_week_start
    ).count()
    
    last_week_matches = db.query(MatchLog).filter(
        MatchLog.user_id == user_id,
        func.date(MatchLog.created_at) >= last_week_start,
        func.date(MatchLog.created_at) < this_week_start
    ).count()
    
    if last_week_matches == 0:
        return 100.0 if this_week_matches > 0 else 0.0
    
    return round(((this_week_matches - last_week_matches) / last_week_matches) * 100, 1)

def calculate_month_over_month_change(db: Session, user_id: int) -> float:
    """Calculate month over month change in matches."""
    today = datetime.now().date()
    this_month_start = today - timedelta(days=30)
    last_month_start = today - timedelta(days=60)
    
    this_month_matches = db.query(MatchLog).filter(
        MatchLog.user_id == user_id,
        func.date(MatchLog.created_at) >= this_month_start
    ).count()
    
    last_month_matches = db.query(MatchLog).filter(
        MatchLog.user_id == user_id,
        func.date(MatchLog.created_at) >= last_month_start,
        func.date(MatchLog.created_at) < this_month_start
    ).count()
    
    if last_month_matches == 0:
        return 100.0 if this_month_matches > 0 else 0.0
    
    return round(((this_month_matches - last_month_matches) / last_month_matches) * 100, 1)