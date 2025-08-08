#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_ai_search_parsing():
    """Test the AI search parsing functionality"""
    from app.services.enhanced_candidate_service import EnhancedCandidateService
    from app.models.database import get_db
    from app.models.models import UserConfig
    from app.utils.encryption import EncryptionService
    import openai
    import json

    service = EnhancedCandidateService()
    encryption_service = EncryptionService()
    
    # Mock test query
    test_query = "project managers"
    
    # Manual test of the AI parsing logic
    print(f"Testing AI parsing for query: '{test_query}'")
    
    # Simulate the prompt that would be sent to OpenAI
    prompt = f"""
    Parse this candidate search query and extract search criteria:
    
    Query: "{test_query}"
    
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
    
    print("Expected AI parsing behavior:")
    print("For 'project managers' query, AI should return:")
    print('{"skills": [], "min_experience": null, "max_experience": null, "location": null, "remote_preference": null, "availability_status": null, "search_term": "project manager", "role_type": "project manager"}')
    
    print("\nThis should then be used in the regular get_candidates() method:")
    print("- search_term='project manager' should match candidates with 'project manager' in:")
    print("  - name")
    print("  - professional_summary") 
    print("  - current_role")
    print("  - current_company")
    
    return prompt

async def test_fallback_search():
    """Test what happens when AI parsing fails"""
    print("\nTesting fallback behavior:")
    print("When AI parsing fails, the system should:")
    print("1. Call get_candidates() with search_term='project managers' directly")
    print("2. This should match candidates where 'project managers' appears in:")
    print("   - name, professional_summary, current_role, or current_company")
    
    print("\nPotential issues:")
    print("1. If AI parsing returns empty result, search_term becomes None")
    print("2. Skills array might be empty when it should contain role-related skills")
    print("3. Role-specific skills like 'project management' might not be extracted")

def main():
    """Main debug function"""
    print("=== CV Matcher Agent - Intelligent Search Debug ===")
    print("Issue: Searching for 'project managers' returns no candidates")
    print("But searching for candidate names works fine.\n")
    
    # Run async test
    loop = asyncio.get_event_loop()
    prompt = loop.run_until_complete(test_ai_search_parsing())
    
    # Test fallback
    loop.run_until_complete(test_fallback_search())
    
    print("\nRecommended fixes:")
    print("1. Add better role-based keyword mapping in AI prompt")
    print("2. Enhance search to include skills_json for role matching")
    print("3. Add debugging logs to track what criteria are extracted")
    print("4. Test the OpenAI API response for 'project managers' query")
    print("5. Ensure current_role field is populated during CV analysis")

if __name__ == "__main__":
    main()