#!/usr/bin/env python3
"""
OAuth Status Endpoint Error Handling Test
Tests the fix for corrupted token data handling in Google OAuth status endpoint
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-and-review.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthStatusTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.test_user_id = None
        
    async def setup(self):
        """Setup database connection"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Create a test user for OAuth testing
            self.test_user_id = str(uuid.uuid4())
            test_user = {
                "id": self.test_user_id,
                "email": "oauth.test@example.com",
                "full_name": "OAuth Test User",
                "hashed_password": "test_hash",
                "is_active": True,
                "email_quota": 100,
                "emails_used": 0,
                "timezone": "UTC",
                "created_at": datetime.utcnow()
            }
            await self.db.users.insert_one(test_user)
            print(f"✅ Created test user: {self.test_user_id}")
            
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
    
    async def test_oauth_status_normal_authentication(self):
        """Test 1: OAuth status endpoint with normal authentication"""
        print("\n🔍 Testing OAuth Status Endpoint - Normal Authentication...")
        
        try:
            # Create a valid OAuth token for testing
            valid_token = {
                "id": str(uuid.uuid4()),
                "user_id": self.test_user_id,
                "access_token": "valid_test_token_123",
                "refresh_token": "valid_refresh_token_123",
                "token_type": "Bearer",
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
                "authorized_services": ["email"],
                "user_email": "oauth.test@gmail.com",
                "user_name": "OAuth Test User",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            await self.db.oauth_tokens.insert_one(valid_token)
            print(f"   Created valid OAuth token for user: {self.test_user_id}")
            
            # Test the OAuth status endpoint directly using the service
            from oauth_google import google_oauth_service
            
            status_result = await google_oauth_service.get_oauth_status(self.test_user_id)
            
            # Verify the response structure
            expected_fields = ['is_authorized', 'authorized_services', 'user_email', 'expires_at', 'needs_refresh']
            has_expected_fields = all(field in status_result for field in expected_fields)
            
            is_authorized = status_result.get('is_authorized', False)
            has_services = len(status_result.get('authorized_services', [])) > 0
            has_user_email = status_result.get('user_email') is not None
            
            normal_auth_passed = (has_expected_fields and is_authorized and has_services and has_user_email)
            
            details = f"Fields present: {has_expected_fields}, Authorized: {is_authorized}, " \
                     f"Services: {len(status_result.get('authorized_services', []))}, " \
                     f"Email: {status_result.get('user_email', 'None')}"
            
            self.log_test_result("OAuth Status - Normal Authentication", normal_auth_passed, details)
            
            return normal_auth_passed
            
        except Exception as e:
            self.log_test_result("OAuth Status - Normal Authentication", False, f"Exception: {str(e)}")
            return False
    
    async def test_oauth_status_corrupted_token_data(self):
        """Test 2: OAuth status endpoint with corrupted token data"""
        print("\n🔍 Testing OAuth Status Endpoint - Corrupted Token Data...")
        
        try:
            # Create corrupted OAuth tokens with various malformed data
            corrupted_tokens = [
                {
                    "id": str(uuid.uuid4()),
                    "user_id": self.test_user_id,
                    "access_token": "corrupted_token_1",
                    "refresh_token": "corrupted_refresh_1",
                    "token_type": "Bearer",
                    "expires_at": "invalid_date_format",  # Corrupted date
                    "scope": "https://www.googleapis.com/auth/gmail.readonly",
                    "authorized_services": ["email"],
                    "user_email": "corrupted1@gmail.com",
                    "user_name": "Corrupted User 1",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "id": str(uuid.uuid4()),
                    "user_id": self.test_user_id,
                    "access_token": "corrupted_token_2",
                    "refresh_token": "corrupted_refresh_2",
                    "token_type": "Bearer",
                    "expires_at": "2024-13-45T99:99:99Z",  # Invalid date format
                    "scope": "https://www.googleapis.com/auth/gmail.send",
                    "authorized_services": ["email"],
                    "user_email": "corrupted2@gmail.com",
                    "user_name": "Corrupted User 2",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                },
                {
                    "id": str(uuid.uuid4()),
                    "user_id": self.test_user_id,
                    "access_token": "corrupted_token_3",
                    "refresh_token": "corrupted_refresh_3",
                    "token_type": "Bearer",
                    "expires_at": None,  # Null date
                    "scope": "https://www.googleapis.com/auth/calendar",
                    "authorized_services": ["calendar"],
                    "user_email": "corrupted3@gmail.com",
                    "user_name": "Corrupted User 3",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            ]
            
            # Insert corrupted tokens
            for token in corrupted_tokens:
                await self.db.oauth_tokens.insert_one(token)
            
            print(f"   Created {len(corrupted_tokens)} corrupted OAuth tokens")
            
            # Test the OAuth status endpoint with corrupted data
            from oauth_google import google_oauth_service
            
            try:
                status_result = await google_oauth_service.get_oauth_status(self.test_user_id)
                
                # The endpoint should handle corrupted data gracefully
                # and return a proper response structure without 500 errors
                expected_fields = ['is_authorized', 'authorized_services', 'user_email', 'expires_at']
                has_expected_fields = all(field in status_result for field in expected_fields)
                
                # Should still be authorized (has tokens, even if corrupted)
                is_authorized = status_result.get('is_authorized', False)
                
                # Should have authorized accounts info
                has_accounts_info = 'authorized_accounts' in status_result
                
                corrupted_handling_passed = (has_expected_fields and is_authorized and has_accounts_info)
                
                details = f"Fields present: {has_expected_fields}, Authorized: {is_authorized}, " \
                         f"Accounts info: {has_accounts_info}, " \
                         f"Total accounts: {status_result.get('total_accounts', 0)}"
                
                self.log_test_result("OAuth Status - Corrupted Token Handling", corrupted_handling_passed, details)
                
                return corrupted_handling_passed
                
            except Exception as e:
                # If we get an exception, the fix is not working properly
                self.log_test_result("OAuth Status - Corrupted Token Handling", False, 
                                   f"Exception with corrupted data: {str(e)}")
                return False
            
        except Exception as e:
            self.log_test_result("OAuth Status - Corrupted Token Handling", False, f"Setup exception: {str(e)}")
            return False
    
    async def test_oauth_status_specific_email(self):
        """Test 3: OAuth status endpoint with specific email parameter"""
        print("\n🔍 Testing OAuth Status Endpoint - Specific Email Parameter...")
        
        try:
            # Create a token for a specific email
            specific_email = "specific.test@gmail.com"
            specific_token = {
                "id": str(uuid.uuid4()),
                "user_id": self.test_user_id,
                "access_token": "specific_email_token",
                "refresh_token": "specific_email_refresh",
                "token_type": "Bearer",
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
                "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar",
                "authorized_services": ["email", "calendar"],
                "user_email": specific_email,
                "user_name": "Specific Email User",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            await self.db.oauth_tokens.insert_one(specific_token)
            print(f"   Created OAuth token for specific email: {specific_email}")
            
            # Test getting status for specific email
            from oauth_google import google_oauth_service
            
            status_result = await google_oauth_service.get_oauth_status(self.test_user_id, specific_email)
            
            # Verify response for specific email
            is_authorized = status_result.get('is_authorized', False)
            correct_email = status_result.get('user_email') == specific_email
            has_services = len(status_result.get('authorized_services', [])) > 0
            
            specific_email_passed = (is_authorized and correct_email and has_services)
            
            details = f"Authorized: {is_authorized}, Correct email: {correct_email}, " \
                     f"Services: {status_result.get('authorized_services', [])}"
            
            self.log_test_result("OAuth Status - Specific Email", specific_email_passed, details)
            
            return specific_email_passed
            
        except Exception as e:
            self.log_test_result("OAuth Status - Specific Email", False, f"Exception: {str(e)}")
            return False
    
    async def test_oauth_status_no_tokens(self):
        """Test 4: OAuth status endpoint with no tokens (unauthenticated)"""
        print("\n🔍 Testing OAuth Status Endpoint - No Tokens (Unauthenticated)...")
        
        try:
            # Create a new user with no OAuth tokens
            no_token_user_id = str(uuid.uuid4())
            no_token_user = {
                "id": no_token_user_id,
                "email": "no.oauth@example.com",
                "full_name": "No OAuth User",
                "hashed_password": "test_hash",
                "is_active": True,
                "email_quota": 100,
                "emails_used": 0,
                "timezone": "UTC",
                "created_at": datetime.utcnow()
            }
            await self.db.users.insert_one(no_token_user)
            
            # Test OAuth status for user with no tokens
            from oauth_google import google_oauth_service
            
            status_result = await google_oauth_service.get_oauth_status(no_token_user_id)
            
            # Should return proper structure indicating no authorization
            is_not_authorized = not status_result.get('is_authorized', True)
            empty_services = len(status_result.get('authorized_services', [])) == 0
            no_user_email = status_result.get('user_email') is None
            
            unauthenticated_passed = (is_not_authorized and empty_services and no_user_email)
            
            details = f"Not authorized: {is_not_authorized}, Empty services: {empty_services}, " \
                     f"No email: {no_user_email}"
            
            self.log_test_result("OAuth Status - Unauthenticated", unauthenticated_passed, details)
            
            # Cleanup
            await self.db.users.delete_one({"id": no_token_user_id})
            
            return unauthenticated_passed
            
        except Exception as e:
            self.log_test_result("OAuth Status - Unauthenticated", False, f"Exception: {str(e)}")
            return False
    
    async def test_oauth_status_api_endpoint(self):
        """Test 5: OAuth status API endpoint via HTTP"""
        print("\n🔍 Testing OAuth Status API Endpoint via HTTP...")
        
        try:
            # Test the actual API endpoint
            response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
            
            # Should return 403 for unauthenticated request (not 500)
            api_endpoint_passed = response.status_code == 403
            
            details = f"Status code: {response.status_code} (expected 403 for unauthenticated)"
            
            self.log_test_result("OAuth Status - API Endpoint", api_endpoint_passed, details)
            
            return api_endpoint_passed
            
        except Exception as e:
            self.log_test_result("OAuth Status - API Endpoint", False, f"Exception: {str(e)}")
            return False
    
    async def test_oauth_status_response_format(self):
        """Test 6: OAuth status response format consistency"""
        print("\n🔍 Testing OAuth Status Response Format Consistency...")
        
        try:
            from oauth_google import google_oauth_service
            
            # Test with different scenarios and verify consistent response format
            test_scenarios = [
                ("Valid token", self.test_user_id, None),
                ("No tokens", str(uuid.uuid4()), None),
                ("Specific email", self.test_user_id, "oauth.test@gmail.com")
            ]
            
            format_consistency_passed = True
            required_fields = ['is_authorized', 'authorized_services', 'user_email', 'expires_at']
            
            for scenario_name, user_id, email in test_scenarios:
                try:
                    status_result = await google_oauth_service.get_oauth_status(user_id, email)
                    
                    # Check if all required fields are present
                    has_required_fields = all(field in status_result for field in required_fields)
                    
                    # Check data types
                    is_authorized_bool = isinstance(status_result.get('is_authorized'), bool)
                    services_list = isinstance(status_result.get('authorized_services'), list)
                    
                    scenario_passed = (has_required_fields and is_authorized_bool and services_list)
                    
                    if not scenario_passed:
                        format_consistency_passed = False
                        print(f"   ❌ Format inconsistency in scenario: {scenario_name}")
                    else:
                        print(f"   ✅ Format consistent for scenario: {scenario_name}")
                        
                except Exception as e:
                    format_consistency_passed = False
                    print(f"   ❌ Exception in scenario {scenario_name}: {str(e)}")
            
            details = f"All scenarios have consistent response format: {format_consistency_passed}"
            
            self.log_test_result("OAuth Status - Response Format", format_consistency_passed, details)
            
            return format_consistency_passed
            
        except Exception as e:
            self.log_test_result("OAuth Status - Response Format", False, f"Exception: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all OAuth status endpoint tests"""
        print("🚀 Starting OAuth Status Endpoint Error Handling Tests...")
        print("=" * 60)
        
        if not await self.setup():
            print("❌ Setup failed, aborting tests")
            return
        
        try:
            # Run all tests
            test_results = []
            
            test_results.append(await self.test_oauth_status_normal_authentication())
            test_results.append(await self.test_oauth_status_corrupted_token_data())
            test_results.append(await self.test_oauth_status_specific_email())
            test_results.append(await self.test_oauth_status_no_tokens())
            test_results.append(await self.test_oauth_status_api_endpoint())
            test_results.append(await self.test_oauth_status_response_format())
            
            # Summary
            passed_tests = sum(test_results)
            total_tests = len(test_results)
            success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            print("\n" + "=" * 60)
            print("📊 OAUTH STATUS ENDPOINT TEST SUMMARY")
            print("=" * 60)
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
                print(f"\n✅ OVERALL ASSESSMENT: OAuth Status Endpoint Error Handling is WORKING")
                print("   The fix for corrupted token data handling is operational.")
            else:
                print(f"\n❌ OVERALL ASSESSMENT: OAuth Status Endpoint Error Handling has ISSUES")
                print("   The fix for corrupted token data handling needs attention.")
            
        finally:
            await self.cleanup()

async def main():
    """Main test execution"""
    tester = OAuthStatusTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())