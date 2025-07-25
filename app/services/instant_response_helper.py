from typing import Dict, Any

def get_instant_processing_response(message: str, user_id: int) -> Dict[str, Any]:
    """Provide instant response while CVs are being processed in background."""
    message_lower = message.lower()
    
    search_terms = []
    if 'senior' in message_lower:
        search_terms.append('senior level candidates')
    elif 'junior' in message_lower:
        search_terms.append('junior level candidates')
    elif 'lead' in message_lower:
        search_terms.append('lead/principal level candidates')
    
    if 'developer' in message_lower or 'engineer' in message_lower:
        search_terms.append('software developers/engineers')
    elif 'manager' in message_lower:
        search_terms.append('management roles')
    elif 'data scientist' in message_lower:
        search_terms.append('data science professionals')
    
    search_context = ', '.join(search_terms) if search_terms else 'candidates matching your criteria'
    
    return {
        'message': f"""🚀 **Got it! I'm analyzing your CV database for {search_context}...**

I'm currently processing your CVs from Google Drive to find the best matches.

✨ **What I'm doing:**
• Parsing and analyzing all CV files in your Google Drive folder
• Extracting key skills, experience, and qualifications  
• Building AI-powered candidate profiles
• Preparing semantic matching algorithms

🎯 **Once ready, I'll provide:**
• Ranked candidate matches with relevance scores
• Detailed skill alignment analysis
• Professional summaries and recommendations

**Your search will be ready shortly! Feel free to refine your requirements.**""",
        'action': 'processing',
        'suggestions': [
            'Add specific skills requirements',
            'Specify years of experience needed', 
            'Tell me about the team or project',
            'What technologies should they know?'
        ]
    }