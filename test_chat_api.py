#!/usr/bin/env python3
"""
Test script to simulate chat API calls and debug the issue
"""

import requests
import json
import time

def test_chat_functionality():
    """Test the chat API with Sana's credentials and the project manager query."""
    
    base_url = "http://localhost:9000/api"
    
    print("🔍 Testing Chat API Functionality")
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
            print(f"   ✅ Login successful, token: {token[:20]}...")
        else:
            print(f"   ❌ Login failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        print("   💡 Is the backend running on port 9000?")
        return
    
    # Step 2: Test chat API
    print("\n2️⃣ Testing chat API...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test the specific query
    chat_data = {
        "message": "i need a project manager",
        "session_id": "test-session-123"
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/chat", json=chat_data, headers=headers, timeout=15)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Chat response received in {response_time:.2f}s")
            print(f"   📝 Action: {result.get('action')}")
            print(f"   💬 Message preview: {result.get('message', '')[:100]}...")
            print(f"   🔍 Suggestions: {len(result.get('suggestions', []))} items")
            
            # Test follow-up message
            print("\n3️⃣ Testing follow-up message...")
            follow_up = {
                "message": "show me senior project managers",
                "session_id": "test-session-123"
            }
            
            start_time = time.time()
            response2 = requests.post(f"{base_url}/chat", json=follow_up, headers=headers, timeout=15)
            response_time2 = time.time() - start_time
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"   ✅ Follow-up response received in {response_time2:.2f}s")
                print(f"   📝 Action: {result2.get('action')}")
                print(f"   💬 Message preview: {result2.get('message', '')[:100]}...")
                
                # Check if responses are different
                if result.get('message') == result2.get('message'):
                    print("   ⚠️  WARNING: Same response received! This confirms the bug.")
                else:
                    print("   ✅ Different responses - conversation is progressing correctly")
            else:
                print(f"   ❌ Follow-up failed: {response2.status_code} - {response2.text}")
                
        else:
            print(f"   ❌ Chat failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"   ❌ Chat error: {e}")
    
    print("\n🎉 API test completed!")

if __name__ == "__main__":
    test_chat_functionality()