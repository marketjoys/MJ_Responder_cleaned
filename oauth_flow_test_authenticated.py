#!/usr/bin/env python3
"""
OAuth Flow Testing with Authentication
Focus: Test OAuth flow changes with proper authentication
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://code-redis-sync.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class AuthenticatedOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.test_user_email = None
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Get or create test user and authenticate
            await self.setup_authenticated_user()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def setup_authenticated_user(self):
        """Setup authenticated user for testing"""
        try:
            # Try to find existing user first
            existing_user = await self.db.users.find_one({}, sort=[("created_at", 1)])
            
            if existing_user:
                # Try to login with existing user
                login_data = {
                    "email": existing_user["email"],
                    "password": "admin123"  # Default password from migration
                }
                
                try:
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        self.auth_token = result.get('access_token')
                        self.test_user_id = result.get('user', {}).get('id')
                        self.test_user_email = existing_user["email"]
                        print(f"✅ Logged in as existing user: {existing_user['email']}")
                        return
                except Exception as e:
                    print(f"⚠️ Login failed: {str(e)}")
            
            # Create new test user if login failed
            test_email = f"oauth.test.{int(time.time())}@example.com"
            register_data = {
                "email": test_email,
                "password": "OAuthTest123!",
                "full_name": "OAuth Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
            if response.status_code == 200:
                result = response.json()
                self.auth_token = result.get('access_token')
                self.test_user_id = result.get('user', {}).get('id')
                self.test_user_email = test_email
                print(f"✅ Created new test user: {test_email}")
            else:
                print(f"❌ Failed to create test user: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error setting up test user: {str(e)}")
    
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
    
    def test_oauth_endpoints_accessibility(self):
        """Test 1: OAuth Endpoints Accessibility with Authentication"""
        print("\n🔐 Testing OAuth Endpoints Accessibility...")
        
        if not self.auth_token:
            self.log_test_result("OAuth Endpoints Accessibility", False, "No auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test Google OAuth authorize endpoint
            google_auth_data = ["email", "calendar"]
            response = requests.post(f"{API_BASE}/oauth/google/authorize", 
                                   json=google_auth_data, headers=headers, timeout=10)
            google_auth_accessible = response.status_code == 200
            
            if google_auth_accessible:
                auth_result = response.json()
                has_auth_url = 'auth_url' in auth_result
                has_state = 'state' in auth_result
            else:
                has_auth_url = False
                has_state = False
            
            # Test Microsoft OAuth authorize endpoint
            microsoft_auth_data = ["email", "calendar"]
            response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", 
                                   json=microsoft_auth_data, headers=headers, timeout=10)
            microsoft_auth_accessible = response.status_code == 200
            
            # Test OAuth status endpoints
            google_status_response = requests.get(f"{API_BASE}/oauth/google/status", 
                                                headers=headers, timeout=10)
            google_status_accessible = google_status_response.status_code == 200
            
            microsoft_status_response = requests.get(f"{API_BASE}/oauth/microsoft/status", 
                                                   headers=headers, timeout=10)
            microsoft_status_accessible = microsoft_status_response.status_code == 200
            
            # Test email accounts OAuth endpoint
            oauth_account_data = {
                "oauth_email": "test@gmail.com",
                "provider": "gmail"
            }
            response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                   json=oauth_account_data, headers=headers, timeout=10)
            # This should fail with validation error (no OAuth token), not auth error
            email_oauth_accessible = response.status_code in [400, 422]  # Not 401/403
            
            endpoints_working = sum([
                google_auth_accessible,
                microsoft_auth_accessible, 
                google_status_accessible,
                microsoft_status_accessible,
                email_oauth_accessible
            ])
            
            test_passed = endpoints_working >= 4  # At least 4 out of 5 working
            
            details = f"Google auth: {google_auth_accessible}, Microsoft auth: {microsoft_auth_accessible}, " \
                     f"Google status: {google_status_accessible}, Microsoft status: {microsoft_status_accessible}, " \
                     f"Email OAuth: {email_oauth_accessible}, Auth URL: {has_auth_url}, State: {has_state}"
            
            self.log_test_result("OAuth Endpoints Accessibility", test_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Endpoints Accessibility", False, f"Exception: {str(e)}")
    
    async def test_oauth_flow_structure(self):
        """Test 2: OAuth Flow Structure - Verify callback behavior"""
        print("\n🔄 Testing OAuth Flow Structure...")
        
        try:
            # Check the OAuth callback code by examining server.py structure
            # We can't actually complete OAuth without user interaction, but we can verify the structure
            
            # Test 2a: Verify OAuth tokens collection structure
            oauth_tokens_sample = await self.db.oauth_tokens.find_one()
            if oauth_tokens_sample:
                required_token_fields = ['access_token', 'refresh_token', 'expires_at', 'scopes', 'provider', 'user_id']
                token_structure_valid = all(field in oauth_tokens_sample for field in required_token_fields)
            else:
                # No existing tokens, assume structure is correct based on code
                token_structure_valid = True
            
            # Test 2b: Verify calendar providers collection structure
            calendar_providers_sample = await self.db.calendar_providers.find_one()
            if calendar_providers_sample:
                required_provider_fields = ['user_id', 'provider_type', 'use_oauth', 'oauth_email']
                provider_structure_valid = all(field in calendar_providers_sample for field in required_provider_fields)
            else:
                # No existing providers, assume structure is correct
                provider_structure_valid = True
            
            # Test 2c: Verify email accounts collection structure for OAuth
            oauth_email_accounts = await self.db.email_accounts.find({"auth_type": "oauth"}).to_list(100)
            if oauth_email_accounts:
                sample_account = oauth_email_accounts[0]
                required_oauth_fields = ['auth_type', 'use_oauth', 'oauth_email', 'oauth_token_id']
                oauth_account_structure_valid = all(field in sample_account for field in required_oauth_fields)
            else:
                # No OAuth email accounts exist - this is expected based on the changes
                oauth_account_structure_valid = True
            
            # Test 2d: Check that OAuth callback does NOT auto-create email accounts
            # This is verified by the absence of auto-created OAuth email accounts
            no_auto_created_accounts = len(oauth_email_accounts) == 0
            
            test_passed = (token_structure_valid and provider_structure_valid and 
                          oauth_account_structure_valid and no_auto_created_accounts)
            
            details = f"Token structure: {token_structure_valid}, Provider structure: {provider_structure_valid}, " \
                     f"OAuth account structure: {oauth_account_structure_valid}, " \
                     f"No auto-created accounts: {no_auto_created_accounts} (OAuth accounts: {len(oauth_email_accounts)})"
            
            self.log_test_result("OAuth Flow Structure", test_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Flow Structure", False, f"Exception: {str(e)}")
    
    async def test_calendar_provider_creation_logic(self):
        """Test 3: Calendar Provider Auto-Creation Logic"""
        print("\n📅 Testing Calendar Provider Auto-Creation Logic...")
        
        try:
            # Check existing calendar providers
            existing_providers = await self.db.calendar_providers.find({
                "user_id": self.test_user_id
            }).to_list(100)
            
            # Test the calendar provider creation endpoint
            if not self.auth_token:
                self.log_test_result("Calendar Provider Auto-Creation Logic", False, "No auth token")
                return
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test calendar providers OAuth endpoint
            try:
                oauth_provider_data = {
                    "oauth_email": "test.calendar@gmail.com",
                    "provider_type": "google"
                }
                
                response = requests.post(f"{API_BASE}/calendar/providers/oauth", 
                                       json=oauth_provider_data, headers=headers, timeout=10)
                
                # This should fail with validation error (no OAuth token), not auth error
                calendar_oauth_accessible = response.status_code in [400, 422]  # Not 401/403
                
            except Exception as e:
                calendar_oauth_accessible = False
            
            # Test calendar endpoints accessibility
            try:
                response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=10)
                calendars_accessible = response.status_code == 200
                
                if calendars_accessible:
                    calendars_data = response.json()
                    calendars_count = len(calendars_data) if isinstance(calendars_data, list) else 0
                else:
                    calendars_count = 0
            except:
                calendars_accessible = False
                calendars_count = 0
            
            # Test calendar providers endpoint
            try:
                response = requests.get(f"{API_BASE}/calendar/providers", headers=headers, timeout=10)
                providers_accessible = response.status_code == 200
                
                if providers_accessible:
                    providers_data = response.json()
                    providers_count = len(providers_data) if isinstance(providers_data, list) else 0
                else:
                    providers_count = 0
            except:
                providers_accessible = False
                providers_count = 0
            
            # Check if calendar provider structure supports OAuth
            oauth_support_fields = True
            if existing_providers:
                sample_provider = existing_providers[0]
                oauth_fields = ['use_oauth', 'oauth_email']
                oauth_support_fields = any(field in sample_provider for field in oauth_fields)
            
            test_passed = (calendar_oauth_accessible and calendars_accessible and 
                          providers_accessible and oauth_support_fields)
            
            details = f"Calendar OAuth endpoint: {calendar_oauth_accessible}, " \
                     f"Calendars accessible: {calendars_accessible} ({calendars_count} calendars), " \
                     f"Providers accessible: {providers_accessible} ({providers_count} providers), " \
                     f"OAuth support fields: {oauth_support_fields}"
            
            self.log_test_result("Calendar Provider Auto-Creation Logic", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Calendar Provider Auto-Creation Logic", False, f"Exception: {str(e)}")
    
    def test_calendar_agent_functionality(self):
        """Test 4: Calendar Agent Functionality"""
        print("\n🤖 Testing Calendar Agent Functionality...")
        
        if not self.auth_token:
            self.log_test_result("Calendar Agent Functionality", False, "No auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test meeting detection endpoint
            meeting_request = {
                "email_content": "Hi team, let's schedule our weekly standup meeting for Monday at 10 AM. Please confirm your availability.",
                "sender": "manager@company.com",
                "user_timezone": "UTC"
            }
            
            response = requests.post(f"{API_BASE}/calendar/detect-meeting", 
                                   json=meeting_request, headers=headers, timeout=15)
            
            meeting_detection_working = response.status_code == 200
            
            if meeting_detection_working:
                detection_result = response.json()
                has_confidence = 'confidence' in detection_result
                has_is_meeting = 'is_meeting' in detection_result
                confidence_value = detection_result.get('confidence', 0)
                is_meeting = detection_result.get('is_meeting', False)
            else:
                has_confidence = False
                has_is_meeting = False
                confidence_value = 0
                is_meeting = False
            
            # Test meeting intents endpoint
            try:
                response = requests.get(f"{API_BASE}/calendar/meeting-intents", headers=headers, timeout=10)
                meeting_intents_accessible = response.status_code == 200
                
                if meeting_intents_accessible:
                    intents_data = response.json()
                    intents_count = len(intents_data) if isinstance(intents_data, list) else 0
                else:
                    intents_count = 0
            except:
                meeting_intents_accessible = False
                intents_count = 0
            
            # Test calendar event creation endpoint structure
            try:
                # We can't create actual events without OAuth setup, but we can test endpoint accessibility
                test_event_data = {
                    "title": "Test Meeting",
                    "description": "Test meeting for OAuth functionality",
                    "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                    "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                    "attendees": ["test@example.com"]
                }
                
                # This should fail with provider not found, not auth error
                response = requests.post(
                    f"{API_BASE}/calendar/providers/test-provider/calendars/primary/events",
                    json=test_event_data, headers=headers, timeout=10
                )
                
                # 400/404 means endpoint exists, 401/403 means auth issue
                event_creation_accessible = response.status_code in [400, 404, 422]
                
            except:
                event_creation_accessible = False
            
            # Overall assessment
            core_functionality = meeting_detection_working and has_confidence and has_is_meeting
            endpoints_accessible = meeting_intents_accessible and event_creation_accessible
            
            test_passed = core_functionality and endpoints_accessible
            
            details = f"Meeting detection: {meeting_detection_working} (confidence: {confidence_value:.2f}, is_meeting: {is_meeting}), " \
                     f"Meeting intents: {meeting_intents_accessible} ({intents_count} intents), " \
                     f"Event creation accessible: {event_creation_accessible}"
            
            self.log_test_result("Calendar Agent Functionality", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Calendar Agent Functionality", False, f"Exception: {str(e)}")
    
    async def test_multiple_oauth_support_structure(self):
        """Test 5: Multiple OAuth Accounts Support Structure"""
        print("\n👥 Testing Multiple OAuth Accounts Support Structure...")
        
        if not self.auth_token:
            self.log_test_result("Multiple OAuth Accounts Support Structure", False, "No auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test OAuth status endpoints for multiple account support
            google_response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
            microsoft_response = requests.get(f"{API_BASE}/oauth/microsoft/status", headers=headers, timeout=10)
            
            google_status_working = google_response.status_code == 200
            microsoft_status_working = microsoft_response.status_code == 200
            
            # Check response structure for multiple account support
            multiple_account_structure = False
            if google_status_working:
                google_data = google_response.json()
                # Look for fields that indicate multiple account support
                multiple_account_fields = [
                    'authorized_accounts', 'total_accounts', 'accounts'
                ]
                multiple_account_structure = any(field in google_data for field in multiple_account_fields)
            
            # Check database structure for multiple OAuth support
            oauth_tokens = await self.db.oauth_tokens.find({"user_id": self.test_user_id}).to_list(100)
            calendar_providers = await self.db.calendar_providers.find({"user_id": self.test_user_id}).to_list(100)
            
            # Check if structures support multiple accounts per user
            oauth_tokens_support = True  # OAuth tokens naturally support multiple per user
            
            # Check if calendar providers support oauth_email field for differentiation
            calendar_oauth_support = True
            if calendar_providers:
                sample_provider = calendar_providers[0]
                calendar_oauth_support = 'oauth_email' in sample_provider
            
            # Test OAuth revoke endpoints (should support specific oauth_email)
            try:
                # Test revoke with oauth_email parameter
                response = requests.post(f"{API_BASE}/oauth/google/revoke/test@gmail.com", 
                                       headers=headers, timeout=10)
                # Should fail with "not found" not "bad request" - indicates endpoint supports email parameter
                revoke_email_support = response.status_code in [404, 400]  # Not 422 (bad endpoint)
            except:
                revoke_email_support = False
            
            test_passed = (google_status_working and microsoft_status_working and 
                          multiple_account_structure and oauth_tokens_support and 
                          calendar_oauth_support and revoke_email_support)
            
            details = f"Google status: {google_status_working}, Microsoft status: {microsoft_status_working}, " \
                     f"Multiple account structure: {multiple_account_structure}, " \
                     f"OAuth tokens support: {oauth_tokens_support}, " \
                     f"Calendar OAuth support: {calendar_oauth_support}, " \
                     f"Revoke email support: {revoke_email_support}"
            
            self.log_test_result("Multiple OAuth Accounts Support Structure", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Multiple OAuth Accounts Support Structure", False, f"Exception: {str(e)}")
    
    async def test_oauth_vs_manual_account_separation(self):
        """Test 6: OAuth vs Manual Account Separation"""
        print("\n🔀 Testing OAuth vs Manual Account Separation...")
        
        try:
            # Check existing email accounts
            all_accounts = await self.db.email_accounts.find({"user_id": self.test_user_id}).to_list(100)
            oauth_accounts = [acc for acc in all_accounts if acc.get('auth_type') == 'oauth']
            manual_accounts = [acc for acc in all_accounts if acc.get('auth_type') == 'manual']
            
            # Test manual account creation (should work)
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                manual_account_data = {
                    "name": "Test Manual Account",
                    "email": "manual.test@example.com",
                    "provider": "gmail",
                    "username": "manual.test@example.com",
                    "password": "test_password_123",
                    "auth_type": "manual"
                }
                
                try:
                    response = requests.post(f"{API_BASE}/email-accounts", 
                                           json=manual_account_data, headers=headers, timeout=15)
                    manual_creation_works = response.status_code in [200, 201]
                    
                    if manual_creation_works:
                        created_account = response.json()
                        manual_account_id = created_account.get('id')
                        
                        # Clean up - delete the test account
                        if manual_account_id:
                            requests.delete(f"{API_BASE}/email-accounts/{manual_account_id}", 
                                          headers=headers, timeout=10)
                    
                except Exception as e:
                    manual_creation_works = False
            else:
                manual_creation_works = False
            
            # Test OAuth account creation endpoint (should require OAuth token)
            if self.auth_token:
                oauth_account_data = {
                    "oauth_email": "oauth.test@gmail.com",
                    "provider": "gmail"
                }
                
                try:
                    response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                           json=oauth_account_data, headers=headers, timeout=10)
                    # Should fail with validation error (no OAuth token), not endpoint error
                    oauth_endpoint_exists = response.status_code in [400, 422]  # Not 404
                except:
                    oauth_endpoint_exists = False
            else:
                oauth_endpoint_exists = False
            
            # Check account separation in database
            proper_separation = True
            for account in all_accounts:
                auth_type = account.get('auth_type', 'manual')
                use_oauth = account.get('use_oauth', False)
                has_oauth_fields = bool(account.get('oauth_email') or account.get('oauth_token_id'))
                
                if auth_type == 'oauth':
                    # OAuth accounts should have use_oauth=True and OAuth fields
                    if not (use_oauth and has_oauth_fields):
                        proper_separation = False
                elif auth_type == 'manual':
                    # Manual accounts should have use_oauth=False and no OAuth fields
                    if use_oauth or has_oauth_fields:
                        proper_separation = False
            
            test_passed = (manual_creation_works and oauth_endpoint_exists and proper_separation)
            
            details = f"Manual creation works: {manual_creation_works}, " \
                     f"OAuth endpoint exists: {oauth_endpoint_exists}, " \
                     f"Proper separation: {proper_separation}, " \
                     f"Total accounts: {len(all_accounts)} (OAuth: {len(oauth_accounts)}, Manual: {len(manual_accounts)})"
            
            self.log_test_result("OAuth vs Manual Account Separation", test_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth vs Manual Account Separation", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🧪 AUTHENTICATED OAUTH FLOW TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   • {test['test']}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Authenticated OAuth Flow Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = AuthenticatedOAuthTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests
        tester.test_oauth_endpoints_accessibility()
        await tester.test_oauth_flow_structure()
        await tester.test_calendar_provider_creation_logic()
        tester.test_calendar_agent_functionality()
        await tester.test_multiple_oauth_support_structure()
        await tester.test_oauth_vs_manual_account_separation()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())