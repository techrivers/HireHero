import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.services.intelligent_chat_agent_service import intelligent_chat_agent_service
from app.services.instant_response_helper import get_instant_processing_response

async def process_chat_message_instant(user_id: int, message: str, db: Session, session_id: str = None) -> Dict[str, Any]:
    """Process chat message with instant response - no blocking operations."""
    try:
        print(f"🚀 Instant chat processing for user {user_id}: {message}")
        
        # Generate session ID if needed
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get conversation context (fast, in-memory)
        context = intelligent_chat_agent_service.get_conversation_context(user_id)
        
        # Add user message to context immediately
        context['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Check if we have cached CVs
        cv_summaries = await intelligent_chat_agent_service.get_cv_summaries_fast(user_id, db)
        
        if not cv_summaries:
            print(f"📋 No cached CVs for user {user_id}, starting background processing...")
            # Start background processing (don't await)
            asyncio.create_task(intelligent_chat_agent_service.process_cvs_background(user_id, db))
            
            # Return instant intelligent response
            response = get_instant_processing_response(message, user_id)
            
        else:
            print(f"✅ Found {len(cv_summaries)} cached CVs for user {user_id}")
            context['cv_summaries'] = cv_summaries
            
            # We have CVs, try to provide an intelligent response
            try:
                # Quick analysis using fallback method (no OpenAI dependency)
                analysis = intelligent_chat_agent_service.create_fallback_analysis(message)
                
                # Generate response based on analysis
                if analysis['intent'] == 'search_request' and analysis['search_criteria']:
                    response = await generate_quick_search_response(analysis, cv_summaries, user_id)
                else:
                    response = {
                        'message': """🤖 **I'm ready to help you find the perfect candidates!**

I have your CVs processed and ready for intelligent matching. I can help you:

🔍 **Search by criteria:**
• Skills: "Find Python developers"
• Experience: "Show me senior candidates"
• Role: "Looking for data scientists"
• Combination: "Senior React developers with 5+ years"

💡 **Smart matching features:**
• Relevance scoring and ranking
• Detailed skill analysis
• Experience level assessment
• Professional summaries

**What type of candidate are you looking for?**""",
                        'action': 'continue',
                        'suggestions': [
                            'Find me senior developers',
                            'Show me Python experts',
                            'Looking for data scientists', 
                            'Need project managers'
                        ]
                    }
                    
            except Exception as e:
                print(f"⚠️ Error in intelligent response generation: {e}")
                response = get_instant_processing_response(message, user_id)
        
        # Add AI response to context
        context['messages'].append({
            'role': 'assistant',
            'content': response['message'],
            'timestamp': datetime.now().isoformat(),
            'action': response['action']
        })
        
        # Clean up old messages (keep last 10)
        if len(context['messages']) > 10:
            context['messages'] = context['messages'][-10:]
        
        print(f"✅ Instant response generated successfully for user {user_id}")
        return response
        
    except Exception as e:
        print(f"❌ Error in instant chat processing: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback response
        return {
            'message': """🤖 **Hello! I'm your AI resume matching assistant.**

I help you find the perfect candidates from your CV database using intelligent matching.

✨ **How I can help:**
• Search by skills, experience, and role
• Provide relevance-scored candidate rankings
• Detailed match analysis and recommendations

🔍 **Try asking:**
• "Find me a senior Python developer"
• "Show me data scientists with ML experience"
• "Looking for project managers"

**What kind of candidate are you looking for today?**""",
            'action': 'continue',
            'suggestions': [
                'Find senior developers',
                'Show me Python experts',
                'Looking for data scientists',
                'Need project managers'
            ]
        }

async def generate_quick_search_response(analysis: Dict[str, Any], cv_summaries: List[Dict[str, Any]], user_id: int) -> Dict[str, Any]:
    """Generate a quick search response with basic matching."""
    try:
        search_criteria = analysis.get('search_criteria', {})
        
        # Quick filtering based on criteria
        job_title = search_criteria.get('job_title', '')
        skills = search_criteria.get('skills', [])
        experience_min = search_criteria.get('experience_min', 0)
        
        # Simple matching logic
        matches = []
        for cv in cv_summaries:
            score = 0
            cv_skills = cv.get('skills', [])
            cv_role = cv.get('role', '').lower()
            cv_experience = cv.get('experience', 0)
            
            # Basic scoring
            if job_title and job_title.lower() in cv_role:
                score += 40
            
            for skill in skills:
                if any(skill.lower() in cv_skill.lower() for cv_skill in cv_skills):
                    score += 20
            
            if cv_experience >= experience_min:
                score += 30
            
            if score >= 50:  # 50% threshold
                matches.append({
                    **cv,
                    'match_score': score / 100.0
                })
        
        # Sort by score
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        if matches:
            return {
                'message': f"""🎯 **Found {len(matches)} matching candidates!**

**Your search criteria:**
• Role: {job_title or 'Any'}
• Skills: {', '.join(skills) if skills else 'Any'}
• Experience: {experience_min}+ years

**Top matches:**
{format_quick_matches(matches[:3])}

💡 **You can:**
• View detailed results
• Refine your search criteria
• Ask for more specific requirements""",
                'action': 'show_results',
                'suggestions': [
                    'Show me more details',
                    'Refine the search',
                    'Find similar candidates',
                    'Try different criteria'
                ],
                'results': format_results_for_ui(matches)
            }
        else:
            return {
                'message': f"""🔍 **No exact matches found**

Searched for:
• Role: {job_title or 'Any'}
• Skills: {', '.join(skills) if skills else 'Any'} 
• Experience: {experience_min}+ years

**Try:**
• Broader skill requirements
• Different experience levels
• Related job titles
• More general search terms

**I can help you adjust the search criteria.**""",
                'action': 'continue',
                'suggestions': [
                    'Try broader skills',
                    'Lower experience requirements',
                    'Show me all candidates',
                    'Search for related roles'
                ]
            }
            
    except Exception as e:
        print(f"❌ Error in quick search: {e}")
        return get_instant_processing_response("search", user_id)

def format_quick_matches(matches: List[Dict[str, Any]]) -> str:
    """Format top matches for display."""
    result = ""
    for i, match in enumerate(matches, 1):
        score = int(match.get('match_score', 0) * 100)
        name = match.get('summary', {}).get('candidate_name', 'Unknown') if isinstance(match.get('summary'), dict) else 'Professional Candidate'
        role = match.get('role', 'Professional')
        experience = match.get('experience', 0)
        
        result += f"\n**{i}. {name}** ({score}% match)\n"
        result += f"• Role: {role}\n"
        result += f"• Experience: {experience} years\n"
    
    return result

def format_results_for_ui(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format results for the UI."""
    try:
        formatted_matches = []
        for match in matches:
            summary = match.get('summary', {})
            formatted_match = {
                'cv_filename': match.get('filename', 'Unknown'),
                'candidate_name': summary.get('candidate_name', 'Unknown') if isinstance(summary, dict) else 'Professional Candidate',
                'relevance_score': match.get('match_score', 0) * 100,
                'candidate_summary': summary.get('summary', 'Professional candidate') if isinstance(summary, dict) else 'Experienced professional',
                'key_skills': json.dumps(match.get('skills', [])),
                'match_analysis': f"Strong match with {int(match.get('match_score', 0) * 100)}% relevance",
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
        print(f"❌ Error formatting results: {e}")
        return {'total_cvs_processed': 0, 'processing_time': '< 1s', 'matches': []}