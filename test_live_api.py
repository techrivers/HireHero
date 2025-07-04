#!/usr/bin/env python3
"""
Test the live API to see actual response format
"""

import requests
import json
import time

def test_live_api():
    """Test the live API with real CV files."""
    
    print("🎯 Testing Live CV Matching API")
    print("=" * 50)
    
    # Login
    login_data = {"username": "testapi", "password": "testpass123"}
    response = requests.post("http://localhost:9000/api/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return
        
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("✅ Login successful")
    
    # Test CV matching
    job_data = {
        "job_description": "Product Development, Business Analysis, Requirements Engineering and Project Management.",
        "max_cvs": 6
    }
    
    print("\n🚀 Running CV matching...")
    match_response = requests.post("http://localhost:9000/api/cv-matching/match", json=job_data, headers=headers)
    
    print(f"Response status: {match_response.status_code}")
    
    if match_response.status_code != 200:
        print(f"❌ Error: {match_response.text}")
        return
        
    result = match_response.json()
    print(f"\nStatus: {result.get('status')}")
    print(f"Message: {result.get('message')}")
    print(f"Total Results: {len(result.get('results', []))}")
    
    if not result.get("results"):
        print("❌ No results returned")
        return
    
    print(f"\n📋 ANALYSIS OF FIRST 3 RESULTS:")
    print("=" * 50)
    
    real_names_found = 0
    ai_analysis_found = 0
    
    for i, cv_result in enumerate(result["results"][:3], 1):
        candidate_name = cv_result.get("candidate_name", "Not extracted")
        match_analysis = cv_result.get("match_analysis", "")
        
        print(f"\n{i}. {cv_result.get('cv_filename')}")
        print(f"   👤 Candidate: {candidate_name}")
        print(f"   📊 Score: {cv_result.get('relevance_score')}%")
        
        # Check if real name extracted
        if candidate_name != "Unknown Candidate":
            real_names_found += 1
            print("   ✅ REAL NAME EXTRACTED")
        else:
            print("   ❌ USING FALLBACK NAME")
            
        # Check analysis quality
        if "✅ STRENGTHS:" in match_analysis and "❌ GAPS:" in match_analysis:
            ai_analysis_found += 1
            print("   ✅ RICH AI ANALYSIS")
        elif "Professional experience" in match_analysis:
            print("   ❌ BASIC FALLBACK ANALYSIS")
        else:
            print("   🔍 UNKNOWN ANALYSIS FORMAT")
            
        # Show first 200 chars of analysis
        print(f"   📝 Analysis preview: {match_analysis[:200]}...")
    
    print(f"\n📊 SUMMARY:")
    print(f"Real names found: {real_names_found}/3")
    print(f"AI analysis found: {ai_analysis_found}/3")
    
    if real_names_found > 0 and ai_analysis_found > 0:
        print("\n🎉 SUCCESS! OpenAI integration is working!")
        print("✅ Your frontend should show proper candidate names and analysis")
    elif real_names_found > 0:
        print("\n⚠️ PARTIAL SUCCESS: Names extracted but analysis may be basic")
    else:
        print("\n❌ ISSUE: Still using fallback analysis")
        print("💡 OpenAI API calls are failing during CV processing")

if __name__ == "__main__":
    test_live_api()