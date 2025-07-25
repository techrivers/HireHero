#!/usr/bin/env python3
"""
Debug script to test the chat functionality step by step
"""

import requests
import json
import time

def test_chat_debug():
    """Test the chat functionality with debug output."""
    
    base_url = "http://localhost:9000/api"
    
    print("🔍 Testing Chat Functionality with Debug")
    print("=" * 50)
    
    # Step 1: Login
    print("\n1️⃣ Testing login...")
    login_data = {
        "email": "sana",
        "password": "sana1234"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=10)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"   ✅ Login successful")
        else:
            print(f"   ❌ Login failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        print("   💡 Make sure the backend is running on port 9000")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Test simple conversation first
    print("\n2️⃣ Testing simple conversation...")
    simple_chat = {
        "message": "hello",
        "session_id": "debug-session-123"
    }
    
    try:
        response = requests.post(f"{base_url}/chat", json=simple_chat, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Simple chat works")
            print(f"   📝 Response: {result.get('message', '')[:100]}...")
        else:
            print(f"   ❌ Simple chat failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Simple chat error: {e}")
        return
    
    # Step 3: Test project manager query
    print("\n3️⃣ Testing project manager query...")
    pm_chat = {
        "message": "i need a project manager",
        "session_id": "debug-session-123"
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/chat", json=pm_chat, headers=headers, timeout=120)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Project manager query completed in {response_time:.2f}s")
            print(f"   📝 Action: {result.get('action')}")
            print(f"   💬 Message: {result.get('message', '')[:200]}...")
            
            # Check if we got results
            results = result.get('results')
            if results:
                matches = results.get('matches', [])
                print(f"   🎯 Found {len(matches)} matches")
                for i, match in enumerate(matches[:3]):
                    print(f"      {i+1}. {match.get('candidate_name', 'Unknown')} - {match.get('relevance_score', 0)}%")
            else:
                print("   ⚠️ No results returned")
                
        else:
            print(f"   ❌ Project manager query failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"   ❌ Project manager query error: {e}")
    
    # Step 4: Test another simple query
    print("\n4️⃣ Testing follow-up query...")
    followup_chat = {
        "message": "what can you do?",
        "session_id": "debug-session-123"
    }
    
    try:
        response = requests.post(f"{base_url}/chat", json=followup_chat, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Follow-up works")
            print(f"   📝 Response: {result.get('message', '')[:100]}...")
        else:
            print(f"   ❌ Follow-up failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Follow-up error: {e}")
    
    print("\n🎉 Chat debug test completed!")
    print("\n💡 Check the backend logs for detailed debug information")

if __name__ == "__main__":
    test_chat_debug()