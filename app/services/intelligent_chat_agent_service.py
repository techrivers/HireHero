import openai
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import UserConfig, MatchLog, MatchResult, User
from app.services.optimized_cv_matching_service import OptimizedCVMatchingService
from app.services.google_drive_service import google_drive_service
from app.services.instant_response_helper import get_instant_processing_response
from app.utils.encryption import encryption_service
import json
import re
import time
from datetime import datetime
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import time

class IntelligentChatAgentService:
    def __init__(self):
        self.openai_client = None
        self.cv_matching_service = OptimizedCVMatchingService()
        self.conversation_contexts = {}  # Store conversation history per user
        self.cv_cache = {}  # Cache CV data for quick access
        self.cache_lock = threading.Lock()
        self.MATCH_THRESHOLD = 0.50  # 50% match threshold
        self.MAX_RESULTS = 6  # Return top 6 most relevant CVs only
        
    def get_openai_key(self, db: Session, user_id: int) -> str:
        """Get user's OpenAI API key."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config or not user_config.openai_api_key:
            return None
        return encryption_service.decrypt(user_config.openai_api_key)
    
    def initialize_openai_client(self, api_key: str):
        """Initialize OpenAI client."""
        try:
            import httpx
            http_client = httpx.Client(
                timeout=30.0,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=30.0
                ),
                follow_redirects=True
            )
            
            self.openai_client = openai.OpenAI(
                api_key=api_key,
                http_client=http_client
            )
            return True
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI client: {e}")
            return False
    
    def get_conversation_context(self, user_id: int) -> Dict[str, Any]:
        """Get or create conversation context for a user with enhanced context tracking."""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = {
                'messages': [],
                'current_search': None,
                'last_results': None,
                'user_preferences': {},
                'conversation_state': 'greeting',  # greeting, searching, refining, analyzing
                'extracted_criteria': {},
                'cv_summaries': [],
                'quick_filters': {},
                'search_history': [],
                'follow_up_context': None,
                'personalization_data': {
                    'common_roles': [],
                    'preferred_skills': [],
                    'typical_experience_range': None
                }
            }
        return self.conversation_contexts[user_id]
    
    def clear_conversation_context(self, user_id: int):
        """Clear conversation context for a user."""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
    
    async def get_cv_summaries_fast(self, user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get cached CV summaries quickly, return empty list if not cached."""
        with self.cache_lock:
            if user_id in self.cv_cache:
                print(f"📋 Using cached CV summaries for user {user_id}: {len(self.cv_cache[user_id])} CVs")
                return self.cv_cache[user_id]
        
        print(f"📋 No cached CV summaries found for user {user_id}")
        return []
    
    async def process_cvs_background(self, user_id: int, db: Session):
        """Process CVs in the background without blocking the chat."""
        try:
            print(f"🔄 Starting background CV processing for user {user_id}")
            # Call the full CV processing function
            cv_summaries = await self.get_cv_summaries(user_id, db)
            
            # Update the conversation context with the processed CVs
            if user_id in self.conversation_contexts:
                self.conversation_contexts[user_id]['cv_summaries'] = cv_summaries
            else:
                # Create context if it doesn't exist
                self.get_conversation_context(user_id)
                self.conversation_contexts[user_id]['cv_summaries'] = cv_summaries
            
            print(f"✅ Background CV processing completed for user {user_id}: {len(cv_summaries)} CVs")
        except Exception as e:
            print(f"❌ Error in background CV processing: {e}")
            import traceback
            traceback.print_exc()
    
    async def preload_user_cvs(self, user_id: int, db: Session) -> bool:
        """Preload CVs for a user when they first access the system."""
        try:
            print(f"🚀 Preloading CVs for user {user_id}")
            
            # Check if already cached
            with self.cache_lock:
                if user_id in self.cv_cache and self.cv_cache[user_id]:
                    print(f"📋 CVs already cached for user {user_id}")
                    return True
            
            # Start background processing
            asyncio.create_task(self.process_cvs_background(user_id, db))
            return True
            
        except Exception as e:
            print(f"❌ Error preloading CVs for user {user_id}: {e}")
            return False
    
    async def get_cv_summaries(self, user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get cached CV summaries or generate them."""
        with self.cache_lock:
            if user_id in self.cv_cache:
                print(f"📋 Using cached CV summaries for user {user_id}: {len(self.cv_cache[user_id])} CVs")
                return self.cv_cache[user_id]
        
        try:
            start_time = time.time()
            print(f"🔄 Fetching CV summaries for user {user_id}")
            # Get user's Google Drive service with validation
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not user_config:
                print(f"❌ No user config found for user {user_id}")
                return []
            
            if not user_config.google_drive_token:
                print(f"⚠️ No Google Drive token found for user {user_id}")
                return []
            
            # Initialize OpenAI client if not already initialized
            if not self.openai_client:
                api_key = self.get_openai_key(db, user_id)
                if api_key:
                    print(f"🤖 Initializing OpenAI client for user {user_id}")
                    if not self.initialize_openai_client(api_key):
                        print(f"❌ Failed to initialize OpenAI client for user {user_id}")
                        return []
                else:
                    print(f"❌ No OpenAI API key found for user {user_id}")
                    return []
            
            # Get CV files from Google Drive with error handling
            folder_name = user_config.cv_folder_name or "cvs"
            print(f"📁 Looking for CVs in Google Drive folder: {folder_name}")
            
            try:
                cv_files = google_drive_service.list_files_in_folder(db, user_id, folder_name)
                print(f"📄 Found {len(cv_files)} CV files in Google Drive")
                
                if not cv_files:
                    print(f"⚠️ No CV files found in folder '{folder_name}' for user {user_id}")
                    return []
                    
            except Exception as e:
                print(f"❌ Error accessing Google Drive for user {user_id}: {e}")
                return []
            
            # Process CVs and generate summaries using async concurrency
            cv_summaries = []
            semaphore = asyncio.Semaphore(2)  # Reduced concurrent processing to 2 CVs for stability
            
            async def process_single_cv(cv_file, index):
                async with semaphore:
                    try:
                        print(f"🔄 Processing CV {index+1}/{min(len(cv_files), 20)}: {cv_file['name']}")
                        # Download and parse CV
                        cv_content_bytes = google_drive_service.download_file(db, user_id, cv_file['id'])
                        if not cv_content_bytes:
                            print(f"❌ Failed to download CV: {cv_file['name']}")
                            return None
                        
                        # Convert bytes to string and parse CV content
                        cv_content = await self.parse_cv_content(cv_content_bytes, cv_file['name'])
                        if not cv_content:
                            print(f"❌ Failed to parse CV content: {cv_file['name']}")
                            return None
                        
                        print(f"📄 Parsed CV content length: {len(cv_content)} characters")
                        
                        # Generate AI summary
                        summary = await self.generate_cv_summary(cv_content, cv_file['name'])
                        print(f"🤖 Generated AI summary for: {cv_file['name']}")
                        
                        return {
                            'filename': cv_file['name'],
                            'file_id': cv_file['id'],
                            'summary': summary,
                            'skills': summary.get('skills', []),
                            'experience': summary.get('experience', 0),
                            'role': summary.get('role', 'Unknown')
                        }
                    except Exception as e:
                        print(f"❌ Error processing CV {cv_file['name']}: {e}")
                        import traceback
                        traceback.print_exc()
                        return None
            
            # Process CVs concurrently with extended timeout
            max_cvs = min(len(cv_files), 25)  # Process up to 25 CVs
            tasks = [process_single_cv(cv_file, i) for i, cv_file in enumerate(cv_files[:max_cvs])]
            try:
                results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=180.0)
                print(f"🔄 Processed {len([r for r in results if r is not None])} CVs successfully")
            except asyncio.TimeoutError:
                print("⏰ CV processing timed out after 3 minutes")
                results = []
            
            # Filter out None results and exceptions
            cv_summaries = [result for result in results if result is not None and not isinstance(result, Exception)]
            
            # Cache the results
            with self.cache_lock:
                self.cv_cache[user_id] = cv_summaries
            
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"✅ Successfully processed {len(cv_summaries)} CVs for user {user_id} in {processing_time:.2f}s")
            return cv_summaries
        except Exception as e:
            print(f"❌ Error getting CV summaries: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def parse_cv_content(self, cv_content_bytes: bytes, filename: str) -> str:
        """Parse CV content from bytes based on file type."""
        try:
            # Import necessary libraries for CV parsing
            import io
            import PyPDF2
            import docx
            import pdfplumber
            
            # Get file extension
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                # Parse PDF
                try:
                    with io.BytesIO(cv_content_bytes) as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() + "\n"
                        return text.strip()
                except Exception as e:
                    print(f"Error parsing PDF with PyPDF2: {e}")
                    # Fallback to pdfplumber
                    try:
                        with io.BytesIO(cv_content_bytes) as pdf_file:
                            with pdfplumber.open(pdf_file) as pdf:
                                text = ""
                                for page in pdf.pages:
                                    text += page.extract_text() + "\n"
                                return text.strip()
                    except Exception as e2:
                        print(f"Error parsing PDF with pdfplumber: {e2}")
                        return ""
            
            elif file_extension in ['doc', 'docx']:
                # Parse Word document
                try:
                    with io.BytesIO(cv_content_bytes) as doc_file:
                        doc = docx.Document(doc_file)
                        text = ""
                        for paragraph in doc.paragraphs:
                            text += paragraph.text + "\n"
                        return text.strip()
                except Exception as e:
                    print(f"Error parsing Word document: {e}")
                    return ""
            
            elif file_extension == 'txt':
                # Parse text file
                try:
                    return cv_content_bytes.decode('utf-8').strip()
                except Exception as e:
                    print(f"Error parsing text file: {e}")
                    return ""
            
            else:
                # Try to decode as text
                try:
                    return cv_content_bytes.decode('utf-8').strip()
                except Exception as e:
                    print(f"Error decoding file as text: {e}")
                    return ""
                    
        except Exception as e:
            print(f"Error parsing CV content for {filename}: {e}")
            return ""
    
    async def generate_cv_summary(self, cv_content: str, filename: str) -> Dict[str, Any]:
        """Generate AI summary of CV content."""
        try:
            # Compress content for efficiency
            compressed_content = cv_content[:3000] if len(cv_content) > 3000 else cv_content
            
            system_prompt = """Analyze this CV and provide a structured summary in JSON format:
            {
                "candidate_name": "full name",
                "role": "primary job role/title",
                "skills": ["skill1", "skill2", "skill3"],
                "experience": number_of_years,
                "education": "highest degree",
                "summary": "2-3 sentence professional summary",
                "strengths": ["strength1", "strength2"],
                "industries": ["industry1", "industry2"]
            }
            
            Focus on extracting key information that would be useful for job matching."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this CV:\n\nFilename: {filename}\n\nContent: {compressed_content}"}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.2,
                max_tokens=500
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error generating CV summary: {e}")
            return {
                "candidate_name": "Unknown",
                "role": "Unknown",
                "skills": [],
                "experience": 0,
                "summary": "Unable to process CV",
                "strengths": [],
                "industries": []
            }
    
    async def analyze_user_query(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user query with enhanced intent recognition and contextual awareness."""
        try:
            cv_summaries = context.get('cv_summaries', [])
            available_skills = list(set([skill for cv in cv_summaries for skill in cv.get('skills', [])]))
            available_roles = list(set([cv.get('role', '') for cv in cv_summaries]))
            
            # Enhanced context awareness
            conversation_history = context.get('messages', [])
            recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
            last_search_criteria = context.get('extracted_criteria', {})
            last_results = context.get('last_results', {})
            personalization_data = context.get('personalization_data', {})
            
            # Enhanced pattern recognition with more intelligent matching
            intelligent_patterns = {
                'senior developer': {'role': 'Senior Developer', 'skills': ['programming', 'development', 'coding'], 'experience_min': 5, 'seniority': 'senior'},
                'senior': {'experience_min': 5, 'seniority': 'senior'},
                'junior developer': {'role': 'Junior Developer', 'skills': ['programming', 'development'], 'experience_max': 2, 'seniority': 'junior'},
                'lead developer': {'role': 'Lead Developer', 'skills': ['programming', 'leadership', 'architecture'], 'experience_min': 7, 'seniority': 'lead'},
                'full stack developer': {'role': 'Full Stack Developer', 'skills': ['full stack', 'frontend', 'backend', 'javascript'], 'experience_min': 3},
                'frontend developer': {'role': 'Frontend Developer', 'skills': ['frontend', 'html', 'css', 'javascript', 'react'], 'experience_min': 2},
                'backend developer': {'role': 'Backend Developer', 'skills': ['backend', 'server', 'database', 'api'], 'experience_min': 2},
                'data scientist': {'role': 'Data Scientist', 'skills': ['machine learning', 'data analysis', 'python', 'statistics'], 'experience_min': 2},
                'machine learning engineer': {'role': 'ML Engineer', 'skills': ['machine learning', 'python', 'tensorflow', 'pytorch'], 'experience_min': 3},
                'devops engineer': {'role': 'DevOps Engineer', 'skills': ['devops', 'ci/cd', 'aws', 'docker', 'kubernetes'], 'experience_min': 2},
                'project manager': {'role': 'Project Manager', 'skills': ['project management', 'leadership', 'coordination', 'agile'], 'experience_min': 3},
                'product manager': {'role': 'Product Manager', 'skills': ['product management', 'strategy', 'roadmap', 'user experience'], 'experience_min': 3},
                'ui/ux designer': {'role': 'UI/UX Designer', 'skills': ['ui/ux', 'design', 'figma', 'user research'], 'experience_min': 2},
                'marketing manager': {'role': 'Marketing Manager', 'skills': ['marketing', 'digital marketing', 'campaign', 'analytics'], 'experience_min': 3},
                'sales manager': {'role': 'Sales Manager', 'skills': ['sales', 'business development', 'crm', 'negotiation'], 'experience_min': 3}
            }
            
            # Check for intelligent pattern matching
            detected_pattern = None
            message_lower = message.lower()
            
            # Exact phrase matching first
            for pattern, criteria in intelligent_patterns.items():
                if pattern in message_lower:
                    detected_pattern = criteria
                    break
            
            # If no exact match, check for keyword combinations
            if not detected_pattern:
                for keyword in ['python', 'javascript', 'react', 'node.js', 'aws', 'docker', 'kubernetes', 'machine learning', 'data analysis']:
                    if keyword in message_lower:
                        detected_pattern = {'skills': [keyword]}
                        break
            
            system_prompt = f"""You are a CV matching assistant. Analyze the user's message and respond with valid JSON only.

            Available CVs: {len(cv_summaries)}
            Available skills: {', '.join(available_skills[:15])}
            
            Pattern detected: {json.dumps(detected_pattern, indent=2) if detected_pattern else 'None'}
            
            Return ONLY valid JSON:
            {{
                "intent": "greeting|search_request|refine_search|show_alternatives|get_details|follow_up",
                "confidence": 0.8,
                "search_criteria": {{
                    "job_title": "role if mentioned",
                    "skills": ["skill1", "skill2"],
                    "experience_min": 2,
                    "seniority_level": "junior|mid|senior"
                }},
                "intelligent_suggestions": {{
                    "show_similar_profiles": true,
                    "suggest_alternatives": true
                }},
                "personalization": {{
                    "tone": "professional",
                    "user_intent_clarity": "clear"
                }}
            }}"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3,
                max_tokens=700
            )
            
            response_content = response.choices[0].message.content.strip()
            print(f"🤖 OpenAI response: {response_content}")
            
            # Try to parse JSON response
            try:
                return json.loads(response_content)
            except json.JSONDecodeError as je:
                print(f"❌ JSON parsing error: {je}")
                print(f"Raw response: {response_content}")
                # Return a fallback response for simple queries
                return self.create_fallback_analysis(user_message)
            
        except Exception as e:
            print(f"❌ Error analyzing query: {e}")
            import traceback
            traceback.print_exc()
            return self.create_fallback_analysis(message)
    
    def create_fallback_analysis(self, message: str) -> Dict[str, Any]:
        """Create a fallback analysis when OpenAI fails."""
        try:
            message_lower = message.lower()
            
            # Simple pattern matching for common queries
            fallback_patterns = {
                'product owner': {
                    'intent': 'search_request',
                    'search_criteria': {
                        'job_title': 'Product Owner',
                        'skills': ['product management', 'agile', 'scrum', 'requirements', 'user stories'],
                        'experience_min': 2,
                        'seniority_level': 'mid'
                    }
                },
                'product manager': {
                    'intent': 'search_request',
                    'search_criteria': {
                        'job_title': 'Product Manager',
                        'skills': ['product management', 'strategy', 'roadmap', 'user experience'],
                        'experience_min': 3,
                        'seniority_level': 'mid'
                    }
                },
                'developer': {
                    'intent': 'search_request',
                    'search_criteria': {
                        'job_title': 'Developer',
                        'skills': ['programming', 'development', 'coding'],
                        'experience_min': 1,
                        'seniority_level': 'mid'
                    }
                },
                'senior developer': {
                    'intent': 'search_request',
                    'search_criteria': {
                        'job_title': 'Senior Developer',
                        'skills': ['programming', 'development', 'coding', 'architecture'],
                        'experience_min': 5,
                        'seniority_level': 'senior'
                    }
                },
                'data scientist': {
                    'intent': 'search_request',
                    'search_criteria': {
                        'job_title': 'Data Scientist',
                        'skills': ['machine learning', 'data analysis', 'python', 'statistics'],
                        'experience_min': 2,
                        'seniority_level': 'mid'
                    }
                },
                'project manager': {
                    'intent': 'search_request',
                    'search_criteria': {
                        'job_title': 'Project Manager',
                        'skills': ['project management', 'leadership', 'coordination', 'agile'],
                        'experience_min': 3,
                        'seniority_level': 'mid'
                    }
                }
            }
            
            # Check for pattern matches
            for pattern, response in fallback_patterns.items():
                if pattern in message_lower:
                    print(f"🎯 Fallback pattern matched: {pattern}")
                    return {
                        "intent": response['intent'],
                        "confidence": 0.8,
                        "context_continuity": False,
                        "search_criteria": response['search_criteria'],
                        "intelligent_suggestions": {
                            "show_similar_profiles": True,
                            "suggest_alternatives": True,
                            "ask_clarifying_questions": False,
                            "provide_recommendations": True
                        },
                        "personalization": {
                            "tone": "professional",
                            "user_intent_clarity": "clear",
                            "follow_up_questions": []
                        }
                    }
            
            # Default fallback
            return {
                "intent": "search_request",
                "confidence": 0.5,
                "context_continuity": False,
                "search_criteria": {},
                "intelligent_suggestions": {},
                "personalization": {"tone": "professional", "user_intent_clarity": "needs_clarification", "follow_up_questions": []}
            }
            
        except Exception as e:
            print(f"❌ Error in fallback analysis: {e}")
            return {
                "intent": "search_request",
                "confidence": 0.5,
                "search_criteria": {},
                "intelligent_suggestions": {},
                "personalization": {"tone": "professional", "user_intent_clarity": "needs_clarification", "follow_up_questions": []}
            }
    
    async def search_relevant_cvs(self, criteria: Dict[str, Any], cv_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhanced CV search with 50% threshold and top 6 results focus."""
        try:
            print(f"🔍 Starting intelligent CV search with {len(cv_summaries)} CVs")
            
            # Enhanced filtering with must-have vs nice-to-have skills
            must_have_skills = criteria.get('must_have_skills', [])
            nice_to_have_skills = criteria.get('nice_to_have_skills', [])
            all_skills = criteria.get('skills', [])
            
            # If no specific must-have/nice-to-have distinction, treat first 3 skills as must-have
            if not must_have_skills and all_skills:
                must_have_skills = all_skills[:3]
                nice_to_have_skills = all_skills[3:]
            
            semaphore = asyncio.Semaphore(6)  # Process up to 6 CVs concurrently for efficiency
            
            async def evaluate_cv_match(cv):
                async with semaphore:
                    try:
                        # Calculate semantic match score
                        match_score = await self.calculate_semantic_match_score(criteria, cv)
                        
                        # Check for 100% exact keyword matches (must include rule)
                        exact_match_bonus = await self.check_exact_keyword_match(criteria, cv)
                        if exact_match_bonus:
                            match_score = max(match_score, 1.0)  # Boost to 100% if exact match
                        
                        # Apply 50% threshold rule
                        if match_score >= self.MATCH_THRESHOLD:
                            cv_copy = cv.copy()
                            cv_copy['match_score'] = match_score
                            cv_copy['match_reasons'] = await self.generate_intelligent_match_reasons(criteria, cv, exact_match_bonus)
                            cv_copy['role_fit'] = await self.assess_role_fit(criteria, cv)
                            cv_copy['improvement_areas'] = await self.identify_improvement_areas(criteria, cv)
                            return cv_copy
                        return None
                    except Exception as e:
                        print(f"Error evaluating CV {cv.get('filename', 'Unknown')}: {e}")
                        return None
            
            # Process all CVs concurrently
            tasks = [evaluate_cv_match(cv) for cv in cv_summaries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            relevant_cvs = [result for result in results if result is not None and not isinstance(result, Exception)]
            
            print(f"✅ Found {len(relevant_cvs)} CVs meeting 50% threshold")
            
            # Sort by match score (highest first)
            relevant_cvs.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Return top 6 most relevant CVs only
            return relevant_cvs[:self.MAX_RESULTS]
            
        except Exception as e:
            print(f"Error in intelligent CV search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def precision_filter_cvs(self, criteria: Dict[str, Any], cv_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pre-filter CVs based on exact criteria matching for precision mode."""
        filtered_cvs = []
        
        for cv in cv_summaries:
            matches = True
            
            # Check role match
            if criteria.get('role'):
                cv_role = cv.get('role', '').lower()
                criteria_role = criteria['role'].lower()
                if criteria_role not in cv_role and cv_role not in criteria_role:
                    matches = False
            
            # Check skills match (at least one skill must match)
            if criteria.get('skills') and matches:
                cv_skills = [skill.lower() for skill in cv.get('skills', [])]
                criteria_skills = [skill.lower() for skill in criteria['skills']]
                
                skill_match = any(skill in ' '.join(cv_skills) for skill in criteria_skills)
                if not skill_match:
                    matches = False
            
            # Check experience requirements
            if criteria.get('experience_min') and matches:
                cv_experience = cv.get('experience', 0)
                if cv_experience < criteria['experience_min']:
                    matches = False
            
            if matches:
                filtered_cvs.append(cv)
        
        return filtered_cvs
    
    async def calculate_semantic_match_score(self, criteria: Dict[str, Any], cv: Dict[str, Any]) -> float:
        """Calculate semantic match score with enhanced intelligence and 50% threshold awareness."""
        try:
            # Extract key information
            job_title = criteria.get('job_title', '')
            required_skills = criteria.get('skills', [])
            must_have_skills = criteria.get('must_have_skills', [])
            nice_to_have_skills = criteria.get('nice_to_have_skills', [])
            experience_min = criteria.get('experience_min', 0)
            seniority_level = criteria.get('seniority_level', '')
            
            cv_summary = cv.get('summary', {})
            cv_skills = cv.get('skills', [])
            cv_experience = cv.get('experience', 0)
            cv_role = cv.get('role', '')
            
            system_prompt = f"""You are an expert CV matching system. Calculate a precise semantic match score (0.0-1.0) between job criteria and CV.
            
            SCORING RULES:
            - Skills match (40%): Must-have skills are critical, nice-to-have adds bonus
            - Experience match (25%): Years of experience vs requirements
            - Role fit (20%): How well the candidate's role matches the job title
            - Seniority alignment (15%): Junior/Mid/Senior/Lead level matching
            
            IMPORTANT: Only return scores ≥ 0.5 if the candidate is genuinely suitable for the role.
            Scores < 0.5 indicate the candidate doesn't meet basic requirements.
            
            Job Requirements:
            - Title: {job_title}
            - Must-have skills: {must_have_skills}
            - Nice-to-have skills: {nice_to_have_skills}
            - All skills: {required_skills}
            - Min experience: {experience_min} years
            - Seniority: {seniority_level}
            
            Candidate Profile:
            - Role: {cv_role}
            - Skills: {cv_skills}
            - Experience: {cv_experience} years
            - Summary: {cv_summary.get('summary', '') if isinstance(cv_summary, dict) else ''}
            
            Respond with only a decimal number between 0.0 and 1.0"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Calculate the semantic match score for this candidate."}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.1,
                max_tokens=50
            )
            
            score_text = response.choices[0].message.content.strip()
            # Extract decimal number
            import re
            match = re.search(r'\b([0-1](?:\.\d+)?|1\.0)\b', score_text)
            if match:
                return float(match.group(1))
            return 0.0
            
        except Exception as e:
            print(f"Error calculating semantic match score: {e}")
            return 0.0
    
    async def check_exact_keyword_match(self, criteria: Dict[str, Any], cv: Dict[str, Any]) -> bool:
        """Check for 100% exact keyword matches that must be included."""
        try:
            # Get all text from CV for keyword matching
            cv_text_parts = [
                cv.get('role', '').lower(),
                ' '.join(cv.get('skills', [])).lower(),
                cv.get('summary', {}).get('summary', '').lower() if isinstance(cv.get('summary'), dict) else '',
                ' '.join(cv.get('summary', {}).get('strengths', [])).lower() if isinstance(cv.get('summary'), dict) else ''
            ]
            cv_full_text = ' '.join(cv_text_parts)
            
            # Check for exact matches in job title
            job_title = criteria.get('job_title', '').lower()
            if job_title and job_title in cv_full_text:
                return True
            
            # Check for exact skill matches
            must_have_skills = criteria.get('must_have_skills', [])
            all_skills = criteria.get('skills', [])
            critical_skills = must_have_skills or all_skills[:3]  # First 3 skills if no must-have specified
            
            for skill in critical_skills:
                if skill.lower() in cv_full_text:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking exact keyword match: {e}")
            return False
    
    async def generate_intelligent_match_reasons(self, criteria: Dict[str, Any], cv: Dict[str, Any], exact_match: bool = False) -> List[str]:
        """Generate intelligent match reasons with contextual awareness."""
        try:
            job_title = criteria.get('job_title', '')
            skills = criteria.get('skills', [])
            experience_min = criteria.get('experience_min', 0)
            
            cv_summary = cv.get('summary', {})
            cv_skills = cv.get('skills', [])
            cv_experience = cv.get('experience', 0)
            cv_role = cv.get('role', '')
            
            system_prompt = f"""Generate 2-3 specific, intelligent reasons why this candidate matches the job requirements.
            
            Job Requirements:
            - Title: {job_title}
            - Skills: {skills}
            - Min Experience: {experience_min} years
            
            Candidate:
            - Role: {cv_role}
            - Skills: {cv_skills}
            - Experience: {cv_experience} years
            - {'EXACT KEYWORD MATCH DETECTED' if exact_match else ''}
            
            Focus on:
            1. Specific skill alignments
            2. Experience level appropriateness
            3. Role compatibility
            4. Any standout qualifications
            
            Return as JSON array of strings. Be specific and helpful."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the match reasons."}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.4,
                max_tokens=250
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error generating intelligent match reasons: {e}")
            return ["Strong skill alignment", "Appropriate experience level", "Good role fit"]
    
    async def assess_role_fit(self, criteria: Dict[str, Any], cv: Dict[str, Any]) -> str:
        """Assess how well the candidate fits the role."""
        try:
            experience_min = criteria.get('experience_min', 0)
            cv_experience = cv.get('experience', 0)
            job_title = criteria.get('job_title', '')
            cv_role = cv.get('role', '')
            
            if cv_experience >= experience_min and job_title.lower() in cv_role.lower():
                return "Excellent fit"
            elif cv_experience >= experience_min:
                return "Good fit with transferable skills"
            elif cv_experience >= experience_min * 0.8:
                return "Close match with growth potential"
            else:
                return "Potential fit with training"
                
        except Exception as e:
            print(f"Error assessing role fit: {e}")
            return "Good potential"
    
    async def identify_improvement_areas(self, criteria: Dict[str, Any], cv: Dict[str, Any]) -> List[str]:
        """Identify areas where the candidate could improve or grow."""
        try:
            required_skills = set(skill.lower() for skill in criteria.get('skills', []))
            cv_skills = set(skill.lower() for skill in cv.get('skills', []))
            
            missing_skills = required_skills - cv_skills
            
            improvements = []
            
            # Check for missing skills
            if missing_skills:
                improvements.append(f"Could benefit from {', '.join(list(missing_skills)[:2])} skills")
            
            # Check experience gap
            experience_min = criteria.get('experience_min', 0)
            cv_experience = cv.get('experience', 0)
            
            if cv_experience < experience_min:
                gap = experience_min - cv_experience
                improvements.append(f"Could gain {gap} more years of experience")
            
            # Add generic improvement if no specific ones found
            if not improvements:
                improvements.append("Strong candidate with continuous learning mindset")
                
            return improvements[:2]  # Return top 2 improvement areas
            
        except Exception as e:
            print(f"Error identifying improvement areas: {e}")
            return ["Opportunity for continued growth"]
    
    def construct_search_query(self, criteria: Dict[str, Any]) -> str:
        """Construct a natural language search query from criteria."""
        parts = []
        
        if criteria.get('role'):
            parts.append(f"Looking for {criteria['role']}")
        
        if criteria.get('skills'):
            skills = criteria['skills'] if isinstance(criteria['skills'], list) else [criteria['skills']]
            parts.append(f"with skills in {', '.join(skills)}")
        
        if criteria.get('experience_min'):
            parts.append(f"with {criteria['experience_min']}+ years of experience")
        
        if criteria.get('industry'):
            parts.append(f"in {criteria['industry']} industry")
        
        if not parts:
            return "Find qualified candidates"
        
        return ' '.join(parts)
    
    async def format_smart_search_results(self, criteria: Dict[str, Any], search_results: Dict[str, Any], is_quick_selection: bool = False) -> str:
        """Format smart search results with enhanced intelligence."""
        try:
            results = search_results['results']
            criteria_text = self.format_criteria(criteria)
            top_matches = results[:3]
            
            # Different messaging based on search type
            if is_quick_selection:
                message = f"""🎯 **Smart Analysis Complete!** Found {len(results)} qualified candidates:

**Search:** {criteria_text}
**Processed:** {search_results['total_processed']} CVs in {search_results['processing_time']}

**Top Matches:**
"""
            else:
                message = f"""🤖 **Intelligent CV Analysis Complete!** 

**Query:** {criteria_text}
**Results:** {len(results)} candidates with 50%+ match from {search_results['total_processed']} CVs
**Processing:** {search_results['processing_time']}

**Top Candidates:**
"""
            
            for i, candidate in enumerate(top_matches, 1):
                match_score = int(candidate.get('match_score', 0) * 100)
                reasons = candidate.get('match_reasons', [])
                
                # Get candidate name from summary or fallback
                candidate_name = 'Unknown'
                summary = candidate.get('summary', {})
                if isinstance(summary, dict) and summary.get('candidate_name'):
                    candidate_name = summary['candidate_name']
                elif candidate.get('candidate_name'):
                    candidate_name = candidate['candidate_name']
                
                message += f"""
**{i}. {candidate_name}** 🏆 {match_score}% match
• **Experience:** {candidate.get('experience', 0)} years
• **Key Skills:** {', '.join(candidate.get('skills', [])[:4])}
• **Why perfect fit:** {', '.join(reasons[:2]) if reasons else 'Strong overall alignment'}
"""
            
            if len(results) > 3:
                message += f"\n💡 **Plus {len(results) - 3} more qualified candidates** ready for review!"
            
            return message
            
        except Exception as e:
            print(f"Error formatting smart search results: {e}")
            return "Found matching candidates with enhanced AI analysis."
    
    async def generate_intelligent_response(self, query_analysis: Dict[str, Any], context: Dict[str, Any], user_message: str, db: Session = None, user_id: int = None) -> Dict[str, Any]:
        """Generate intelligent contextual response with enhanced conversation awareness."""
        intent = query_analysis.get('intent', 'search_request')
        search_criteria = query_analysis.get('search_criteria', {})
        specific_requests = query_analysis.get('specific_requests', {})
        tone = query_analysis.get('response_tone', 'professional')
        context_continuity = query_analysis.get('context_continuity', False)
        
        response_data = {
            'message': '',
            'action': 'continue',
            'suggestions': [],
            'results': None,
            'quick_actions': []
        }
        
        # Get CV summaries
        cv_summaries = context.get('cv_summaries', [])
        
        # Handle context continuity for follow-up questions
        if context_continuity and context.get('extracted_criteria'):
            # Merge with previous criteria while preserving new specific requirements
            previous_criteria = context.get('extracted_criteria', {})
            search_criteria = {**previous_criteria, **search_criteria}
            print(f"🔄 Context continuity: merging criteria {previous_criteria} with {search_criteria}")
        
        if intent == 'greeting':
            cv_count = len(cv_summaries)
            if cv_count > 0:
                response_data['message'] = f"""👋 Hello! I'm your intelligent CV matching assistant with {cv_count} CVs ready for analysis.

I can:
• 🔍 Search for candidates based on skills, experience, and roles
• 📊 Provide detailed candidate summaries and match analysis
• 🎯 Suggest similar profiles and alternatives
• 💡 Give personalized recommendations

What kind of candidate are you looking for today?"""
            else:
                response_data['message'] = """👋 Hello! I'm your intelligent CV matching assistant.

🔄 **I'm currently analyzing your CVs from Google Drive...**
This usually takes about 30-60 seconds for the first time.

In the meantime, tell me what kind of candidate you're looking for and I'll search as soon as the analysis is complete!

What kind of candidate are you looking for today?"""
            
            response_data['suggestions'] = [
                "Find me a senior developer",
                "Looking for marketing professionals",
                "Show me data scientists",
                "Need project managers"
            ]
            
        elif intent == 'search_request' or intent == 'quick_selection':
            if not search_criteria:
                response_data['message'] = "I'd love to help you find the right candidates! Could you tell me more about what you're looking for? For example, specific skills, experience level, or job role?"
                response_data['suggestions'] = [
                    "Senior Python developer with 5+ years",
                    "Marketing manager with digital experience",
                    "Data scientist with machine learning skills"
                ]
            elif len(cv_summaries) == 0:
                # CVs not yet processed
                response_data['message'] = f"""🔄 **I'm processing your CVs from Google Drive...** 

**Your search criteria:** {self.format_criteria(search_criteria)}

I'll search for candidates matching these requirements as soon as the CV analysis is complete (usually takes 30-60 seconds for the first time).

**In the meantime, would you like to:**
• Refine your search criteria
• Add more specific requirements
• Wait for the processing to complete"""
                
                response_data['suggestions'] = [
                    "Add more specific skills",
                    "Specify experience level", 
                    "Tell me about the role requirements",
                    "I'll wait for processing to complete"
                ]
                
                # Store the search criteria for later use
                context['extracted_criteria'] = {**context.get('extracted_criteria', {}), **search_criteria}
                
            else:
                # Use the smart CV search with existing matching API
                try:
                    # Construct search query from criteria
                    search_query = self.construct_search_query(search_criteria)
                    print(f"🔍 Smart search query: {search_query}")
                    
                    # Get user ID for database access
                    # This should be passed from the calling function
                    search_results = await self.smart_cv_search_with_matching_api(search_query, db, user_id)
                    
                    if search_results['results']:
                        # Generate contextual response
                        response_data['message'] = await self.format_smart_search_results(search_criteria, search_results, intent == 'quick_selection')
                        response_data['action'] = 'show_results'
                        
                        # Format results as dictionary for ChatMessageResponse schema
                        formatted_results = {
                            'total_cvs_processed': search_results['total_processed'],
                            'processing_time': search_results['processing_time'],
                            'matches': []
                        }
                        
                        for cv in search_results['results']:
                            summary = cv.get('summary', {})
                            match_data = {
                                'cv_filename': cv.get('filename', 'Unknown'),
                                'candidate_name': summary.get('candidate_name', 'Unknown') if isinstance(summary, dict) else cv.get('candidate_name', 'Unknown'),
                                'relevance_score': cv.get('match_score', 0) * 100,
                                'candidate_summary': summary.get('summary', 'No summary available') if isinstance(summary, dict) else 'Professional candidate',
                                'key_skills': json.dumps(cv.get('skills', [])),
                                'match_analysis': '\n'.join(cv.get('match_reasons', [])),
                                'download_url': f"#download-{cv.get('file_id', '')}",
                                'google_drive_file_id': cv.get('file_id', ''),
                                'experience_years': cv.get('experience', 0)
                            }
                            formatted_results['matches'].append(match_data)
                        
                        response_data['results'] = formatted_results
                        response_data['suggestions'] = [
                            "Show me more details about the top candidate",
                            "Find similar profiles",
                            "Search for different skills",
                            "Show candidates with more experience"
                        ]
                    else:
                        # No matches found
                        if intent == 'quick_selection':
                            response_data['message'] = f"""🎯 I analyzed your CV database for **{self.format_criteria(search_criteria)}** but didn't find candidates meeting the 50% match threshold.

**What I searched for:**
{self.format_criteria(search_criteria)}

**Suggestions:**
• Try broader skill requirements
• Consider candidates with transferable skills
• Look for junior candidates with growth potential

Would you like me to search with different criteria?"""
                        else:
                            response_data['message'] = f"""🔍 I analyzed {search_results['total_processed']} CVs but didn't find candidates with 50%+ match for your criteria.

**Your search:** {self.format_criteria(search_criteria)}

**Suggestions:**
• Try broader skill requirements
• Consider different experience levels
• Look for related technologies or roles

Would you like me to adjust the search criteria?"""
                        
                        response_data['suggestions'] = [
                            "Search for junior candidates",
                            "Try broader skill requirements",
                            "Look for related technologies"
                        ]
                        
                except Exception as e:
                    print(f"❌ Smart search error: {e}")
                    response_data['message'] = "I encountered an issue while searching your CVs. Please ensure your Google Drive and OpenAI are properly configured."
                    response_data['suggestions'] = [
                        "Check your configuration",
                        "Try a simpler search",
                        "Refresh and try again"
                    ]
        
        elif intent == 'show_alternatives':
            if context.get('last_results'):
                alternatives = await self.find_similar_profiles(context['last_results'], cv_summaries)
                response_data['message'] = await self.format_alternatives(alternatives)
                
                # Format alternatives as dictionary for ChatMessageResponse schema
                formatted_alternatives = {
                    'total_cvs_processed': len(cv_summaries),
                    'processing_time': '< 1 second',
                    'matches': []
                }
                
                for cv in alternatives:
                    summary = cv.get('summary', {})
                    match_data = {
                        'cv_filename': cv.get('filename', 'Unknown'),
                        'candidate_name': summary.get('candidate_name', 'Unknown') if isinstance(summary, dict) else 'Unknown',
                        'relevance_score': cv.get('similarity_score', 0) * 100,
                        'candidate_summary': summary.get('summary', 'No summary available') if isinstance(summary, dict) else 'No summary available',
                        'key_skills': json.dumps(cv.get('skills', [])),
                        'match_analysis': f"Similar profile with {cv.get('similarity_score', 0)*100:.0f}% similarity",
                        'download_url': f"#download-{cv.get('file_id', '')}"
                    }
                    formatted_alternatives['matches'].append(match_data)
                
                response_data['results'] = formatted_alternatives
            else:
                response_data['message'] = "I don't have any previous results to show alternatives for. Would you like to start a new search?"
        
        elif intent == 'get_details':
            candidate_name = specific_requests.get('get_candidate_details')
            if candidate_name:
                details = await self.get_candidate_details(candidate_name, cv_summaries)
                response_data['message'] = await self.format_candidate_details(details)
            else:
                response_data['message'] = "Which candidate would you like to know more about?"
        
        elif intent == 'refine_search':
            if context.get('last_results'):
                # Merge new criteria with previous
                merged_criteria = {**context.get('extracted_criteria', {}), **search_criteria}
                refined_results = await self.search_relevant_cvs(merged_criteria, cv_summaries)
                response_data['message'] = await self.format_refined_results(refined_results)
                
                # Format refined results as dictionary for ChatMessageResponse schema
                formatted_refined = {
                    'total_cvs_processed': len(cv_summaries),
                    'processing_time': '< 1 second',
                    'matches': []
                }
                
                for cv in refined_results:
                    summary = cv.get('summary', {})
                    match_data = {
                        'cv_filename': cv.get('filename', 'Unknown'),
                        'candidate_name': summary.get('candidate_name', 'Unknown') if isinstance(summary, dict) else 'Unknown',
                        'relevance_score': cv.get('match_score', 0) * 100,
                        'candidate_summary': summary.get('summary', 'No summary available') if isinstance(summary, dict) else 'No summary available',
                        'key_skills': json.dumps(cv.get('skills', [])),
                        'match_analysis': '\n'.join(cv.get('match_reasons', [])),
                        'download_url': f"#download-{cv.get('file_id', '')}"
                    }
                    formatted_refined['matches'].append(match_data)
                
                response_data['results'] = formatted_refined
            else:
                response_data['message'] = "I don't have previous search results to refine. Let's start a new search!"
        
        else:
            # General conversation
            response_data['message'] = await self.generate_conversational_response(user_message, context)
        
        # Update context
        context['last_results'] = response_data.get('results')
        context['extracted_criteria'] = {**context.get('extracted_criteria', {}), **search_criteria}
        
        return response_data
    
    async def format_search_results(self, criteria: Dict[str, Any], results: List[Dict[str, Any]], is_quick_selection: bool = False) -> str:
        """Format search results in a conversational way with context awareness."""
        try:
            criteria_text = self.format_criteria(criteria)
            top_matches = results[:3]
            
            # Different messaging for quick selections vs general searches
            if is_quick_selection:
                message = f"""🎯 **Perfect! Found {len(results)} candidates matching your selection:**

**Selected criteria:** {criteria_text}

**Top Matches:**
"""
            else:
                message = f"""🎯 **Found {len(results)} matching candidates!**

**Your search:** {criteria_text}

**Top Matches:**
"""
            
            for i, candidate in enumerate(top_matches, 1):
                match_score = int(candidate.get('match_score', 0) * 100)
                reasons = candidate.get('match_reasons', [])
                summary = candidate.get('summary', {})
                
                # Get candidate name from summary if available
                candidate_name = 'Unknown'
                if isinstance(summary, dict) and summary.get('candidate_name'):
                    candidate_name = summary['candidate_name']
                elif candidate.get('candidate_name'):
                    candidate_name = candidate['candidate_name']
                
                message += f"""
**{i}. {candidate_name}** ({match_score}% match)
• **Role:** {candidate.get('role', 'Unknown')}
• **Experience:** {candidate.get('experience', 0)} years
• **Key Skills:** {', '.join(candidate.get('skills', [])[:3])}
• **Why it's a good fit:** {', '.join(reasons[:2])}
"""
            
            if len(results) > 3:
                message += f"\n💡 **{len(results) - 3} more candidates** available. Would you like to see them?"
            
            return message
            
        except Exception as e:
            print(f"Error formatting search results: {e}")
            return "Found matching candidates, but there was an error formatting the results."
    
    def format_criteria(self, criteria: Dict[str, Any]) -> str:
        """Format search criteria in a readable way."""
        parts = []
        
        if criteria.get('role'):
            parts.append(f"**Role:** {criteria['role']}")
        
        if criteria.get('skills'):
            skills = criteria['skills']
            if isinstance(skills, list):
                parts.append(f"**Skills:** {', '.join(skills)}")
            else:
                parts.append(f"**Skills:** {skills}")
        
        if criteria.get('experience_min'):
            parts.append(f"**Experience:** {criteria['experience_min']}+ years")
        
        if criteria.get('industry'):
            parts.append(f"**Industry:** {criteria['industry']}")
        
        if criteria.get('location'):
            parts.append(f"**Location:** {criteria['location']}")
        
        return ' | '.join(parts) if parts else "General search"
    
    async def smart_cv_search_with_matching_api(self, user_query: str, db: Session, user_id: int) -> Dict[str, Any]:
        """Enhanced CV search using the existing optimized matching API logic."""
        try:
            print(f"🤖 Starting smart CV search for query: {user_query}")
            
            # Use the optimized CV matching service for real CV analysis
            matching_service = self.cv_matching_service
            
            # Process the user query as a job description
            search_results = matching_service.process_optimized_cv_matching(
                db=db,
                user_id=user_id,
                job_description=user_query
            )
            
            # Convert to chat-friendly format with enhanced scoring
            if search_results.get('results'):
                enhanced_results = []
                for result in search_results['results']:
                    # Implement smart scoring rules
                    enhanced_score = await self.calculate_enhanced_score(result, user_query)
                    
                    # Only include results with 50% or higher match
                    if enhanced_score >= 50:
                        enhanced_result = {
                            'filename': result['cv_filename'],
                            'candidate_name': result['candidate_name'],
                            'summary': {
                                'candidate_name': result['candidate_name'],
                                'summary': result['candidate_summary']
                            },
                            'skills': result.get('key_skills', []),
                            'experience': result.get('experience_years', 0),
                            'role': 'Professional',  # Default role
                            'match_score': enhanced_score / 100,  # Convert to decimal
                            'match_reasons': self.extract_match_reasons(result.get('match_analysis', '')),
                            'file_id': result.get('google_drive_file_id', '')
                        }
                        enhanced_results.append(enhanced_result)
                
                # Sort by enhanced score
                enhanced_results.sort(key=lambda x: x['match_score'], reverse=True)
                print(f"✅ Smart search found {len(enhanced_results)} qualified candidates")
                return {
                    'results': enhanced_results,
                    'total_processed': search_results.get('total_cvs_processed', 0),
                    'processing_time': search_results.get('enhanced_summary', {}).get('processing_time', '< 1s')
                }
            
            return {'results': [], 'total_processed': 0, 'processing_time': '< 1s'}
            
        except Exception as e:
            print(f"❌ Error in smart CV search: {e}")
            import traceback
            traceback.print_exc()
            return {'results': [], 'total_processed': 0, 'processing_time': '< 1s'}
    
    async def calculate_enhanced_score(self, result: Dict[str, Any], user_query: str) -> float:
        """Calculate enhanced score with 50% threshold and 100% exact match logic."""
        base_score = result.get('relevance_score', 0)
        
        # Check for exact keyword matches (100% score rule)
        query_lower = user_query.lower()
        cv_text = f"{result.get('candidate_summary', '')} {result.get('match_analysis', '')}".lower()
        
        # Extract key terms from query
        key_terms = self.extract_key_terms(query_lower)
        
        # Check for exact matches
        exact_matches = 0
        for term in key_terms:
            if term in cv_text:
                exact_matches += 1
        
        # If significant exact matches found, boost to 100%
        if len(key_terms) > 0 and (exact_matches / len(key_terms)) >= 0.7:
            return 100.0
        
        # Apply smart enhancements to base score
        enhanced_score = base_score
        
        # Boost for senior roles if mentioned
        if any(term in query_lower for term in ['senior', 'lead', 'principal', 'expert']):
            if result.get('experience_years', 0) >= 5:
                enhanced_score *= 1.2
        
        # Boost for specific technologies
        tech_keywords = ['python', 'javascript', 'react', 'node', 'aws', 'docker', 'kubernetes']
        for tech in tech_keywords:
            if tech in query_lower and tech in cv_text:
                enhanced_score *= 1.1
        
        return min(100.0, enhanced_score)
    
    def extract_key_terms(self, query: str) -> List[str]:
        """Extract important terms from user query."""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'need', 'want', 'looking', 'find'}
        
        # Split into words and filter
        words = query.split()
        key_terms = [word.strip('.,!?()[]{}\"') for word in words if len(word) > 2 and word.lower() not in stop_words]
        
        return key_terms
    
    def extract_match_reasons(self, match_analysis: str) -> List[str]:
        """Extract match reasons from analysis text."""
        if not match_analysis:
            return ['Good overall match']
        
        # Split by common delimiters
        reasons = []
        for delimiter in ['|', '\n', ';']:
            if delimiter in match_analysis:
                parts = match_analysis.split(delimiter)
                for part in parts:
                    cleaned = part.strip()
                    if len(cleaned) > 10:
                        reasons.append(cleaned[:100])  # Limit length
                break
        
        if not reasons:
            reasons = [match_analysis[:100] if len(match_analysis) > 100 else match_analysis]
        
        return reasons[:3]  # Return top 3 reasons
    
    async def find_similar_profiles(self, current_results: List[Dict[str, Any]], all_cvs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find similar profiles to current results with async optimization."""
        if not current_results:
            return []
        
        print(f"🔄 Finding similar profiles from {len(all_cvs)} CVs")
        
        # Get skills from top matches
        top_skills = []
        for result in current_results[:2]:
            top_skills.extend(result.get('skills', []))
        
        # Use async processing for similarity calculation
        async def calculate_similarity(cv):
            try:
                if cv.get('filename') in [r.get('filename') for r in current_results]:
                    return None  # Skip already shown results
                
                # Calculate similarity based on skills overlap
                cv_skills = set(cv.get('skills', []))
                target_skills = set(top_skills)
                
                if cv_skills & target_skills:  # If there's any overlap
                    overlap_ratio = len(cv_skills & target_skills) / len(cv_skills | target_skills)
                    if overlap_ratio > 0.2:  # 20% skill overlap
                        cv_copy = cv.copy()
                        cv_copy['similarity_score'] = overlap_ratio
                        return cv_copy
                return None
            except Exception as e:
                print(f"Error calculating similarity for CV {cv.get('filename', 'Unknown')}: {e}")
                return None
        
        # Process similarity calculations concurrently
        tasks = [calculate_similarity(cv) for cv in all_cvs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        similar_cvs = [result for result in results if result is not None and not isinstance(result, Exception)]
        
        print(f"✅ Found {len(similar_cvs)} similar profiles")
        
        # Sort by similarity and return top 5
        similar_cvs.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar_cvs[:5]
    
    async def format_alternatives(self, alternatives: List[Dict[str, Any]]) -> str:
        """Format alternative candidates."""
        if not alternatives:
            return "No similar profiles found in your database."
        
        message = f"🔄 **Found {len(alternatives)} similar profiles you might also consider:**\n"
        
        for i, candidate in enumerate(alternatives, 1):
            similarity = int(candidate.get('similarity_score', 0) * 100)
            message += f"""
**{i}. {candidate.get('candidate_name', 'Unknown')}** ({similarity}% similar)
• **Role:** {candidate.get('role', 'Unknown')}
• **Experience:** {candidate.get('experience', 0)} years
• **Key Skills:** {', '.join(candidate.get('skills', [])[:3])}
"""
        
        return message
    
    async def get_candidate_details(self, candidate_name: str, cv_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get detailed information about a specific candidate."""
        for cv in cv_summaries:
            if candidate_name.lower() in cv.get('candidate_name', '').lower() or candidate_name.lower() in cv.get('filename', '').lower():
                return cv
        return {}
    
    async def format_candidate_details(self, details: Dict[str, Any]) -> str:
        """Format detailed candidate information."""
        if not details:
            return "Sorry, I couldn't find that candidate in the database."
        
        message = f"""📋 **Detailed Profile: {details.get('candidate_name', 'Unknown')}**

**🎯 Role:** {details.get('role', 'Unknown')}
**📅 Experience:** {details.get('experience', 0)} years
**🎓 Education:** {details.get('education', 'Not specified')}

**💼 Professional Summary:**
{details.get('summary', 'No summary available')}

**🛠️ Technical Skills:**
{', '.join(details.get('skills', []))}

**💪 Key Strengths:**
{', '.join(details.get('strengths', []))}

**🏢 Industries:**
{', '.join(details.get('industries', []))}

**📄 CV File:** {details.get('filename', 'Unknown')}
"""
        
        return message
    
    async def generate_conversational_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate a conversational response for general queries."""
        return await self.generate_intelligent_conversational_response(message, context)
    
    async def process_chat_message(self, user_id: int, message: str, db: Session) -> Dict[str, Any]:
        """Process a chat message and return intelligent response with enhanced context management."""
        try:
            # Get OpenAI key and initialize client
            api_key = self.get_openai_key(db, user_id)
            openai_available = False
            
            if api_key:
                if not self.openai_client:
                    if self.initialize_openai_client(api_key):
                        openai_available = True
                    else:
                        print("❌ Failed to initialize OpenAI client, using fallback mode")
                else:
                    openai_available = True
            else:
                print("⚠️ No OpenAI API key found, using fallback mode")
            
            # Get conversation context
            context = self.get_conversation_context(user_id)
            
            # Check CV processing status and provide instant feedback
            cv_summaries = await self.get_cv_summaries_fast(user_id, db)
            context['cv_summaries'] = cv_summaries
            
            # If no CVs cached, provide instant response and start background processing
            if not cv_summaries:
                print("🔄 No cached CVs, providing instant response...")
                
                # Start background processing immediately (don't wait)
                asyncio.create_task(self.process_cvs_background(user_id, db))
                
                # Return instant response for better UX
                return get_instant_processing_response(message, user_id)
            
            # Enhanced context management - track conversation flow
            previous_message = context['messages'][-1] if context['messages'] else None
            
            # Add user message to context with enhanced metadata
            context['messages'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat(),
                'message_type': await self.classify_message_type(message, context)
            })
            
            # Analyze user query with enhanced context awareness
            if openai_available:
                query_analysis = await self.analyze_user_query(message, context)
            else:
                print("🔄 Using fallback analysis due to OpenAI unavailability")
                query_analysis = self.create_fallback_analysis(message)
            
            # Update conversation state based on query analysis
            self.update_conversation_state(context, query_analysis)
            
            # Generate intelligent response
            response_data = await self.generate_intelligent_response(query_analysis, context, message, db, user_id)
            
            # Add AI response to context with enhanced metadata
            context['messages'].append({
                'role': 'assistant',
                'content': response_data['message'],
                'timestamp': datetime.now().isoformat(),
                'action': response_data['action'],
                'results_count': len(response_data.get('results', {}).get('matches', [])) if response_data.get('results') else 0
            })
            
            # Clean up old messages to prevent context bloat (keep last 10 messages)
            if len(context['messages']) > 10:
                context['messages'] = context['messages'][-10:]
            
            return response_data
            
        except Exception as e:
            print(f"❌ Error processing chat message: {e}")
            import traceback
            traceback.print_exc()
            return {
                'message': "I apologize, but I encountered an error processing your message. Please try again.",
                'action': 'continue',
                'suggestions': ["Try asking about candidates", "Search for specific skills", "Ask for help"]
            }
    
    def get_conversation_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        context = self.get_conversation_context(user_id)
        return context.get('messages', [])
    
    async def classify_message_type(self, message: str, context: Dict[str, Any]) -> str:
        """Classify the type of message for better context management."""
        message_lower = message.lower()
        
        # Check if it's a follow-up question
        follow_up_indicators = ['also', 'what about', 'can you', 'show me more', 'tell me about', 'how about']
        if any(indicator in message_lower for indicator in follow_up_indicators):
            return 'follow_up'
        
        # Check if it's a refinement
        refinement_indicators = ['but', 'however', 'instead', 'actually', 'rather', 'more specific']
        if any(indicator in message_lower for indicator in refinement_indicators):
            return 'refinement'
        
        # Check if it's a quick selection
        quick_patterns = ['senior developer', 'marketing', 'data scientist', 'project manager', 'python', 'javascript']
        if any(pattern in message_lower for pattern in quick_patterns):
            return 'quick_selection'
        
        return 'new_query'
    
    def update_conversation_state(self, context: Dict[str, Any], query_analysis: Dict[str, Any]):
        """Update conversation state based on query analysis."""
        intent = query_analysis.get('intent', 'search_request')
        
        if intent == 'search_request' or intent == 'quick_selection':
            context['conversation_state'] = 'searching'
        elif intent == 'refine_search':
            context['conversation_state'] = 'refining'
        elif intent == 'show_alternatives':
            context['conversation_state'] = 'exploring'
        elif intent == 'get_details':
            context['conversation_state'] = 'analyzing'
        else:
            context['conversation_state'] = 'conversing'
    
    def get_search_suggestions(self, user_id: int) -> List[str]:
        """Get contextually aware search suggestions based on available CVs and conversation history."""
        context = self.get_conversation_context(user_id)
        cv_summaries = context.get('cv_summaries', [])
        conversation_state = context.get('conversation_state', 'greeting')
        last_results = context.get('last_results', {})
        
        # Context-aware suggestions based on conversation state
        if conversation_state == 'searching' and last_results:
            return [
                "Show me more details about the top candidate",
                "Find similar profiles",
                "Refine the search criteria",
                "Show alternatives"
            ]
        
        if not cv_summaries:
            return [
                "Find me a senior developer",
                "Looking for marketing professionals",
                "Show me data scientists",
                "Need project managers"
            ]
        
        # Generate suggestions based on available CVs
        roles = list(set([cv.get('role', '') for cv in cv_summaries if cv.get('role')]))
        skills = list(set([skill for cv in cv_summaries for skill in cv.get('skills', [])]))
        
        suggestions = []
        
        # Add role-based suggestions
        for role in roles[:3]:
            suggestions.append(f"Find {role} candidates")
        
        # Add skill-based suggestions
        for skill in skills[:3]:
            suggestions.append(f"Show me {skill} experts")
        
        return suggestions[:5]
    
    async def execute_search(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Execute CV search based on conversation context."""
        try:
            context = self.get_conversation_context(user_id)
            extracted_criteria = context.get('extracted_criteria', {})
            
            if not extracted_criteria:
                return {
                    'message': "I need more information about your requirements before I can search for candidates.",
                    'action': 'continue',
                    'suggestions': [
                        "Tell me about the role you're hiring for",
                        "What skills are you looking for?",
                        "What experience level do you need?"
                    ]
                }
            
            # Get CV summaries
            cv_summaries = context.get('cv_summaries', [])
            if not cv_summaries:
                cv_summaries = await self.get_cv_summaries(user_id, db)
                context['cv_summaries'] = cv_summaries
            
            # Use smart CV search with matching API
            search_query = self.construct_search_query(extracted_criteria)
            search_results = await self.smart_cv_search_with_matching_api(search_query, db, user_id)
            relevant_cvs = search_results['results']
            
            if not relevant_cvs:
                return {
                    'message': f"""🔍 I searched through {len(cv_summaries)} CVs but couldn't find exact matches for your criteria.

**Your search criteria:**
{self.format_criteria(extracted_criteria)}

**Suggestions:**
• Try broader skill requirements
• Consider different experience levels
• Look for transferable skills from related fields

Would you like me to show you the closest matches or help you refine your search?""",
                    'action': 'continue',
                    'suggestions': [
                        "Show me the closest matches",
                        "Broaden the search criteria",
                        "Try different skills"
                    ]
                }
            
            # Format results for the existing UI structure
            formatted_results = {
                'total_cvs_processed': search_results['total_processed'],
                'processing_time': search_results['processing_time'],
                'matches': []
            }
            
            for cv in relevant_cvs:
                summary = cv.get('summary', {})
                match_data = {
                    'cv_filename': cv.get('filename', 'Unknown'),
                    'candidate_name': summary.get('candidate_name', 'Unknown') if isinstance(summary, dict) else cv.get('candidate_name', 'Unknown'),
                    'relevance_score': cv.get('match_score', 0) * 100,
                    'candidate_summary': summary.get('summary', 'No summary available') if isinstance(summary, dict) else 'Professional candidate',
                    'key_skills': json.dumps(cv.get('skills', [])),
                    'match_analysis': '\n'.join(cv.get('match_reasons', [])),
                    'download_url': f"#download-{cv.get('file_id', '')}",
                    'google_drive_file_id': cv.get('file_id', ''),
                    'experience_years': cv.get('experience', 0)
                }
                formatted_results['matches'].append(match_data)
            
            # Update context
            context['last_results'] = formatted_results
            
            # Generate response message
            message = f"""🎯 **Search Complete!**

Found **{len(relevant_cvs)} matching candidates** for your requirements:
{self.format_criteria(extracted_criteria)}

The candidates are ranked by AI-powered relevance scoring. You can now:
• Review detailed match analysis and summaries
• Explore candidate profiles and skills
• Refine your search criteria
• Find similar candidates"""
            
            return {
                'message': message,
                'action': 'show_results',
                'results': formatted_results,
                'suggestions': [
                    "Show me more details about the top candidate",
                    "Find similar profiles",
                    "Refine the search criteria",
                    "Start a new search"
                ]
            }
            
        except Exception as e:
            print(f"❌ Error executing search: {e}")
            import traceback
            traceback.print_exc()
            return {
                'message': "I encountered an error while searching for candidates. Please try again.",
                'action': 'continue',
                'suggestions': [
                    "Try a different search",
                    "Check your requirements",
                    "Ask for help"
                ]
            }

    async def format_refined_results(self, refined_results: List[Dict[str, Any]]) -> str:
        """Format refined results."""
        return await self.format_refined_results_with_intelligence(refined_results, {})
    
    async def format_refined_results_with_intelligence(self, refined_results: List[Dict[str, Any]], criteria: Dict[str, Any]) -> str:
        """Format refined results with intelligent analysis."""
        if not refined_results:
            return f"""No candidates found matching your refined criteria:

{self.format_criteria(criteria)}

Would you like to try different criteria or see the closest matches?"""
        
        message = f"""🔄 **Refined Search Results** - {len(refined_results)} candidates found

**Updated Criteria:**
{self.format_criteria(criteria)}

**🎯 Refined Matches:**
"""
        
        for i, candidate in enumerate(refined_results[:3], 1):
            match_score = int(candidate.get('match_score', 0) * 100)
            summary = candidate.get('summary', {})
            candidate_name = 'Unknown'
            
            if isinstance(summary, dict) and summary.get('candidate_name'):
                candidate_name = summary['candidate_name']
            elif candidate.get('candidate_name'):
                candidate_name = candidate['candidate_name']
            
            message += f"""
**{i}. {candidate_name}** ({match_score}% match)
• **Role:** {candidate.get('role', 'Professional')}
• **Experience:** {candidate.get('experience', 0)} years
• **Skills:** {', '.join(candidate.get('skills', [])[:3])}
• **Fit:** {candidate.get('role_fit', 'Good match')}
"""
        
        return message
    
    async def format_refined_results_data(self, refined_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format refined results as data structure."""
        try:
            formatted_results = {
                'total_cvs_processed': len(refined_results),
                'processing_time': '< 1 second',
                'matches': []
            }
            
            for cv in refined_results:
                summary = cv.get('summary', {})
                match_data = {
                    'cv_filename': cv.get('filename', 'Unknown'),
                    'candidate_name': summary.get('candidate_name', 'Unknown') if isinstance(summary, dict) else 'Unknown',
                    'relevance_score': cv.get('match_score', 0) * 100,
                    'candidate_summary': summary.get('summary', 'No summary available') if isinstance(summary, dict) else 'No summary available',
                    'key_skills': json.dumps(cv.get('skills', [])),
                    'match_analysis': '\n'.join(cv.get('match_reasons', [])),
                    'role_fit': cv.get('role_fit', 'Good fit'),
                    'improvement_areas': ' | '.join(cv.get('improvement_areas', [])),
                    'download_url': f"#download-{cv.get('file_id', '')}",
                    'google_drive_file_id': cv.get('file_id', ''),
                    'experience_years': cv.get('experience', 0)
                }
                formatted_results['matches'].append(match_data)
            
            return formatted_results
            
        except Exception as e:
            print(f"Error formatting refined results: {e}")
            return {'total_cvs_processed': 0, 'processing_time': '< 1s', 'matches': []}

# Global instance
intelligent_chat_agent_service = IntelligentChatAgentService()