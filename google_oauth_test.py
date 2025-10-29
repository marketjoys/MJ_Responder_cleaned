#!/usr/bin/env python3
"""
Google OAuth Integration Testing for Email Assistant System
Tests OAuth status, authorization initiation, callback handling, and database collections
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid
from urllib.parse import urlparse, parse_qs

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://component-check-2.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')

class GoogleOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        
    async def setup(self):
        """Setup database connection"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
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

    def test_oauth_credentials_configuration(self):
        """Test 1: Verify Google OAuth credentials are properly loaded from environment variables"""
        print("\n🔑 Testing OAuth Credentials Configuration...")
        
        try:
            # Test 1a: Check if credentials are loaded
            client_id_loaded = bool(GOOGLE_CLIENT_ID)
            client_secret_loaded = bool(GOOGLE_CLIENT_SECRET)
            redirect_uri_loaded = bool(GOOGLE_REDIRECT_URI)
            
            # Test 1b: Verify credential format
            client_id_format_valid = (GOOGLE_CLIENT_ID and 
                                    GOOGLE_CLIENT_ID.endswith('.apps.googleusercontent.com') and
                                    len(GOOGLE_CLIENT_ID) > 50)
            
            client_secret_format_valid = (GOOGLE_CLIENT_SECRET and 
                                        GOOGLE_CLIENT_SECRET.startswith('GOCSPX-') and
                                        len(GOOGLE_CLIENT_SECRET) > 20)
            
            redirect_uri_format_valid = (GOOGLE_REDIRECT_URI and 
                                       GOOGLE_REDIRECT_URI.startswith('https://') and
                                       'oauth/google/callback' in GOOGLE_REDIRECT_URI)
            
            # Test 1c: Verify expected values match
            expected_client_id = "691413402120-tlhotgqvkpevgvaaaff8h1r8t7lk0k9i.apps.googleusercontent.com"
            expected_client_secret = "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"
            expected_redirect_uri = "https://component-check-2.preview.emergentagent.com/oauth/google/callback"
            
            credentials_match_expected = (GOOGLE_CLIENT_ID == expected_client_id and
                                        GOOGLE_CLIENT_SECRET == expected_client_secret and
                                        GOOGLE_REDIRECT_URI == expected_redirect_uri)
            
            all_passed = (client_id_loaded and client_secret_loaded and redirect_uri_loaded and
                         client_id_format_valid and client_secret_format_valid and 
                         redirect_uri_format_valid and credentials_match_expected)
            
            details = f"Client ID: {client_id_loaded and client_id_format_valid}, " \
                     f"Client Secret: {client_secret_loaded and client_secret_format_valid}, " \
                     f"Redirect URI: {redirect_uri_loaded and redirect_uri_format_valid}, " \
                     f"Expected Values: {credentials_match_expected}"
            
            self.log_test_result("OAuth Credentials Configuration", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Credentials Configuration", False, f"Exception: {str(e)}")

    def test_authentication_setup(self):
        """Setup authentication for OAuth testing"""
        print("\n🔐 Setting up Authentication for OAuth Testing...")
        
        test_user_email = f"oauth.test.{int(time.time())}@example.com"
        test_password = "OAuthTestPassword123!"
        
        try:
            # Register test user
            register_data = {
                "email": test_user_email,
                "password": test_password,
                "full_name": "OAuth Test User"
            }
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
            
            if response.status_code == 200:
                register_result = response.json()
                self.auth_token = register_result.get('access_token')
                self.test_user_id = register_result.get('user', {}).get('id')
                
                self.log_test_result("OAuth Test User Registration", True, 
                                   f"User ID: {self.test_user_id}, Token: {bool(self.auth_token)}")
                return True
            else:
                self.log_test_result("OAuth Test User Registration", False, 
                                   f"Status: {response.status_code}, Error: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test_result("OAuth Test User Registration", False, f"Exception: {str(e)}")
            return False

    def test_oauth_status_endpoint(self):
        """Test 2: OAuth Status Endpoint (/api/oauth/google/status)"""
        print("\n📊 Testing OAuth Status Endpoint...")
        
        if not self.auth_token:
            self.log_test_result("OAuth Status Endpoint", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 2a: Get OAuth status for new user (should be unauthorized)
            response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
            status_endpoint_accessible = response.status_code == 200
            
            if status_endpoint_accessible:
                status_data = response.json()
                
                # Test 2b: Verify response structure
                has_required_fields = all(field in status_data for field in 
                                        ['is_authorized', 'authorized_services', 'user_email', 'expires_at'])
                
                # Test 2c: Verify initial state (should be unauthorized)
                initial_state_correct = (not status_data.get('is_authorized', True) and
                                       status_data.get('authorized_services', []) == [] and
                                       status_data.get('user_email') is None)
                
                all_passed = status_endpoint_accessible and has_required_fields and initial_state_correct
                
                details = f"Status: {response.status_code}, Authorized: {status_data.get('is_authorized')}, " \
                         f"Services: {status_data.get('authorized_services', [])}, " \
                         f"Required Fields: {has_required_fields}"
            else:
                all_passed = False
                details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            
            self.log_test_result("OAuth Status Endpoint", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Status Endpoint", False, f"Exception: {str(e)}")

    def test_oauth_authorization_initiation(self):
        """Test 3: OAuth Authorization Initiation (/api/oauth/google/authorize)"""
        print("\n🚀 Testing OAuth Authorization Initiation...")
        
        if not self.auth_token:
            self.log_test_result("OAuth Authorization Initiation", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 3a: Request authorization for email service only
            email_only_data = ["email"]
            response = requests.post(f"{API_BASE}/oauth/google/authorize", 
                                   json=email_only_data, headers=headers, timeout=15)
            
            email_auth_passed = response.status_code == 200
            if email_auth_passed:
                email_auth_result = response.json()
                
                # Verify response structure
                has_auth_url = 'auth_url' in email_auth_result
                has_state = 'state' in email_auth_result
                has_requested_services = 'requested_services' in email_auth_result
                
                # Verify auth URL format
                auth_url_valid = False
                if has_auth_url:
                    auth_url = email_auth_result['auth_url']
                    parsed_url = urlparse(auth_url)
                    query_params = parse_qs(parsed_url.query)
                    
                    auth_url_valid = (parsed_url.netloc == 'accounts.google.com' and
                                    'client_id' in query_params and
                                    query_params['client_id'][0] == GOOGLE_CLIENT_ID and
                                    'redirect_uri' in query_params and
                                    query_params['redirect_uri'][0] == GOOGLE_REDIRECT_URI)
                
                email_auth_details = f"Status: {response.status_code}, Auth URL Valid: {auth_url_valid}, " \
                                   f"Has State: {has_state}, Services: {email_auth_result.get('requested_services')}"
            else:
                email_auth_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            
            # Test 3b: Request authorization for both email and calendar services
            both_services_data = ["email", "calendar"]
            response = requests.post(f"{API_BASE}/oauth/google/authorize", 
                                   json=both_services_data, headers=headers, timeout=15)
            
            both_services_passed = response.status_code == 200
            if both_services_passed:
                both_services_result = response.json()
                
                # Verify unified OAuth flow (both services in one request)
                unified_flow_correct = (both_services_result.get('requested_services') == both_services_data)
                
                # Verify scopes include both email and calendar
                auth_url = both_services_result.get('auth_url', '')
                parsed_url = urlparse(auth_url)
                query_params = parse_qs(parsed_url.query)
                scopes = query_params.get('scope', [''])[0].split()
                
                has_email_scopes = any('gmail' in scope for scope in scopes)
                has_calendar_scopes = any('calendar' in scope for scope in scopes)
                
                both_services_details = f"Status: {response.status_code}, Unified Flow: {unified_flow_correct}, " \
                                      f"Email Scopes: {has_email_scopes}, Calendar Scopes: {has_calendar_scopes}"
            else:
                both_services_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            
            # Test 3c: Test invalid service request
            invalid_data = ["invalid_service"]
            response = requests.post(f"{API_BASE}/oauth/google/authorize", 
                                   json=invalid_data, headers=headers, timeout=10)
            
            invalid_service_handled = response.status_code == 400
            invalid_service_details = f"Status: {response.status_code} (should be 400)"
            
            all_passed = (email_auth_passed and auth_url_valid and both_services_passed and 
                         unified_flow_correct and has_email_scopes and has_calendar_scopes and 
                         invalid_service_handled)
            
            # Log individual results
            self.log_test_result("OAuth Auth - Email Only", email_auth_passed and auth_url_valid, email_auth_details)
            self.log_test_result("OAuth Auth - Both Services", both_services_passed and unified_flow_correct, both_services_details)
            self.log_test_result("OAuth Auth - Invalid Service", invalid_service_handled, invalid_service_details)
            
            details = f"Email: {email_auth_passed}, Both Services: {both_services_passed}, " \
                     f"Invalid Handled: {invalid_service_handled}, URL Valid: {auth_url_valid}"
            
            self.log_test_result("OAuth Authorization Initiation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Authorization Initiation", False, f"Exception: {str(e)}")

    def test_oauth_callback_endpoint_accessibility(self):
        """Test 4: OAuth Callback Endpoint Accessibility and Configuration"""
        print("\n🔄 Testing OAuth Callback Endpoint...")
        
        try:
            # Test 4a: Test callback endpoint accessibility (without valid code/state)
            # This should return an error but the endpoint should be accessible
            response = requests.get(f"{API_BASE}/oauth/google/callback?code=test&state=test", timeout=10)
            
            callback_accessible = response.status_code in [400, 401, 500]  # Should fail but be accessible
            
            # Test 4b: Test callback with missing parameters
            response_no_params = requests.get(f"{API_BASE}/oauth/google/callback", timeout=10)
            missing_params_handled = response_no_params.status_code in [400, 422]  # Should handle missing params
            
            # Test 4c: Verify callback URL matches configuration
            callback_url_correct = GOOGLE_REDIRECT_URI.endswith('/oauth/google/callback')
            
            all_passed = callback_accessible and missing_params_handled and callback_url_correct
            
            details = f"Accessible: {callback_accessible} (status: {response.status_code}), " \
                     f"Missing Params Handled: {missing_params_handled} (status: {response_no_params.status_code}), " \
                     f"URL Config: {callback_url_correct}"
            
            self.log_test_result("OAuth Callback Endpoint", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Callback Endpoint", False, f"Exception: {str(e)}")

    async def test_database_collections(self):
        """Test 5: Database Collections for oauth_states and oauth_tokens"""
        print("\n🗄️ Testing OAuth Database Collections...")
        
        try:
            # Test 5a: Check if oauth_states collection exists and can be accessed
            oauth_states_count = await self.db.oauth_states.count_documents({})
            oauth_states_accessible = True
            
            # Test 5b: Check if oauth_tokens collection exists and can be accessed  
            oauth_tokens_count = await self.db.oauth_tokens.count_documents({})
            oauth_tokens_accessible = True
            
            # Test 5c: Test inserting a test state record
            test_state = {
                "id": str(uuid.uuid4()),
                "user_id": "test_user_id",
                "state": "test_state_value",
                "requested_services": ["email"],
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "used": False
            }
            
            insert_result = await self.db.oauth_states.insert_one(test_state)
            state_insert_successful = bool(insert_result.inserted_id)
            
            # Test 5d: Test querying the inserted state
            found_state = await self.db.oauth_states.find_one({"id": test_state["id"]})
            state_query_successful = found_state is not None
            
            # Test 5e: Test updating the state
            update_result = await self.db.oauth_states.update_one(
                {"id": test_state["id"]},
                {"$set": {"used": True}}
            )
            state_update_successful = update_result.modified_count == 1
            
            # Test 5f: Clean up test data
            delete_result = await self.db.oauth_states.delete_one({"id": test_state["id"]})
            cleanup_successful = delete_result.deleted_count == 1
            
            # Test 5g: Test oauth_tokens collection operations
            test_token = {
                "id": str(uuid.uuid4()),
                "user_id": "test_user_id",
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "token_type": "Bearer",
                "expires_at": datetime.utcnow() + timedelta(hours=1),
                "scope": "test scope",
                "authorized_services": ["email"],
                "user_email": "test@example.com",
                "user_name": "Test User",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            token_insert_result = await self.db.oauth_tokens.insert_one(test_token)
            token_insert_successful = bool(token_insert_result.inserted_id)
            
            # Clean up token test data
            await self.db.oauth_tokens.delete_one({"id": test_token["id"]})
            
            all_passed = (oauth_states_accessible and oauth_tokens_accessible and 
                         state_insert_successful and state_query_successful and 
                         state_update_successful and cleanup_successful and 
                         token_insert_successful)
            
            details = f"States Collection: {oauth_states_accessible} ({oauth_states_count} docs), " \
                     f"Tokens Collection: {oauth_tokens_accessible} ({oauth_tokens_count} docs), " \
                     f"CRUD Operations: Insert={state_insert_successful}, Query={state_query_successful}, " \
                     f"Update={state_update_successful}, Delete={cleanup_successful}"
            
            self.log_test_result("OAuth Database Collections", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Database Collections", False, f"Exception: {str(e)}")

    def test_oauth_revoke_endpoint(self):
        """Test 6: OAuth Revoke Endpoint"""
        print("\n🚫 Testing OAuth Revoke Endpoint...")
        
        if not self.auth_token:
            self.log_test_result("OAuth Revoke Endpoint", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test revoke endpoint (should work even without existing tokens)
            response = requests.post(f"{API_BASE}/oauth/google/revoke", headers=headers, timeout=10)
            
            revoke_accessible = response.status_code == 200
            if revoke_accessible:
                revoke_result = response.json()
                has_success_field = 'success' in revoke_result
                has_message_field = 'message' in revoke_result
                
                revoke_details = f"Status: {response.status_code}, Success: {revoke_result.get('success')}, " \
                               f"Message: {bool(revoke_result.get('message'))}"
            else:
                has_success_field = has_message_field = False
                revoke_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            
            all_passed = revoke_accessible and has_success_field and has_message_field
            
            self.log_test_result("OAuth Revoke Endpoint", all_passed, revoke_details)
            
        except Exception as e:
            self.log_test_result("OAuth Revoke Endpoint", False, f"Exception: {str(e)}")

    def test_oauth_unified_flow_support(self):
        """Test 7: Unified OAuth Flow (requesting both email and calendar permissions)"""
        print("\n🔗 Testing Unified OAuth Flow Support...")
        
        if not self.auth_token:
            self.log_test_result("Unified OAuth Flow", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test unified flow by requesting both services
            unified_request = ["email", "calendar"]
            response = requests.post(f"{API_BASE}/oauth/google/authorize", 
                                   json=unified_request, headers=headers, timeout=15)
            
            unified_flow_works = response.status_code == 200
            
            if unified_flow_works:
                result = response.json()
                
                # Verify both services are requested
                both_services_requested = result.get('requested_services') == unified_request
                
                # Parse the auth URL to check scopes
                auth_url = result.get('auth_url', '')
                parsed_url = urlparse(auth_url)
                query_params = parse_qs(parsed_url.query)
                scopes = query_params.get('scope', [''])[0].split()
                
                # Check for Gmail scopes
                gmail_scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/gmail.modify'
                ]
                has_gmail_scopes = any(scope in scopes for scope in gmail_scopes)
                
                # Check for Calendar scopes
                calendar_scopes = [
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/calendar.events'
                ]
                has_calendar_scopes = any(scope in scopes for scope in calendar_scopes)
                
                # Check for user info scopes
                userinfo_scopes = [
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile'
                ]
                has_userinfo_scopes = any(scope in scopes for scope in userinfo_scopes)
                
                # Verify OAuth parameters
                has_offline_access = query_params.get('access_type', [''])[0] == 'offline'
                has_consent_prompt = query_params.get('prompt', [''])[0] == 'consent'
                
                all_passed = (unified_flow_works and both_services_requested and 
                             has_gmail_scopes and has_calendar_scopes and has_userinfo_scopes and
                             has_offline_access and has_consent_prompt)
                
                details = f"Status: {response.status_code}, Both Services: {both_services_requested}, " \
                         f"Gmail Scopes: {has_gmail_scopes}, Calendar Scopes: {has_calendar_scopes}, " \
                         f"UserInfo Scopes: {has_userinfo_scopes}, Offline Access: {has_offline_access}, " \
                         f"Consent Prompt: {has_consent_prompt}"
            else:
                all_passed = False
                details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            
            self.log_test_result("Unified OAuth Flow", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Unified OAuth Flow", False, f"Exception: {str(e)}")

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🏁 GOOGLE OAUTH TESTING SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        print("\n" + "=" * 80)

    async def run_oauth_tests(self):
        """Run comprehensive Google OAuth tests"""
        print("🚀 Starting Google OAuth Integration Testing")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        print(f"Google Client ID: {GOOGLE_CLIENT_ID}")
        print(f"Google Redirect URI: {GOOGLE_REDIRECT_URI}")
        print("=" * 80)
        
        # Setup
        if not await self.setup():
            return
        
        # Test 1: OAuth Credentials Configuration
        self.test_oauth_credentials_configuration()
        
        # Setup authentication for OAuth testing
        if not self.test_authentication_setup():
            print("❌ Cannot proceed with OAuth tests - authentication setup failed")
            await self.cleanup()
            return
        
        # Test 2: OAuth Status Endpoint
        self.test_oauth_status_endpoint()
        
        # Test 3: OAuth Authorization Initiation
        self.test_oauth_authorization_initiation()
        
        # Test 4: OAuth Callback Endpoint
        self.test_oauth_callback_endpoint_accessibility()
        
        # Test 5: Database Collections
        await self.test_database_collections()
        
        # Test 6: OAuth Revoke Endpoint
        self.test_oauth_revoke_endpoint()
        
        # Test 7: Unified OAuth Flow
        self.test_oauth_unified_flow_support()
        
        # Cleanup
        await self.cleanup()
        
        # Print summary
        self.print_test_summary()

async def main():
    """Main function to run Google OAuth tests"""
    tester = GoogleOAuthTester()
    await tester.run_oauth_tests()

if __name__ == "__main__":
    asyncio.run(main())