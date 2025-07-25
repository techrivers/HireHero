#!/usr/bin/env python3
"""
Test script to verify intelligent conversation works for any topic
"""

import requests
import json
import time

def test_intelligent_chat():
    """Test the intelligent chat functionality for various topics."""
    
    base_url = "http://localhost:9000/api"
    
    print("🧠 Testing Intelligent Chat for Any Topic")
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
    
    # Test different types of conversations
    test_queries = [
        # Greetings
        {
            "message": "Hello! How are you?",
            "expected": "greeting response",
            "type": "Greeting"
        },
        
        # General recommendations
        {
            "message": "What programming language should I learn in 2024?",
            "expected": "programming advice",
            "type": "Tech Recommendation"
        },
        
        # Business advice
        {
            "message": "How can I improve my startup's hiring process?",
            "expected": "business/hiring advice",
            "type": "Business Advice"
        },
        
        # CV/Recruitment query
        {
            "message": "I need a project manager for my team",
            "expected": "CV search results",
            "type": "CV Search"
        },
        
        # General knowledge
        {
            "message": "What are the benefits of remote work?",
            "expected": "remote work insights",
            "type": "General Knowledge"
        },
        
        # Follow-up question
        {
            "message": "Can you give me more details about that?",
            "expected": "contextual follow-up",
            "type": "Follow-up"
        },
        
        # Technical question
        {
            "message": "What's the difference between React and Vue?",
            "expected": "technical comparison",
            "type": "Technical Question"
        }
    ]
    
    session_id = "intelligent-test-123"
    
    for i, query in enumerate(test_queries, 2):
        print(f"\n{i}️⃣ Testing {query['type']}: '{query['message'][:50]}...'")
        
        chat_data = {
            "message": query["message"],
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
                suggestions = result.get('suggestions', [])
                
                print(f"   ✅ Response received in {response_time:.2f}s")
                print(f"   📝 Action: {action}")
                print(f"   💬 Response length: {len(message)} chars")
                print(f"   🎯 Suggestions: {len(suggestions)} items")
                print(f"   📄 Preview: {message[:100]}...")
                
                # Check if response is intelligent (more than basic template)
                if len(message) > 50 and any(word in message.lower() for word in ['can', 'help', 'recommend', 'suggest', 'consider', 'think', 'important']):
                    print(f"   🧠 ✅ Intelligent response detected")
                else:
                    print(f"   ⚠️ Response seems basic/templated")
                    
                # Check if it handles CV queries differently
                if query['type'] == 'CV Search':
                    results = result.get('results')
                    if results and results.get('matches'):
                        print(f"   🎯 ✅ CV search returned {len(results['matches'])} matches")
                    else:
                        print(f"   ⚠️ CV search didn't return matches")
                
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)  # Brief pause between requests
    
    print("\n🎉 Intelligent chat test completed!")
    print("\n💡 Expected Results:")
    print("   - All queries should get intelligent, contextual responses")
    print("   - CV queries should trigger search functionality")
    print("   - General questions should get knowledgeable answers")
    print("   - Responses should be conversational, not templated")

if __name__ == "__main__":
    test_intelligent_chat()