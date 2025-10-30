#!/usr/bin/env python3
"""
OAuth Flow Testing for Email Account Auto-Creation Changes
Focus: Verify email accounts are NOT auto-created but calendar providers ARE still created
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://setup-redis-sync.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthFlowTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.test_user_email = "amits.joys@gmail.com"  # Existing OAuth user
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Get existing OAuth user
            await self.setup_oauth_user()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def setup_oauth_user(self):
        """Setup OAuth user for testing"""
        try:
            # Find existing OAuth user
            existing_user = await self.db.users.find_one({"email": self.test_user_email})
            
            if existing_user:
                # Try to login with existing user
                login_data = {
                    "email": self.test_user_email,
                    "password": "admin123"  # Default password
                }
                
                try:
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        self.auth_token = result.get('access_token')
                        self.test_user_id = result.get('user', {}).get('id')
                        print(f"✅ Logged in as OAuth user: {self.test_user_email}")
                        return
                except Exception as e:
                    print(f"⚠️ Login failed: {str(e)}")
            
            print(f"❌ OAuth user {self.test_user_email} not found or login failed")
                
        except Exception as e:
            print(f"❌ Error setting up OAuth user: {str(e)}")
    
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
    
    async def test_oauth_token_storage(self):
        """Test 1: OAuth Token Storage - Verify tokens are stored correctly"""
        print("\n🔐 Testing OAuth Token Storage...")
        
        try:
            # Check oauth_tokens collection for existing user
            oauth_tokens = await self.db.oauth_tokens.find({
                "user_id": self.test_user_id
            }).to_list(100)
            
            # Verify token structure
            tokens_found = len(oauth_tokens) > 0
            valid_structure = False
            
            if tokens_found:
                token = oauth_tokens[0]
                required_fields = ['access_token', 'refresh_token', 'expires_at', 'scopes', 'provider']
                valid_structure = all(field in token for field in required_fields)
                
                # Check scopes include both email and calendar
                scopes = token.get('scopes', [])
                has_email_scope = any('mail' in scope or 'gmail' in scope for scope in scopes)
                has_calendar_scope = any('calendar' in scope for scope in scopes)
                
                details = f"Tokens found: {len(oauth_tokens)}, Valid structure: {valid_structure}, " \
                         f"Email scope: {has_email_scope}, Calendar scope: {has_calendar_scope}, " \
                         f"Provider: {token.get('provider')}, Expires: {token.get('expires_at')}"
                
                test_passed = tokens_found and valid_structure and has_email_scope and has_calendar_scope
            else:
                details = "No OAuth tokens found for user"
                test_passed = False
            
            self.log_test_result("OAuth Token Storage", test_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Token Storage", False, f"Exception: {str(e)}")
    
    async def test_email_account_not_auto_created(self):
        """Test 2: Email Account Auto-Creation Removal - Verify NOT auto-created"""
        print("\n📧 Testing Email Account Auto-Creation Removal...")
        
        try:
            # Check if email accounts exist for OAuth user
            email_accounts = await self.db.email_accounts.find({
                "user_id": self.test_user_id,
                "auth_type": "oauth"
            }).to_list(100)
            
            # For this test, we expect NO auto-created email accounts
            # (They should be manually created via /api/email-accounts/oauth)
            auto_created_accounts = [acc for acc in email_accounts 
                                   if acc.get('oauth_email') == self.test_user_email]
            
            # Check if OAuth callback returns success without email_account_created field
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
            
            try:
                # Test OAuth status endpoint
                response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
                oauth_status_working = response.status_code == 200
                
                if oauth_status_working:
                    status_data = response.json()
                    # Should not have email_account_created field in response
                    no_auto_create_field = 'email_account_created' not in status_data
                else:
                    no_auto_create_field = False
            except:
                oauth_status_working = False
                no_auto_create_field = False
            
            # The test passes if:
            # 1. OAuth tokens exist (from previous test)
            # 2. No auto-created email accounts exist
            # 3. OAuth status works without email_account_created field
            
            test_passed = (len(auto_created_accounts) == 0 and 
                          oauth_status_working and no_auto_create_field)
            
            details = f"Auto-created email accounts: {len(auto_created_accounts)}, " \
                     f"OAuth status working: {oauth_status_working}, " \
                     f"No auto-create field: {no_auto_create_field}"
            
            self.log_test_result("Email Account Auto-Creation Removal", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Account Auto-Creation Removal", False, f"Exception: {str(e)}")
    
    async def test_calendar_provider_auto_creation(self):
        """Test 3: Calendar Provider Auto-Creation - Verify ARE still created"""
        print("\n📅 Testing Calendar Provider Auto-Creation...")
        
        try:
            # Check calendar_providers collection for OAuth user
            calendar_providers = await self.db.calendar_providers.find({
                "user_id": self.test_user_id
            }).to_list(100)
            
            # Look for OAuth calendar providers
            oauth_providers = [cp for cp in calendar_providers 
                             if cp.get('use_oauth') == True and 
                                cp.get('oauth_email') == self.test_user_email]
            
            providers_found = len(oauth_providers) > 0
            
            if providers_found:
                provider = oauth_providers[0]
                
                # Verify provider structure
                required_fields = ['provider_type', 'oauth_email', 'use_oauth', 'is_active']
                valid_structure = all(field in provider for field in required_fields)
                
                # Verify provider type is correct
                correct_provider_type = provider.get('provider_type') in ['google', 'microsoft']
                
                # Verify oauth_email matches
                correct_oauth_email = provider.get('oauth_email') == self.test_user_email
                
                details = f"OAuth providers found: {len(oauth_providers)}, " \
                         f"Valid structure: {valid_structure}, " \
                         f"Correct provider type: {correct_provider_type}, " \
                         f"Correct OAuth email: {correct_oauth_email}, " \
                         f"Provider type: {provider.get('provider_type')}"
                
                test_passed = (providers_found and valid_structure and 
                              correct_provider_type and correct_oauth_email)
            else:
                details = "No OAuth calendar providers found"
                test_passed = False
            
            self.log_test_result("Calendar Provider Auto-Creation", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Calendar Provider Auto-Creation", False, f"Exception: {str(e)}")
    
    async def test_calendar_functionality(self):
        """Test 4: Calendar Agent Functionality - Verify calendar operations work"""
        print("\n🤖 Testing Calendar Agent Functionality...")
        
        if not self.auth_token:
            self.log_test_result("Calendar Agent Functionality", False, "No auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 4a: Get calendars endpoint
            try:
                response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
                calendars_accessible = response.status_code == 200
                
                if calendars_accessible:
                    calendars_data = response.json()
                    calendars_count = len(calendars_data) if isinstance(calendars_data, list) else 0
                else:
                    calendars_count = 0
            except Exception as e:
                calendars_accessible = False
                calendars_count = 0
            
            # Test 4b: Meeting detection endpoint
            try:
                meeting_request = {
                    "email_content": "Hi, can we schedule a meeting for tomorrow at 2 PM to discuss the project?",
                    "sender": "test@example.com",
                    "user_timezone": "UTC"
                }
                
                response = requests.post(f"{API_BASE}/calendar/detect-meeting", 
                                       json=meeting_request, headers=headers, timeout=15)
                meeting_detection_working = response.status_code == 200
                
                if meeting_detection_working:
                    detection_result = response.json()
                    has_confidence = 'confidence' in detection_result
                    has_meeting_detected = detection_result.get('is_meeting', False)
                else:
                    has_confidence = False
                    has_meeting_detected = False
            except Exception as e:
                meeting_detection_working = False
                has_confidence = False
                has_meeting_detected = False
            
            # Test 4c: Calendar event creation (if we have providers)
            event_creation_working = False
            if calendars_accessible and calendars_count > 0:
                try:
                    # Get calendar providers first
                    providers_response = requests.get(f"{API_BASE}/calendar/providers", headers=headers, timeout=10)
                    
                    if providers_response.status_code == 200:
                        providers = providers_response.json()
                        oauth_providers = [p for p in providers if p.get('provider_type') == 'google']
                        
                        if oauth_providers:
                            provider_id = oauth_providers[0]['id']
                            
                            # Try to create a test event
                            event_data = {
                                "title": "OAuth Test Event",
                                "description": "Test event for OAuth calendar functionality",
                                "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                                "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                                "attendees": ["test@example.com"]
                            }
                            
                            # We need a calendar ID - try to get from calendars endpoint
                            if calendars_count > 0:
                                calendar_id = "primary"  # Default Google calendar
                                
                                response = requests.post(
                                    f"{API_BASE}/calendar/providers/{provider_id}/calendars/{calendar_id}/events",
                                    json=event_data, headers=headers, timeout=15
                                )
                                event_creation_working = response.status_code in [200, 201]
                except Exception as e:
                    event_creation_working = False
            
            # Overall assessment
            core_functionality = calendars_accessible and meeting_detection_working
            advanced_functionality = event_creation_working or calendars_count > 0
            
            test_passed = core_functionality
            
            details = f"Calendars accessible: {calendars_accessible} ({calendars_count} calendars), " \
                     f"Meeting detection: {meeting_detection_working}, " \
                     f"Event creation: {event_creation_working}, " \
                     f"Has confidence: {has_confidence}"
            
            self.log_test_result("Calendar Agent Functionality", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Calendar Agent Functionality", False, f"Exception: {str(e)}")
    
    async def test_multiple_oauth_accounts(self):
        """Test 5: Multiple OAuth Accounts - Verify support for multiple accounts"""
        print("\n👥 Testing Multiple OAuth Accounts Support...")
        
        try:
            # Check for multiple OAuth tokens
            oauth_tokens = await self.db.oauth_tokens.find({
                "user_id": self.test_user_id
            }).to_list(100)
            
            # Check for multiple calendar providers
            calendar_providers = await self.db.calendar_providers.find({
                "user_id": self.test_user_id,
                "use_oauth": True
            }).to_list(100)
            
            # Check OAuth status endpoint for multiple account support
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
            
            try:
                response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    
                    # Check for multiple account support fields
                    has_multiple_support = (
                        'authorized_accounts' in status_data or
                        'total_accounts' in status_data or
                        isinstance(status_data.get('accounts'), list)
                    )
                    
                    # Check if structure supports multiple accounts
                    accounts_list = status_data.get('authorized_accounts', status_data.get('accounts', []))
                    if isinstance(accounts_list, list):
                        multiple_accounts_structure = True
                        accounts_count = len(accounts_list)
                    else:
                        multiple_accounts_structure = False
                        accounts_count = 0
                else:
                    has_multiple_support = False
                    multiple_accounts_structure = False
                    accounts_count = 0
            except:
                has_multiple_support = False
                multiple_accounts_structure = False
                accounts_count = 0
            
            # Test passes if:
            # 1. OAuth infrastructure supports multiple accounts (structure)
            # 2. Calendar providers can have oauth_email field for differentiation
            # 3. System can handle multiple OAuth tokens per user
            
            oauth_tokens_count = len(oauth_tokens)
            calendar_providers_count = len(calendar_providers)
            
            # Check if calendar providers have oauth_email field
            providers_with_oauth_email = [cp for cp in calendar_providers 
                                        if 'oauth_email' in cp and cp.get('oauth_email')]
            
            oauth_email_support = len(providers_with_oauth_email) > 0
            
            test_passed = (has_multiple_support and multiple_accounts_structure and oauth_email_support)
            
            details = f"OAuth tokens: {oauth_tokens_count}, " \
                     f"Calendar providers: {calendar_providers_count}, " \
                     f"Multiple account structure: {multiple_accounts_structure}, " \
                     f"OAuth email support: {oauth_email_support}, " \
                     f"Accounts in status: {accounts_count}"
            
            self.log_test_result("Multiple OAuth Accounts Support", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Multiple OAuth Accounts Support", False, f"Exception: {str(e)}")
    
    async def test_calendar_event_creation_workflow(self):
        """Test 6: Calendar Event Creation Workflow - End-to-end testing"""
        print("\n🔄 Testing Calendar Event Creation Workflow...")
        
        if not self.auth_token:
            self.log_test_result("Calendar Event Creation Workflow", False, "No auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Check if we have calendar events in database
            calendar_events = await self.db.calendar_events.find({
                "user_id": self.test_user_id
            }).to_list(100)
            
            events_in_db = len(calendar_events) > 0
            
            # Check meeting intents
            meeting_intents = await self.db.meeting_intents.find({
                "user_id": self.test_user_id
            }).to_list(100)
            
            meeting_intents_exist = len(meeting_intents) > 0
            
            # Test _create_calendar_event function via meeting detection
            try:
                meeting_request = {
                    "email_content": "Let's schedule a team meeting for Friday at 3 PM to review the quarterly results and plan next steps.",
                    "sender": "manager@company.com",
                    "user_timezone": "UTC"
                }
                
                response = requests.post(f"{API_BASE}/calendar/detect-meeting", 
                                       json=meeting_request, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    detection_result = response.json()
                    meeting_detected = detection_result.get('is_meeting', False)
                    confidence = detection_result.get('confidence', 0)
                    
                    # High confidence meeting should trigger calendar event creation
                    workflow_triggered = meeting_detected and confidence >= 0.6
                else:
                    workflow_triggered = False
                    confidence = 0
            except:
                workflow_triggered = False
                confidence = 0
            
            # Check if calendar agent can create events
            try:
                # Test calendar agent endpoint directly
                response = requests.get(f"{API_BASE}/calendar/meeting-intents", headers=headers, timeout=10)
                agent_accessible = response.status_code == 200
                
                if agent_accessible:
                    intents_data = response.json()
                    intents_count = len(intents_data) if isinstance(intents_data, list) else 0
                else:
                    intents_count = 0
            except:
                agent_accessible = False
                intents_count = 0
            
            # Overall workflow assessment
            workflow_components = [
                events_in_db,           # Events stored in DB
                meeting_intents_exist,  # Meeting intents created
                workflow_triggered,     # Detection workflow works
                agent_accessible        # Agent endpoints accessible
            ]
            
            components_working = sum(workflow_components)
            test_passed = components_working >= 3  # At least 3 out of 4 components working
            
            details = f"Events in DB: {len(calendar_events)}, " \
                     f"Meeting intents: {len(meeting_intents)}, " \
                     f"Workflow triggered: {workflow_triggered} (confidence: {confidence:.2f}), " \
                     f"Agent accessible: {agent_accessible}, " \
                     f"Components working: {components_working}/4"
            
            self.log_test_result("Calendar Event Creation Workflow", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Calendar Event Creation Workflow", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🧪 OAUTH FLOW TEST SUMMARY")
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
    print("🚀 Starting OAuth Flow Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = OAuthFlowTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests
        await tester.test_oauth_token_storage()
        await tester.test_email_account_not_auto_created()
        await tester.test_calendar_provider_auto_creation()
        await tester.test_calendar_functionality()
        await tester.test_multiple_oauth_accounts()
        await tester.test_calendar_event_creation_workflow()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())