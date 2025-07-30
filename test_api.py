#!/usr/bin/env python3
"""
Test script for Resume Matcher Agent API endpoints
"""

import requests
import json
import time
from typing import Dict, Any

class CVMatcherTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
        self.headers = {"Content-Type": "application/json"}
    
    def test_health(self) -> bool:
        """Test health endpoint."""
        print("🏥 Testing health endpoint...")
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_register(self, username: str = "testapi", email: str = "testapi@example.com", password: str = "testpass123") -> bool:
        """Test user registration."""
        print(f"👤 Testing user registration for {username}...")
        
        user_data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/register", json=user_data, headers=self.headers)
            if response.status_code == 200:
                print("✅ User registration successful")
                return True
            elif response.status_code == 400:
                print("ℹ️  User already exists")
                return True
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def test_login(self, username: str = "testapi", password: str = "testpass123") -> bool:
        """Test user login."""
        print(f"🔐 Testing login for {username}...")
        
        login_data = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=login_data, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_get_current_user(self) -> bool:
        """Test getting current user info."""
        print("👤 Testing get current user...")
        
        try:
            response = requests.get(f"{self.base_url}/auth/me", headers=self.headers)
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Current user: {user_data['username']} ({user_data['email']})")
                return True
            else:
                print(f"❌ Get current user failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Get current user error: {e}")
            return False
    
    def test_config_endpoints(self) -> bool:
        """Test configuration endpoints."""
        print("⚙️  Testing configuration endpoints...")
        
        # Test getting config (should exist but be empty)
        try:
            response = requests.get(f"{self.base_url}/config/", headers=self.headers)
            if response.status_code == 200:
                print("✅ Get config successful")
            else:
                print(f"ℹ️  Config not found (normal for new user): {response.status_code}")
            
            # Test setup status
            response = requests.get(f"{self.base_url}/config/setup-status", headers=self.headers)
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Setup status: {status}")
                return True
            else:
                print(f"❌ Setup status failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Config test error: {e}")
            return False
    
    def test_google_drive_auth_url(self) -> bool:
        """Test Google Drive auth URL generation."""
        print("📁 Testing Google Drive auth URL...")
        
        try:
            response = requests.get(f"{self.base_url}/google-drive/auth", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                print("✅ Google Drive auth URL generated")
                print(f"   URL: {data['authorization_url'][:100]}...")
                return True
            else:
                print(f"❌ Google Drive auth URL failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Google Drive auth URL error: {e}")
            return False
    
    def test_google_drive_status(self) -> bool:
        """Test Google Drive connection status."""
        print("📁 Testing Google Drive status...")
        
        try:
            response = requests.get(f"{self.base_url}/google-drive/status", headers=self.headers)
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Google Drive status: {status['message']}")
                return True
            else:
                print(f"❌ Google Drive status failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Google Drive status error: {e}")
            return False
    
    def test_matching_stats(self) -> bool:
        """Test matching statistics."""
        print("📊 Testing matching statistics...")
        
        try:
            response = requests.get(f"{self.base_url}/cv-matching/stats", headers=self.headers)
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Matching stats: {stats}")
                return True
            else:
                print(f"❌ Matching stats failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Matching stats error: {e}")
            return False
    
    def test_match_history(self) -> bool:
        """Test match history."""
        print("📋 Testing match history...")
        
        try:
            response = requests.get(f"{self.base_url}/cv-matching/history", headers=self.headers)
            if response.status_code == 200:
                history = response.json()
                print(f"✅ Match history: {len(history)} entries")
                return True
            else:
                print(f"❌ Match history failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Match history error: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests."""
        print("🧪 Resume Matcher Agent API Tests")
        print("=============================")
        
        results = {}
        
        # Health check
        results["health"] = self.test_health()
        
        # Authentication flow
        results["register"] = self.test_register()
        results["login"] = self.test_login()
        
        if results["login"]:
            # Protected endpoints (require authentication)
            results["current_user"] = self.test_get_current_user()
            results["config"] = self.test_config_endpoints()
            results["google_drive_auth"] = self.test_google_drive_auth_url()
            results["google_drive_status"] = self.test_google_drive_status()
            results["matching_stats"] = self.test_matching_stats()
            results["match_history"] = self.test_match_history()
        else:
            print("❌ Skipping authenticated tests due to login failure")
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary."""
        print("\n📊 Test Summary")
        print("================")
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, passed_test in results.items():
            status = "✅ PASS" if passed_test else "❌ FAIL"
            print(f"{test_name:20} {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the application setup.")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Resume Matcher Agent API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--wait", type=int, default=0, help="Wait time before starting tests")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for services to start...")
        time.sleep(args.wait)
    
    tester = CVMatcherTester(args.url)
    results = tester.run_all_tests()
    tester.print_summary(results)

if __name__ == "__main__":
    main()
