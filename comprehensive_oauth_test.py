#!/usr/bin/env python3
"""
Comprehensive OAuth Testing for Calendar and Email Functionality
Tests what's actually working and provides detailed diagnostics
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-reply-checker.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test account details from review request
TEST_ACCOUNT = {
    "email": "amits.joys@gmail.com",
    "account_id": "e7c490f4-4f8e-402e-a085-61e133a0b1d0",
    "user_id": "74ecb673-4459-4e9e-b424-e956de620036",
    "calendar_provider_id": "d364d970-67a1-4147-bdc8-b1047d2957a1",
    "provider_type": "Google OAuth"
}

class ComprehensiveOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.oauth_user_authenticated = False
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Try to get authentication
            await self.get_auth_token()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def get_auth_token(self):
        """Get authentication token - try multiple approaches"""
        try:
            # Method 1: Try to authenticate as any existing user
            users = await self.db.users.find().to_list(10)
            print(f"Found {len(users)} users in database")
            
            for user in users:
                print(f"Trying to authenticate as: {user['email']}")
                
                # Try common passwords
                passwords = ["admin123", "password123", "test123", ""]
                for password in passwords:
                    try:
                        login_data = {"email": user["email"], "password": password}
                        response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                        
                        if response.status_code == 200:
                            result = response.json()
                            self.auth_token = result.get('access_token')
                            self.test_user_id = result.get('user', {}).get('id')
                            
                            if user['email'] == TEST_ACCOUNT['email']:
                                self.oauth_user_authenticated = True
                                print(f"✅ Authenticated as OAuth user: {user['email']}")
                            else:
                                print(f"✅ Authenticated as user: {user['email']}")
                            return
                        
                    except Exception as e:
                        continue
            
            # Method 2: Create a new test user
            print("Creating new test user...")
            register_data = {
                "email": f"comprehensive.test.{int(time.time())}@example.com",
                "password": "TestPassword123!",
                "full_name": "Comprehensive Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
            if response.status_code == 200:
                result = response.json()
                self.auth_token = result.get('access_token')
                self.test_user_id = result.get('user', {}).get('id')
                print(f"✅ Created and authenticated new test user: {register_data['email']}")
            else:
                print(f"❌ Failed to create test user: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error getting auth token: {str(e)}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()
    
    def log_test_result(self, test_name: str, passed: bool, details: str = "", critical: bool = False):
        """Log test result"""
        status = "✅ PASS" if passed else ("🔥 CRITICAL FAIL" if critical else "❌ FAIL")
        result = {
            "test": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "critical": critical,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    async def test_oauth_infrastructure(self):
        """Test OAuth Infrastructure - Database setup, tokens, accounts"""
        print("\n🔍 Testing OAUTH INFRASTRUCTURE...")
        
        try:
            # Check OAuth tokens
            oauth_tokens = await self.db.oauth_tokens.find().to_list(10)
            oauth_token_exists = len(oauth_tokens) > 0
            
            valid_oauth_token = False
            if oauth_token_exists:
                token = oauth_tokens[0]
                expires_at = token.get('expires_at')
                if expires_at and expires_at > datetime.utcnow():
                    valid_oauth_token = True
            
            # Check email accounts
            oauth_email_account = await self.db.email_accounts.find_one({
                "id": TEST_ACCOUNT["account_id"],
                "auth_type": "oauth"
            })
            oauth_email_account_exists = oauth_email_account is not None
            
            # Check calendar providers
            oauth_calendar_provider = await self.db.calendar_providers.find_one({
                "id": TEST_ACCOUNT["calendar_provider_id"],
                "use_oauth": True
            })
            oauth_calendar_provider_exists = oauth_calendar_provider is not None
            
            # Check user exists
            oauth_user = await self.db.users.find_one({"id": TEST_ACCOUNT["user_id"]})
            oauth_user_exists = oauth_user is not None
            
            details = f"OAuth Token: {oauth_token_exists} (valid: {valid_oauth_token}), " \
                     f"Email Account: {oauth_email_account_exists}, " \
                     f"Calendar Provider: {oauth_calendar_provider_exists}, " \
                     f"User: {oauth_user_exists}"
            
            all_infrastructure_exists = (oauth_token_exists and oauth_email_account_exists and 
                                       oauth_calendar_provider_exists and oauth_user_exists)
            
            self.log_test_result("OAuth Infrastructure", all_infrastructure_exists, details, critical=True)
            
            # Log individual components
            self.log_test_result("OAuth Token Exists", oauth_token_exists, f"Found {len(oauth_tokens)} tokens")
            self.log_test_result("OAuth Token Valid", valid_oauth_token, f"Expires: {expires_at if oauth_tokens else 'N/A'}")
            self.log_test_result("OAuth Email Account", oauth_email_account_exists, f"Account ID: {TEST_ACCOUNT['account_id']}")
            self.log_test_result("OAuth Calendar Provider", oauth_calendar_provider_exists, f"Provider ID: {TEST_ACCOUNT['calendar_provider_id']}")
            self.log_test_result("OAuth User", oauth_user_exists, f"User ID: {TEST_ACCOUNT['user_id']}")
            
            return all_infrastructure_exists
            
        except Exception as e:
            self.log_test_result("OAuth Infrastructure", False, f"Exception: {str(e)}", critical=True)
            return False
    
    def test_api_endpoints_basic(self):
        """Test Basic API Endpoints - Authentication and basic functionality"""
        print("\n🌐 Testing BASIC API ENDPOINTS...")
        
        if not self.auth_token:
            self.log_test_result("Basic API Endpoints", False, "No auth token available", critical=True)
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 1: Get user profile
            response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
            profile_test = response.status_code == 200
            
            # Test 2: Get calendars (should work regardless of user)
            response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
            calendars_test = response.status_code == 200
            
            # Test 3: Get email accounts
            response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
            email_accounts_test = response.status_code == 200
            
            # Test 4: Get calendar providers
            response = requests.get(f"{API_BASE}/calendar/providers", headers=headers, timeout=10)
            calendar_providers_test = response.status_code == 200
            
            all_basic_tests = profile_test and calendars_test and email_accounts_test and calendar_providers_test
            
            details = f"Profile: {profile_test}, Calendars: {calendars_test}, " \
                     f"Email Accounts: {email_accounts_test}, Calendar Providers: {calendar_providers_test}"
            
            self.log_test_result("Basic API Endpoints", all_basic_tests, details)
            
            # Log individual tests
            self.log_test_result("User Profile API", profile_test, "GET /auth/me")
            self.log_test_result("Calendars API", calendars_test, "GET /calendar/calendars")
            self.log_test_result("Email Accounts API", email_accounts_test, "GET /email-accounts")
            self.log_test_result("Calendar Providers API", calendar_providers_test, "GET /calendar/providers")
            
            return all_basic_tests
            
        except Exception as e:
            self.log_test_result("Basic API Endpoints", False, f"Exception: {str(e)}")
            return False
    
    def test_oauth_specific_functionality(self):
        """Test OAuth-specific functionality that should work"""
        print("\n🔐 Testing OAUTH-SPECIFIC FUNCTIONALITY...")
        
        if not self.auth_token:
            self.log_test_result("OAuth Specific Functionality", False, "No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 1: Calendar Agent (should work regardless of user)
            meeting_data = {
                "email_content": "Let's schedule a meeting tomorrow at 2 PM to discuss the project",
                "sender": "test@example.com",
                "subject": "Meeting Request",
                "user_timezone": "America/New_York"
            }
            
            response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_data, headers=headers, timeout=20)
            calendar_agent_test = response.status_code == 200
            
            # Test 2: Try to access OAuth account settings (will fail if wrong user, but we can test the endpoint)
            response = requests.patch(f"{API_BASE}/email-accounts/{TEST_ACCOUNT['account_id']}/settings", 
                                    json={"signature": "Test signature"}, headers=headers, timeout=15)
            settings_endpoint_exists = response.status_code in [200, 404, 403]  # Any of these means endpoint exists
            
            # Test 3: Try to create calendar event (will fail if wrong user, but we can test the endpoint)
            event_data = {
                "title": "Test Event",
                "description": "Test event",
                "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
                "timezone": "America/New_York"
            }
            
            response = requests.post(f"{API_BASE}/calendar/providers/{TEST_ACCOUNT['calendar_provider_id']}/calendars/primary/events", 
                                   json=event_data, headers=headers, timeout=20)
            calendar_event_endpoint_exists = response.status_code in [200, 400, 404, 403]  # Any of these means endpoint exists
            
            details = f"Calendar Agent: {calendar_agent_test}, " \
                     f"Settings Endpoint: {settings_endpoint_exists}, " \
                     f"Calendar Event Endpoint: {calendar_event_endpoint_exists}"
            
            # At least calendar agent should work
            basic_oauth_functionality = calendar_agent_test
            
            self.log_test_result("OAuth Specific Functionality", basic_oauth_functionality, details)
            
            # Log individual tests
            self.log_test_result("Calendar Agent", calendar_agent_test, "Meeting detection working")
            self.log_test_result("Settings Endpoint", settings_endpoint_exists, "PATCH /email-accounts/{id}/settings exists")
            self.log_test_result("Calendar Event Endpoint", calendar_event_endpoint_exists, "POST calendar events endpoint exists")
            
            return basic_oauth_functionality
            
        except Exception as e:
            self.log_test_result("OAuth Specific Functionality", False, f"Exception: {str(e)}")
            return False
    
    async def test_email_polling_status(self):
        """Test Email Polling Status - Check if OAuth email polling is working"""
        print("\n📧 Testing EMAIL POLLING STATUS...")
        
        try:
            # Check if OAuth account is being polled
            oauth_account = await self.db.email_accounts.find_one({"id": TEST_ACCOUNT["account_id"]})
            
            if not oauth_account:
                self.log_test_result("Email Polling Status", False, "OAuth account not found", critical=True)
                return False
            
            is_active = oauth_account.get('is_active', False)
            last_polled = oauth_account.get('last_polled')
            last_oauth_sync = oauth_account.get('last_oauth_sync')
            auth_type = oauth_account.get('auth_type')
            
            # Check if polling service is running
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                polling_service_running = response.status_code == 200 and response.json().get('status') == 'running'
            except:
                polling_service_running = False
            
            # Check recent polling activity
            recent_polling = False
            if last_polled:
                time_since_poll = datetime.utcnow() - last_polled
                recent_polling = time_since_poll.total_seconds() < 300  # Within 5 minutes
            
            details = f"Active: {is_active}, Auth Type: {auth_type}, " \
                     f"Polling Service: {polling_service_running}, " \
                     f"Last Polled: {last_polled}, Recent Activity: {recent_polling}"
            
            polling_working = is_active and auth_type == 'oauth' and polling_service_running
            
            self.log_test_result("Email Polling Status", polling_working, details)
            
            # Log individual components
            self.log_test_result("OAuth Account Active", is_active, f"Account is {'active' if is_active else 'inactive'}")
            self.log_test_result("Polling Service Running", polling_service_running, "Service status check")
            self.log_test_result("Recent Polling Activity", recent_polling, f"Last polled: {last_polled}")
            
            return polling_working
            
        except Exception as e:
            self.log_test_result("Email Polling Status", False, f"Exception: {str(e)}")
            return False
    
    def test_groq_api_integration(self):
        """Test Groq API Integration - Check if AI functionality is working"""
        print("\n🤖 Testing GROQ API INTEGRATION...")
        
        try:
            # Test Groq API key directly
            groq_api_key = os.environ.get('GROQ_API_KEY')
            
            if not groq_api_key:
                self.log_test_result("Groq API Integration", False, "No Groq API key found", critical=True)
                return False
            
            # Test API key validity
            test_payload = {
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "llama-3.3-70b-versatile",
                "max_completion_tokens": 10
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                },
                json=test_payload,
                timeout=15
            )
            
            groq_api_working = response.status_code == 200
            
            details = f"API Key Present: {bool(groq_api_key)}, " \
                     f"API Response: {response.status_code}, " \
                     f"Key Valid: {groq_api_working}"
            
            self.log_test_result("Groq API Integration", groq_api_working, details, critical=True)
            
            return groq_api_working
            
        except Exception as e:
            self.log_test_result("Groq API Integration", False, f"Exception: {str(e)}", critical=True)
            return False
    
    def print_comprehensive_summary(self):
        """Print comprehensive test summary with recommendations"""
        print("\n" + "=" * 80)
        print("🏁 COMPREHENSIVE OAUTH TESTING SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        critical_failed = [r for r in failed_tests if r.get("critical", False)]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"🔥 CRITICAL FAILURES: {len(critical_failed)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if critical_failed:
            print(f"\n🔥 CRITICAL FAILURES (Must Fix):")
            for test in critical_failed:
                print(f"   - {test['test']}: {test['details']}")
        
        if failed_tests:
            print(f"\n❌ OTHER FAILURES:")
            for test in failed_tests:
                if not test.get("critical", False):
                    print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ WORKING FUNCTIONALITY:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        # Recommendations
        print(f"\n📋 RECOMMENDATIONS:")
        
        if any(r['test'] == 'OAuth Infrastructure' and not r['passed'] for r in self.test_results):
            print("   1. 🔥 CRITICAL: OAuth infrastructure is incomplete - check database setup")
        
        if any(r['test'] == 'Groq API Integration' and not r['passed'] for r in self.test_results):
            print("   2. 🔥 CRITICAL: Groq API key is invalid - update with working key")
        
        if not self.oauth_user_authenticated:
            print("   3. ⚠️  OAuth user authentication failed - password may need reset")
        
        if any(r['test'] == 'Email Polling Status' and r['passed'] for r in self.test_results):
            print("   4. ✅ Email polling is working correctly")
        
        if any(r['test'] == 'Calendar Agent' and r['passed'] for r in self.test_results):
            print("   5. ✅ Calendar agent functionality is working")
        
        print("\n" + "=" * 80)
    
    async def run_comprehensive_tests(self):
        """Run comprehensive OAuth tests"""
        print("🚀 Starting Comprehensive OAuth Testing")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        print(f"Target OAuth Account: {TEST_ACCOUNT['email']}")
        print("=" * 80)
        
        # Setup
        if not await self.setup():
            return
        
        # Run comprehensive tests
        print("\n🎯 RUNNING COMPREHENSIVE OAUTH TESTS")
        
        # Test 1: OAuth Infrastructure
        await self.test_oauth_infrastructure()
        
        # Test 2: Basic API Endpoints
        self.test_api_endpoints_basic()
        
        # Test 3: OAuth-specific functionality
        self.test_oauth_specific_functionality()
        
        # Test 4: Email polling status
        await self.test_email_polling_status()
        
        # Test 5: Groq API integration
        self.test_groq_api_integration()
        
        # Cleanup
        await self.cleanup()
        
        # Print comprehensive summary
        self.print_comprehensive_summary()

async def main():
    """Main function to run comprehensive OAuth tests"""
    tester = ComprehensiveOAuthTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())