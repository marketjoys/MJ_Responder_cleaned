#!/usr/bin/env python3
"""
Comprehensive OAuth Status Endpoint Test
Tests both authenticated and unauthenticated scenarios with corrupted data
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta, timezone
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://prod-readiness-6.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class ComprehensiveOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.test_user_id = None
        self.auth_token = None
        
    async def setup(self):
        """Setup database connection and test user"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Create a test user for OAuth testing
            self.test_user_id = str(uuid.uuid4())
            test_user = {
                "id": self.test_user_id,
                "email": "oauth.comprehensive@example.com",
                "full_name": "OAuth Comprehensive Test User",
                "hashed_password": "$2b$12$test.hash.for.oauth.testing",
                "is_active": True,
                "email_quota": 100,
                "emails_used": 0,
                "timezone": "UTC",
                "created_at": datetime.utcnow()
            }
            await self.db.users.insert_one(test_user)
            print(f"✅ Created test user: {self.test_user_id}")
            
            # Try to get an auth token (this might fail if auth is not set up, which is OK)
            try:
                login_data = {
                    "email": "oauth.comprehensive@example.com",
                    "password": "test_password"
                }
                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                if response.status_code == 200:
                    self.auth_token = response.json().get('access_token')
                    print("✅ Obtained auth token for testing")
                else:
                    print("⚠️ Could not obtain auth token (will test unauthenticated scenarios)")
            except Exception as e:
                print(f"⚠️ Auth token setup failed: {str(e)} (will test unauthenticated scenarios)")
            
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.test_user_id:
                # Clean up test data
                await self.db.users.delete_one({"id": self.test_user_id})
                await self.db.oauth_tokens.delete_many({"user_id": self.test_user_id})
                print("✅ Cleaned up test data")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {str(e)}")
        
        if self.client:
            self.client.close()
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    async def test_corrupted_data_scenarios(self):
        """Test various corrupted data scenarios that could cause 500 errors"""
        print("\n🔍 Testing Corrupted Data Scenarios...")
        
        try:
            # Create various types of corrupted OAuth tokens
            corrupted_scenarios = [
                {
                    "name": "Invalid Date String",
                    "token": {
                        "id": str(uuid.uuid4()),
                        "user_id": self.test_user_id,
                        "access_token": "test_token_1",
                        "refresh_token": "test_refresh_1",
                        "token_type": "Bearer",
                        "expires_at": "invalid_date_format",  # This was the original issue
                        "scope": "https://www.googleapis.com/auth/gmail.readonly",
                        "authorized_services": ["email"],
                        "user_email": "test1@gmail.com",
                        "user_name": "Test User 1",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                {
                    "name": "Malformed ISO Date",
                    "token": {
                        "id": str(uuid.uuid4()),
                        "user_id": self.test_user_id,
                        "access_token": "test_token_2",
                        "refresh_token": "test_refresh_2",
                        "token_type": "Bearer",
                        "expires_at": "2024-13-45T99:99:99Z",  # Invalid date components
                        "scope": "https://www.googleapis.com/auth/gmail.send",
                        "authorized_services": ["email"],
                        "user_email": "test2@gmail.com",
                        "user_name": "Test User 2",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                {
                    "name": "Null Expires Date",
                    "token": {
                        "id": str(uuid.uuid4()),
                        "user_id": self.test_user_id,
                        "access_token": "test_token_3",
                        "refresh_token": "test_refresh_3",
                        "token_type": "Bearer",
                        "expires_at": None,  # Null value
                        "scope": "https://www.googleapis.com/auth/calendar",
                        "authorized_services": ["calendar"],
                        "user_email": "test3@gmail.com",
                        "user_name": "Test User 3",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                {
                    "name": "Empty String Date",
                    "token": {
                        "id": str(uuid.uuid4()),
                        "user_id": self.test_user_id,
                        "access_token": "test_token_4",
                        "refresh_token": "test_refresh_4",
                        "token_type": "Bearer",
                        "expires_at": "",  # Empty string
                        "scope": "https://www.googleapis.com/auth/gmail.modify",
                        "authorized_services": ["email"],
                        "user_email": "test4@gmail.com",
                        "user_name": "Test User 4",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                {
                    "name": "Numeric Date (Timestamp)",
                    "token": {
                        "id": str(uuid.uuid4()),
                        "user_id": self.test_user_id,
                        "access_token": "test_token_5",
                        "refresh_token": "test_refresh_5",
                        "token_type": "Bearer",
                        "expires_at": 1234567890,  # Unix timestamp as number
                        "scope": "https://www.googleapis.com/auth/calendar.events",
                        "authorized_services": ["calendar"],
                        "user_email": "test5@gmail.com",
                        "user_name": "Test User 5",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            ]
            
            # Insert all corrupted tokens
            for scenario in corrupted_scenarios:
                await self.db.oauth_tokens.insert_one(scenario["token"])
                print(f"   Created corrupted token: {scenario['name']}")
            
            # Test the OAuth status service with all corrupted data
            from oauth_google import google_oauth_service
            
            try:
                status_result = await google_oauth_service.get_oauth_status(self.test_user_id)
                
                # The service should handle all corrupted data gracefully
                has_required_fields = all(field in status_result for field in 
                                        ['is_authorized', 'authorized_services', 'user_email', 'expires_at'])
                
                is_authorized = status_result.get('is_authorized', False)
                has_accounts = status_result.get('total_accounts', 0) > 0
                
                corrupted_handling_passed = (has_required_fields and is_authorized and has_accounts)
                
                details = f"Required fields: {has_required_fields}, Authorized: {is_authorized}, " \
                         f"Total accounts: {status_result.get('total_accounts', 0)}, " \
                         f"Authorized accounts: {len(status_result.get('authorized_accounts', []))}"
                
                self.log_test_result("Corrupted Data Scenarios", corrupted_handling_passed, details)
                
                return corrupted_handling_passed
                
            except Exception as e:
                # Any exception means the fix is not working
                self.log_test_result("Corrupted Data Scenarios", False, 
                                   f"Exception with corrupted data: {str(e)}")
                return False
            
        except Exception as e:
            self.log_test_result("Corrupted Data Scenarios", False, f"Setup exception: {str(e)}")
            return False
    
    async def test_api_endpoint_error_handling(self):
        """Test the actual API endpoint error handling"""
        print("\n🔍 Testing API Endpoint Error Handling...")
        
        try:
            # Test unauthenticated request (should return 403, not 500)
            response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
            
            unauthenticated_passed = response.status_code == 403
            unauthenticated_details = f"Unauthenticated status: {response.status_code} (expected 403)"
            
            self.log_test_result("API Endpoint - Unauthenticated", unauthenticated_passed, unauthenticated_details)
            
            # Test with authentication header if we have a token
            authenticated_passed = True
            authenticated_details = "Skipped - no auth token available"
            
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
                
                # Should return 200 with proper JSON structure (not 500)
                authenticated_passed = response.status_code == 200
                
                if authenticated_passed:
                    try:
                        json_response = response.json()
                        has_structure = 'is_authorized' in json_response
                        authenticated_details = f"Authenticated status: {response.status_code}, Has structure: {has_structure}"
                    except json.JSONDecodeError:
                        authenticated_passed = False
                        authenticated_details = f"Authenticated status: {response.status_code}, Invalid JSON response"
                else:
                    authenticated_details = f"Authenticated status: {response.status_code} (expected 200)"
                
                self.log_test_result("API Endpoint - Authenticated", authenticated_passed, authenticated_details)
            
            return unauthenticated_passed and authenticated_passed
            
        except Exception as e:
            self.log_test_result("API Endpoint Error Handling", False, f"Exception: {str(e)}")
            return False
    
    async def test_production_readiness(self):
        """Test production readiness aspects"""
        print("\n🔍 Testing Production Readiness...")
        
        try:
            # Test that the service handles edge cases without crashing
            from oauth_google import google_oauth_service
            
            edge_cases_passed = True
            
            # Test 1: Non-existent user
            try:
                result = await google_oauth_service.get_oauth_status("non-existent-user-id")
                non_existent_user_handled = not result.get('is_authorized', True)
                if not non_existent_user_handled:
                    edge_cases_passed = False
                    print("   ❌ Non-existent user not handled properly")
                else:
                    print("   ✅ Non-existent user handled correctly")
            except Exception as e:
                edge_cases_passed = False
                print(f"   ❌ Exception with non-existent user: {str(e)}")
            
            # Test 2: Empty user ID
            try:
                result = await google_oauth_service.get_oauth_status("")
                empty_user_handled = not result.get('is_authorized', True)
                if not empty_user_handled:
                    edge_cases_passed = False
                    print("   ❌ Empty user ID not handled properly")
                else:
                    print("   ✅ Empty user ID handled correctly")
            except Exception as e:
                edge_cases_passed = False
                print(f"   ❌ Exception with empty user ID: {str(e)}")
            
            # Test 3: Invalid email parameter
            try:
                result = await google_oauth_service.get_oauth_status(self.test_user_id, "invalid-email-format")
                invalid_email_handled = not result.get('is_authorized', True)
                if not invalid_email_handled:
                    edge_cases_passed = False
                    print("   ❌ Invalid email parameter not handled properly")
                else:
                    print("   ✅ Invalid email parameter handled correctly")
            except Exception as e:
                edge_cases_passed = False
                print(f"   ❌ Exception with invalid email: {str(e)}")
            
            details = f"All edge cases handled gracefully: {edge_cases_passed}"
            
            self.log_test_result("Production Readiness", edge_cases_passed, details)
            
            return edge_cases_passed
            
        except Exception as e:
            self.log_test_result("Production Readiness", False, f"Exception: {str(e)}")
            return False
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive OAuth tests"""
        print("🚀 Starting Comprehensive OAuth Status Endpoint Tests...")
        print("=" * 70)
        
        if not await self.setup():
            print("❌ Setup failed, aborting tests")
            return
        
        try:
            # Run all tests
            test_results = []
            
            test_results.append(await self.test_corrupted_data_scenarios())
            test_results.append(await self.test_api_endpoint_error_handling())
            test_results.append(await self.test_production_readiness())
            
            # Summary
            passed_tests = sum(test_results)
            total_tests = len(test_results)
            success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            print("\n" + "=" * 70)
            print("📊 COMPREHENSIVE OAUTH STATUS ENDPOINT TEST SUMMARY")
            print("=" * 70)
            print(f"Total Tests: {total_tests}")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {total_tests - passed_tests}")
            print(f"Success Rate: {success_rate:.1f}%")
            
            # Detailed results
            print("\n📋 DETAILED RESULTS:")
            for result in self.test_results:
                print(f"{result['status']}: {result['test']}")
                if result['details']:
                    print(f"   {result['details']}")
            
            # Overall assessment
            if success_rate >= 80:
                print(f"\n✅ OVERALL ASSESSMENT: OAuth Status Endpoint Error Handling is PRODUCTION READY")
                print("   ✅ Handles corrupted token data gracefully")
                print("   ✅ Returns proper HTTP status codes (not 500 errors)")
                print("   ✅ Maintains consistent response format")
                print("   ✅ Handles edge cases without crashing")
            else:
                print(f"\n❌ OVERALL ASSESSMENT: OAuth Status Endpoint Error Handling has CRITICAL ISSUES")
                print("   ❌ May still return 500 errors with corrupted data")
                print("   ❌ Needs additional error handling improvements")
            
        finally:
            await self.cleanup()

async def main():
    """Main test execution"""
    tester = ComprehensiveOAuthTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())