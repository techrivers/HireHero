from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, timedelta
import logging
import openai
from ..models.models import Job, JobMatch, Candidate, User, UserConfig
from ..models.schemas import (
    JobCreate, JobUpdate, JobResponse, 
    JobAnalyticsResponse, BulkMatchRequest
)
from ..utils.encryption import EncryptionService
import json

logger = logging.getLogger(__name__)

class JobManagementService:
    """
    Comprehensive service for managing job postings with AI-powered enhancements.
    Handles CRUD operations, AI analysis, and bulk processing.
    """
    
    def __init__(self):
        self.encryption_service = EncryptionService()
    
    async def create_job(self, job_data: JobCreate, db: Session) -> JobResponse:
        """Create a new job posting with AI-enhanced analysis"""
        try:
            # Create the job record
            job = Job(
                title=job_data.title,
                company=job_data.company,
                description=job_data.description,
                required_skills=job_data.required_skills,
                experience_level=job_data.experience_level,
                salary_range=job_data.salary_range,
                location=job_data.location,
                remote_friendly=job_data.remote_friendly,
                url=job_data.url,
                posted_date=job_data.posted_date or datetime.utcnow(),
                expiry_date=job_data.expiry_date,
                scrape_source=job_data.scrape_source,
                status='active'
            )
            
            # Enhance job description with AI analysis
            enhanced_data = await self._analyze_job_with_ai(job)
            if enhanced_data:
                job.required_skills = enhanced_data.get('skills', job.required_skills)
                job.experience_level = enhanced_data.get('experience_level', job.experience_level)
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            logger.info(f"Created job: {job.title} at {job.company}")
            return self._job_to_response(job)
            
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            db.rollback()
            raise
    
    async def get_job(self, job_id: int, db: Session) -> Optional[JobResponse]:
        """Get a single job by ID"""
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            return self._job_to_response(job, include_match_count=True, db=db)
        return None
    
    async def get_jobs(
        self, 
        db: Session,
        skip: int = 0, 
        limit: int = 100,
        company: Optional[str] = None,
        location: Optional[str] = None,
        experience_level: Optional[str] = None,
        remote_only: Optional[bool] = None,
        status: Optional[str] = None,
        search_term: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[JobResponse], int]:
        """Get jobs with advanced filtering and search"""
        
        query = db.query(Job)
        
        # Apply filters
        if company:
            query = query.filter(Job.company.ilike(f"%{company}%"))
        
        if location:
            query = query.filter(
                or_(
                    Job.location.ilike(f"%{location}%"),
                    Job.remote_friendly == True
                )
            )
        
        if experience_level:
            query = query.filter(Job.experience_level == experience_level)
            
        if remote_only:
            query = query.filter(Job.remote_friendly == True)
            
        if status:
            query = query.filter(Job.status == status)
        else:
            query = query.filter(Job.status != "deleted")
        
        if search_term:
            search_filter = or_(
                Job.title.ilike(f"%{search_term}%"),
                Job.description.ilike(f"%{search_term}%"),
                Job.company.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply sorting
        if sort_order.lower() == "desc":
            order_func = desc
        else:
            order_func = asc
            
        if hasattr(Job, sort_by):
            query = query.order_by(order_func(getattr(Job, sort_by)))
        else:
            query = query.order_by(desc(Job.created_at))
        
        # Apply pagination
        jobs = query.offset(skip).limit(limit).all()
        
        # Convert to response format
        job_responses = [
            self._job_to_response(job, include_match_count=True, db=db) 
            for job in jobs
        ]
        
        return job_responses, total_count
    
    async def update_job(self, job_id: int, job_update: JobUpdate, db: Session) -> Optional[JobResponse]:
        """Update an existing job"""
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            
            # Update fields that are provided
            update_data = job_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(job, field):
                    setattr(job, field, value)
            
            job.updated_at = datetime.utcnow()
            
            # Re-analyze with AI if description changed
            if 'description' in update_data or 'required_skills' in update_data:
                enhanced_data = await self._analyze_job_with_ai(job)
                if enhanced_data:
                    job.required_skills = enhanced_data.get('skills', job.required_skills)
                    job.experience_level = enhanced_data.get('experience_level', job.experience_level)
            
            db.commit()
            db.refresh(job)
            
            logger.info(f"Updated job: {job.title} at {job.company}")
            return self._job_to_response(job)
            
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {str(e)}")
            db.rollback()
            raise
    
    async def delete_job(self, job_id: int, db: Session, soft_delete: bool = True) -> bool:
        """Delete a job (soft delete by default)"""
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return False
            
            if soft_delete:
                job.status = "deleted"
                job.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Soft deleted job: {job.title} at {job.company}")
            else:
                # Hard delete - also removes all related matches
                db.delete(job)
                db.commit()
                logger.info(f"Hard deleted job: {job.title} at {job.company}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            db.rollback()
            raise
    
    async def get_job_analytics(self, db: Session, days: int = 30) -> JobAnalyticsResponse:
        """Get comprehensive job analytics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic counts
            total_jobs = db.query(Job).filter(Job.status != "deleted").count()
            active_jobs = db.query(Job).filter(Job.status == "active").count()
            
            # Jobs by company
            company_stats = db.query(
                Job.company,
                func.count(Job.id).label('count')
            ).filter(
                Job.status == "active"
            ).group_by(Job.company).order_by(desc('count')).limit(10).all()
            
            jobs_by_company = {company: count for company, count in company_stats}
            
            # Jobs by experience level
            experience_stats = db.query(
                Job.experience_level,
                func.count(Job.id).label('count')
            ).filter(
                Job.status == "active"
            ).group_by(Job.experience_level).all()
            
            jobs_by_experience_level = {level or "not_specified": count for level, count in experience_stats}
            
            # Top required skills
            jobs_with_skills = db.query(Job).filter(
                Job.status == "active",
                Job.required_skills != None
            ).all()
            
            skill_counts = {}
            for job in jobs_with_skills:
                if job.required_skills:
                    for skill in job.required_skills:
                        skill_counts[skill] = skill_counts.get(skill, 0) + 1
            
            top_required_skills = [
                {'skill': skill, 'count': count}
                for skill, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:15]
            ]
            
            # Recent jobs trend
            recent_jobs = db.query(
                func.date(Job.created_at).label('date'),
                func.count(Job.id).label('count')
            ).filter(
                Job.created_at >= cutoff_date,
                Job.status != "deleted"
            ).group_by(func.date(Job.created_at)).order_by('date').all()
            
            recent_jobs_trend = [
                {'date': date.isoformat(), 'count': count}
                for date, count in recent_jobs
            ]
            
            return JobAnalyticsResponse(
                total_jobs=total_jobs,
                active_jobs=active_jobs,
                jobs_by_company=jobs_by_company,
                jobs_by_experience_level=jobs_by_experience_level,
                top_required_skills=top_required_skills,
                recent_jobs_trend=recent_jobs_trend
            )
            
        except Exception as e:
            logger.error(f"Error getting job analytics: {str(e)}")
            raise
    
    async def bulk_update_job_status(self, job_ids: List[int], status: str, db: Session) -> Dict[str, int]:
        """Bulk update job status"""
        try:
            result = db.query(Job).filter(
                Job.id.in_(job_ids)
            ).update(
                {"status": status, "updated_at": datetime.utcnow()},
                synchronize_session=False
            )
            
            db.commit()
            
            logger.info(f"Updated {result} jobs to status: {status}")
            return {"updated": result, "requested": len(job_ids)}
            
        except Exception as e:
            logger.error(f"Error bulk updating job status: {str(e)}")
            db.rollback()
            raise
    
    async def get_similar_jobs(self, job_id: int, db: Session, limit: int = 5) -> List[JobResponse]:
        """Find similar jobs based on title, company, and skills"""
        try:
            target_job = db.query(Job).filter(Job.id == job_id).first()
            if not target_job:
                return []
            
            # Find similar jobs using various criteria
            similar_jobs = db.query(Job).filter(
                Job.id != job_id,
                Job.status == "active",
                or_(
                    Job.title.ilike(f"%{target_job.title}%"),
                    Job.company == target_job.company,
                    Job.experience_level == target_job.experience_level
                )
            ).limit(limit).all()
            
            return [
                self._job_to_response(job, include_match_count=True, db=db)
                for job in similar_jobs
            ]
            
        except Exception as e:
            logger.error(f"Error finding similar jobs: {str(e)}")
            return []
    
    async def _analyze_job_with_ai(
        self, 
        job: Job, 
        user_id: Optional[int] = None, 
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """Analyze job posting with OpenAI to extract skills and classify experience level"""
        try:
            # Get OpenAI API key (you'll need to adapt this based on your user config system)
            api_key = None
            if user_id and db:
                user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
                if user_config and user_config.openai_api_key:
                    api_key = self.encryption_service.decrypt(user_config.openai_api_key)
            
            if not api_key:
                logger.debug("No OpenAI API key available for job analysis")
                return None
            
            client = openai.OpenAI(api_key=api_key)
            
            prompt = f"""
            Analyze this job posting and extract structured information:
            
            Title: {job.title}
            Company: {job.company}
            Description: {job.description[:2000]}  # Limit to avoid token limits
            
            Please provide a JSON response with:
            1. "skills": Array of technical skills, tools, and technologies mentioned
            2. "experience_level": One of ["entry", "mid", "senior", "executive"]
            3. "key_requirements": Array of main requirements
            4. "nice_to_have": Array of preferred/nice-to-have skills
            
            Focus on technical skills and be specific. Return only valid JSON.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a job analysis expert. Return only valid JSON."}, 
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.debug(f"Could not analyze job with AI: {str(e)}")
            return None
    
    def _job_to_response(self, job: Job, include_match_count: bool = False, db: Optional[Session] = None) -> JobResponse:
        """Convert Job model to JobResponse schema"""
        match_count = 0
        if include_match_count and db:
            match_count = db.query(JobMatch).filter(JobMatch.job_id == job.id).count()
        
        return JobResponse(
            id=job.id,
            title=job.title,
            company=job.company,
            description=job.description,
            required_skills=job.required_skills or [],
            experience_level=job.experience_level,
            salary_range=job.salary_range,
            location=job.location,
            remote_friendly=job.remote_friendly,
            url=job.url,
            posted_date=job.posted_date,
            expiry_date=job.expiry_date,
            status=job.status,
            scrape_source=job.scrape_source,
            created_at=job.created_at,
            updated_at=job.updated_at,
            match_count=match_count
        )