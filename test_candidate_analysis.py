#!/usr/bin/env python3
"""
Test script to verify candidate analysis functionality
"""

import requests
import json
import time

def test_candidate_analysis():
    """Test the candidate analysis functionality."""
    
    base_url = "http://localhost:9000/api"
    
    print("📋 Testing Candidate Analysis Functionality")
    print("=" * 50)
    
    # Step 1: Login
    print("\n1️⃣ Login...")
    login_data = {"email": "sana", "password": "sana1234"}
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=10)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"   ✅ Login successful")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    session_id = "candidate-analysis-test"
    
    # Step 2: Search for project managers first
    print("\n2️⃣ Searching for project managers...")
    search_data = {
        "message": "i need a project manager",
        "session_id": session_id
    }
    
    try:
        response = requests.post(f"{base_url}/chat", json=search_data, headers=headers, timeout=60)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Search completed")
            
            # Check if we got results
            results = result.get('results')
            if results and results.get('matches'):
                matches = results['matches']
                print(f"   🎯 Found {len(matches)} candidates")
                for i, match in enumerate(matches[:3]):
                    print(f"      {i+1}. {match.get('candidate_name', 'Unknown')} - {match.get('relevance_score', 0)}%")
            else:
                print("   ⚠️ No candidates found - cannot test analysis")
                return
        else:
            print(f"   ❌ Search failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Search error: {e}")
        return
    
    # Step 3: Test different ways to ask about candidates
    candidate_questions = [
        {
            "message": "tell me more about the first candidate",
            "type": "Position-based inquiry"
        },
        {
            "message": "analyze the top candidate for me",
            "type": "Analysis request"
        },
        {
            "message": "what are the details of the second candidate?",
            "type": "Details request"
        },
        {
            "message": "give me a summary of this candidate",
            "type": "Summary request"
        },
        {
            "message": "why is this person a good fit?",
            "type": "Fit analysis"
        }
    ]
    
    for i, question in enumerate(candidate_questions, 3):
        print(f"\n{i}️⃣ Testing {question['type']}: '{question['message']}'")
        
        chat_data = {
            "message": question["message"],
            "session_id": session_id
        }
        
        try:
            start_time = time.time()
            response = requests.post(f"{base_url}/chat", json=chat_data, headers=headers, timeout=60)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', '')
                action = result.get('action', '')
                
                print(f"   ✅ Response received in {response_time:.2f}s")
                print(f"   📝 Action: {action}")
                print(f"   💬 Response length: {len(message)} chars")
                print(f"   📄 Preview: {message[:150]}...")
                
                # Check if response contains candidate analysis
                if any(keyword in message.lower() for keyword in ['candidate', 'analysis', 'experience', 'skills', 'role', 'match']):
                    print(f"   🎯 ✅ Candidate analysis detected")
                else:
                    print(f"   ⚠️ Response doesn't seem to contain candidate analysis")
                    
                # Check if it's not the generic "can't review CVs" message
                if "unable to review cvs" in message.lower() or "general questions" in message.lower():
                    print(f"   ❌ Still getting generic response - fix needed")
                else:
                    print(f"   ✅ Specific candidate response provided")
                
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)  # Brief pause between requests
    
    print("\n🎉 Candidate analysis test completed!")
    print("\n💡 Expected Results:")
    print("   - All candidate questions should get detailed analysis")
    print("   - Should provide candidate name, role, skills, experience")
    print("   - Should explain why they're a good match")
    print("   - Should NOT say 'unable to review CVs'")

if __name__ == "__main__":
    test_candidate_analysis()