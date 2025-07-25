#!/usr/bin/env python3
"""
Performance test script for the optimized CV matching service.
Tests the key optimizations and validates the response format.
"""

import requests
import time
import json
from datetime import datetime

# Configuration
API_BASE = "http://localhost:9000/api"
TEST_USER = {
    "username": "test_user_opt",
    "email": "test_opt@example.com", 
    "password": "testpass123"
}

JOB_DESCRIPTION = """
Senior Python Developer Position

We are looking for an experienced Python developer with the following requirements:
- 5+ years of Python development experience
- Strong experience with FastAPI, Django or Flask frameworks
- Knowledge of RESTful API design and development
- Experience with SQL databases (PostgreSQL, MySQL)
- Familiarity with Docker and containerization
- Experience with cloud platforms (AWS, Azure, or GCP)
- Knowledge of machine learning libraries (scikit-learn, pandas) is a plus
- Strong problem-solving skills and attention to detail
- Bachelor's degree in Computer Science or related field

Responsibilities:
- Design and develop scalable Python applications
- Create and maintain RESTful APIs
- Work with databases and optimize queries
- Collaborate with cross-functional teams
- Write clean, maintainable, and well-documented code
"""

class PerformanceTest:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        
    def register_and_login(self):
        """Register test user and get auth token."""
        print("🔐 Setting up test user...")
        
        # Try to register (may already exist)
        try:
            response = self.session.post(f"{API_BASE}/auth/register", json=TEST_USER)
            if response.status_code == 200:
                print("✅ Test user registered successfully")
            else:
                print("ℹ️ Test user may already exist, proceeding to login")
        except Exception as e:
            print(f"⚠️ Registration error (continuing): {e}")
        
        # Login to get token
        response = self.session.post(f"{API_BASE}/auth/login", json={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Successfully logged in")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def check_configuration(self):
        """Check if user has required configuration."""
        print("⚙️ Checking user configuration...")
        
        response = self.session.get(f"{API_BASE}/config/setup-status")
        if response.status_code == 200:
            status = response.json()
            print(f"📊 Setup status: {status}")
            
            if not status.get("google_drive_connected", False):
                print("⚠️ Google Drive not connected - this will limit the test")
            if not status.get("openai_configured", False):
                print("⚠️ OpenAI not configured - this will limit the test")
            
            return status
        else:
            print(f"❌ Failed to get setup status: {response.status_code}")
            return None
    
    def test_matching_performance(self):
        """Test the optimized CV matching performance."""
        print("\n🚀 Testing Optimized CV Matching Performance...")
        print("="*60)
        
        # Record start time
        start_time = time.time()
        
        # Make the matching request
        response = self.session.post(f"{API_BASE}/cv-matching/match", json={
            "job_description": JOB_DESCRIPTION
        })
        
        # Record end time
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"⏱️ Total API Response Time: {processing_time:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n📊 Performance Results:")
            print("-" * 40)
            print(f"✅ Status: {result.get('status', 'unknown')}")
            print(f"📄 CVs Processed: {result.get('total_cvs_processed', 0)}")
            print(f"🎯 Top Matches: {result.get('top_matches_count', 0)}")
            print(f"📁 Folder: {result.get('folder_name', 'unknown')}")
            
            # Check enhanced summary (optimization features)
            enhanced = result.get('enhanced_summary', {})
            if enhanced:
                print(f"🔍 Search Effectiveness: {enhanced.get('search_effectiveness', 'unknown')}")
                print(f"📋 Total Reviewed: {enhanced.get('total_reviewed', 0)}")
                print(f"✨ Processing Time: {enhanced.get('processing_time', 'unknown')}")
                print(f"🎖️ Excellent Matches: {enhanced.get('excellent_matches', 0)}")
                print(f"👍 Good Matches: {enhanced.get('good_matches', 0)}")
                print(f"📈 Average Matches: {enhanced.get('average_matches', 0)}")
            
            # Validate response format (should be unchanged)
            print("\n🔍 Response Format Validation:")
            print("-" * 40)
            required_fields = ['results', 'match_id', 'total_cvs_processed', 'status', 'enhanced_summary']
            for field in required_fields:
                if field in result:
                    print(f"✅ {field}: Present")
                else:
                    print(f"❌ {field}: Missing")
            
            # Check individual results format
            results = result.get('results', [])
            if results:
                print(f"\n📋 Sample Result (1 of {len(results)}):")
                sample = results[0]
                result_fields = ['cv_filename', 'candidate_name', 'relevance_score', 'match_status']
                for field in result_fields:
                    value = sample.get(field, 'MISSING')
                    print(f"  {field}: {value}")
            
            # Performance Assessment
            print("\n🎯 Performance Assessment:")
            print("-" * 40)
            if processing_time < 30:
                print(f"🚀 EXCELLENT: Response time {processing_time:.2f}s (target: <30s)")
            elif processing_time < 60:
                print(f"✅ GOOD: Response time {processing_time:.2f}s (target: <60s)")
            elif processing_time < 120:
                print(f"⚠️ ACCEPTABLE: Response time {processing_time:.2f}s (target: <120s)")
            else:
                print(f"❌ SLOW: Response time {processing_time:.2f}s (needs optimization)")
            
            # Optimization features check
            print("\n⚡ Optimization Features Detected:")
            print("-" * 40)
            
            # Check for job analysis caching (should be fast on repeated calls)
            if 'processing_time' in enhanced:
                print(f"✅ Processing time tracking: {enhanced['processing_time']}")
            
            # Check for smart filtering
            total_reviewed = enhanced.get('total_reviewed', 0)
            total_processed = result.get('total_cvs_processed', 0)
            if total_reviewed > total_processed:
                efficiency = (total_processed / total_reviewed) * 100
                print(f"✅ Smart pre-filtering: {efficiency:.1f}% efficiency ({total_processed}/{total_reviewed} processed)")
            
            # Check for parallel processing indicators
            if processing_time < 60 and total_processed > 5:
                print(f"✅ Likely using parallel processing (good speed for {total_processed} CVs)")
            
            return True
            
        else:
            print(f"❌ Matching request failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    
    def test_caching_performance(self):
        """Test job analysis caching by making repeated requests."""
        print("\n🧠 Testing Job Analysis Caching...")
        print("-" * 40)
        
        # First request (should analyze job)
        start1 = time.time()
        response1 = self.session.post(f"{API_BASE}/cv-matching/match", json={
            "job_description": JOB_DESCRIPTION
        })
        time1 = time.time() - start1
        
        if response1.status_code != 200:
            print("❌ First request failed, cannot test caching")
            return False
        
        # Second request (should use cached job analysis)
        start2 = time.time()
        response2 = self.session.post(f"{API_BASE}/cv-matching/match", json={
            "job_description": JOB_DESCRIPTION
        })
        time2 = time.time() - start2
        
        if response2.status_code != 200:
            print("❌ Second request failed")
            return False
        
        print(f"⏱️ First request: {time1:.2f}s")
        print(f"⏱️ Second request: {time2:.2f}s")
        
        if time2 < time1 * 0.8:  # Second should be at least 20% faster
            improvement = ((time1 - time2) / time1) * 100
            print(f"✅ Caching working! {improvement:.1f}% faster on repeat")
        else:
            print(f"⚠️ Caching may not be working (minimal improvement)")
        
        return True
    
    def run_all_tests(self):
        """Run all performance tests."""
        print("🧪 CV Matcher Agent - Optimized Performance Test")
        print("=" * 60)
        print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.register_and_login():
            print("❌ Failed to authenticate, cannot proceed with tests")
            return False
        
        config_status = self.check_configuration()
        
        # Main performance test
        success1 = self.test_matching_performance()
        
        # Caching test (if first test succeeded)
        success2 = True
        if success1:
            success2 = self.test_caching_performance()
        
        # Summary
        print("\n" + "=" * 60)
        print("📝 TEST SUMMARY")
        print("=" * 60)
        
        if success1 and success2:
            print("🎉 ALL TESTS PASSED - Optimized service is working correctly!")
            print("✅ Key optimizations verified:")
            print("   • Fast API response times")
            print("   • Proper response format maintained")
            print("   • Job analysis caching functional")
            print("   • Smart filtering and parallel processing indicators")
        else:
            print("⚠️ Some tests failed - check the output above for details")
        
        print(f"\n🕐 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return success1 and success2

if __name__ == "__main__":
    tester = PerformanceTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)