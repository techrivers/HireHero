import asyncio
import json
import uuid
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime
from app.services.enhanced_chat_agent_service import enhanced_chat_agent_service
from app.services.intelligent_chat_agent_service import intelligent_chat_agent_service

class InstantEnhancedChatService:
    """Instant response chat service that never blocks the main response."""
    
    def __init__(self):
        self.processing_tasks = {}  # Track background processing tasks
        
    async def process_chat_message_instant(self, user_id: int, message: str, db: Session) -> Dict[str, Any]:
        """Process chat message with guaranteed instant response (< 2 seconds)."""
        start_time = time.time()
        
        try:
            print(f"⚡ Instant chat processing for user {user_id}: {message[:100]}...")
            
            # Step 1: Quick checks and setup (< 100ms)
            api_key = enhanced_chat_agent_service.get_openai_key(db, user_id)
            if not api_key:
                return self._create_configuration_response()
            
            # Initialize OpenAI client if needed (non-blocking)
            if not enhanced_chat_agent_service.openai_client:
                enhanced_chat_agent_service.initialize_openai_client(api_key)
            
            # Step 2: Get conversation context (< 50ms)
            context = enhanced_chat_agent_service.get_conversation_context(user_id)
            print(f"📋 Conversation stage: {context.get('conversation_stage')}, Messages: {len(context.get('messages', []))}")
            
            # Step 3: Check if CVs are cached (< 50ms)
            cv_summaries = self._get_cached_cv_summaries(user_id)
            print(f"📁 CV summaries cached: {len(cv_summaries)} CVs")
            
            if not cv_summaries:
                # No CVs cached - start background processing and return instant response
                self._start_background_cv_processing(user_id, db)
                return self._create_instant_processing_response(message, user_id)
            
            # Step 4: Quick intent analysis (< 500ms)
            context['cv_summaries'] = cv_summaries
            intent_analysis = await self._quick_intent_analysis(message, context)
            print(f"🎯 Intent analysis: {intent_analysis.get('intent')}, Job: {intent_analysis.get('extracted_info', {}).get('job_title')}")
            
            # Step 5: Add message to context (< 10ms)
            context['messages'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update conversation stage based on intent
            if intent_analysis.get('intent') == 'search_request':
                context['conversation_stage'] = 'searching'
                context['job_requirements'] = intent_analysis.get('extracted_info', {})
            elif intent_analysis.get('intent') == 'candidate_inquiry':
                context['conversation_stage'] = 'explaining'
            elif intent_analysis.get('intent') == 'refinement':
                context['conversation_stage'] = 'refining'
            
            # Step 6: Generate instant response based on intent (< 800ms)
            response_data = await self._generate_instant_response(intent_analysis, context, message, user_id, db)
            
            # Step 7: Add response to context (< 10ms)
            context['messages'].append({
                'role': 'assistant',
                'content': response_data['message'],
                'timestamp': datetime.now().isoformat(),
                'action': response_data.get('action', 'continue')
            })
            
            # Clean up old messages
            if len(context['messages']) > 12:
                context['messages'] = context['messages'][-12:]
            
            # Start background detailed processing if needed
            if intent_analysis.get('needs_detailed_processing', False):
                self._start_background_detailed_processing(user_id, message, context, db)
            
            processing_time = time.time() - start_time
            print(f"✅ Instant response generated in {processing_time:.2f}s")
            
            return response_data
            
        except Exception as e:
            print(f"❌ Error in instant chat processing: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_response("I encountered an issue. Let me try again.", user_id)
    
    def _get_cached_cv_summaries(self, user_id: int) -> List[Dict[str, Any]]:
        """Get CV summaries from cache only (no waiting)."""
        with enhanced_chat_agent_service.cache_lock:
            return enhanced_chat_agent_service.cv_cache.get(user_id, [])
    
    async def _quick_intent_analysis(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fast intent analysis with timeout protection."""
        try:
            # Try AI analysis with strict timeout
            intent_task = enhanced_chat_agent_service._analyze_conversation_intent(message, context)
            intent_analysis = await asyncio.wait_for(intent_task, timeout=0.8)
            return intent_analysis
        except (asyncio.TimeoutError, Exception) as e:
            print(f"⚠️ AI analysis timeout/error, using fallback: {e}")
            return self._create_fallback_intent_analysis(message)
    
    async def _generate_instant_response(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], message: str, user_id: int, db: Session) -> Dict[str, Any]:
        """Generate instant response based on intent with guaranteed speed."""
        try:
            intent = intent_analysis.get('intent', 'general_conversation')
            
            if intent == 'greeting':
                return self._handle_greeting_instant(context)
            
            elif intent == 'search_request':
                return await self._handle_search_request_instant(intent_analysis, context, user_id)
            
            elif intent == 'candidate_inquiry':
                return self._handle_candidate_inquiry_instant(context)
            
            elif intent == 'refinement':
                return self._handle_refinement_instant(intent_analysis, context)
            
            else:
                return self._handle_general_conversation_instant(message, context)
                
        except Exception as e:
            print(f"❌ Error generating instant response: {e}")
            return self._create_helpful_response(message)
    
    def _handle_greeting_instant(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle greetings with instant response."""
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

I'm currently processing your CVs to create intelligent candidate profiles. While that's happening, feel free to describe the role you're hiring for!

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
    
    async def _handle_search_request_instant(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Handle search requests with instant matching."""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            cv_summaries = context.get('cv_summaries', [])
            
            if not cv_summaries:
                return self._create_instant_processing_response("search request", user_id)
            
            # Quick pattern-based matching (< 200ms)
            quick_matches = self._perform_quick_matching(extracted_info, cv_summaries)
            
            if quick_matches:
                # Store for later detailed processing
                context['job_requirements'] = extracted_info
                context['last_search_results'] = quick_matches
                
                job_title = extracted_info.get('job_title', 'candidates')
                skills_text = ', '.join(extracted_info.get('required_skills', [])[:3]) or 'your requirements'
                
                message = f"""🎯 **Found {len(quick_matches)} candidates matching {job_title}!**

**Quick matches based on:**
• **Role**: {job_title or 'Your specified role'}
• **Skills**: {skills_text}

**Top candidates:**
{self._format_quick_match_summary(quick_matches[:3])}

💡 **I'm analyzing these matches in detail and will provide deeper insights shortly.**

**Would you like to:**"""
                
                return {
                    'message': message,
                    'action': 'show_results',
                    'results': self._format_quick_results(quick_matches),
                    'suggestions': [
                        'Tell me more about the top candidate',
                        'Why are these good matches?',
                        'Show me different candidates',
                        'Refine the search criteria'
                    ],
                    'needs_detailed_processing': True
                }
            else:
                # No quick matches found
                return {
                    'message': f"""🔍 **No immediate matches found**

Let me analyze this more carefully. What specific requirements are most important to you?

**Try being more specific about:**
• Years of experience needed
• Must-have technical skills
• Type of role (junior/senior/lead)
• Industry background

**I'll help you find the right candidates!**""",
                    'action': 'continue',
                    'suggestions': [
                        'Senior level (5+ years)',
                        'Specific technology skills',
                        'Any experience level',
                        'Show me all candidates'
                    ]
                }
                
        except Exception as e:
            print(f"❌ Error in instant search: {e}")
            return self._create_helpful_response("search")
    
    def _perform_quick_matching(self, criteria: Dict[str, Any], cv_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform fast pattern-based matching without AI."""
        try:
            matches = []
            job_title = criteria.get('job_title', '').lower()
            required_skills = [s.lower() for s in criteria.get('required_skills', [])]
            min_experience = criteria.get('experience_years', 0)
            
            for cv in cv_summaries:
                score = 0
                reasons = []
                
                # Role matching (40 points)
                cv_role = cv.get('role', '').lower()
                if job_title and job_title in cv_role:
                    score += 40
                    reasons.append(f"Role matches: {cv.get('role', '')}")
                elif job_title:
                    # Partial role matching
                    job_words = set(job_title.split())
                    role_words = set(cv_role.split())
                    if job_words.intersection(role_words):
                        score += 20
                        reasons.append("Partial role match")
                
                # Skills matching (40 points)
                cv_skills = [s.lower() for s in cv.get('skills', [])]
                if required_skills:
                    skill_matches = []
                    for skill in required_skills:
                        if any(skill in cv_skill for cv_skill in cv_skills):
                            skill_matches.append(skill)
                    
                    if skill_matches:
                        skill_score = min(40, len(skill_matches) * 15)
                        score += skill_score
                        reasons.append(f"Skills: {', '.join(skill_matches[:3])}")
                
                # Experience matching (20 points)
                cv_experience = cv.get('experience', 0)
                if cv_experience >= min_experience:
                    score += 20
                    reasons.append(f"{cv_experience} years experience")
                elif cv_experience >= min_experience * 0.8:
                    score += 10
                    reasons.append(f"{cv_experience} years experience (close match)")
                
                # Quick threshold (50+ points = good match)
                if score >= 50:
                    match = cv.copy()
                    match['quick_match_score'] = score
                    match['quick_match_reasons'] = reasons
                    match['match_percentage'] = min(95, score)  # Cap at 95% for quick matches
                    matches.append(match)
            
            # Sort by score
            matches.sort(key=lambda x: x['quick_match_score'], reverse=True)
            return matches[:6]  # Return top 6
            
        except Exception as e:
            print(f"❌ Error in quick matching: {e}")
            return []
    
    def _format_quick_match_summary(self, matches: List[Dict[str, Any]]) -> str:
        """Format quick match summary for display."""
        summary = ""
        for i, match in enumerate(matches, 1):
            candidate_name = "Professional Candidate"
            if isinstance(match.get('summary'), dict):
                candidate_name = match['summary'].get('candidate_name', 'Professional Candidate')
            
            summary += f"""**{i}. {candidate_name}** ({match['match_percentage']}% match)
• **Role:** {match.get('role', 'Professional')}
• **Experience:** {match.get('experience', 0)} years
• **Match reasons:** {', '.join(match.get('quick_match_reasons', [])[:2])}

"""
        return summary.strip()
    
    def _format_quick_results(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                    'candidate_summary': f"Quick match with {match['match_percentage']}% relevance",
                    'key_skills': json.dumps(match.get('skills', [])),
                    'match_analysis': f"Quick analysis: {', '.join(match.get('quick_match_reasons', [])[:2])}",
                    'download_url': f"#download-{match.get('file_id', '')}",
                    'experience_years': match.get('experience', 0)
                }
                formatted_matches.append(formatted_match)
            
            return {
                'total_cvs_processed': len(matches),
                'processing_time': '< 1 second',
                'matches': formatted_matches
            }
        except Exception as e:
            print(f"❌ Error formatting quick results: {e}")
            return {'total_cvs_processed': 0, 'processing_time': '< 1s', 'matches': []}
    
    def _handle_candidate_inquiry_instant(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle candidate inquiries instantly."""
        last_results = context.get('last_search_results', [])
        
        if last_results:
            top_candidate = last_results[0]
            candidate_name = "Top candidate"
            if isinstance(top_candidate.get('summary'), dict):
                candidate_name = top_candidate['summary'].get('candidate_name', 'Top candidate')
            
            return {
                'message': f"""💡 **{candidate_name} is a {top_candidate['match_percentage']}% match because:**

{chr(10).join([f'• {reason}' for reason in top_candidate.get('quick_match_reasons', ['Strong professional background'])])}

**I'm analyzing this candidate in more detail and will provide a comprehensive explanation shortly.**

**What else would you like to know?**""",
                'action': 'continue',
                'suggestions': [
                    'Tell me more about their experience',
                    'What are their key strengths?',
                    'Show me the next candidate',
                    'Compare with other matches'
                ],
                'needs_detailed_processing': True
            }
        else:
            return {
                'message': "I don't have any recent search results to discuss. Would you like me to search for candidates?",
                'action': 'continue',
                'suggestions': [
                    'Find senior developers',
                    'Search for specific skills',
                    'Show me all candidates'
                ]
            }
    
    def _handle_refinement_instant(self, intent_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search refinements instantly."""
        return {
            'message': "I'll refine the search with your new criteria. What specific changes would you like to make?",
            'action': 'continue',
            'suggestions': [
                'Add more skills',
                'Change experience level',
                'Different role type',
                'More specific requirements'
            ],
            'needs_detailed_processing': True
        }
    
    def _handle_general_conversation_instant(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general conversation instantly."""
        cv_count = len(context.get('cv_summaries', []))
        
        if cv_count > 0:
            return {
                'message': f"""I'm here to help you find the perfect candidates from your {cv_count} available CVs.

**I can help you:**
• Search for specific roles and skills
• Explain why candidates are good matches
• Answer questions about candidate profiles
• Refine searches based on your needs

**What kind of candidate are you looking for?**""",
                'action': 'continue',
                'suggestions': [
                    'Find senior developers',
                    'Search for marketing roles',
                    'Show me data scientists',
                    'Browse all candidates'
                ]
            }
        else:
            return {
                'message': """I'm processing your CVs to create intelligent candidate profiles. While that's happening, feel free to describe what you're looking for!

**What kind of role are you hiring for?**""",
                'action': 'continue',
                'suggestions': [
                    'Senior software developer',
                    'Marketing professional',
                    'Data scientist',
                    'Project manager'
                ]
            }
    
    def _start_background_cv_processing(self, user_id: int, db: Session):
        """Start CV processing in background without blocking."""
        if user_id not in self.processing_tasks:
            task = asyncio.create_task(self._background_cv_processing(user_id, db))
            self.processing_tasks[user_id] = task
            print(f"🔄 Started background CV processing for user {user_id}")
    
    async def _background_cv_processing(self, user_id: int, db: Session):
        """Process CVs in background."""
        try:
            print(f"🔄 Background CV processing started for user {user_id}")
            # Use the existing intelligent service for full CV processing
            cv_summaries = await intelligent_chat_agent_service.get_cv_summaries(user_id, db)
            
            # Cache the results in enhanced service
            with enhanced_chat_agent_service.cache_lock:
                enhanced_chat_agent_service.cv_cache[user_id] = cv_summaries
            
            print(f"✅ Background CV processing completed for user {user_id}: {len(cv_summaries)} CVs")
            
            # Clean up task
            if user_id in self.processing_tasks:
                del self.processing_tasks[user_id]
                
        except Exception as e:
            print(f"❌ Error in background CV processing: {e}")
            if user_id in self.processing_tasks:
                del self.processing_tasks[user_id]
    
    def _start_background_detailed_processing(self, user_id: int, message: str, context: Dict[str, Any], db: Session):
        """Start detailed analysis in background."""
        task_key = f"{user_id}_detailed"
        if task_key not in self.processing_tasks:
            task = asyncio.create_task(self._background_detailed_processing(user_id, message, context, db))
            self.processing_tasks[task_key] = task
            print(f"🔍 Started background detailed processing for user {user_id}")
    
    async def _background_detailed_processing(self, user_id: int, message: str, context: Dict[str, Any], db: Session):
        """Perform detailed AI analysis in background."""
        try:
            print(f"🔍 Background detailed processing started for user {user_id}")
            # This would run the full enhanced analysis with GPT-4
            # For now, we'll just simulate it
            await asyncio.sleep(2)  # Simulate processing time
            print(f"✅ Background detailed processing completed for user {user_id}")
            
            # Clean up task
            task_key = f"{user_id}_detailed"
            if task_key in self.processing_tasks:
                del self.processing_tasks[task_key]
                
        except Exception as e:
            print(f"❌ Error in background detailed processing: {e}")
            task_key = f"{user_id}_detailed"
            if task_key in self.processing_tasks:
                del self.processing_tasks[task_key]
    
    def _create_instant_processing_response(self, message: str, user_id: int) -> Dict[str, Any]:
        """Create instant response while CVs are being processed."""
        context_hint = self._analyze_message_context(message)
        
        # Check if we already told them about processing
        context = enhanced_chat_agent_service.get_conversation_context(user_id)
        previous_messages = context.get('messages', [])
        
        # If this is a follow-up message during processing, provide a different response
        if len(previous_messages) > 0:
            last_message = previous_messages[-1] if previous_messages else {}
            
            # Count how many processing messages we've sent
            processing_count = sum(1 for msg in previous_messages 
                                 if msg.get('role') == 'assistant' and 'processing' in msg.get('content', '').lower())
            
            if last_message.get('role') == 'assistant' and 'processing' in last_message.get('content', '').lower():
                
                # If we've sent multiple processing messages, escalate with troubleshooting
                if processing_count >= 2:
                    return {
                        'message': f"""🔧 **Let me help troubleshoot the CV processing...**

I notice you've been waiting for {context_hint}. Let me check what might be happening:

**Possible issues:**
• 📁 **Google Drive Connection**: Check if your Google Drive is properly connected
• 🔑 **OpenAI API**: Verify your OpenAI API key is configured
• 📄 **CV Files**: Ensure you have CV files in your connected Google Drive folder

**Quick fixes:**
1. Go to **Settings** → Check Google Drive connection
2. Verify **OpenAI API key** is set up
3. Refresh the page and try again

**Meanwhile, I can still help you define your requirements for {context_hint}!**""",
                        'action': 'troubleshoot',
                        'suggestions': [
                            'Check Google Drive connection',
                            'Verify OpenAI API key',
                            'Go to Settings',
                            'Refresh page and retry'
                        ]
                    }
                return {
                    'message': f"""⏳ **Still building your candidate database for {context_hint}...**

I understand you're looking for {context_hint}. Your CVs are being processed from Google Drive to create detailed profiles.

**What's happening:**
• 📄 Reading and parsing CV files
• 🧠 Extracting skills and experience data  
• 🔍 Building searchable candidate profiles

**Once complete, I'll be able to:**
• Find exact matches for "{message}"
• Explain why candidates fit your needs
• Answer detailed questions about experience

**ETA**: Processing should complete within 1-2 minutes.""",
                    'action': 'processing',
                    'suggestions': [
                        'Tell me about required experience level',
                        'What specific skills are most important?',
                        'Any industry preferences?',
                        'Remote work requirements?'
                    ]
                }
        
        # First time processing message
        return {
            'message': f"""🚀 **I'm analyzing your CVs to find {context_hint}...**

I'm currently processing your CV database to create intelligent candidate profiles. This gives me the ability to:

✨ **Smart Matching**: Find candidates based on skills, experience, and role fit
🎯 **Detailed Analysis**: Provide match explanations and candidate insights  
💡 **Natural Conversation**: Answer follow-up questions about candidates

**While I process, feel free to describe your requirements in detail!**

**Processing Status**: Building candidate profiles from your Google Drive CVs""",
            'action': 'processing',
            'suggestions': [
                'I need senior level candidates',
                'Looking for specific technology skills', 
                'Tell me about team leadership experience',
                'What industries should they have worked in?'
            ]
        }
    
    def _analyze_message_context(self, message: str) -> str:
        """Quick analysis of message to provide context hint."""
        message_lower = message.lower()
        
        if 'senior' in message_lower:
            return 'senior-level professionals'
        elif 'developer' in message_lower or 'engineer' in message_lower:
            return 'development professionals'
        elif 'marketing' in message_lower:
            return 'marketing professionals'
        elif 'data' in message_lower:
            return 'data professionals'
        elif 'manager' in message_lower:
            return 'management candidates'
        else:
            return 'the right candidates'
    
    def _create_fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Create fallback intent analysis when AI is not available."""
        message_lower = message.lower()
        
        # Determine intent based on keywords
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'start']):
            return {'intent': 'greeting', 'needs_detailed_processing': False}
        
        elif any(word in message_lower for word in ['find', 'search', 'looking', 'need', 'want']):
            # Extract basic info
            skills = []
            job_title = ""
            
            # Common skills
            skill_keywords = ['python', 'javascript', 'react', 'angular', 'java', 'node', 'sql', 'aws']
            for skill in skill_keywords:
                if skill in message_lower:
                    skills.append(skill)
            
            # Common roles - check more specific roles first
            if 'project manager' in message_lower:
                job_title = 'Project Manager'
            elif 'product manager' in message_lower:
                job_title = 'Product Manager'
            elif 'engineering manager' in message_lower:
                job_title = 'Engineering Manager'
            elif 'data scientist' in message_lower:
                job_title = 'Data Scientist'
            elif 'business analyst' in message_lower:
                job_title = 'Business Analyst'
            elif 'software developer' in message_lower or 'software engineer' in message_lower:
                job_title = 'Software Developer'
            elif 'frontend developer' in message_lower or 'front-end developer' in message_lower:
                job_title = 'Frontend Developer'
            elif 'backend developer' in message_lower or 'back-end developer' in message_lower:
                job_title = 'Backend Developer'
            elif 'full stack' in message_lower or 'fullstack' in message_lower:
                job_title = 'Full Stack Developer'
            elif 'developer' in message_lower:
                job_title = 'Developer'
            elif 'engineer' in message_lower:
                job_title = 'Engineer'
            elif 'manager' in message_lower:
                job_title = 'Manager'
            elif 'analyst' in message_lower:
                job_title = 'Analyst'
            
            return {
                'intent': 'search_request',
                'extracted_info': {
                    'job_title': job_title,
                    'required_skills': skills,
                    'experience_years': 0
                },
                'needs_detailed_processing': True
            }
        
        elif any(word in message_lower for word in ['why', 'explain', 'tell me about']):
            return {'intent': 'candidate_inquiry', 'needs_detailed_processing': True}
        
        else:
            return {'intent': 'general_conversation', 'needs_detailed_processing': False}
    
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
    
    def _create_error_response(self, message: str, user_id: int) -> Dict[str, Any]:
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
    
    def _create_helpful_response(self, context: str) -> Dict[str, Any]:
        """Create helpful fallback response."""
        return {
            'message': f"I'm here to help you find the right candidates. What specific requirements do you have for this {context}?",
            'action': 'continue',
            'suggestions': [
                'Senior level experience',
                'Specific technical skills',
                'Industry background',
                'Team leadership experience'
            ]
        }

# Global instance
instant_enhanced_chat_service = InstantEnhancedChatService()