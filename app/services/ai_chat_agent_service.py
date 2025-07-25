import openai
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.models import UserConfig, MatchLog, MatchResult, User
from app.services.optimized_cv_matching_service import OptimizedCVMatchingService
from app.utils.encryption import encryption_service
import json
import re
import time
from datetime import datetime
import hashlib

class AIChatAgentService:
    def __init__(self):
        self.openai_client = None
        self.cv_matching_service = OptimizedCVMatchingService()
        self.conversation_contexts = {}  # Store conversation history per user
        
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
        """Get or create conversation context for a user."""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = {
                'messages': [],
                'job_requirements': None,
                'search_history': [],
                'last_results': None,
                'conversation_state': 'initial',  # initial, gathering_requirements, searching, refining
                'extracted_criteria': {}
            }
        return self.conversation_contexts[user_id]
    
    def clear_conversation_context(self, user_id: int):
        """Clear conversation context for a user."""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
    
    def analyze_user_intent(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent and determine next action."""
        try:
            system_prompt = """You are an AI assistant helping users find the best CV matches for their job requirements.
            Analyze the user's message and determine their intent. Respond with a JSON object containing:
            
            {
                "intent": "one of: initial_request, provide_requirements, refine_search, ask_question, start_over, request_results",
                "confidence": 0.0-1.0,
                "extracted_info": {
                    "job_title": "if mentioned",
                    "required_skills": ["skill1", "skill2"],
                    "experience_level": "junior/mid/senior/lead",
                    "years_experience": "number if mentioned",
                    "location": "if mentioned",
                    "industry": "if mentioned",
                    "specific_requirements": "any specific requirements"
                },
                "query_refinement": "if user wants to refine previous search",
                "questions": ["questions to ask user if more info needed"]
            }
            
            Previous context: """ + json.dumps(context.get('extracted_criteria', {}), indent=2)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            
            intent_analysis = json.loads(response.choices[0].message.content)
            return intent_analysis
            
        except Exception as e:
            print(f"❌ Error analyzing intent: {e}")
            return {
                "intent": "provide_requirements",
                "confidence": 0.5,
                "extracted_info": {},
                "questions": ["Could you please describe the job requirements you're looking for?"]
            }
    
    def generate_job_description(self, extracted_criteria: Dict[str, Any]) -> str:
        """Generate a structured job description from extracted criteria."""
        try:
            system_prompt = """Based on the extracted job criteria, generate a comprehensive job description that can be used for CV matching.
            Make it detailed and professional, including all the requirements, skills, and preferences mentioned.
            
            Format the response as a clear, structured job description ready for CV matching."""
            
            criteria_text = json.dumps(extracted_criteria, indent=2)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a job description from these criteria:\n{criteria_text}"}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.4,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Error generating job description: {e}")
            return f"Looking for candidates with: {', '.join(extracted_criteria.get('required_skills', []))}"
    
    def generate_response(self, intent_analysis: Dict[str, Any], context: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Generate appropriate response based on intent analysis."""
        intent = intent_analysis.get('intent', 'provide_requirements')
        extracted_info = intent_analysis.get('extracted_info', {})
        
        # Update context with extracted information
        if extracted_info:
            context['extracted_criteria'].update({k: v for k, v in extracted_info.items() if v})
        
        response_data = {
            'message': '',
            'action': 'continue',  # continue, search, show_results
            'suggestions': [],
            'job_description': None,
            'results': None
        }
        
        if intent == 'initial_request':
            response_data['message'] = """👋 Hello! I'm your AI Resume matching assistant. I'll help you find the perfect candidates for your job requirements.

Tell me about the position you're hiring for. You can describe:
• Job title and role
• Required skills and technologies
• Experience level needed
• Any specific requirements

What kind of candidate are you looking for?"""
            context['conversation_state'] = 'gathering_requirements'
            
        elif intent == 'provide_requirements':
            # Check if we have enough information to search
            criteria = context['extracted_criteria']
            missing_info = []
            
            if not criteria.get('required_skills') and not criteria.get('job_title'):
                missing_info.append("job title or key skills")
            
            if missing_info:
                response_data['message'] = f"""Got it! I'm gathering information about your requirements. 

So far I understand you're looking for:
{self._format_criteria(criteria)}

To help you find the best candidates, could you also tell me about:
• {', '.join(missing_info)}"""
                
                response_data['suggestions'] = [
                    "I need a senior Python developer",
                    "Looking for a frontend developer with React experience",
                    "Need someone with 3+ years in data science"
                ]
            else:
                # We have enough info to search
                response_data['message'] = f"""Perfect! I understand you're looking for:
{self._format_criteria(criteria)}

Should I search for candidates matching these requirements? I'll analyze all CVs in your Google Drive folder and rank them by relevance."""
                
                response_data['action'] = 'ready_to_search'
                response_data['suggestions'] = [
                    "Yes, search for candidates",
                    "Let me refine the requirements first",
                    "Show me similar searches I've done before"
                ]
        
        elif intent == 'refine_search':
            query_refinement = intent_analysis.get('query_refinement', '')
            response_data['message'] = f"""I'll refine your search based on: "{query_refinement}"

Updated requirements:
{self._format_criteria(context['extracted_criteria'])}

Ready to search with these updated criteria?"""
            
            response_data['action'] = 'ready_to_search'
            response_data['suggestions'] = [
                "Yes, search with updated criteria",
                "Make more changes to requirements",
                "Start over with new requirements"
            ]
        
        elif intent == 'request_results':
            if context.get('last_results'):
                response_data['message'] = "Here are your most recent search results:"
                response_data['action'] = 'show_results'
                response_data['results'] = context['last_results']
            else:
                response_data['message'] = "I don't have any previous search results. Would you like me to search for candidates based on your requirements?"
                response_data['suggestions'] = [
                    "Yes, search for candidates",
                    "Let me update my requirements first"
                ]
        
        elif intent == 'start_over':
            context['extracted_criteria'] = {}
            context['conversation_state'] = 'initial'
            response_data['message'] = "Let's start fresh! What kind of candidate are you looking for?"
            response_data['suggestions'] = [
                "I need a software developer",
                "Looking for a marketing specialist",
                "Need someone in sales"
            ]
        
        else:
            # Default response for unclear intent
            questions = intent_analysis.get('questions', [])
            if questions:
                response_data['message'] = f"I'd like to help you find the right candidates. {questions[0]}"
            else:
                response_data['message'] = "I'm here to help you find the best candidates. Could you tell me more about what you're looking for?"
        
        return response_data
    
    def _format_criteria(self, criteria: Dict[str, Any]) -> str:
        """Format criteria for display."""
        formatted_parts = []
        
        if criteria.get('job_title'):
            formatted_parts.append(f"📋 **Position**: {criteria['job_title']}")
        
        if criteria.get('required_skills'):
            skills = criteria['required_skills']
            if isinstance(skills, list):
                formatted_parts.append(f"🛠️ **Skills**: {', '.join(skills)}")
            else:
                formatted_parts.append(f"🛠️ **Skills**: {skills}")
        
        if criteria.get('experience_level'):
            formatted_parts.append(f"📊 **Level**: {criteria['experience_level'].title()}")
        
        if criteria.get('years_experience'):
            formatted_parts.append(f"⏱️ **Experience**: {criteria['years_experience']} years")
        
        if criteria.get('location'):
            formatted_parts.append(f"📍 **Location**: {criteria['location']}")
        
        if criteria.get('industry'):
            formatted_parts.append(f"🏢 **Industry**: {criteria['industry']}")
        
        if criteria.get('specific_requirements'):
            formatted_parts.append(f"📝 **Additional**: {criteria['specific_requirements']}")
        
        return '\n'.join(formatted_parts) if formatted_parts else "*(Still gathering requirements)*"
    
    async def process_chat_message(self, user_id: int, message: str, db: Session) -> Dict[str, Any]:
        """Process a chat message and return response."""
        try:
            # Get OpenAI key and initialize client
            api_key = self.get_openai_key(db, user_id)
            if not api_key:
                return {
                    'message': "⚠️ Please configure your OpenAI API key in the Configuration section first.",
                    'action': 'configure',
                    'suggestions': []
                }
            
            if not self.openai_client:
                if not self.initialize_openai_client(api_key):
                    return {
                        'message': "❌ Failed to initialize AI service. Please check your OpenAI API key.",
                        'action': 'configure',
                        'suggestions': []
                    }
            
            # Get conversation context
            context = self.get_conversation_context(user_id)
            
            # Add user message to context
            context['messages'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Analyze user intent
            intent_analysis = self.analyze_user_intent(message, context)
            
            # Generate response
            response_data = self.generate_response(intent_analysis, context, message)
            
            # Add AI response to context
            context['messages'].append({
                'role': 'assistant',
                'content': response_data['message'],
                'timestamp': datetime.now().isoformat(),
                'action': response_data['action']
            })
            
            return response_data
            
        except Exception as e:
            print(f"❌ Error processing chat message: {e}")
            return {
                'message': "I apologize, but I encountered an error processing your message. Please try again.",
                'action': 'continue',
                'suggestions': []
            }
    
    async def execute_search(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Execute CV search based on conversation context."""
        try:
            context = self.get_conversation_context(user_id)
            criteria = context.get('extracted_criteria', {})
            
            if not criteria:
                return {
                    'message': "I need more information about your requirements before I can search.",
                    'action': 'continue',
                    'suggestions': []
                }
            
            # Generate job description from criteria
            job_description = self.generate_job_description(criteria)
            
            # Execute the search using the existing CV matching service
            results = self.cv_matching_service.process_optimized_cv_matching(
                db=db,
                user_id=user_id,
                job_description=job_description
            )
            
            # Store results in context
            context['last_results'] = results
            context['search_history'].append({
                'criteria': criteria.copy(),
                'job_description': job_description,
                'timestamp': datetime.now().isoformat(),
                'results_count': len(results.get('matches', []))
            })
            
            # Generate response message
            match_count = len(results.get('matches', []))
            if match_count > 0:
                message = f"""🎯 **Search Complete!** 

Found **{match_count} matching candidates** for your requirements:
{self._format_criteria(criteria)}

The candidates are ranked by relevance score. You can now:
• Review detailed match analysis
• Download CVs of top candidates
• Refine your search criteria
• Start a new search"""
            else:
                message = f"""🔍 **Search Complete**

No candidates found matching your exact requirements:
{self._format_criteria(criteria)}

Would you like to:
• Broaden the search criteria
• Try different skill requirements
• Search for a different role"""
            
            return {
                'message': message,
                'action': 'show_results',
                'results': results,
                'suggestions': [
                    "Show me the top candidates",
                    "Refine search criteria",
                    "Start a new search"
                ]
            }
            
        except Exception as e:
            print(f"❌ Error executing search: {e}")
            return {
                'message': "I encountered an error while searching. Please try again.",
                'action': 'continue',
                'suggestions': []
            }
    
    def get_conversation_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        context = self.get_conversation_context(user_id)
        return context.get('messages', [])
    
    def get_search_suggestions(self, user_id: int) -> List[str]:
        """Get search suggestions based on conversation history."""
        context = self.get_conversation_context(user_id)
        search_history = context.get('search_history', [])
        
        suggestions = [
            "I need a senior software developer",
            "Looking for a marketing manager with digital experience",
            "Need a data scientist with Python skills",
            "Looking for a UI/UX designer",
            "Need someone with project management experience"
        ]
        
        # Add suggestions based on search history
        for search in search_history[-3:]:  # Last 3 searches
            criteria = search.get('criteria', {})
            if criteria.get('job_title'):
                suggestions.insert(0, f"Find another {criteria['job_title']}")
        
        return suggestions[:5]

# Global instance
ai_chat_agent_service = AIChatAgentService()