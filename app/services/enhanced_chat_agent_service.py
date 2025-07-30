import openai
import asyncio
import json
import re
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import UserConfig, MatchLog, MatchResult, User
from app.services.google_drive_service import google_drive_service
from app.utils.encryption import encryption_service
from datetime import datetime
import threading

class EnhancedChatAgentService:
    """Enhanced AI-powered chat agent with natural conversation capabilities and intelligent Resume matching."""
    
    def __init__(self):
        self.openai_client = None
        self.current_api_key = None  # Track current API key to detect changes
        self.conversation_contexts = {}  # Store detailed conversation context per user
        self.cv_cache = {}  # Cache processed CV data
        self.cache_lock = threading.Lock()
        self.MATCH_THRESHOLD = 0.50  # Lower threshold for chat matching
        self.MAX_RESULTS = 6  # Return top 6 most relevant candidates
        
    def get_openai_key(self, db: Session, user_id: int) -> str:
        """Get user's OpenAI API key."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config or not user_config.openai_api_key:
            return None
        return encryption_service.decrypt(user_config.openai_api_key)
    
    def initialize_openai_client(self, api_key: str) -> bool:
        """Initialize OpenAI client with proper configuration."""
        # Check if we need to reinitialize (different API key)
        if self.openai_client and self.current_api_key == api_key:
            print(f"🔄 OpenAI client already initialized with same key")
            return True
            
        try:
            print(f"🔄 Initializing OpenAI client with new API key: {api_key[:10]}...")
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
            self.current_api_key = api_key  # Store current key
            print(f"✅ OpenAI client initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI client: {e}")
            return False
    
    def get_conversation_context(self, user_id: int) -> Dict[str, Any]:
        """Get or create detailed conversation context for a user."""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = {
                'messages': [],
                'job_requirements': {},  # Extracted job requirements
                'candidate_preferences': {},  # User's preferences for candidates
                'clarification_needed': [],  # What needs to be clarified
                'conversation_stage': 'initial',  # initial, gathering_requirements, searching, refining, explaining
                'last_search_results': None,
                'cv_summaries': [],
                'user_context': {
                    'industry_focus': None,
                    'typical_roles': [],
                    'preferred_experience_levels': []
                }
            }
        return self.conversation_contexts[user_id]

#     def _handle_general_conversation_sync(self, user_id: int, message: str, db: Session) -> Dict[str, Any]:
#         prompt = f"""
#     You are an AI recruitment assistant. Respond conversationally to the user based on the message below.
#
#     User message:
#     \"{message}\"
#
#     If they’re asking about a job role, skill, or candidate, guide them. If they’re just saying hi, respond politely and invite them to describe what kind of candidate they’re looking for.
#     """
#
#         try:
#             response = self.openai_client.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[{"role": "user", "content": prompt}],
#                 temperature=0.5,
#                 max_tokens=300
#             )
#             return {
#                 "message": response.choices[0].message.content.strip(),
#                 "action": "general_conversation",
#                 "suggestions": [
#                     "Find a React developer",
#                     "List CVs with Python skills",
#                     "Search for 5+ years experience"
#                 ]
#             }
#         except Exception as e:
#             print(f"❌ GPT conversation failed: {e}")
#             return self._create_error_response("Something went wrong while generating the response.")





    def _create_error_response(self, message: str) -> Dict[str, Any]:
        return {
            "message": message,
            "action": "error",
            "suggestions": [
                "Try again",
                "Check your input",
                "Contact support if issue persists"
            ]
        }

    def process_chat_message_sync(self, user_id: int, message: str, db: Session) -> Dict[str, Any]:
        """Process chat message synchronously (same pattern as Resume matching service)."""
        try:
            print(f"🤖 Processing chat message synchronously for user {user_id}: {message[:100]}...")
            
            # Step 1: Initialize OpenAI client (always check for key changes)
            api_key = self.get_openai_key(db, user_id)
            if not api_key:
                return self._create_configuration_response()
            
            print(f"🔑 Using API key for user {user_id}: {api_key[:15]}...{api_key[-10:]}")
            
            # Always attempt to initialize/reinitialize with current API key
            if not self.initialize_openai_client(api_key):
                return self._create_error_response("Failed to initialize AI service")
            
            # Step 2: Get conversation context
            context = self.get_conversation_context(user_id)
            
            # Step 3: Get CV summaries (same approach as CV matching - direct processing)
            cv_summaries = self.get_cv_summaries_sync(user_id, db)
            context['cv_summaries'] = cv_summaries
            
            print(f"📁 Found {len(cv_summaries)} CV summaries")
            
            # Step 4: Add user message to context
            context['messages'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Step 5: Process message and generate response (synchronous)
            response_data = self._generate_conversational_response_sync(user_id, message, context, db)
            
            # Step 6: Add AI response to context
            context['messages'].append({
                'role': 'assistant',
                'content': response_data['message'],
                'timestamp': datetime.now().isoformat(),
                'action': response_data.get('action', 'continue')
            })
            
            # Keep conversation history manageable
            if len(context['messages']) > 12:
                context['messages'] = context['messages'][-12:]
            
            print(f"✅ Chat response generated successfully")
            return response_data
            
        except Exception as e:
            print(f"❌ Error in synchronous chat processing: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_response("I encountered an unexpected error. Please try again.")
    
    def get_cv_summaries_sync(self, user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get CV summaries synchronously (same pattern as Resume matching service)."""
        with self.cache_lock:
            if user_id in self.cv_cache:
                print(f"📋 Using cached CV summaries for user {user_id}: {len(self.cv_cache[user_id])} CVs")
                return self.cv_cache[user_id]
        
        try:
            print(f"🔄 Processing CV summaries synchronously for user {user_id}")
            
            # Get user configuration
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not user_config or not user_config.google_drive_token:
                print(f"⚠️ Google Drive not configured for user {user_id}")
                return []
            
            # Get CV files from Google Drive
            folder_name = user_config.cv_folder_name or "cvs"
            cv_files = google_drive_service.list_files_in_folder(db, user_id, folder_name)
            
            if not cv_files:
                print(f"⚠️ No CV files found in folder '{folder_name}'")
                return []
            
            print(f"📄 Found {len(cv_files)} CV files, processing...")
            
            # Process CVs synchronously (like CV matching service)
            cv_summaries = []
            max_cvs = min(len(cv_files), 25)  # Process up to 25 CVs
            
            for i, cv_file in enumerate(cv_files[:max_cvs]):
                try:
                    print(f"  📄 Processing CV {i+1}/{max_cvs}: {cv_file['name']}")
                    
                    # Download file content
                    cv_content_bytes = google_drive_service.download_file(db, user_id, cv_file['id'])
                    if not cv_content_bytes:
                        continue
                    
                    # Parse CV content
                    from app.utils.simple_document_parser import simple_document_parser as document_parser
                    cv_content = document_parser.extract_text_from_file(cv_content_bytes, cv_file['name'])
                    if not cv_content or len(cv_content.strip()) < 100:
                        continue
                    
                    # Generate summary using the same OpenAI approach as CV matching
                    summary = self._generate_cv_summary_sync(cv_content, cv_file['name'])
                    
                    cv_summary = {
                        'filename': cv_file['name'],
                        'file_id': cv_file['id'],
                        'summary': summary,
                        'skills': summary.get('skills', []),
                        'experience': summary.get('experience', 0),
                        'role': summary.get('role', 'Professional')
                    }
                    cv_summaries.append(cv_summary)
                    print(f"    ✅ Processed: {summary.get('candidate_name', 'Unknown')}")
                    print(f"       Role: {summary.get('role', 'Unknown')}")
                    print(f"       Skills: {summary.get('skills', [])}")
                    print(f"       Experience: {summary.get('experience', 0)} years")
                    
                except Exception as e:
                    print(f"    ❌ Error processing {cv_file['name']}: {e}")
                    continue
            
            # Cache the results
            with self.cache_lock:
                self.cv_cache[user_id] = cv_summaries
            
            print(f"✅ Processed {len(cv_summaries)} CVs successfully")
            return cv_summaries
            
        except Exception as e:
            print(f"❌ Error in synchronous CV processing: {e}")
            return []
    
    def _generate_cv_summary_sync(self, cv_content: str, filename: str) -> Dict[str, Any]:
        """Generate CV summary synchronously using OpenAI (same pattern as Resume matching)."""
        if not self.openai_client:
            return self._fallback_cv_summary(cv_content, filename)
        
        try:
            # Compress CV content (same approach as CV matching)
            compressed_cv = cv_content[:3000] if len(cv_content) > 3000 else cv_content
            
            # Single AI call for CV analysis (same pattern as CV matching)
            prompt = f"""Analyze this CV and return ONLY valid JSON:

CV Content:
{compressed_cv}

Return JSON:
{{
    "candidate_name": "full name from CV",
    "role": "current or most recent job title",
    "skills": ["list of ALL technical skills found"],
    "experience": "total years of experience as number or null",
    "seniority_level": "junior/mid/senior",
    "education": ["degrees and certifications"],
    "summary": "2-sentence professional summary"
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Faster model like CV matching
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.1,
                top_p=0.95
            )
            
            ai_response = response.choices[0].message.content.strip()
            summary = json.loads(ai_response)
            return summary
            
        except Exception as e:
            print(f"❌ AI summary failed for {filename}: {e}")
            return self._fallback_cv_summary(cv_content, filename)
    
    def _fallback_cv_summary(self, cv_content: str, filename: str) -> Dict[str, Any]:
        """Fallback Resume summary without AI (same pattern as Resume matching)."""
        from app.utils.simple_document_parser import simple_document_parser as document_parser
        
        return {
            "candidate_name": document_parser.extract_candidate_name(cv_content) or "Professional Candidate",
            "role": "Professional",
            "skills": document_parser.extract_skills_section(cv_content) or [],
            "experience": document_parser.extract_experience_years(cv_content) or 0,
            "seniority_level": "mid",
            "education": [],
            "summary": "Experienced professional with relevant background"
        }
    
    def _generate_conversational_response_sync(self, user_id: int, message: str, context: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Generate conversational response synchronously (RESTORED ORIGINAL LOGIC)."""
        try:
            # Use the ORIGINAL intent-based approach that was working
            intent_analysis = self._analyze_conversation_intent_sync(message, context)
            
            print(f"🎯 Intent analysis: {intent_analysis['intent']}")

            # Handle different conversation flows (ORIGINAL WORKING LOGIC)
            if intent_analysis['intent'] == 'greeting':
                return self._handle_greeting_sync(context)
            
            elif intent_analysis['intent'] == 'search_request':
                return self._handle_search_request_sync(intent_analysis, context, db, user_id)
            
            elif intent_analysis['intent'] == 'candidate_inquiry':
                return self._handle_candidate_inquiry_sync(context)
            
            elif intent_analysis['intent'] == 'refinement':
                return self._handle_refinement_sync(intent_analysis, context)
            
            else:
                # ONLY this part gets OpenAI intelligence for general questions
                return self._handle_general_conversation_sync(message, context)
                
        except Exception as e:
            print(f"❌ Error generating conversational response: {e}")
            return self._create_error_response("I encountered an issue processing your message.")
    
    def _generate_smart_suggestions(self, user_message: str, ai_response: str, cv_count: int) -> List[str]:
        """Generate contextual suggestions based on the conversation."""
        message_lower = user_message.lower()
        response_lower = ai_response.lower()
        
        # CV/Recruitment related suggestions
        if any(word in message_lower for word in ['cv', 'candidate', 'job', 'hire', 'recruit', 'find', 'search']):
            return [
                'Find candidates for a specific role',
                'Search by skills and experience',
                'Show me all available candidates',
                'Help me refine my requirements'
            ]
        
        # General advice/recommendations
        elif any(word in message_lower for word in ['recommend', 'advice', 'suggest', 'help', 'should', 'how']):
            return [
                'Tell me more details',
                'Give me specific examples',
                'What else should I consider?',
                'Help me with recruitment needs'
            ]
        
        # Technology/skills related
        elif any(word in message_lower for word in ['technology', 'programming', 'software', 'development', 'tech']):
            return [
                'Find developers with these skills',
                'What other technologies to consider?',
                'Show me tech professionals',
                'Recommend related skills'
            ]
        
        # Business/strategy related
        elif any(word in message_lower for word in ['business', 'strategy', 'company', 'startup', 'growth']):
            return [
                'Find business professionals',
                'Tell me more about this topic',
                'Help with team building',
                'Strategic hiring advice'
            ]
        
        # Greeting/general
        elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'thanks', 'thank']):
            return [
                'Find candidates for a role',
                'Ask me anything',
                'Get recruitment advice',
                f'Search through my {cv_count} CVs'
            ]
        
        # Default suggestions for any other topic
        else:
            return [
                'Tell me more about this',
                'Ask me another question',
                'Help me find candidates',
                'Get specific recommendations'
            ]
    
    def _analyze_conversation_intent_sync(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conversation intent synchronously (with fallback like Resume matching)."""
        print(f"🤖 DEBUG: OpenAI client available: {self.openai_client is not None}")
        
        if not self.openai_client:
            print("⚠️ DEBUG: No OpenAI client, using fallback")
            return self._create_fallback_intent_analysis(message)
        
        try:
            print(f"🤖 DEBUG: Using OpenAI for intent analysis of: '{message}'")
            
            # Quick AI analysis with timeout (same approach as CV matching)
            prompt = f"""Analyze this message and return ONLY valid JSON:

Message: "{message}"

Return JSON:
{{
    "intent": "greeting/search_request/candidate_inquiry/refinement/general_conversation",
    "extracted_info": {{
        "job_title": "job title if mentioned",
        "required_skills": ["skills if mentioned"],
        "experience_years": "years if mentioned as number or null"
    }},
    "needs_detailed_processing": true/false
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0,
                timeout=10.0  # 10 second timeout
            )
            
            ai_response = response.choices[0].message.content.strip()
            print(f"🤖 DEBUG: OpenAI response: {ai_response}")
            
            result = json.loads(ai_response)
            print(f"🤖 DEBUG: Parsed OpenAI result: {result}")
            return result
            
        except Exception as e:
            print(f"❌ AI intent analysis failed, using fallback: {e}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_intent_analysis(message)
    
    def _create_fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Create fallback intent analysis (enhanced for candidate inquiries)."""
        message_lower = message.lower()
        
        # Determine intent based on keywords
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'start']):
            return {'intent': 'greeting', 'extracted_info': {}, 'needs_detailed_processing': False}
        
        elif any(word in message_lower for word in ['find', 'search', 'looking', 'need', 'want']):
            # Extract basic info
            skills = []
            job_title = ""
            
            # Common skills
            skill_keywords = ['python', 'javascript', 'react', 'angular', 'java', 'node', 'sql', 'aws']
            for skill in skill_keywords:
                if skill in message_lower:
                    skills.append(skill)
            
            # Enhanced role detection (same as instant service)
            if 'project manager' in message_lower:
                job_title = 'Project Manager'
            elif 'product manager' in message_lower:
                job_title = 'Product Manager'
            elif 'data scientist' in message_lower:
                job_title = 'Data Scientist'
            elif 'developer' in message_lower:
                job_title = 'Developer'
            elif 'engineer' in message_lower:
                job_title = 'Engineer'
            elif 'manager' in message_lower:
                job_title = 'Manager'
            
            return {
                'intent': 'search_request',
                'extracted_info': {
                    'job_title': job_title,
                    'required_skills': skills,
                    'experience_years': None
                },
                'needs_detailed_processing': True
            }
        
        # Enhanced candidate inquiry detection
        elif any(word in message_lower for word in [
            'why', 'explain', 'tell me about', 'detail', 'details', 'summary', 'analyze', 'review',
            'candidate', 'profile', 'experience', 'background', 'qualification', 'skills',
            'strength', 'weakness', 'suitable', 'fit', 'good match', 'recommend',
            'cv', 'resume', 'about him', 'about her', 'about this person', 'more info'
        ]):
            return {'intent': 'candidate_inquiry', 'extracted_info': {}, 'needs_detailed_processing': True}
        
        # Check if message contains potential candidate names (capitalized words)
        words = message.split()
        has_potential_name = any(word[0].isupper() and len(word) > 2 for word in words if word.isalpha())
        if has_potential_name:
            return {'intent': 'candidate_inquiry', 'extracted_info': {}, 'needs_detailed_processing': True}
        
        else:
            return {'intent': 'general_conversation', 'extracted_info': {}, 'needs_detailed_processing': False}
    
    def _handle_greeting_sync(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle greetings synchronously."""
        cv_count = len(context.get('cv_summaries', []))
        
        if cv_count > 0:
            message = f"""👋 **Hello! I'm your AI recruitment assistant.**

I have **{cv_count} CVs** ready for intelligent matching. I can help you:

🔍 **Find candidates** for specific roles
💡 **Match skills** to job requirements  
🎯 **Explain matches** with detailed reasoning
❓ **Answer questions** about candidate profiles

**What position are you looking to fill?**"""
        else:
            message = """👋 **Hello! I'm your AI recruitment assistant.**

I'm processing your CVs to create intelligent candidate profiles. This may take a moment...

**What kind of position are you looking to fill?**"""
        
        return {
            'message': message,
            'action': 'continue',
            'suggestions': [
                'I need a senior software developer',
                'Looking for marketing professionals',
                'Find me data scientists',
                'Show me available candidates'
            ]
        }
    
    def _handle_search_request_sync(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], db: Session, user_id: int) -> Dict[str, Any]:
        """Handle search requests synchronously (similar to Resume matching approach)."""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            cv_summaries = context.get('cv_summaries', [])
            
            if not cv_summaries:
                return {
                    'message': """🔄 **Processing your CVs for this search...**

I'm analyzing your CV database to find candidates. This may take a moment as I process and understand each candidate's profile.

**What specific requirements are most important to you?**""",
                    'action': 'processing',
                    'suggestions': [
                        'Senior level experience',
                        'Specific technical skills',
                        'Industry background',
                        'Remote work capability'
                    ]
                }
            
            # Perform matching using the same approach as CV matching service
            matches = self._perform_cv_matching_sync(extracted_info, cv_summaries)
            
            if matches:
                # Store for later reference
                context['job_requirements'] = extracted_info
                context['last_search_results'] = matches
                context['conversation_stage'] = 'searching'
                
                job_title = extracted_info.get('job_title', 'candidates')
                
                message = f"""🎯 **Found {len(matches)} candidates matching {job_title}!**

**Search criteria:**
• **Role**: {job_title or 'Your specified role'}
• **Skills**: {', '.join(extracted_info.get('required_skills', [])[:3]) or 'Various skills'}

**Top matches:**
{self._format_match_summary_sync(matches[:3])}

**Would you like to:**"""
                
                return {
                    'message': message,
                    'action': 'show_results',
                    'results': self._format_match_results_sync(matches),
                    'suggestions': [
                        'Tell me more about the top candidate',
                        'Why are these good matches?',
                        'Show me different candidates',
                        'Refine the search criteria'
                    ]
                }
            else:
                return {
                    'message': f"""🔍 **No matches found for {extracted_info.get('job_title', 'your criteria')}**

Let me help you refine your search. What specific requirements are most important?

**Try being more specific about:**
• Years of experience needed
• Must-have technical skills
• Type of role (junior/senior/lead)
• Industry background""",
                    'action': 'continue',
                    'suggestions': [
                        'Senior level (5+ years)',
                        'Specific technology skills',
                        'Any experience level',
                        'Show me all candidates'
                    ]
                }
                
        except Exception as e:
            print(f"❌ Error in search request: {e}")
            return self._create_error_response("I encountered an issue with your search. Please try again.")
    
#     def _perform_cv_matching_sync(self, criteria: Dict[str, Any], cv_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         """Perform CV matching synchronously with debug info."""
#         try:
#             print(f"🔍 DEBUG: Matching criteria: {criteria}")
#             print(f"🔍 DEBUG: CV summaries count: {len(cv_summaries)}")
#
#             matches = []
#             job_title = criteria.get('job_title', '').lower()
#             required_skills = [s.lower() for s in criteria.get('required_skills', [])]
#             min_experience = criteria.get('experience_years') or 0
#
#             print(f"🔍 DEBUG: Looking for job_title='{job_title}', skills={required_skills}")
#
#             for i, cv in enumerate(cv_summaries):
#                 print(f"  🔍 DEBUG CV {i+1}: {cv.get('filename', 'Unknown')}")
#                 print(f"    Role: '{cv.get('role', '')}' | Skills: {cv.get('skills', [])} | Experience: {cv.get('experience', 0)}")
#
#                 score = 0
#                 reasons = []
#
#                 # More flexible role matching - check for manager, project, owner keywords
#                 cv_role = cv.get('role', '').lower()
#                 cv_filename = cv.get('filename', '').lower()
#                 cv_summary = str(cv.get('summary', {})).lower()
#
#                 # Check role in multiple places
#                 all_cv_text = f"{cv_role} {cv_filename} {cv_summary}"
#
#                 if job_title:
#                     # Exact match
#                     if job_title in cv_role or job_title in cv_filename:
#                         score += 50
#                         reasons.append(f"Exact role match: {cv.get('role', '')}")
#                     # Individual word matching for compound titles like "project manager"
#                     elif job_title == "project manager":
#                         if any(word in all_cv_text for word in ["project", "manager", "pm", "lead", "owner"]):
#                             score += 40
#                             reasons.append("Project/Management role detected")
#                     elif "manager" in job_title:
#                         if any(word in all_cv_text for word in ["manager", "lead", "director", "head", "owner"]):
#                             score += 35
#                             reasons.append("Management role detected")
#                     # Partial matching
#                     else:
#                         job_words = set(job_title.split())
#                         role_words = set(cv_role.split()) | set(cv_filename.split())
#                         if job_words.intersection(role_words):
#                             score += 25
#                             reasons.append("Partial role match")
#
#                 # Give points for having a CV at all
#                 if cv.get('filename'):
#                     score += 20
#                     reasons.append("Valid candidate profile")
#
#                 # Skills matching (if any skills specified)
#                 cv_skills = [s.lower() for s in cv.get('skills', [])]
#                 if required_skills and cv_skills:
#                     skill_matches = []
#                     for skill in required_skills:
#                         if any(skill in cv_skill for cv_skill in cv_skills):
#                             skill_matches.append(skill)
#
#                     if skill_matches:
#                         skill_score = min(30, len(skill_matches) * 10)
#                         score += skill_score
#                         reasons.append(f"Skills: {', '.join(skill_matches[:3])}")
#
#                 # Experience matching (if specified)
#                 cv_experience = cv.get('experience', 0)
#                 if min_experience > 0:
#                     if cv_experience >= min_experience:
#                         score += 20
#                         reasons.append(f"{cv_experience} years experience")
#                     elif cv_experience >= min_experience * 0.7:
#                         score += 10
#                         reasons.append(f"{cv_experience} years experience (close)")
#                 else:
#                     # Give some points for any experience
#                     if cv_experience > 0:
#                         score += 10
#                         reasons.append(f"{cv_experience} years experience")
#
#                 print(f"    Score: {score}, Reasons: {reasons}")
#
#                 # Lower threshold to include more matches - 30+ points instead of 50
#                 if score >= 30:
#                     match = cv.copy()
#                     match['match_score'] = score
#                     match['match_reasons'] = reasons
#                     match['match_percentage'] = min(95, score)
#                     matches.append(match)
#                     print(f"    ✅ MATCHED with {score} points")
#                 else:
#                     print(f"    ❌ No match (score too low: {score})")
#
#             # Sort by score
#             matches.sort(key=lambda x: x['match_score'], reverse=True)
#             print(f"🔍 DEBUG: Total matches found: {len(matches)}")
#             return matches[:6]  # Return top 6
#
#         except Exception as e:
#             print(f"❌ Error in CV matching: {e}")
#             import traceback
#             traceback.print_exc()
#             return []
#
# PATCHED: _perform_cv_matching_sync with GPT-powered semantic scoring
# Add this method to your EnhancedChatAgentService class

    def _generate_match_analysis_sync(self, job_requirements: Dict[str, Any], cv: Dict[str, Any], match_score: float) -> Dict[str, Any]:
        try:
            cv_summary = cv.get('summary', {})
            cv_skills = cv.get('skills', [])
            cv_role = cv.get('role', '')

            prompt = f"""Generate a match analysis in JSON format.

    Job Requirements:
    {json.dumps(job_requirements, indent=2)}

    Candidate:
    - Role: {cv_role}
    - Skills: {cv_skills}
    - Experience: {cv.get('experience', 0)} years
    - Summary: {cv_summary if isinstance(cv_summary, str) else json.dumps(cv_summary, indent=2)}

    Match Score: {match_score}

    Return:
    {{
      "reasons": ["reason 1", "reason 2", "reason 3"],
      "experience_fit": "Perfect fit|Good fit|Adequate fit",
      "overall_assessment": "Concise summary"
    }}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            return json.loads(response.choices[0].message.content.strip())

        except Exception as e:
            print(f"❌ Error generating match analysis: {e}")
            return {
                "reasons": ["Experience aligns", "Skill match"],
                "experience_fit": "Good fit",
                "overall_assessment": "Strong match based on skillset and experience"
            }

    def _perform_cv_matching_sync(self, criteria: Dict[str, Any], cv_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform Resume matching with enhanced GPT semantic scoring."""
        try:
            print(f"🔍 Matching with criteria: {criteria}")
            matches = []

            job_title = criteria.get('job_title', '').strip()
            required_skills = criteria.get('required_skills', [])
            min_experience = criteria.get('experience_years', 0)

            for cv in cv_summaries:
                summary_text = cv.get("summary", {})
                if isinstance(summary_text, dict):
                    summary_text = json.dumps(summary_text, indent=2)

                candidate_prompt = f"""
    Job Role: {job_title}
    Required Skills: {required_skills}
    Minimum Experience: {min_experience} years

    CV:
    {summary_text}

    On a scale of 0 to 1, how well does this candidate match the job requirements?
    Return only a float number like 0.87
    """
                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": candidate_prompt}],
                        max_tokens=10,
                        temperature=0.1
                    )
                    score_text = response.choices[0].message.content.strip()
                    score = float(re.search(r"\b(0\.\d+|1\.0|0\.0)\b", score_text).group(1))
                    print(f"✅ GPT Score: {score:.2f} for {cv.get('filename', 'CV')}")
                except Exception as e:
                    print(f"⚠️ GPT scoring failed: {e}")
                    score = 0.0

                if score >= self.MATCH_THRESHOLD:
                    # ✅ Dynamically generate match_analysis
                    match_analysis = self._generate_match_analysis_sync(criteria, cv, score)
                    match = cv.copy()
                    match['match_score'] = score
                    match['match_percentage'] = round(score * 100)
                    match['match_reasons'] = match_analysis.get("reasons", ["Strong professional background"])
                    match['match_analysis'] = match_analysis
                    matches.append(match)

            matches.sort(key=lambda x: x['match_score'], reverse=True)
            return matches[:self.MAX_RESULTS]

        except Exception as e:
            print(f"❌ Error in GPT-powered matchings: {e}")
            return []

    def _format_match_summary_sync(self, matches: List[Dict[str, Any]]) -> str:
        """Format match summary for display."""
        summary = ""
        for i, match in enumerate(matches, 1):
            candidate_name = "Professional Candidate"
            if isinstance(match.get('summary'), dict):
                candidate_name = match['summary'].get('candidate_name', 'Professional Candidate')
            
            summary += f"""**{i}. {candidate_name}** ({match['match_percentage']}% match)
• **Role:** {match.get('role', 'Professional')}
• **Experience:** {match.get('experience', 0)} years
• **Match reasons:** {', '.join(match.get('match_reasons', [])[:2])}

"""
        return summary.strip()
    
    def _format_match_results_sync(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format results for API response."""
        try:
            formatted_matches = []
            for match in matches:
                candidate_name = "Professional Candidate"
                if isinstance(match.get('summary'), dict):
                    candidate_name = match['summary'].get('candidate_name', 'Professional Candidate')
                
                formatted_match = {
                    'cv_filename': match.get('filename', 'Unknown'),
                    'candidate_name': candidate_name,
                    'relevance_score': match['match_percentage'],
                    'candidate_summary': f"Match with {match['match_percentage']}% relevance",
                    'key_skills': json.dumps(match.get('skills', [])),
                    'match_analysis': f"Match analysis: {', '.join(match.get('match_reasons', [])[:2])}",
                    'download_url': f"#download-{match.get('file_id', '')}",
                    'experience_years': match.get('experience', 0)
                }
                formatted_matches.append(formatted_match)
            
            return {
                'total_cvs_processed': len(matches),
                'processing_time': 'Complete',
                'matches': formatted_matches
            }
        except Exception as e:
            print(f"❌ Error formatting results: {e}")
            return {'total_cvs_processed': 0, 'processing_time': 'Error', 'matches': []}
    
    def _handle_candidate_inquiry_sync(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle candidate inquiries with detailed CV analysis."""
        last_results = context.get('last_search_results', [])
        cv_summaries = context.get('cv_summaries', [])
        
        print(f"🔍 DEBUG: Candidate inquiry - Last results: {len(last_results)}, CV summaries: {len(cv_summaries)}")
        
        if last_results and cv_summaries:
            # Try to find the specific candidate being asked about
            candidate_to_analyze = None
            
            # Get the last user message to see if they mentioned a specific candidate
            messages = context.get('messages', [])
            last_user_message = ""
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    last_user_message = msg.get('content', '').lower()
                    break
            
            print(f"🔍 DEBUG: Last user message: '{last_user_message}'")
            
            # Try to match candidate by name or position in results
            if any(word in last_user_message for word in ['first', 'top', '1st', 'number 1']):
                candidate_to_analyze = last_results[0]
            elif any(word in last_user_message for word in ['second', '2nd', 'number 2']) and len(last_results) > 1:
                candidate_to_analyze = last_results[1]
            elif any(word in last_user_message for word in ['third', '3rd', 'number 3']) and len(last_results) > 2:
                candidate_to_analyze = last_results[2]
            else:
                # Try to match by candidate name (enhanced)
                for candidate in last_results:
                    candidate_name = ""
                    if isinstance(candidate.get('summary'), dict):
                        candidate_name = candidate['summary'].get('candidate_name', '').lower()
                    
                    # Also check filename for names
                    filename = candidate.get('filename', '').lower()
                    
                    # Extract potential names from filename
                    if not candidate_name and filename:
                        # Remove extensions and common words
                        clean_filename = filename.replace('.pdf', '').replace('.doc', '').replace('.docx', '').replace('_', ' ').replace('-', ' ')
                        candidate_name = clean_filename
                    
                    print(f"🔍 DEBUG: Checking candidate: '{candidate_name}' vs user message: '{last_user_message}'")
                    
                    if candidate_name:
                        # Check if any part of the candidate name appears in the user message
                        name_parts = [part for part in candidate_name.split() if len(part) > 2]
                        for name_part in name_parts:
                            if name_part in last_user_message:
                                candidate_to_analyze = candidate
                                print(f"🔍 DEBUG: Found name match: '{name_part}'")
                                break
                        if candidate_to_analyze:
                            break
                
                # If no specific match, analyze the top candidate
                if not candidate_to_analyze:
                    candidate_to_analyze = last_results[0]
            
            print(f"🔍 DEBUG: Selected candidate: {candidate_to_analyze.get('filename', 'Unknown')}")
            
            # Use OpenAI to provide detailed candidate analysis
            if self.openai_client and candidate_to_analyze:
                try:
                    candidate_summary = candidate_to_analyze.get('summary', {})
                    if isinstance(candidate_summary, dict):
                        candidate_details = json.dumps(candidate_summary, indent=2)
                    else:
                        candidate_details = str(candidate_summary)
                    
                    # Get additional candidate info
                    candidate_filename = candidate_to_analyze.get('filename', 'Unknown')
                    candidate_skills = candidate_to_analyze.get('skills', [])
                    candidate_experience = candidate_to_analyze.get('experience', 0)
                    candidate_role = candidate_to_analyze.get('role', 'Professional')
                    match_reasons = candidate_to_analyze.get('match_reasons', [])
                    
                    prompt = f"""You are analyzing a candidate for a recruitment position. Provide a comprehensive professional summary.

Candidate Data:
{candidate_details}

Role: {candidate_role}
Skills: {candidate_skills}
Experience: {candidate_experience} years
Match Reasons: {match_reasons}
CV File: {candidate_filename}

User asked: "{last_user_message}"

Provide a detailed professional analysis covering:

**1. CANDIDATE OVERVIEW**
- Full name and current role
- Years of experience and seniority level
- Industry background

**2. CORE COMPETENCIES**  
- Technical skills and expertise
- Soft skills and leadership abilities
- Certifications or qualifications

**3. PROFESSIONAL BACKGROUND**
- Career progression and achievements
- Notable projects or accomplishments
- Industry experience

**4. STRENGTHS FOR THIS ROLE**
- Why they're a good fit
- Specific value they'd bring
- Alignment with requirements

**5. ASSESSMENT & RECOMMENDATION**
- Overall suitability rating
- Potential concerns or gaps
- Hiring recommendation

Make it conversational, detailed, and actionable. Be specific about their qualifications and experience."""

                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=400,
                        temperature=0.3
                    )
                    
                    ai_analysis = response.choices[0].message.content.strip()
                    print(f"🤖 DEBUG: Generated candidate analysis")
                    
                    candidate_name = "Unknown"
                    if isinstance(candidate_summary, dict):
                        candidate_name = candidate_summary.get('candidate_name', 'Professional Candidate')
                    
                    return {
                        'message': f"""📋 **Detailed Analysis: {candidate_name}**

{ai_analysis}

**Match Score:** {candidate_to_analyze.get('match_percentage', 0)}%
**CV File:** {candidate_filename}""",
                        'action': 'continue',
                        'suggestions': [
                            'Tell me about the next candidate',
                            'Compare with other candidates',
                            'What are their weaknesses?',
                            'Show me their CV file'
                        ]
                    }
                    
                except Exception as e:
                    print(f"❌ Error in AI candidate analysis: {e}")
                    # Fall back to basic analysis
            
            # Fallback analysis without AI
            candidate_name = "Professional Candidate"
            if isinstance(candidate_to_analyze.get('summary'), dict):
                candidate_name = candidate_to_analyze['summary'].get('candidate_name', 'Professional Candidate')
            
            return {
                'message': f"""📋 **Candidate Analysis: {candidate_name}**

**Role:** {candidate_to_analyze.get('role', 'Professional')}
**Experience:** {candidate_to_analyze.get('experience', 0)} years
**Key Skills:** {', '.join(candidate_to_analyze.get('skills', [])[:5])}

**Why this candidate matches:**
{chr(10).join([f'• {reason}' for reason in candidate_to_analyze.get('match_reasons', ['Strong professional background'])])}

**Match Score:** {candidate_to_analyze.get('match_percentage', 0)}%
**CV File:** {candidate_to_analyze.get('filename', 'Unknown')}

**Would you like more details about this candidate?**""",
                'action': 'continue',
                'suggestions': [
                    'Tell me about their experience',
                    'What are their key strengths?',
                    'Show me the next candidate',
                    'Compare with other candidates'
                ]
            }
        else:
            return {
                'message': "I don't have any recent search results to analyze. Please search for candidates first, then I can provide detailed analysis of specific candidates.",
                'action': 'continue',
                'suggestions': [
                    'Find project managers',
                    'Search for developers',
                    'Show me all candidates',
                    'Find specific skills'
                ]
            }
    
    def _handle_refinement_sync(self, intent_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search refinements synchronously."""
        return {
            'message': "I'll refine the search with your new criteria. What specific changes would you like to make?",
            'action': 'continue',
            'suggestions': [
                'Add more skills',
                'Change experience level',
                'Different role type',
                'More specific requirements'
            ]
        }
    
#     def _handle_general_conversation_sync(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
#         """Handle general conversation synchronously - ONLY for non-CV questions with OpenAI intelligence."""
#         cv_count = len(context.get('cv_summaries', []))
#
#         # Use OpenAI ONLY for general questions (not CV-related ones)
#         if self.openai_client:
#             try:
#                 print(f"🤖 DEBUG: Using OpenAI for general (non-CV) conversation: '{message}'")
#
#                 prompt = f"""You are an intelligent AI assistant. The user is asking a general question.
#
# User's message: "{message}"
#
# Instructions:
#
# -Answer any general question clearly and professionally – whether it's about technology, business, career, life advice, or recommendations.
#
# -Be engaging, helpful, and concise (max 150 words).
#
# -If the user asks about a CV in general, generate a brief and informative summary of that CV.
#
# -If the user asks about a specific person by name, find the matching CV by exact name, extract all available details, and generate a well-defined, concise summary of that person’s profile.
#
# -If the user requests suggestions, offer thoughtful, relevant suggestions based on context.
#
# -If needed, ask clarifying questions to ensure accurate and helpful responses.
#
# -Always respond as if you are a smart assistant who understands both context and intent.
#
# Response:"""
#
#                 response = self.openai_client.chat.completions.create(
#                     model="gpt-3.5-turbo",
#                     messages=[{"role": "user", "content": prompt}],
#                     max_tokens=250,
#                     temperature=0.7
#                 )
#
#                 ai_response = response.choices[0].message.content.strip()
#                 print(f"🤖 DEBUG: OpenAI general response: {ai_response}")
#
#                 return {
#                     'message': ai_response,
#                     'action': 'continue',
#                     'suggestions': [
#                         'Tell me more about this',
#                         'Ask me another question',
#                         'Get more recommendations',
#                         'Help me find candidates' if cv_count > 0 else 'What else can you help with?'
#                     ]
#                 }
#
#             except Exception as e:
#                 print(f"❌ OpenAI general conversation failed: {e}")
#                 # Fall through to default response
#
#         # Default response if OpenAI fails
#         return {
#             'message': f"""I'm here to help you with anything! I can answer general questions and provide advice on various topics.
#
# **I can help you with:**
# • Technology and programming advice
# • Business and career recommendations
# • General questions and explanations
# • {f'CV/recruitment from my {cv_count} available profiles' if cv_count > 0 else 'Various topics'}
#
# **What would you like to know about?**""",
#             'action': 'continue',
#             'suggestions': [
#                 'Ask for recommendations',
#                 'Get technology advice',
#                 'Business questions',
#                 'Find candidates' if cv_count > 0 else 'General advice'
#             ]
#         }

    def _handle_general_conversation_sync(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general conversation synchronously - responds intelligently to general or CV-related questions."""
        cv_summaries = context.get('cv_summaries', [])
        cv_count = len(cv_summaries)

        # Format CVs for prompt
        cv_summaries_text = "\n\n".join(
            [
                f"Name: {cv.get('name')}\n"
                f"Role: {cv.get('title', 'N/A')}\n"
                f"Email: {cv.get('email', 'Not provided')}\n"
                f"Phone: {cv.get('phone', 'Not provided')}\n"
                f"Summary: {cv.get('summary', 'No summary available')}\n"
                f"Skills: {', '.join(cv.get('skills', [])) if isinstance(cv.get('skills'), list) else cv.get('skills', 'N/A')}\n"
                f"Experience: {cv.get('experience', 'N/A')}"
                for cv in cv_summaries
            ]
        ) or "No CVs available."

        if self.openai_client:
            try:
                print(f"🤖 DEBUG: Using OpenAI for conversation: '{message}'")

                prompt = f"""You are an intelligent AI assistant. A user is chatting with you.

    User's message: "{message}"

    Below is a list of available candidate CVs:

    {cv_summaries_text}

    Instructions:
    - If the user asks about a specific person by name (e.g., "Marya Zamir Khan"), search for that **exact name** in the list above and return a detailed, professional summary of that person.
    - If the name is not found, respond politely that no match was found and suggest checking the spelling.
    - If the user asks about CVs in general, summarize one or more of them concisely.
    - If the question is general (e.g., about technology, business, careers, advice), respond intelligently and clearly with helpful information.
    - Keep responses under 150 words.
    - If the user asks for contact details (like email or phone), include them in the response if available.
    - Return the **top 2–3 relevant candidates** in a clean, formatted response.
    - For each matching candidate, use the following format:

    Candidate: <Full Name>
    Role: <Job Title>
    Email: <Email>
    Phone: <Phone>
    Summary: <Concise 2–3 sentence summary>
    Skills: <Key skills>
    Experience: <Years of experience>

    - If the user asks about a person by exact name, return that person's full CV details in the format above.
    - If no matching candidate is found, reply politely asking the user to check the spelling or try a different query.
    - Be helpful, conversational, and professional. Offer relevant suggestions when appropriate.

    Response:"""

                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=250,
                    temperature=0.7
                )

                ai_response = response.choices[0].message.content.strip()
                print(f"🤖 DEBUG: OpenAI response: {ai_response}")

                return {
                    'message': ai_response,
                    'action': 'continue',
                    'suggestions': [
                        'Tell me more about this',
                        'Ask me another question',
                        'Get more recommendations',
                        'Help me find candidates' if cv_count > 0 else 'What else can you help with?'
                    ]
                }

            except Exception as e:
                print(f"❌ OpenAI general conversation failed: {e}")

        # Fallback default response
        return {
            'message': f"""I'm here to help you with anything! I can answer general questions and provide advice on various topics.

    **I can help you with:**
    • Technology and programming advice
    • Business and career recommendations
    • General topics and ideas
    • {f'CV/recruitment from my {cv_count} available profiles' if cv_count > 0 else 'Much more'}

    **What would you like to explore?**""",
            'action': 'continue',
            'suggestions': [
                'Ask for recommendations',
                'Get technology advice',
                'Business questions',
                'Find candidates' if cv_count > 0 else 'General advice'
            ]
        }


    async def process_chat_message(self, user_id: int, message: str, db: Session) -> Dict[str, Any]:
        """Enhanced chat processing with natural conversation flow and intelligent Resume matching."""
        try:
            print(f"🤖 Processing enhanced chat message for user {user_id}: {message[:100]}...")
            
            # Initialize OpenAI client if needed
            api_key = self.get_openai_key(db, user_id)
            if not api_key:
                return self._create_configuration_response()
            
            if not self.openai_client:
                if not self.initialize_openai_client(api_key):
                    return self._create_error_response("Failed to initialize AI service")
            
            # Get conversation context
            context = self.get_conversation_context(user_id)
            
            # Ensure CV data is available
            cv_summaries = await self.get_cv_summaries(user_id, db)
            context['cv_summaries'] = cv_summaries
            
            if not cv_summaries:
                # Start background processing and return processing message
                asyncio.create_task(self._process_cvs_background(user_id, db))
                return self._create_processing_response(message)
            
            # Add user message to context
            context['messages'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Analyze the conversation and determine the best response
            response_data = await self._generate_conversational_response(user_id, message, context, db)
            
            # Add AI response to context
            context['messages'].append({
                'role': 'assistant',
                'content': response_data['message'],
                'timestamp': datetime.now().isoformat(),
                'action': response_data.get('action', 'continue')
            })
            
            # Keep conversation history manageable
            if len(context['messages']) > 12:
                context['messages'] = context['messages'][-12:]
            
            return response_data
            
        except Exception as e:
            print(f"❌ Error in enhanced chat processing: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_response("I encountered an unexpected error. Please try again.")
    
    async def _generate_conversational_response(self, user_id: int, message: str, context: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Generate intelligent, conversational responses with proper flow management."""
        try:
            # Analyze user intent and extract information
            intent_analysis = await self._analyze_conversation_intent(message, context)
            
            print(f"🎯 Intent analysis: {intent_analysis['intent']}")
            
            # Handle different conversation flows
            if intent_analysis['intent'] == 'greeting':
                print("here in 1")
                return await self._handle_greeting(context)
            
            elif intent_analysis['intent'] == 'job_description':
                print("here in 2")
                return await self._handle_job_description(intent_analysis, context, db, user_id)
            
            elif intent_analysis['intent'] == 'clarification_response':
                print("here in 3")
                return await self._handle_clarification_response(intent_analysis, context, db, user_id)
            
            elif intent_analysis['intent'] == 'search_request':
                print("here in 4")
                return await self._handle_search_request(intent_analysis, context, db, user_id)
            
            elif intent_analysis['intent'] == 'candidate_inquiry':
                print("here in 5")
                return await self._handle_candidate_inquiry(intent_analysis, context, db, user_id)
            
            elif intent_analysis['intent'] == 'refinement':
                print("here in 6")
                return await self._handle_search_refinement(intent_analysis, context, db, user_id)
            
            else:
                print("here is else.")
                return await self._handle_general_conversation(intent_analysis, context, message)
            
        except Exception as e:
            print(f"❌ Error generating conversational response: {e}")
            return self._create_error_response("Let me try to help you in a different way.")
    
    async def _analyze_conversation_intent(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user message to understand intent and extract relevant information."""
        try:
            conversation_history = context.get('messages', [])[-4:]  # Last 4 messages for context
            current_stage = context.get('conversation_stage', 'initial')
            
            system_prompt = f"""You are an intelligent HR assistant that helps find the best candidates from CV database. 
            
            Analyze the user's message and determine their intent, then extract relevant information.
            
            Current conversation stage: {current_stage}
            Recent conversation: {json.dumps(conversation_history, indent=2) if conversation_history else 'None'}
            
            Classify the intent and extract information. Respond with ONLY valid JSON:
            
            {{
                "intent": "greeting|job_description|search_request|clarification_response|candidate_inquiry|refinement|general_conversation",
                "confidence": 0.85,
                "extracted_info": {{
                    "job_title": "specific role if mentioned",
                    "required_skills": ["skill1", "skill2"],
                    "preferred_skills": ["nice to have skills"],
                    "experience_level": "junior|mid|senior|lead|executive",
                    "experience_years": number_or_null,
                    "industry": "industry if mentioned",
                    "team_size": number_or_null,
                    "urgency": "urgent|normal|flexible",
                    "specific_requirements": ["any specific requirements"]
                }},
                "clarification_needed": {{
                    "needs_clarification": true/false,
                    "unclear_aspects": ["what needs clarification"],
                    "suggested_questions": ["questions to ask user"]
                }},
                "conversation_flow": {{
                    "next_stage": "initial|gathering_requirements|searching|refining|explaining",
                    "user_satisfaction": "seeking|engaged|satisfied|frustrated"
                }}
            }}
            
            Focus on understanding what the user really needs and whether we have enough information to search effectively."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User message: '{message}'"}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using GPT-4 for better analysis
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            
            response_text = response.choices[0].message.content.strip()
            print(f"🤖 Raw AI analysis: {response_text}")
            
            return json.loads(response_text)
            
        except Exception as e:
            print(f"❌ Error analyzing conversation intent: {e}")
            # Fallback analysis
            return self._create_fallback_intent_analysis(message)
    
    async def _handle_greeting(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initial greetings and introductions."""
        cv_count = len(context.get('cv_summaries', []))
        
        message = f"""👋 **Hello! I'm your AI recruitment assistant.**

I'm here to help you find the perfect candidates from your CV database. I have **{cv_count} CVs** ready for analysis.

**I can help you with:**
• Finding candidates for specific roles
• Matching skills to job requirements  
• Explaining why candidates are good fits
• Answering questions about candidate profiles

**To get started, you can:**
• Describe the role you're hiring for
• Ask for specific types of candidates
• Share a job description for detailed matching

**What position are you looking to fill today?**"""

        context['conversation_stage'] = 'gathering_requirements'
        
        return {
            'message': message,
            'action': 'continue',
            'suggestions': [
                'I need a senior software developer',
                'Looking for marketing professionals',
                'Find me data scientists with ML experience',
                'Show me project managers'
            ]
        }
    
    async def _handle_job_description(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], db: Session, user_id: int) -> Dict[str, Any]:
        """Handle when user provides a detailed job description."""
        extracted_info = intent_analysis.get('extracted_info', {})
        clarification = intent_analysis.get('clarification_needed', {})
        
        # Store job requirements
        context['job_requirements'].update(extracted_info)
        context['conversation_stage'] = 'gathering_requirements'
        
        # Check if we need clarification
        if clarification.get('needs_clarification', False):
            return await self._ask_clarifying_questions(clarification, context, extracted_info)
        
        # If we have enough information, proceed with search
        if self._has_sufficient_search_criteria(extracted_info):
            return await self._execute_intelligent_search(context, db, user_id)
        
        # Need more information
        return await self._request_more_details(extracted_info)
    
    async def _ask_clarifying_questions(self, clarification: Dict[str, Any], context: Dict[str, Any], extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """Ask intelligent clarifying questions based on what's unclear."""
        unclear_aspects = clarification.get('unclear_aspects', [])
        suggested_questions = clarification.get('suggested_questions', [])
        
        # Generate personalized clarifying questions
        questions_text = ""
        if suggested_questions:
            questions_text = "\n".join([f"• {q}" for q in suggested_questions[:3]])
        
        job_title = extracted_info.get('job_title', 'this role')
        
        message = f"""🤔 **I'd like to understand the requirements better for {job_title}.**

To find you the most suitable candidates, could you help clarify:

{questions_text}

**The more specific you can be, the better I can match candidates to your exact needs!**"""

        context['clarification_needed'] = unclear_aspects
        context['conversation_stage'] = 'gathering_requirements'
        
        return {
            'message': message,
            'action': 'continue',
            'suggestions': [
                'Entry to mid-level (1-4 years)',
                'Senior level (5+ years)',
                'Expert level (8+ years)',
                'Any experience level is fine'
            ]
        }
    
    async def _execute_intelligent_search(self, context: Dict[str, Any], db: Session, user_id: int) -> Dict[str, Any]:
        """Execute intelligent CV search with detailed matching."""
        try:
            job_requirements = context['job_requirements']
            cv_summaries = context.get('cv_summaries', [])
            
            print(f"🔍 Executing search with requirements: {job_requirements}")
            
            # Find matching candidates
            matches = await self._find_intelligent_matches(job_requirements, cv_summaries)
            
            if not matches:
                return await self._handle_no_matches(job_requirements, cv_summaries)
            
            # Format results for display
            formatted_results = await self._format_search_results(matches, job_requirements)
            
            # Store results in context
            context['last_search_results'] = matches
            context['conversation_stage'] = 'explaining'
            
            # Generate conversational response
            job_title = job_requirements.get('job_title', 'your requirements')
            skills_text = ', '.join(job_requirements.get('required_skills', [])[:3])
            
            message = f"""🎯 **Found {len(matches)} excellent candidates for {job_title}!**

**Search criteria:**
• **Role:** {job_title}
• **Key skills:** {skills_text}
• **Experience:** {job_requirements.get('experience_years', 'Any')} years

**Top candidates:**

{formatted_results['summary_text']}

**Would you like me to:**
• Explain why these candidates are good matches
• Show more detailed candidate profiles  
• Refine the search criteria
• Find candidates with different skills"""

            return {
                'message': message,
                'action': 'show_results',
                'results': formatted_results['detailed_results'],
                'suggestions': [
                    'Why is the top candidate a good fit?',
                    'Show me more details about candidate profiles',
                    'Find candidates with different skills',
                    'Refine the search criteria'
                ]
            }
            
        except Exception as e:
            print(f"❌ Error executing intelligent search: {e}")
            return self._create_error_response("I had trouble searching the candidates. Let me try a different approach.")
    
    async def _find_intelligent_matches(self, job_requirements: Dict[str, Any], cv_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find matches using advanced AI-powered semantic matching."""
        try:
            matches = []
            
            for cv in cv_summaries:
                match_score = await self._calculate_intelligent_match_score(job_requirements, cv)
                
                if match_score >= self.MATCH_THRESHOLD:
                    # Add detailed match analysis
                    match_analysis = await self._generate_match_analysis(job_requirements, cv, match_score)
                    
                    match_data = {
                        **cv,
                        'match_score': match_score,
                        'match_percentage': int(match_score * 100),
                        'match_analysis': match_analysis,
                        'match_reasons': match_analysis.get('reasons', []),
                        'skills_alignment': match_analysis.get('skills_alignment', {}),
                        'experience_fit': match_analysis.get('experience_fit', 'Good fit')
                    }
                    matches.append(match_data)
            
            # Sort by match score
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            return matches[:self.MAX_RESULTS]
            
        except Exception as e:
            print(f"❌ Error finding intelligent matches: {e}")
            return []
    
    async def _calculate_intelligent_match_score(self, job_requirements: Dict[str, Any], cv: Dict[str, Any]) -> float:
        """Calculate intelligent match score using GPT-4."""
        try:
            cv_summary = cv.get('summary', {})
            cv_skills = cv.get('skills', [])
            cv_role = cv.get('role', '')
            cv_experience = cv.get('experience', 0)
            
            system_prompt = f"""You are an expert HR matching system. Calculate a precise match score (0.0-1.0) between job requirements and candidate.

SCORING FRAMEWORK:
- Role alignment (25%): How well candidate's experience matches the job title
- Skills match (35%): Required skills vs candidate skills (weighted by importance)
- Experience level (20%): Years and type of experience appropriateness  
- Cultural/soft skills fit (10%): Based on candidate background
- Growth potential (10%): Candidate's learning trajectory and adaptability

IMPORTANT: 
- Score 0.6+ only for genuinely suitable candidates
- Consider both exact matches and transferable skills
- Account for career progression and potential

Job Requirements:
{json.dumps(job_requirements, indent=2)}

Candidate Profile:
- Role: {cv_role}
- Experience: {cv_experience} years
- Skills: {cv_skills}
- Summary: {cv_summary.get('summary', '') if isinstance(cv_summary, dict) else str(cv_summary)[:200]}

Return only a decimal number between 0.0 and 1.0"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Calculate the match score for this candidate."}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.1,
                max_tokens=50
            )
            
            score_text = response.choices[0].message.content.strip()
            
            # Extract score
            score_match = re.search(r'\b(0\.\d+|1\.0|0\.0)\b', score_text)
            if score_match:
                return float(score_match.group(1))
            
            return 0.0
            
        except Exception as e:
            print(f"❌ Error calculating match score: {e}")
            return 0.0
    
    async def _generate_match_analysis(self, job_requirements: Dict[str, Any], cv: Dict[str, Any], match_score: float) -> Dict[str, Any]:
        """Generate detailed match analysis explaining why candidate is a good fit."""
        try:
            cv_summary = cv.get('summary', {})
            cv_skills = cv.get('skills', [])
            cv_role = cv.get('role', '')
            
            system_prompt = f"""Generate a detailed match analysis explaining why this candidate is a good fit for the role.

Job Requirements:
{json.dumps(job_requirements, indent=2)}

Candidate:
- Role: {cv_role}
- Skills: {cv_skills}
- Experience: {cv.get('experience', 0)} years
- Match Score: {match_score * 100:.1f}%

Provide analysis in JSON format:
{{
    "reasons": ["specific reason 1", "specific reason 2", "specific reason 3"],
    "skills_alignment": {{
        "strong_matches": ["skill1", "skill2"],
        "partial_matches": ["skill3"],
        "missing_skills": ["skill4"]
    }},
    "experience_fit": "Perfect fit|Good fit|Adequate fit|Potential with training",
    "key_strengths": ["strength 1", "strength 2"],
    "development_areas": ["area 1", "area 2"],
    "overall_assessment": "2-3 sentence summary of why this candidate works"
}}

Focus on specific, actionable insights that help hiring decisions."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Analyze this candidate match."}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3,
                max_tokens=600
            )
            
            analysis_text = response.choices[0].message.content.strip()
            return json.loads(analysis_text)
            
        except Exception as e:
            print(f"❌ Error generating match analysis: {e}")
            return {
                "reasons": ["Experience aligns with requirements", "Has relevant skills"],
                "skills_alignment": {"strong_matches": [], "partial_matches": [], "missing_skills": []},
                "experience_fit": "Good fit",
                "key_strengths": ["Professional experience"],
                "development_areas": [],
                "overall_assessment": "This candidate shows promise for the role."
            }
    
    async def _format_search_results(self, matches: List[Dict[str, Any]], job_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Format search results for both display and API response."""
        summary_text = ""
        detailed_results = {
            'total_cvs_processed': len(self.conversation_contexts.get(list(self.conversation_contexts.keys())[0] if self.conversation_contexts else 0, {}).get('cv_summaries', [])),
            'matches': [],
            'processing_time': '< 2 seconds'
        }
        
        for i, match in enumerate(matches, 1):
            candidate_name = "Professional Candidate"
            if isinstance(match.get('summary'), dict):
                candidate_name = match['summary'].get('candidate_name', 'Professional Candidate')
            
            # Summary text for message
            summary_text += f"""**{i}. {candidate_name}** ({match['match_percentage']}% match)
• **Role:** {match.get('role', 'Professional')}
• **Experience:** {match.get('experience', 0)} years
• **Top skills:** {', '.join(match.get('skills', [])[:3])}
• **Why good fit:** {match['match_analysis'].get('overall_assessment', 'Strong candidate')}

"""
            
            # Detailed results for API
            detailed_results['matches'].append({
                'cv_filename': match.get('filename', 'Unknown'),
                'candidate_name': candidate_name,
                'relevance_score': match['match_percentage'],
                'candidate_summary': match['match_analysis'].get('overall_assessment', 'Strong candidate'),
                'key_skills': json.dumps(match.get('skills', [])),
                'match_analysis': f"Strong match with {match['match_percentage']}% relevance. " + 
                                '. '.join(match['match_reasons'][:2]),
                'download_url': f"#download-{match.get('file_id', '')}",
                'experience_years': match.get('experience', 0)
            })
        
        return {
            'summary_text': summary_text.strip(),
            'detailed_results': detailed_results
        }
    
    async def _handle_candidate_inquiry(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], db: Session, user_id: int) -> Dict[str, Any]:
        """Handle questions about specific candidates."""
        try:
            last_results = context.get('last_search_results', [])
            
            if not last_results:
                return {
                    'message': "I don't have any recent search results to discuss. Would you like me to search for candidates first?",
                    'action': 'continue',
                    'suggestions': [
                        'Find me senior developers',
                        'Search for marketing professionals',
                        'Show me data scientists'
                    ]
                }
            
            # Identify which candidate they're asking about
            message_content = intent_analysis.get('original_message', '').lower()
            
            # Check if asking about top candidate or specific one
            if 'top' in message_content or 'first' in message_content or '1' in message_content:
                candidate = last_results[0]
            elif 'why' in message_content:
                # Explain the top candidate
                candidate = last_results[0]
                return await self._explain_candidate_match(candidate, context)
            else:
                # Default to top candidate
                candidate = last_results[0]
            
            return await self._provide_candidate_details(candidate, context)
            
        except Exception as e:
            print(f"❌ Error handling candidate inquiry: {e}")
            return self._create_error_response("Let me help you understand the candidate matches better.")
    
    async def _explain_candidate_match(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide detailed explanation of why a candidate is a good match."""
        try:
            match_analysis = candidate.get('match_analysis', {})
            candidate_name = "This candidate"
            
            if isinstance(candidate.get('summary'), dict):
                candidate_name = candidate['summary'].get('candidate_name', 'This candidate')
            
            reasons = match_analysis.get('reasons', [])
            skills_alignment = match_analysis.get('skills_alignment', {})
            experience_fit = match_analysis.get('experience_fit', 'Good fit')
            
            message = f"""🎯 **Why {candidate_name} is a {candidate['match_percentage']}% match:**

**Key Match Reasons:**
{chr(10).join([f'• {reason}' for reason in reasons[:3]])}

**Skills Analysis:**
• **Strong matches:** {', '.join(skills_alignment.get('strong_matches', [])[:4])}
• **Partial matches:** {', '.join(skills_alignment.get('partial_matches', [])[:3])}
{'• **Areas for development:** ' + ', '.join(skills_alignment.get('development_areas', [])[:2]) if skills_alignment.get('development_areas') else ''}

**Experience Level:** {experience_fit}

**Overall Assessment:**
{match_analysis.get('overall_assessment', 'This candidate shows strong potential for the role.')}

**Would you like me to:**
• Show more candidates with similar profiles
• Compare this candidate with others
• Find candidates with complementary skills"""

            return {
                'message': message,
                'action': 'continue',
                'suggestions': [
                    'Show me similar candidates',
                    'Compare with other matches',
                    'Find complementary profiles',
                    'What about the second candidate?'
                ]
            }
            
        except Exception as e:
            print(f"❌ Error explaining candidate match: {e}")
            return self._create_error_response("Let me provide candidate information in a simpler format.")
    
    # Additional helper methods
    def _get_cached_cv_summaries(self, user_id: int) -> List[Dict[str, Any]]:
        """Get CV summaries from cache only (no waiting)."""
        with self.cache_lock:
            return self.cv_cache.get(user_id, [])

    async def get_cv_summaries(self, user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get cached CV summaries or generate them."""
        with self.cache_lock:
            if user_id in self.cv_cache:
                return self.cv_cache[user_id]
        
        # If not cached, return empty and let background processing handle it
        return []
    
    async def _process_cvs_background(self, user_id: int, db: Session):
        """Process CVs in the background."""
        try:
            # This would call the existing CV processing logic
            from app.services.intelligent_chat_agent_service import intelligent_chat_agent_service
            cv_summaries = await intelligent_chat_agent_service.get_cv_summaries(user_id, db)
            
            # Cache the results
            with self.cache_lock:
                self.cv_cache[user_id] = cv_summaries
                
            print(f"✅ Background CV processing completed for user {user_id}: {len(cv_summaries)} CVs")
            
        except Exception as e:
            print(f"❌ Error in background CV processing: {e}")
    
    def _create_configuration_response(self) -> Dict[str, Any]:
        """Create response when configuration is needed."""
        return {
            'message': """🔧 **Configuration Required**

To use the AI chat assistant, please:
1. Add your OpenAI API key in Settings
2. Connect your Google Drive with CVs
3. Return here to start finding candidates

**I'll be ready to help once you're set up!**""",
            'action': 'configure',
            'suggestions': [
                'Go to Settings',
                'Configure OpenAI API',
                'Connect Google Drive'
            ]
        }
    
    def _create_processing_response(self, message: str) -> Dict[str, Any]:
        """Create response during CV processing."""
        return {
            'message': """🔄 **Processing your CVs...**

I'm analyzing the CVs in your Google Drive to create intelligent candidate profiles. This usually takes 1-2 minutes.

**What I'm doing:**
• Extracting candidate information and skills
• Creating searchable profiles
• Preparing AI-powered matching capabilities

**While I process, feel free to describe the role you're hiring for!**""",
            'action': 'processing',
            'suggestions': [
                'I need a senior software developer',
                'Looking for marketing manager',
                'Find data science professionals',
                'Check processing status'
            ]
        }
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            'message': f"❌ {message}\n\nLet me help you in a different way. What would you like to do?",
            'action': 'continue',
            'suggestions': [
                'Search for candidates',
                'Describe the role you need',
                'Show available candidates',
                'Help with configuration'
            ]
        }
    
    def _create_fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Create fallback intent analysis when AI fails."""
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in ['hello', 'hi', 'hey', 'start']):
            return {'intent': 'greeting', 'confidence': 0.8}
        
        if any(search_term in message_lower for search_term in ['find', 'search', 'looking for', 'need']):
            return {
                'intent': 'search_request',
                'confidence': 0.7,
                'extracted_info': {
                    'job_title': self._extract_job_title(message),
                    'required_skills': self._extract_skills(message)
                }
            }
        
        return {'intent': 'general_conversation', 'confidence': 0.5}
    
    def _extract_job_title(self, message: str) -> str:
        """Extract job title from message."""
        message_lower = message.lower()
        titles = ['developer', 'engineer', 'manager', 'analyst', 'designer', 'scientist']
        
        for title in titles:
            if title in message_lower:
                return title.title()
        
        return ""
    
    def _extract_skills(self, message: str) -> List[str]:
        """Extract skills from message."""
        message_lower = message.lower()
        skills = ['python', 'javascript', 'react', 'angular', 'node.js', 'java', 'machine learning', 'data analysis']
        
        return [skill for skill in skills if skill in message_lower]
    
    def clear_conversation_context(self, user_id: int):
        """Clear conversation context for a user."""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
    
    async def execute_search(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Execute CV search based on stored conversation context."""
        try:
            context = self.get_conversation_context(user_id)
            job_requirements = context.get('job_requirements', {})
            
            if not job_requirements:
                return {
                    'message': "I need more information about what you're looking for to execute a search.",
                    'action': 'continue',
                    'suggestions': ['Describe the role', 'List required skills', 'Specify experience level']
                }
            
            return await self._execute_intelligent_search(context, db, user_id)
            
        except Exception as e:
            print(f"❌ Error executing search: {e}")
            return {
                'message': "I encountered an error during the search. Please try again.",
                'action': 'error',
                'suggestions': ['Try a different search', 'Refine criteria']
            }
    
    def get_search_suggestions(self, user_id: int) -> List[str]:
        """Get contextually aware search suggestions."""
        context = self.get_conversation_context(user_id)
        cv_summaries = context.get('cv_summaries', [])
        last_results = context.get('last_search_results')
        
        if last_results:
            return [
                "Tell me more about the top candidate",
                "Show me similar profiles",
                "Find candidates with different skills",
                "Why is this candidate a good match?"
            ]
        
        if not cv_summaries:
            return [
                "Find me senior developers",
                "Looking for marketing professionals", 
                "Show me data scientists",
                "Need project managers"
            ]
        
        # Generate suggestions based on available CVs
        available_roles = list(set([cv.get('role', '') for cv in cv_summaries if cv.get('role')]))[:4]
        return [f"Find me {role.lower()}s" for role in available_roles] if available_roles else [
            "Search for specific skills",
            "Find senior level candidates",
            "Show me all available profiles"
        ]
    
    def _has_sufficient_search_criteria(self, extracted_info: Dict[str, Any]) -> bool:
        """Check if we have enough information to perform a search."""
        return bool(
            extracted_info.get('job_title') or 
            extracted_info.get('required_skills') or
            extracted_info.get('industry')
        )
    
    # Additional methods for handling different conversation flows...
    async def _handle_search_refinement(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], db: Session, user_id: int) -> Dict[str, Any]:
        """Handle search refinement requests."""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            last_results = context.get('last_search_results', [])
            
            if not last_results:
                return {
                    'message': "I don't have any previous search results to refine. Let's start with a new search!",
                    'action': 'continue',
                    'suggestions': [
                        'Find senior developers',
                        'Search for specific skills',
                        'Look for marketing professionals'
                    ]
                }
            
            # Update job requirements with new criteria
            job_requirements = context.get('job_requirements', {})
            
            # Merge new requirements
            for key, value in extracted_info.items():
                if value:  # Only update if value is not empty
                    job_requirements[key] = value
            
            context['job_requirements'] = job_requirements
            context['conversation_stage'] = 'refining'
            
            # Execute refined search
            return await self._execute_intelligent_search(context, db, user_id)
            
        except Exception as e:
            print(f"❌ Error handling search refinement: {e}")
            return {
                'message': "I can help refine your search. What aspects would you like to adjust?",
                'action': 'continue',
                'suggestions': ['Change experience level', 'Add more skills', 'Different role type']
            }
    
    async def _handle_general_conversation(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Handle general conversation that doesn't fit other categories."""
        return {
            'message': "I'm here to help you find the best candidates. What kind of role are you looking to fill?",
            'action': 'continue',
            'suggestions': ['Find senior developers', 'Search for managers', 'Show me analysts']
        }
    
    async def _handle_no_matches(self, job_requirements: Dict[str, Any], cv_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle when no candidates match the criteria."""
        return {
            'message': "I couldn't find exact matches. Would you like me to broaden the search criteria?",
            'action': 'continue',
            'suggestions': ['Broaden skill requirements', 'Lower experience needs', 'Show all candidates']
        }
    
    async def _request_more_details(self, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """Request more details when information is insufficient."""
        return {
            'message': "Could you provide more details about the role? For example, required skills or experience level?",
            'action': 'continue',
            'suggestions': ['Senior level position', 'Entry to mid-level', 'Specific technology skills']
        }
    
    async def _provide_candidate_details(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide detailed information about a specific candidate."""
        return {
            'message': "Here are the detailed candidate information...",
            'action': 'continue',
            'suggestions': ['Show next candidate', 'Compare candidates', 'Refine search']
        }
    
    async def _handle_search_request(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], db: Session, user_id: int) -> Dict[str, Any]:
        """Handle search requests from users."""
        extracted_info = intent_analysis.get('extracted_info', {})
        clarification = intent_analysis.get('clarification_needed', {})
        
        # Store job requirements
        context['job_requirements'].update(extracted_info)
        context['conversation_stage'] = 'gathering_requirements'
        
        # Check if we need clarification
        if clarification.get('needs_clarification', False):
            return await self._ask_clarifying_questions(clarification, context, extracted_info)
        
        # If we have enough information, proceed with search
        if self._has_sufficient_search_criteria(extracted_info):
            return await self._execute_intelligent_search(context, db, user_id)
        
        # Need more information
        return await self._request_more_details(extracted_info)
    
    async def _handle_clarification_response(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], db: Session, user_id: int) -> Dict[str, Any]:
        """Handle user responses to clarification questions."""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            
            # Update job requirements with clarification responses
            job_requirements = context.get('job_requirements', {})
            job_requirements.update(extracted_info)
            context['job_requirements'] = job_requirements
            
            # Clear clarification needed
            context['clarification_needed'] = []
            context['conversation_stage'] = 'searching'
            
            # Check if we now have sufficient criteria
            if self._has_sufficient_search_criteria(job_requirements):
                return await self._execute_intelligent_search(context, db, user_id)
            else:
                # Still need more information
                return await self._request_more_details(job_requirements)
                
        except Exception as e:
            print(f"❌ Error handling clarification response: {e}")
            return await self._request_more_details({})

# Global instance
enhanced_chat_agent_service = EnhancedChatAgentService()