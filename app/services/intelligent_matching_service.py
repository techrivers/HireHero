from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime
import logging
import openai
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ..models.models import Job, Candidate, JobMatch, UserConfig
from ..models.schemas import (
    JobMatchCreate, JobMatchResponse, BulkMatchRequest, BulkMatchResponse,
    MatchingAnalyticsResponse
)
from ..utils.encryption import EncryptionService

logger = logging.getLogger(__name__)

class IntelligentMatchingService:
    """
    AI-powered intelligent matching service that analyzes job-candidate compatibility
    using OpenAI to provide detailed explanations, skill analysis, and recommendations.
    """
    
    def __init__(self):
        self.encryption_service = EncryptionService()
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def match_candidate_to_jobs(
        self,
        candidate_id: int,
        user_id: int,
        db: Session,
        job_ids: Optional[List[int]] = None,
        min_score: float = 0.3,
        limit: int = 10
    ) -> List[JobMatchResponse]:
        """Match a candidate against jobs and return sorted matches"""
        try:
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                return []
            
            # Get jobs to match against
            query = db.query(Job).filter(Job.status == "active")
            if job_ids:
                query = query.filter(Job.id.in_(job_ids))
            jobs = query.all()
            
            if not jobs:
                return []
            
            # Perform matching with AI
            matches = await self._analyze_candidate_job_matches(
                candidate, jobs, user_id, db
            )
            
            # Filter by minimum score and sort
            filtered_matches = [
                match for match in matches 
                if match.get('match_score', 0) >= min_score
            ]
            
            sorted_matches = sorted(
                filtered_matches, 
                key=lambda x: x.get('match_score', 0), 
                reverse=True
            )[:limit]
            
            # Save matches to database and return responses
            match_responses = []
            for match_data in sorted_matches:
                job_match = await self._save_job_match(
                    match_data, candidate_id, db
                )
                if job_match:
                    match_responses.append(job_match)
            
            return match_responses
            
        except Exception as e:
            logger.error(f"Error matching candidate to jobs: {str(e)}")
            return []
    
    async def match_job_to_candidates(
        self,
        job_id: int,
        user_id: int,
        db: Session,
        candidate_ids: Optional[List[int]] = None,
        min_score: float = 0.3,
        limit: int = 20
    ) -> List[JobMatchResponse]:
        """Match a job against candidates and return sorted matches"""
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return []
            
            # Get candidates to match against
            query = db.query(Candidate)
            if candidate_ids:
                query = query.filter(Candidate.id.in_(candidate_ids))
            candidates = query.all()
            
            if not candidates:
                return []
            
            # Perform matching with AI
            matches = await self._analyze_job_candidate_matches(
                job, candidates, user_id, db
            )
            
            # Filter by minimum score and sort
            filtered_matches = [
                match for match in matches 
                if match.get('match_score', 0) >= min_score
            ]
            
            sorted_matches = sorted(
                filtered_matches, 
                key=lambda x: x.get('match_score', 0), 
                reverse=True
            )[:limit]
            
            # Save matches to database and return responses
            match_responses = []
            for match_data in sorted_matches:
                job_match = await self._save_job_match(
                    match_data, None, db, job_id
                )
                if job_match:
                    match_responses.append(job_match)
            
            return match_responses
            
        except Exception as e:
            logger.error(f"Error matching job to candidates: {str(e)}")
            return []
    
    async def bulk_matching(
        self,
        request: BulkMatchRequest,
        user_id: int,
        db: Session
    ) -> BulkMatchResponse:
        """Perform bulk matching between jobs and candidates"""
        start_time = datetime.now()
        stats = {
            'matches_created': 0,
            'matches_updated': 0,
            'errors': [],
            'job_results': {}
        }
        
        try:
            # Get jobs and candidates
            jobs = db.query(Job).filter(
                Job.id.in_(request.job_ids),
                Job.status == "active"
            ).all()
            
            if request.candidate_ids:
                candidates = db.query(Candidate).filter(
                    Candidate.id.in_(request.candidate_ids)
                ).all()
            else:
                candidates = db.query(Candidate).all()
            
            # Process each job
            for job in jobs:
                try:
                    job_matches = await self._analyze_job_candidate_matches(
                        job, candidates, user_id, db
                    )
                    
                    job_match_count = 0
                    for match_data in job_matches:
                        if match_data.get('match_score', 0) >= 0.3:  # Minimum threshold
                            existing_match = db.query(JobMatch).filter(
                                JobMatch.job_id == job.id,
                                JobMatch.candidate_id == match_data['candidate_id']
                            ).first()
                            
                            if existing_match and not request.force_refresh:
                                # Update existing match
                                existing_match.match_score = match_data['match_score']
                                existing_match.explanation = match_data.get('explanation')
                                existing_match.extra_skills = match_data.get('extra_skills', [])
                                existing_match.alternative_roles = match_data.get('alternative_roles', [])
                                existing_match.strengths = match_data.get('strengths', [])
                                existing_match.gaps = match_data.get('gaps', [])
                                existing_match.recommendation = match_data.get('recommendation', 'consider')
                                existing_match.updated_at = datetime.utcnow()
                                stats['matches_updated'] += 1
                            else:
                                # Create new match
                                new_match = JobMatch(
                                    job_id=job.id,
                                    candidate_id=match_data['candidate_id'],
                                    match_score=match_data['match_score'],
                                    explanation=match_data.get('explanation'),
                                    extra_skills=match_data.get('extra_skills', []),
                                    alternative_roles=match_data.get('alternative_roles', []),
                                    strengths=match_data.get('strengths', []),
                                    gaps=match_data.get('gaps', []),
                                    recommendation=match_data.get('recommendation', 'consider')
                                )
                                db.add(new_match)
                                stats['matches_created'] += 1
                            
                            job_match_count += 1
                    
                    stats['job_results'][job.id] = job_match_count
                    
                except Exception as e:
                    error_msg = f"Error processing job {job.id}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            db.commit()
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return BulkMatchResponse(
                matches_created=stats['matches_created'],
                matches_updated=stats['matches_updated'],
                processing_time=processing_time,
                errors=stats['errors'],
                job_results=stats['job_results']
            )
            
        except Exception as e:
            logger.error(f"Error in bulk matching: {str(e)}")
            db.rollback()
            return BulkMatchResponse(
                matches_created=0,
                matches_updated=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)],
                job_results={}
            )
    
    async def get_matching_analytics(self, db: Session) -> MatchingAnalyticsResponse:
        """Get comprehensive matching analytics"""
        try:
            # Basic statistics
            total_matches = db.query(JobMatch).count()
            avg_match_score = db.query(func.avg(JobMatch.match_score)).scalar() or 0.0
            
            # Matches by recommendation
            recommendation_stats = db.query(
                JobMatch.recommendation,
                func.count(JobMatch.id).label('count')
            ).group_by(JobMatch.recommendation).all()
            
            matches_by_recommendation = {
                rec or "unknown": count for rec, count in recommendation_stats
            }
            
            # Top matched jobs
            top_jobs = db.query(
                Job.id,
                Job.title,
                Job.company,
                func.count(JobMatch.id).label('match_count'),
                func.avg(JobMatch.match_score).label('avg_score')
            ).join(JobMatch).group_by(
                Job.id, Job.title, Job.company
            ).order_by(desc('match_count')).limit(10).all()
            
            top_matched_jobs = [
                {
                    'job_id': job_id,
                    'title': title,
                    'company': company,
                    'match_count': match_count,
                    'avg_score': round(float(avg_score), 2)
                }
                for job_id, title, company, match_count, avg_score in top_jobs
            ]
            
            # Top matched candidates
            top_candidates = db.query(
                Candidate.id,
                Candidate.name,
                Candidate.current_role,
                func.count(JobMatch.id).label('match_count'),
                func.avg(JobMatch.match_score).label('avg_score')
            ).join(JobMatch).group_by(
                Candidate.id, Candidate.name, Candidate.current_role
            ).order_by(desc('match_count')).limit(10).all()
            
            top_matched_candidates = [
                {
                    'candidate_id': candidate_id,
                    'name': name,
                    'current_role': current_role or 'Unknown',
                    'match_count': match_count,
                    'avg_score': round(float(avg_score), 2)
                }
                for candidate_id, name, current_role, match_count, avg_score in top_candidates
            ]
            
            # Skill gap analysis
            skill_gap_analysis = await self._analyze_skill_gaps(db)
            
            return MatchingAnalyticsResponse(
                total_matches=total_matches,
                avg_match_score=round(avg_match_score, 2),
                matches_by_recommendation=matches_by_recommendation,
                top_matched_jobs=top_matched_jobs,
                top_matched_candidates=top_matched_candidates,
                skill_gap_analysis=skill_gap_analysis
            )
            
        except Exception as e:
            logger.error(f"Error getting matching analytics: {str(e)}")
            raise
    
    async def _analyze_candidate_job_matches(
        self,
        candidate: Candidate,
        jobs: List[Job],
        user_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Analyze how well a candidate matches against multiple jobs"""
        try:
            # Get OpenAI API key
            api_key = await self._get_openai_key(user_id, db)
            if not api_key:
                return []
            
            client = openai.OpenAI(api_key=api_key)
            
            # Prepare candidate profile
            candidate_profile = self._format_candidate_for_analysis(candidate)
            
            # Analyze matches in batches to avoid token limits
            batch_size = 3
            all_matches = []
            
            for i in range(0, len(jobs), batch_size):
                job_batch = jobs[i:i + batch_size]
                
                # Format jobs for analysis
                jobs_data = []
                for job in job_batch:
                    jobs_data.append({
                        'id': job.id,
                        'title': job.title,
                        'company': job.company,
                        'description': job.description[:1000],  # Limit description
                        'required_skills': job.required_skills or [],
                        'experience_level': job.experience_level
                    })
                
                batch_matches = await self._analyze_matches_with_ai(
                    client, candidate_profile, jobs_data, 'candidate_to_jobs'
                )
                
                if batch_matches:
                    all_matches.extend(batch_matches)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.1)
            
            return all_matches
            
        except Exception as e:
            logger.error(f"Error analyzing candidate job matches: {str(e)}")
            return []
    
    async def _analyze_job_candidate_matches(
        self,
        job: Job,
        candidates: List[Candidate],
        user_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Analyze how well candidates match against a job"""
        try:
            # Get OpenAI API key
            api_key = await self._get_openai_key(user_id, db)
            if not api_key:
                return []
            
            client = openai.OpenAI(api_key=api_key)
            
            # Prepare job profile
            job_profile = {
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'description': job.description[:1500],
                'required_skills': job.required_skills or [],
                'experience_level': job.experience_level
            }
            
            # Analyze matches in batches
            batch_size = 5
            all_matches = []
            
            for i in range(0, len(candidates), batch_size):
                candidate_batch = candidates[i:i + batch_size]
                
                # Format candidates for analysis
                candidates_data = []
                for candidate in candidate_batch:
                    candidates_data.append(self._format_candidate_for_analysis(candidate))
                
                batch_matches = await self._analyze_matches_with_ai(
                    client, job_profile, candidates_data, 'job_to_candidates'
                )
                
                if batch_matches:
                    all_matches.extend(batch_matches)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.1)
            
            return all_matches
            
        except Exception as e:
            logger.error(f"Error analyzing job candidate matches: {str(e)}")
            return []
    
    async def _analyze_matches_with_ai(
        self,
        client: openai.OpenAI,
        primary_profile: Dict[str, Any],
        secondary_profiles: List[Dict[str, Any]],
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """Use AI to analyze matches between profiles"""
        try:
            if analysis_type == 'candidate_to_jobs':
                prompt = self._create_candidate_to_jobs_prompt(primary_profile, secondary_profiles)
            else:
                prompt = self._create_job_to_candidates_prompt(primary_profile, secondary_profiles)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert recruiter analyzing job-candidate matches. Return only valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get('matches', [])
            
        except Exception as e:
            logger.error(f"Error in AI match analysis: {str(e)}")
            return []
    
    def _create_candidate_to_jobs_prompt(
        self, 
        candidate: Dict[str, Any], 
        jobs: List[Dict[str, Any]]
    ) -> str:
        """Create AI prompt for candidate-to-jobs matching"""
        return f"""
        Analyze how well this candidate matches against the following jobs:
        
        CANDIDATE:
        Name: {candidate.get('name', 'Unknown')}
        Experience: {candidate.get('experience_years', 0)} years
        Current Role: {candidate.get('current_role', 'N/A')}
        Skills: {candidate.get('skills', {})}
        Summary: {candidate.get('professional_summary', 'N/A')}
        
        JOBS TO EVALUATE:
        {json.dumps(jobs, indent=2)}
        
        For each job, provide a match analysis with this JSON structure:
        {{
            "matches": [
                {{
                    "job_id": int,
                    "candidate_id": {candidate.get('id')},
                    "match_score": float (0.0 to 1.0),
                    "explanation": "Brief explanation of the match",
                    "strengths": ["list of candidate strengths for this role"],
                    "gaps": ["list of skill/experience gaps"],
                    "extra_skills": ["skills beyond job requirements"],
                    "alternative_roles": ["alternative roles candidate could consider"],
                    "recommendation": "strong" | "consider" | "weak"
                }}
            ]
        }}
        
        Consider:
        - Skill alignment (technical and soft skills)
        - Experience level match
        - Role progression potential
        - Company culture fit potential
        
        Return only valid JSON.
        """
    
    def _create_job_to_candidates_prompt(
        self, 
        job: Dict[str, Any], 
        candidates: List[Dict[str, Any]]
    ) -> str:
        """Create AI prompt for job-to-candidates matching"""
        return f"""
        Analyze how well these candidates match against this job opening:
        
        JOB OPENING:
        Title: {job.get('title')}
        Company: {job.get('company')}
        Required Skills: {job.get('required_skills', [])}
        Experience Level: {job.get('experience_level', 'N/A')}
        Description: {job.get('description', '')[:500]}...
        
        CANDIDATES TO EVALUATE:
        {json.dumps(candidates, indent=2)}
        
        For each candidate, provide a match analysis with this JSON structure:
        {{
            "matches": [
                {{
                    "job_id": {job.get('id')},
                    "candidate_id": int,
                    "match_score": float (0.0 to 1.0),
                    "explanation": "Brief explanation of the match",
                    "strengths": ["list of candidate strengths for this role"],
                    "gaps": ["list of skill/experience gaps"],
                    "extra_skills": ["skills beyond job requirements"],
                    "alternative_roles": ["alternative roles candidate could consider"],
                    "recommendation": "strong" | "consider" | "weak"
                }}
            ]
        }}
        
        Focus on:
        - Technical skill match
        - Experience alignment
        - Growth potential
        - Cultural fit indicators
        
        Return only valid JSON.
        """
    
    def _format_candidate_for_analysis(self, candidate: Candidate) -> Dict[str, Any]:
        """Format candidate data for AI analysis"""
        return {
            'id': candidate.id,
            'name': candidate.name,
            'experience_years': candidate.experience_years or 0,
            'current_role': candidate.current_role,
            'current_company': candidate.current_company,
            'skills': candidate.skills_json or {},
            'professional_summary': candidate.professional_summary or '',
            'education': candidate.education or [],
            'certifications': candidate.certifications or []
        }
    
    async def _save_job_match(
        self,
        match_data: Dict[str, Any],
        candidate_id: Optional[int],
        db: Session,
        job_id: Optional[int] = None
    ) -> Optional[JobMatchResponse]:
        """Save match result to database and return response"""
        try:
            # Determine IDs
            final_job_id = job_id or match_data.get('job_id')
            final_candidate_id = candidate_id or match_data.get('candidate_id')
            
            if not final_job_id or not final_candidate_id:
                return None
            
            # Check if match already exists
            existing_match = db.query(JobMatch).filter(
                JobMatch.job_id == final_job_id,
                JobMatch.candidate_id == final_candidate_id
            ).first()
            
            if existing_match:
                # Update existing match
                existing_match.match_score = match_data.get('match_score', 0)
                existing_match.explanation = match_data.get('explanation')
                existing_match.extra_skills = match_data.get('extra_skills', [])
                existing_match.alternative_roles = match_data.get('alternative_roles', [])
                existing_match.strengths = match_data.get('strengths', [])
                existing_match.gaps = match_data.get('gaps', [])
                existing_match.recommendation = match_data.get('recommendation', 'consider')
                existing_match.updated_at = datetime.utcnow()
                job_match = existing_match
            else:
                # Create new match
                job_match = JobMatch(
                    job_id=final_job_id,
                    candidate_id=final_candidate_id,
                    match_score=match_data.get('match_score', 0),
                    explanation=match_data.get('explanation'),
                    extra_skills=match_data.get('extra_skills', []),
                    alternative_roles=match_data.get('alternative_roles', []),
                    strengths=match_data.get('strengths', []),
                    gaps=match_data.get('gaps', []),
                    recommendation=match_data.get('recommendation', 'consider')
                )
                db.add(job_match)
            
            db.commit()
            db.refresh(job_match)
            
            # Load related data
            job = db.query(Job).filter(Job.id == job_match.job_id).first()
            candidate = db.query(Candidate).filter(Candidate.id == job_match.candidate_id).first()
            
            return JobMatchResponse(
                id=job_match.id,
                job_id=job_match.job_id,
                candidate_id=job_match.candidate_id,
                match_score=job_match.match_score,
                explanation=job_match.explanation,
                extra_skills=job_match.extra_skills,
                alternative_roles=job_match.alternative_roles,
                strengths=job_match.strengths,
                gaps=job_match.gaps,
                recommendation=job_match.recommendation,
                created_at=job_match.created_at,
                updated_at=job_match.updated_at,
                job=self._job_to_basic_response(job) if job else None,
                candidate=self._candidate_to_basic_response(candidate) if candidate else None
            )
            
        except Exception as e:
            logger.error(f"Error saving job match: {str(e)}")
            db.rollback()
            return None
    
    async def _get_openai_key(self, user_id: int, db: Session) -> Optional[str]:
        """Get decrypted OpenAI API key for user"""
        try:
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if user_config and user_config.openai_api_key:
                return self.encryption_service.decrypt(user_config.openai_api_key)
            return None
        except Exception as e:
            logger.error(f"Error getting OpenAI key: {str(e)}")
            return None
    
    async def _analyze_skill_gaps(self, db: Session) -> List[Dict[str, Any]]:
        """Analyze skill gaps across all matches"""
        try:
            # Get all matches with gaps
            matches_with_gaps = db.query(JobMatch).filter(
                JobMatch.gaps != None,
                JobMatch.gaps != '[]'
            ).all()
            
            # Count gap frequency
            gap_counts = {}
            for match in matches_with_gaps:
                if match.gaps:
                    for gap in match.gaps:
                        gap_counts[gap] = gap_counts.get(gap, 0) + 1
            
            # Return top gaps
            sorted_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)
            return [
                {'skill': skill, 'gap_frequency': count}
                for skill, count in sorted_gaps[:15]
            ]
            
        except Exception as e:
            logger.error(f"Error analyzing skill gaps: {str(e)}")
            return []
    
    def _job_to_basic_response(self, job: Job) -> Dict[str, Any]:
        """Convert job to basic response for match results"""
        return {
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'remote_friendly': job.remote_friendly
        }
    
    def _candidate_to_basic_response(self, candidate: Candidate) -> Dict[str, Any]:
        """Convert candidate to basic response for match results"""
        return {
            'id': candidate.id,
            'name': candidate.name,
            'current_role': candidate.current_role,
            'current_company': candidate.current_company,
            'experience_years': candidate.experience_years
        }
