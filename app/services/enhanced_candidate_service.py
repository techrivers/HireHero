from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from datetime import datetime, timedelta
import logging
import openai
import json
import re
from ..models.models import Candidate, Job, JobMatch, User, UserConfig
from ..models.schemas import (
    CandidateCreate, CandidateUpdate, CandidateResponse,
    CandidateAnalyticsResponse, IntelligentSearchRequest
)
from ..utils.encryption import EncryptionService
from ..services.google_drive_service import GoogleDriveService
from ..utils.document_parser import DocumentParser

logger = logging.getLogger(__name__)

class EnhancedCandidateService:
    """
    Advanced candidate management service with AI-powered profiling,
    intelligent search, and comprehensive analytics.
    """
    
    def __init__(self):
        self.encryption_service = EncryptionService()
        self.google_drive_service = GoogleDriveService()
        self.document_parser = DocumentParser()
    
    async def create_candidate_from_cv(
        self, 
        cv_filename: str, 
        google_drive_file_id: str, 
        user_id: int,
        db: Session,
        force_reanalyze: bool = False
    ) -> Optional[CandidateResponse]:
        """Create or update candidate profile from CV with AI analysis"""
        try:
            # Check if candidate already exists
            existing_candidate = db.query(Candidate).filter(
                Candidate.google_drive_file_id == google_drive_file_id
            ).first()
            
            if existing_candidate and not force_reanalyze:
                return self._candidate_to_response(existing_candidate, db=db)
            
            # Download and parse CV
            cv_content = await self._download_and_parse_cv(
                google_drive_file_id, user_id, db
            )
            
            if not cv_content:
                logger.error(f"Could not parse CV: {cv_filename}")
                return None
            
            # Analyze CV with AI
            candidate_profile = await self._analyze_cv_with_ai(
                cv_content, user_id, db
            )
            
            if not candidate_profile:
                # Fallback to basic extraction
                logger.info("AI analysis failed, using basic extraction")
                candidate_profile = self._extract_basic_candidate_info(cv_content)
            else:
                logger.info("AI analysis successful")
            
            # Create or update candidate
            if existing_candidate:
                logger.info("Updating existing candidate")
                candidate = await self._update_candidate_profile(
                    existing_candidate, candidate_profile, cv_filename
                )
            else:
                logger.info(f"Creating new candidate with profile: {candidate_profile}")
                candidate = Candidate(
                    name=candidate_profile.get('name', 'Unknown'),
                    email=candidate_profile.get('email'),
                    phone=candidate_profile.get('phone'),
                    cv_filename=cv_filename,
                    google_drive_file_id=google_drive_file_id,
                    skills_json=candidate_profile.get('skills', {}),
                    experience_years=candidate_profile.get('experience_years', 0),
                    education=candidate_profile.get('education', []),
                    certifications=candidate_profile.get('certifications', []),
                    professional_summary=candidate_profile.get('professional_summary'),
                    current_role=candidate_profile.get('current_role'),
                    current_company=candidate_profile.get('current_company'),
                    preferred_locations=candidate_profile.get('preferred_locations', []),
                    remote_preference=candidate_profile.get('remote_preference', True),
                    availability_status='available',
                    salary_expectation=candidate_profile.get('salary_expectation')
                )
                db.add(candidate)
            
            db.commit()
            db.refresh(candidate)
            
            logger.info(f"Created/updated candidate: {candidate.name}")
            return self._candidate_to_response(candidate, db=db)
            
        except Exception as e:
            logger.error(f"Error creating candidate from CV: {str(e)}")
            db.rollback()
            return None
    
    async def get_candidate(self, candidate_id: int, db: Session) -> Optional[CandidateResponse]:
        """Get a single candidate by ID with match statistics"""
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            return self._candidate_to_response(candidate, include_stats=True, db=db)
        return None
    
    async def get_candidates(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search_term: Optional[str] = None,
        skills: Optional[List[str]] = None,
        min_experience: Optional[int] = None,
        max_experience: Optional[int] = None,
        availability_status: Optional[str] = None,
        remote_preference: Optional[bool] = None,
        location: Optional[str] = None,
        sort_by: str = "last_updated",
        sort_order: str = "desc"
    ) -> Tuple[List[CandidateResponse], int]:
        """Get candidates with advanced filtering and search"""
        
        query = db.query(Candidate)
        
        # Apply filters
        if search_term:
            search_filter = or_(
                Candidate.name.ilike(f"%{search_term}%"),
                Candidate.professional_summary.ilike(f"%{search_term}%"),
                Candidate.current_role.ilike(f"%{search_term}%"),
                Candidate.current_company.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)
        
        if skills:
            # Search for candidates with any of the specified skills
            skill_filters = []
            for skill in skills:
                skill_filters.append(
                    func.json_extract_path_text(Candidate.skills_json, 'technical_skills')
                    .ilike(f"%{skill}%")
                )
            query = query.filter(or_(*skill_filters))
        
        if min_experience is not None:
            query = query.filter(Candidate.experience_years >= min_experience)
        
        if max_experience is not None:
            query = query.filter(Candidate.experience_years <= max_experience)
        
        if availability_status:
            query = query.filter(Candidate.availability_status == availability_status)
        
        if remote_preference is not None:
            query = query.filter(Candidate.remote_preference == remote_preference)
        
        if location:
            query = query.filter(
                func.json_array_length(Candidate.preferred_locations) > 0
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply sorting
        if sort_order.lower() == "desc":
            order_func = desc
        else:
            order_func = asc
        
        if hasattr(Candidate, sort_by):
            query = query.order_by(order_func(getattr(Candidate, sort_by)))
        else:
            query = query.order_by(desc(Candidate.last_updated))
        
        # Apply pagination
        candidates = query.offset(skip).limit(limit).all()
        
        # Convert to response format
        candidate_responses = [
            self._candidate_to_response(candidate, include_stats=True, db=db)
            for candidate in candidates
        ]
        
        return candidate_responses, total_count
    
    async def intelligent_candidate_search(
        self,
        search_request: IntelligentSearchRequest,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """AI-powered intelligent candidate search using natural language"""
        try:
            start_time = datetime.now()
            
            # Parse search query with AI to extract criteria
            search_criteria = await self._parse_search_query_with_ai(
                search_request.query, user_id, db
            )
            
            if not search_criteria:
                # Fallback to basic text search
                candidates, total = await self.get_candidates(
                    db=db, search_term=search_request.query, limit=50
                )
                return {
                    'results': candidates,
                    'total_results': total,
                    'search_time': (datetime.now() - start_time).total_seconds(),
                    'criteria_used': {'search_term': search_request.query},
                    'suggestions': []
                }
            
            # Apply extracted criteria
            candidates, total = await self.get_candidates(
                db=db,
                search_term=search_criteria.get('search_term'),
                skills=search_criteria.get('skills', []),
                min_experience=search_criteria.get('min_experience'),
                max_experience=search_criteria.get('max_experience'),
                availability_status=search_criteria.get('availability_status'),
                remote_preference=search_criteria.get('remote_preference'),
                location=search_criteria.get('location'),
                limit=50
            )
            
            # Generate suggestions for refinement
            suggestions = await self._generate_search_suggestions(
                search_criteria, candidates, db
            )
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'results': candidates,
                'total_results': total,
                'search_time': search_time,
                'criteria_used': search_criteria,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent search: {str(e)}")
            # Fallback to basic search
            candidates, total = await self.get_candidates(
                db=db, search_term=search_request.query, limit=50
            )
            return {
                'results': candidates,
                'total_results': total,
                'search_time': 0,
                'criteria_used': {'search_term': search_request.query},
                'suggestions': [],
                'error': str(e)
            }
    
    async def update_candidate(
        self, 
        candidate_id: int, 
        candidate_update: CandidateUpdate, 
        db: Session
    ) -> Optional[CandidateResponse]:
        """Update candidate information"""
        try:
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                return None
            
            # Update fields
            update_data = candidate_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(candidate, field):
                    setattr(candidate, field, value)
            
            candidate.last_updated = datetime.utcnow()
            
            db.commit()
            db.refresh(candidate)
            
            logger.info(f"Updated candidate: {candidate.name}")
            return self._candidate_to_response(candidate, db=db)
            
        except Exception as e:
            logger.error(f"Error updating candidate {candidate_id}: {str(e)}")
            db.rollback()
            raise
    
    async def bulk_import_candidates_from_folder(
        self, 
        folder_name: str, 
        user_id: int, 
        db: Session,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """Bulk import candidates from Google Drive folder"""
        results = {
            'total_files': 0,
            'successfully_processed': 0,
            'failed_processing': 0,
            'skipped_existing': 0,
            'candidates_created': [],
            'processing_errors': []
        }
        
        try:
            # Get files from Google Drive folder
            from ..services.google_drive_service import google_drive_service
            files = google_drive_service.list_files_in_folder(db, user_id, folder_name)
            
            if not files:
                logger.warning(f"No files found in folder '{folder_name}' for user {user_id}")
                return results
            
            results['total_files'] = len(files)
            
            # Filter for CV-like files (PDF, DOCX, DOC)
            cv_files = []
            for file in files:
                mime_type = file.get('mimeType', '')
                name = file.get('name', '').lower()
                
                if (mime_type in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'] or
                    any(ext in name for ext in ['.pdf', '.docx', '.doc'])):
                    cv_files.append(file)
            
            logger.info(f"Found {len(cv_files)} CV files in folder '{folder_name}'")
            
            # Process each CV file
            for file in cv_files:
                try:
                    file_id = file.get('id')
                    filename = file.get('name')
                    
                    logger.info(f"Processing CV: {filename}")
                    
                    # Check if candidate already exists
                    existing_candidate = db.query(Candidate).filter(
                        Candidate.google_drive_file_id == file_id
                    ).first()
                    
                    if existing_candidate and not force_reanalyze:
                        logger.info(f"Candidate already exists for {filename}, skipping")
                        results['skipped_existing'] += 1
                        continue
                    
                    # Create candidate from CV
                    candidate_response = await self.create_candidate_from_cv(
                        cv_filename=filename,
                        google_drive_file_id=file_id,
                        user_id=user_id,
                        db=db,
                        force_reanalyze=force_reanalyze
                    )
                    
                    if candidate_response:
                        results['successfully_processed'] += 1
                        results['candidates_created'].append({
                            'name': candidate_response.name,
                            'filename': filename,
                            'id': candidate_response.id
                        })
                        logger.info(f"Successfully processed: {filename} -> {candidate_response.name}")
                    else:
                        results['failed_processing'] += 1
                        results['processing_errors'].append(f"Failed to process {filename}")
                        logger.error(f"Failed to process {filename}")
                    
                except Exception as e:
                    results['failed_processing'] += 1
                    error_msg = f"Error processing {filename}: {str(e)}"
                    results['processing_errors'].append(error_msg)
                    logger.error(error_msg)
            
            logger.info(f"Bulk import completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk import: {str(e)}")
            results['processing_errors'].append(f"Bulk import error: {str(e)}")
            return results
    
    async def get_candidate_analytics(self, db: Session) -> CandidateAnalyticsResponse:
        """Get comprehensive candidate analytics"""
        try:
            # Basic counts
            total_candidates = db.query(Candidate).count()
            
            # Candidates by experience level
            experience_ranges = [
                ("0-2 years", 0, 2),
                ("3-5 years", 3, 5),
                ("6-10 years", 6, 10),
                ("10+ years", 11, 100)
            ]
            
            candidates_by_experience = {}
            for label, min_exp, max_exp in experience_ranges:
                count = db.query(Candidate).filter(
                    Candidate.experience_years >= min_exp,
                    Candidate.experience_years <= max_exp
                ).count()
                candidates_by_experience[label] = count
            
            # Candidates by availability status
            availability_stats = db.query(
                Candidate.availability_status,
                func.count(Candidate.id).label('count')
            ).group_by(Candidate.availability_status).all()
            
            candidates_by_availability = {
                status or "unknown": count for status, count in availability_stats
            }
            
            # Calculate average experience
            avg_experience = db.query(
                func.avg(Candidate.experience_years)
            ).scalar() or 0.0
            
            # Get all candidates with skills for analysis
            candidates_with_skills = db.query(Candidate).filter(
                Candidate.skills_json != None
            ).all()
            
            # Analyze skills
            skill_counts = {}
            for candidate in candidates_with_skills:
                if candidate.skills_json and isinstance(candidate.skills_json, dict):
                    technical_skills = candidate.skills_json.get('technical_skills', [])
                    if isinstance(technical_skills, list):
                        for skill in technical_skills:
                            skill_name = skill if isinstance(skill, str) else skill.get('name', '')
                            if skill_name:
                                skill_counts[skill_name] = skill_counts.get(skill_name, 0) + 1
            
            top_candidate_skills = [
                {'skill': skill, 'count': count}
                for skill, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            ]
            
            return CandidateAnalyticsResponse(
                total_candidates=total_candidates,
                candidates_by_experience=candidates_by_experience,
                candidates_by_availability=candidates_by_availability,
                top_candidate_skills=top_candidate_skills,
                avg_experience_years=round(avg_experience, 1),
                skill_distribution=skill_counts
            )
            
        except Exception as e:
            logger.error(f"Error getting candidate analytics: {str(e)}")
            raise
    
    async def _download_and_parse_cv(
        self, 
        google_drive_file_id: str, 
        user_id: int, 
        db: Session
    ) -> Optional[str]:
        """Download CV from Google Drive and extract text content"""
        try:
            # Download file content using the google drive service
            file_content = self.google_drive_service.download_file(db, user_id, google_drive_file_id)
            
            if not file_content:
                return None
            
            # Get file metadata to determine type
            from ..services.google_drive_service import google_drive_service
            credentials = google_drive_service.get_user_credentials(db, user_id)
            if credentials:
                from googleapiclient.discovery import build
                service = build('drive', 'v3', credentials=credentials)
                file_metadata = service.files().get(fileId=google_drive_file_id).execute()
                filename = file_metadata.get('name', 'unknown.pdf')
            else:
                filename = 'unknown.pdf'
            
            # Parse document content using filename to detect type
            parsed_content = self.document_parser.extract_text_from_file(file_content, filename)
            
            return parsed_content
            
        except Exception as e:
            logger.error(f"Error downloading/parsing CV: {str(e)}")
            return None
    
    async def _analyze_cv_with_ai(
        self, 
        cv_content: str, 
        user_id: int, 
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Analyze CV content with OpenAI to extract structured candidate data"""
        try:
            # Get OpenAI API key
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not user_config or not user_config.openai_api_key:
                return None
            
            api_key = self.encryption_service.decrypt(user_config.openai_api_key)
            client = openai.OpenAI(api_key=api_key)
            
            prompt = f"""
            Analyze this resume/CV and extract structured candidate information:
            
            {cv_content[:6000]}  # Increased limit to capture more content
            
            Please provide a JSON response with:
            1. "name": Full name
            2. "email": Email address
            3. "phone": Phone number
            4. "professional_summary": A compelling 2-3 sentence professional summary that highlights:
               - Current role and years of experience
               - Key technical skills and expertise areas
               - Notable achievements or unique value proposition
               - Career focus or specialization
               Example: "Experienced Senior Software Engineer with 8+ years developing scalable web applications using React, Node.js, and AWS. Led cross-functional teams to deliver high-impact products that increased user engagement by 40%. Passionate about clean code, system architecture, and mentoring junior developers."
            5. "current_role": Current job title
            6. "current_company": Current company
            7. "experience_years": Total years of professional experience (integer)
            8. "skills": Object with:
               - "technical_skills": Array of technical skills with proficiency
               - "soft_skills": Array of soft skills
               - "tools": Array of tools/software
               - "languages": Array of programming languages
            9. "education": Array of education entries with degree, institution, year
            10. "certifications": Array of certifications
            11. "preferred_locations": Array of preferred work locations if mentioned
            12. "remote_preference": Boolean if remote work is preferred
            13. "salary_expectation": Salary expectation if mentioned
            
            Return only valid JSON. If information is not found, use null or empty array.
            IMPORTANT: Make the professional_summary specific and compelling, not generic.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a resume analysis expert. Return only valid JSON."}, 
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,  # Increased for better summaries
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and enhance professional summary
            if not result.get('professional_summary') or result['professional_summary'] in ['', 'null', None]:
                logger.warning("AI generated empty professional summary, creating fallback")
                result['professional_summary'] = self._create_fallback_summary(result, cv_content)
            elif len(result['professional_summary']) < 50:  # Too short, likely generic
                logger.warning("AI generated very short professional summary, enhancing")
                result['professional_summary'] = self._enhance_short_summary(result, cv_content)
                
            logger.info(f"AI analysis successful for candidate: {result.get('name', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Could not analyze CV with AI: {str(e)}")
            return None
    
    def _extract_basic_candidate_info(self, cv_content: str) -> Dict[str, Any]:
        """Fallback basic information extraction without AI"""
        # Basic regex patterns for common information
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'[\+]?[1-9]?[0-9]{7,15}'
        
        email_match = re.search(email_pattern, cv_content)
        phone_match = re.search(phone_pattern, cv_content)
        
        # Extract potential name (first few words of non-common content)
        lines = cv_content.split('\n')[:10] if cv_content else []
        potential_name = None
        for line in lines:
            if line and len(line.strip()) > 3 and '@' not in line and 'http' not in line.lower():
                potential_name = line.strip()
                break
        
        # Try to create a basic professional summary from content
        basic_summary = self._extract_basic_summary(cv_content, potential_name)
        
        return {
            'name': potential_name or 'Unknown',
            'email': email_match.group() if email_match else None,
            'phone': phone_match.group() if phone_match else None,
            'professional_summary': basic_summary,
            'experience_years': 0,
            'skills': {'technical_skills': [], 'soft_skills': [], 'tools': [], 'languages': []},
            'education': [],
            'certifications': [],
            'preferred_locations': [],
            'remote_preference': True
        }
    
    def _create_fallback_summary(self, candidate_data: Dict[str, Any], cv_content: str) -> str:
        """Create a fallback professional summary when AI fails to generate one"""
        try:
            name = candidate_data.get('name', 'Professional')
            current_role = candidate_data.get('current_role', '')
            current_company = candidate_data.get('current_company', '')
            experience_years = candidate_data.get('experience_years', 0)
            
            # Extract technical skills
            skills = candidate_data.get('skills', {})
            tech_skills = skills.get('technical_skills', [])[:3]  # Top 3 skills
            
            # Build summary components
            parts = []
            
            if current_role and current_company:
                parts.append(f"Currently working as {current_role} at {current_company}")
            elif current_role:
                parts.append(f"Experienced {current_role}")
            else:
                parts.append("Experienced professional")
            
            if experience_years > 0:
                parts.append(f"with {experience_years}+ years of experience")
            
            if tech_skills:
                skills_text = ", ".join(tech_skills)
                parts.append(f"skilled in {skills_text}")
            
            # Add basic content analysis
            content_lower = cv_content.lower()
            if 'lead' in content_lower or 'manager' in content_lower:
                parts.append("with leadership experience")
            elif 'senior' in content_lower:
                parts.append("with senior-level expertise")
            
            summary = ". ".join(parts) + "."
            
            # Ensure minimum length
            if len(summary) < 50:
                summary += " Dedicated to delivering high-quality results and continuous professional growth."
            
            return summary
            
        except Exception as e:
            logger.warning(f"Error creating fallback summary: {str(e)}")
            return f"Experienced professional with expertise in various technologies and business domains."
    
    def _enhance_short_summary(self, candidate_data: Dict[str, Any], cv_content: str) -> str:
        """Enhance a short AI-generated summary with additional context"""
        try:
            original_summary = candidate_data.get('professional_summary', '')
            
            # Add context from other fields
            current_role = candidate_data.get('current_role', '')
            experience_years = candidate_data.get('experience_years', 0)
            skills = candidate_data.get('skills', {})
            tech_skills = skills.get('technical_skills', [])[:3]
            
            enhancements = []
            
            if experience_years > 0:
                enhancements.append(f"with {experience_years}+ years of professional experience")
            
            if tech_skills:
                skills_text = ", ".join(tech_skills)
                enhancements.append(f"specialized in {skills_text}")
            
            if current_role:
                enhancements.append(f"currently serving as {current_role}")
            
            if enhancements:
                enhanced = f"{original_summary.rstrip('.')} {', '.join(enhancements[:2])}."
                return enhanced
            
            return original_summary
            
        except Exception as e:
            logger.warning(f"Error enhancing short summary: {str(e)}")
            return candidate_data.get('professional_summary', '')
    
    def _extract_basic_summary(self, cv_content: str, name: str) -> str:
        """Extract basic professional summary from CV content without AI"""
        try:
            if not cv_content:
                return "Professional profile available upon request."
            
            content_lower = cv_content.lower()
            lines = [line.strip() for line in cv_content.split('\n') if line.strip()]
            
            # Look for summary sections
            summary_keywords = ['summary', 'profile', 'objective', 'about', 'overview']
            summary_content = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in summary_keywords) and len(line) < 100:
                    # Found a summary section, get next few lines
                    for j in range(i+1, min(i+4, len(lines))):
                        next_line = lines[j]
                        if len(next_line) > 20 and not next_line.lower().startswith(('education', 'experience', 'skills')):
                            summary_content.append(next_line)
            
            if summary_content:
                summary = '. '.join(summary_content[:2])
                if len(summary) > 300:
                    summary = summary[:297] + "..."
                return summary
            
            # Fallback: analyze content for role and skills
            role_indicators = ['developer', 'engineer', 'manager', 'analyst', 'consultant', 'specialist', 'director']
            tech_indicators = ['python', 'java', 'react', 'aws', 'sql', 'javascript', 'project management']
            
            found_role = None
            found_skills = []
            
            for indicator in role_indicators:
                if indicator in content_lower:
                    found_role = indicator
                    break
            
            for tech in tech_indicators:
                if tech in content_lower:
                    found_skills.append(tech.upper() if len(tech) <= 4 else tech.title())
            
            # Build basic summary
            if found_role:
                summary = f"Experienced {found_role}"
                if found_skills:
                    skills_text = ", ".join(found_skills[:3])
                    summary += f" with expertise in {skills_text}"
                summary += ". Dedicated professional committed to delivering quality results."
                return summary
            
            return "Experienced professional with diverse skills and industry expertise. Committed to excellence and continuous learning."
            
        except Exception as e:
            logger.warning(f"Error extracting basic summary: {str(e)}")
            return "Professional profile with relevant experience and skills."
    
    async def _parse_search_query_with_ai(
        self, 
        query: str, 
        user_id: int, 
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Parse natural language search query with AI to extract search criteria"""
        try:
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not user_config or not user_config.openai_api_key:
                return None
            
            api_key = self.encryption_service.decrypt(user_config.openai_api_key)
            client = openai.OpenAI(api_key=api_key)
            
            prompt = f"""
            Parse this candidate search query and extract search criteria:
            
            Query: "{query}"
            
            Extract and return JSON with:
            1. "skills": Array of mentioned technical skills
            2. "min_experience": Minimum years of experience (integer or null)
            3. "max_experience": Maximum years of experience (integer or null)  
            4. "location": Location preference if mentioned
            5. "remote_preference": true/false/null if remote work is mentioned
            6. "availability_status": "available"/"employed"/null
            7. "search_term": General search terms for name/company/role
            8. "role_type": Job role/position type if mentioned
            
            Examples:
            - "Python developers with 5+ years experience" -> {{"skills": ["Python"], "min_experience": 5}}
            - "Senior React engineers in New York" -> {{"skills": ["React"], "location": "New York", "search_term": "senior engineer"}}
            
            Return only valid JSON.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a search query parser. Return only valid JSON."}, 
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.debug(f"Could not parse search query with AI: {str(e)}")
            return None
    
    async def _generate_search_suggestions(
        self, 
        criteria: Dict[str, Any], 
        results: List[CandidateResponse], 
        db: Session
    ) -> List[str]:
        """Generate suggestions to refine search based on results"""
        suggestions = []
        
        if len(results) == 0:
            suggestions.append("Try broadening your search criteria")
            suggestions.append("Remove experience requirements")
            suggestions.append("Try different skill keywords")
        elif len(results) > 20:
            suggestions.append("Add more specific skills to narrow results")
            suggestions.append("Specify experience level requirements")
            suggestions.append("Add location preferences")
        
        # Add skill-based suggestions
        if criteria.get('skills'):
            # Find related skills from the database
            related_skills = await self._get_related_skills(
                criteria['skills'], db
            )
            for skill in related_skills[:3]:
                suggestions.append(f"Also consider candidates with {skill}")
        
        return suggestions[:5]  # Limit suggestions
    
    async def _get_related_skills(self, skills: List[str], db: Session) -> List[str]:
        """Find skills commonly associated with the given skills"""
        # This is a simplified implementation
        # In a real system, you might use ML to find skill associations
        
        skill_associations = {
            'python': ['django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'javascript': ['react', 'node.js', 'typescript', 'vue.js', 'angular'],
            'react': ['redux', 'next.js', 'javascript', 'typescript', 'css'],
            'java': ['spring', 'hibernate', 'maven', 'junit', 'kotlin'],
            'aws': ['docker', 'kubernetes', 'terraform', 'jenkins', 'devops']
        }
        
        related = []
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in skill_associations:
                related.extend(skill_associations[skill_lower])
        
        return list(set(related))  # Remove duplicates
    
    async def regenerate_professional_summaries(self, db: Session) -> int:
        """Regenerate professional summaries for candidates with missing or poor summaries"""
        try:
            # Find candidates with missing or poor professional summaries
            candidates_needing_updates = db.query(Candidate).filter(
                or_(
                    Candidate.professional_summary.is_(None),
                    Candidate.professional_summary == '',
                    Candidate.professional_summary == 'Profile extracted from resume',
                    Candidate.professional_summary.like('Professional profile%'),
                    func.length(Candidate.professional_summary) < 50
                )
            ).all()
            
            logger.info(f"Found {len(candidates_needing_updates)} candidates needing summary updates")
            updated_count = 0
            
            for candidate in candidates_needing_updates:
                try:
                    logger.info(f"Regenerating summary for candidate: {candidate.name}")
                    
                    # Get the first user to use their OpenAI key (improve this later for multi-user)
                    user = db.query(User).first()
                    if not user:
                        logger.error("No users found for OpenAI key")
                        continue
                    
                    # Check if we have google drive file to re-parse
                    if candidate.google_drive_file_id:
                        # Download and parse CV again
                        cv_content = await self._download_and_parse_cv(
                            candidate.google_drive_file_id, user.id, db
                        )
                        
                        if cv_content:
                            # Try AI analysis for professional summary
                            candidate_profile = await self._analyze_cv_with_ai(cv_content, user.id, db)
                            
                            if candidate_profile and candidate_profile.get('professional_summary'):
                                candidate.professional_summary = candidate_profile['professional_summary']
                                logger.info(f"Updated summary via AI for {candidate.name}")
                            else:
                                # Use basic extraction
                                basic_summary = self._extract_basic_summary(cv_content, candidate.name)
                                candidate.professional_summary = basic_summary
                                logger.info(f"Updated summary via basic extraction for {candidate.name}")
                        else:
                            # Create summary from existing candidate data
                            fallback_summary = self._create_fallback_summary(
                                {
                                    'name': candidate.name,
                                    'current_role': candidate.current_role,
                                    'current_company': candidate.current_company,
                                    'experience_years': candidate.experience_years,
                                    'skills': candidate.skills_json or {}
                                },
                                ''
                            )
                            candidate.professional_summary = fallback_summary
                            logger.info(f"Updated summary via fallback for {candidate.name}")
                    else:
                        # No CV file, create from existing data
                        fallback_summary = self._create_fallback_summary(
                            {
                                'name': candidate.name,
                                'current_role': candidate.current_role,
                                'current_company': candidate.current_company,
                                'experience_years': candidate.experience_years,
                                'skills': candidate.skills_json or {}
                            },
                            ''
                        )
                        candidate.professional_summary = fallback_summary
                        logger.info(f"Updated summary from existing data for {candidate.name}")
                    
                    updated_count += 1
                    
                    # Commit every 5 updates to avoid large transactions
                    if updated_count % 5 == 0:
                        db.commit()
                        logger.info(f"Committed batch of 5 updates, total: {updated_count}")
                
                except Exception as e:
                    logger.error(f"Error updating summary for candidate {candidate.name}: {str(e)}")
                    db.rollback()
                    continue
            
            # Final commit
            db.commit()
            logger.info(f"Successfully regenerated summaries for {updated_count} candidates")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in regenerate_professional_summaries: {str(e)}")
            db.rollback()
            raise e
    
    def _candidate_to_response(
        self, 
        candidate: Candidate, 
        include_stats: bool = False, 
        db: Optional[Session] = None
    ) -> CandidateResponse:
        """Convert Candidate model to CandidateResponse schema"""
        match_count = 0
        avg_match_score = 0.0
        
        if include_stats and db:
            matches = db.query(JobMatch).filter(JobMatch.candidate_id == candidate.id).all()
            match_count = len(matches)
            if matches:
                avg_match_score = sum(match.match_score for match in matches) / len(matches)
        
        return CandidateResponse(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            cv_filename=candidate.cv_filename,
            skills_json=candidate.skills_json,
            experience_years=candidate.experience_years,
            education=candidate.education,
            certifications=candidate.certifications,
            professional_summary=candidate.professional_summary,
            current_role=candidate.current_role,
            current_company=candidate.current_company,
            preferred_locations=candidate.preferred_locations,
            remote_preference=candidate.remote_preference,
            availability_status=candidate.availability_status,
            salary_expectation=candidate.salary_expectation,
            google_drive_file_id=candidate.google_drive_file_id,
            last_updated=candidate.last_updated,
            created_at=candidate.created_at,
            match_count=match_count,
            avg_match_score=round(avg_match_score, 2)
        )