#!/usr/bin/env python3
"""
Debug script to test intent analysis for the specific query
"""

import sys
sys.path.append('.')

from app.services.instant_enhanced_chat_service import instant_enhanced_chat_service

def test_intent_analysis():
    """Test intent analysis for the specific query."""
    print("🔍 Testing Intent Analysis for 'i need a project manager'")
    print("=" * 60)
    
    message = "i need a project manager"
    
    # Test fallback intent analysis
    print("\n1️⃣ Testing fallback intent analysis...")
    analysis = instant_enhanced_chat_service._create_fallback_intent_analysis(message)
    
    print(f"   Message: '{message}'")
    print(f"   Intent: {analysis.get('intent')}")
    print(f"   Extracted info: {analysis.get('extracted_info', {})}")
    print(f"   Needs detailed processing: {analysis.get('needs_detailed_processing')}")
    
    # Test context hint
    print("\n2️⃣ Testing context hint analysis...")
    context_hint = instant_enhanced_chat_service._analyze_message_context(message)
    print(f"   Context hint: '{context_hint}'")
    
    # Test with different variations
    print("\n3️⃣ Testing variations...")
    variations = [
        "looking for a project manager",
        "find project managers",
        "I want a senior project manager",
        "search for project management candidates"
    ]
    
    for var in variations:
        analysis = instant_enhanced_chat_service._create_fallback_intent_analysis(var)
        context_hint = instant_enhanced_chat_service._analyze_message_context(var)
        intent = analysis.get('intent')
        job_title = analysis.get('extracted_info', {}).get('job_title', 'None')
        
        print(f"   '{var}' → Intent: {intent}, Job: {job_title}, Context: {context_hint}")
    
    print("\n✅ Intent analysis test completed!")

if __name__ == "__main__":
    test_intent_analysis()