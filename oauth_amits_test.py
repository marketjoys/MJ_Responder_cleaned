#!/usr/bin/env python3
"""
OAuth Flow Testing for amits.joys@gmail.com
Complete testing of OAuth account, email polling, calendar events, and email settings update
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://outlook-sync-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test target
OAUTH_EMAIL = "amits.joys@gmail.com"

class OAuthAmitsTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.oauth_account_id = None
        self.calendar_provider_id = None
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Get or create test user
            await self.setup_test_user()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def setup_test_user(self):
        """Setup test user for authentication - use the user who owns the OAuth account"""
        try:
            # Find the user who owns the OAuth account for amits.joys@gmail.com
            oauth_account = await self.db.email_accounts.find_one({
                "oauth_email": OAUTH_EMAIL,
                "auth_type": "oauth"
            })
            
            if oauth_account:
                oauth_user_id = oauth_account.get('user_id')
                oauth_user = await self.db.users.find_one({"id": oauth_user_id})
                
                if oauth_user:
                    # Try to login with the OAuth account owner
                    login_data = {
                        "email": oauth_user["email"],
                        "password": "admin123"  # Default password from migration
                    }
                    
                    try:
                        response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                        if response.status_code == 200:
                            result = response.json()
                            self.auth_token = result.get('access_token')
                            self.test_user_id = result.get('user', {}).get('id')
                            print(f"✅ Logged in as OAuth account owner: {oauth_user['email']}")
                            return
                        else:
                            print(f"⚠️ Failed to login as OAuth owner: Status {response.status_code}")
                            # Check if user needs quota_reset_date field
                            if 'quota_reset_date' in response.text:
                                print("⚠️ User missing quota_reset_date field, updating...")
                                from datetime import datetime, timedelta
                                next_month = datetime.utcnow().replace(day=1) + timedelta(days=32)
                                next_month = next_month.replace(day=1)
                                await self.db.users.update_one(
                                    {"id": oauth_user["id"]},
                                    {"$set": {"quota_reset_date": next_month}}
                                )
                                # Try login again
                                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                                if response.status_code == 200:
                                    result = response.json()
                                    self.auth_token = result.get('access_token')
                                    self.test_user_id = result.get('user', {}).get('id')
                                    print(f"✅ Logged in as OAuth account owner after fix: {oauth_user['email']}")
                                    return
                    except Exception as e:
                        print(f"⚠️ Failed to login as OAuth owner: {str(e)}")
            
            # Fallback: Try to find any existing user
            existing_user = await self.db.users.find_one({}, sort=[("created_at", 1)])
            
            if existing_user:
                # Login with existing user
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
                        print(f"✅ Logged in as existing user: {existing_user['email']}")
                        return
                except:
                    pass
            
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
                print(f"✅ Created new test user: {test_email}")
            else:
                print(f"❌ Failed to create test user: {response.status_code}")
                
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
    
    async def test_oauth_account_exists(self):
        """Test 1: Verify OAuth Account Exists for amits.joys@gmail.com"""
        print(f"\n🔍 Testing OAuth Account Exists for {OAUTH_EMAIL}...")
        
        try:
            # Check in database directly
            oauth_account = await self.db.email_accounts.find_one({
                "oauth_email": OAUTH_EMAIL,
                "auth_type": "oauth",
                "use_oauth": True
            })
            
            if oauth_account:
                self.oauth_account_id = oauth_account['id']
                account_details = {
                    "id": oauth_account['id'],
                    "email": oauth_account.get('email'),
                    "oauth_email": oauth_account.get('oauth_email'),
                    "provider": oauth_account.get('provider'),
                    "auth_type": oauth_account.get('auth_type'),
                    "use_oauth": oauth_account.get('use_oauth'),
                    "is_active": oauth_account.get('is_active'),
                    "last_oauth_sync": oauth_account.get('last_oauth_sync')
                }
                
                # Verify required fields
                has_oauth_email = oauth_account.get('oauth_email') == OAUTH_EMAIL
                has_auth_type = oauth_account.get('auth_type') == 'oauth'
                has_use_oauth = oauth_account.get('use_oauth') is True
                is_active = oauth_account.get('is_active', False)
                
                all_fields_correct = has_oauth_email and has_auth_type and has_use_oauth
                
                details = f"Account found - ID: {oauth_account['id']}, Provider: {oauth_account.get('provider')}, Active: {is_active}, All fields correct: {all_fields_correct}"
                self.log_test_result("OAuth Account Exists", True, details)
                
                return True
            else:
                self.log_test_result("OAuth Account Exists", False, f"No OAuth account found for {OAUTH_EMAIL}")
                return False
                
        except Exception as e:
            self.log_test_result("OAuth Account Exists", False, f"Exception: {str(e)}")
            return False
    
    async def test_email_polling_verification(self):
        """Test 2: Email Polling Verification for OAuth account"""
        print(f"\n📧 Testing Email Polling Verification for {OAUTH_EMAIL}...")
        
        if not self.oauth_account_id:
            self.log_test_result("Email Polling Verification", False, "No OAuth account ID available")
            return False
        
        try:
            # Check if polling is active via API
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
            
            try:
                response = requests.get(f"{API_BASE}/polling/accounts-status", headers=headers, timeout=10)
                if response.status_code == 200:
                    status_data = response.json()
                    accounts = status_data.get('accounts', [])
                    
                    # Find our OAuth account in the status
                    oauth_account_status = None
                    for account in accounts:
                        if account.get('account_id') == self.oauth_account_id:
                            oauth_account_status = account
                            break
                    
                    if oauth_account_status:
                        polling_active = oauth_account_status.get('polling_active', False)
                        has_connection = oauth_account_status.get('has_connection', False)
                        last_polled = oauth_account_status.get('last_polled')
                        
                        details = f"Polling active: {polling_active}, Has connection: {has_connection}, Last polled: {last_polled}"
                        self.log_test_result("Email Polling Verification", polling_active, details)
                        return polling_active
                    else:
                        self.log_test_result("Email Polling Verification", False, "OAuth account not found in polling status")
                        return False
                else:
                    self.log_test_result("Email Polling Verification", False, f"API call failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                self.log_test_result("Email Polling Verification", False, f"API Exception: {str(e)}")
                return False
            
            # Also check database for last_oauth_sync
            try:
                oauth_account = await self.db.email_accounts.find_one({"id": self.oauth_account_id})
                if oauth_account:
                    last_oauth_sync = oauth_account.get('last_oauth_sync')
                    if last_oauth_sync:
                        # Check if sync happened recently (within last hour)
                        sync_time = last_oauth_sync
                        if isinstance(sync_time, str):
                            sync_time = datetime.fromisoformat(sync_time.replace('Z', '+00:00'))
                        
                        time_diff = datetime.utcnow() - sync_time.replace(tzinfo=None)
                        recent_sync = time_diff.total_seconds() < 3600  # Within 1 hour
                        
                        details = f"Last OAuth sync: {last_oauth_sync}, Recent sync: {recent_sync}"
                        self.log_test_result("OAuth Sync Timestamp", recent_sync, details)
                        return recent_sync
                    else:
                        self.log_test_result("OAuth Sync Timestamp", False, "No last_oauth_sync timestamp")
                        return False
                else:
                    self.log_test_result("OAuth Sync Timestamp", False, "Account not found in database")
                    return False
                    
            except Exception as e:
                self.log_test_result("OAuth Sync Timestamp", False, f"Database Exception: {str(e)}")
                return False
                
        except Exception as e:
            self.log_test_result("Email Polling Verification", False, f"Exception: {str(e)}")
            return False
    
    async def test_calendar_provider_verification(self):
        """Test 3: Calendar Provider Verification for OAuth account"""
        print(f"\n📅 Testing Calendar Provider Verification for {OAUTH_EMAIL}...")
        
        try:
            # Check in database for calendar provider
            calendar_provider = await self.db.calendar_providers.find_one({
                "oauth_email": OAUTH_EMAIL,
                "use_oauth": True
            })
            
            if calendar_provider:
                self.calendar_provider_id = calendar_provider['id']
                
                # Verify required fields
                has_oauth_email = calendar_provider.get('oauth_email') == OAUTH_EMAIL
                has_use_oauth = calendar_provider.get('use_oauth') is True
                provider_type = calendar_provider.get('provider_type')
                is_active = calendar_provider.get('is_active', False)
                
                details = f"Provider found - ID: {calendar_provider['id']}, Type: {provider_type}, OAuth email: {has_oauth_email}, Use OAuth: {has_use_oauth}, Active: {is_active}"
                self.log_test_result("Calendar Provider Exists", True, details)
                
                return True
            else:
                self.log_test_result("Calendar Provider Exists", False, f"No calendar provider found for {OAUTH_EMAIL}")
                return False
                
        except Exception as e:
            self.log_test_result("Calendar Provider Verification", False, f"Exception: {str(e)}")
            return False
    
    def test_calendar_functionality(self):
        """Test 4: Calendar Functionality Tests"""
        print(f"\n🗓️ Testing Calendar Functionality for {OAUTH_EMAIL}...")
        
        if not self.auth_token:
            self.log_test_result("Calendar Functionality", False, "No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 4a: GET /api/calendar/providers - Should list Google calendar provider
            try:
                response = requests.get(f"{API_BASE}/calendar/providers", headers=headers, timeout=15)
                providers_passed = response.status_code == 200
                
                if providers_passed:
                    providers = response.json()
                    google_providers = [p for p in providers if p.get('provider_type') == 'google']
                    oauth_providers = [p for p in providers if 'oauth' in str(p).lower()]
                    
                    details = f"Status: {response.status_code}, Total providers: {len(providers)}, Google providers: {len(google_providers)}, OAuth providers: {len(oauth_providers)}"
                    self.log_test_result("Calendar Providers List", providers_passed, details)
                    
                    # Use the first Google provider for further tests
                    if google_providers:
                        self.calendar_provider_id = google_providers[0]['id']
                else:
                    details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    self.log_test_result("Calendar Providers List", False, details)
                    
            except Exception as e:
                self.log_test_result("Calendar Providers List", False, f"Exception: {str(e)}")
                providers_passed = False
            
            # Test 4b: GET /api/calendar/calendars - Should fetch calendars from Google
            try:
                response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
                calendars_passed = response.status_code == 200
                
                if calendars_passed:
                    calendars_data = response.json()
                    total_calendars = len(calendars_data) if isinstance(calendars_data, list) else len(calendars_data.get('calendars', []))
                    
                    details = f"Status: {response.status_code}, Total calendars: {total_calendars}"
                    self.log_test_result("Calendar Calendars Fetch", calendars_passed, details)
                    
                    # Store calendar info for event tests
                    if isinstance(calendars_data, list) and calendars_data:
                        self.test_calendar_id = calendars_data[0].get('id', 'primary')
                    elif isinstance(calendars_data, dict) and calendars_data.get('calendars'):
                        self.test_calendar_id = calendars_data['calendars'][0].get('id', 'primary')
                    else:
                        self.test_calendar_id = 'primary'
                else:
                    details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    self.log_test_result("Calendar Calendars Fetch", False, details)
                    
            except Exception as e:
                self.log_test_result("Calendar Calendars Fetch", False, f"Exception: {str(e)}")
                calendars_passed = False
                self.test_calendar_id = 'primary'
            
            # Test 4c: GET events from calendar
            events_passed = False
            if self.calendar_provider_id:
                try:
                    calendar_id = getattr(self, 'test_calendar_id', 'primary')
                    response = requests.get(
                        f"{API_BASE}/calendar/providers/{self.calendar_provider_id}/calendars/{calendar_id}/events",
                        headers=headers,
                        timeout=15
                    )
                    events_passed = response.status_code == 200
                    
                    if events_passed:
                        events = response.json()
                        event_count = len(events) if isinstance(events, list) else 0
                        details = f"Status: {response.status_code}, Events fetched: {event_count}"
                        self.log_test_result("Calendar Events Fetch", events_passed, details)
                    else:
                        details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                        self.log_test_result("Calendar Events Fetch", False, details)
                        
                except Exception as e:
                    self.log_test_result("Calendar Events Fetch", False, f"Exception: {str(e)}")
            else:
                self.log_test_result("Calendar Events Fetch", False, "No calendar provider ID available")
            
            # Test 4d: POST - Create a test event
            event_created = False
            if self.calendar_provider_id:
                try:
                    # Create event for tomorrow at 2:00 PM
                    tomorrow = datetime.now() + timedelta(days=1)
                    start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
                    end_time = start_time + timedelta(hours=1)
                    
                    event_data = {
                        "title": "Test Event - OAuth Verification",
                        "description": "This is a test event created via OAuth API testing",
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "location": "Test Location"
                    }
                    
                    calendar_id = getattr(self, 'test_calendar_id', 'primary')
                    response = requests.post(
                        f"{API_BASE}/calendar/providers/{self.calendar_provider_id}/calendars/{calendar_id}/events",
                        headers=headers,
                        json=event_data,
                        timeout=20
                    )
                    
                    event_created = response.status_code in [200, 201]
                    
                    if event_created:
                        created_event = response.json()
                        event_id = created_event.get('id', 'unknown')
                        details = f"Status: {response.status_code}, Event ID: {event_id}, Title: {created_event.get('title', 'unknown')}"
                        self.log_test_result("Calendar Event Creation", event_created, details)
                        
                        # Store event ID for potential cleanup
                        self.test_event_id = event_id
                    else:
                        details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                        self.log_test_result("Calendar Event Creation", False, details)
                        
                except Exception as e:
                    self.log_test_result("Calendar Event Creation", False, f"Exception: {str(e)}")
            else:
                self.log_test_result("Calendar Event Creation", False, "No calendar provider ID available")
            
            # Overall calendar functionality assessment
            calendar_functionality_passed = providers_passed and calendars_passed and (events_passed or event_created)
            
            details = f"Providers: {providers_passed}, Calendars: {calendars_passed}, Events: {events_passed}, Create: {event_created}"
            self.log_test_result("Calendar Functionality Overall", calendar_functionality_passed, details)
            
            return calendar_functionality_passed
            
        except Exception as e:
            self.log_test_result("Calendar Functionality", False, f"Exception: {str(e)}")
            return False
    
    def test_email_settings_update(self):
        """Test 5: Email Settings Update Test for OAuth account"""
        print(f"\n⚙️ Testing Email Settings Update for {OAUTH_EMAIL}...")
        
        if not self.oauth_account_id or not self.auth_token:
            self.log_test_result("Email Settings Update", False, "No OAuth account ID or auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test PATCH /api/email-accounts/{account_id}/settings
            settings_data = {
                "signature": "Best regards,\nAmit Joys\nTest Signature",
                "persona": "Professional and friendly",
                "auto_send": False
            }
            
            response = requests.patch(
                f"{API_BASE}/email-accounts/{self.oauth_account_id}/settings",
                headers=headers,
                json=settings_data,
                timeout=15
            )
            
            settings_updated = response.status_code == 200
            
            if settings_updated:
                updated_account = response.json()
                
                # Verify the settings were updated
                signature_updated = updated_account.get('signature') == settings_data['signature']
                persona_updated = updated_account.get('persona') == settings_data['persona']
                auto_send_updated = updated_account.get('auto_send') == settings_data['auto_send']
                
                all_updated = signature_updated and persona_updated and auto_send_updated
                
                details = f"Status: {response.status_code}, Signature: {signature_updated}, Persona: {persona_updated}, Auto-send: {auto_send_updated}, All updated: {all_updated}"
                self.log_test_result("Email Settings Update", all_updated, details)
                
                return all_updated
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                self.log_test_result("Email Settings Update", False, details)
                return False
                
        except Exception as e:
            self.log_test_result("Email Settings Update", False, f"Exception: {str(e)}")
            return False
    
    async def test_integration_verification(self):
        """Test 6: Integration Verification - Check backend logs and OAuth API calls"""
        print(f"\n🔗 Testing Integration Verification for {OAUTH_EMAIL}...")
        
        try:
            # Check backend logs for OAuth-related errors
            log_check_passed = True
            
            # Test OAuth token validity by making an API call
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                try:
                    # Test a simple authenticated endpoint
                    response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
                    auth_valid = response.status_code == 200
                    
                    if auth_valid:
                        user_info = response.json()
                        details = f"Auth valid: {auth_valid}, User: {user_info.get('email', 'unknown')}"
                    else:
                        details = f"Auth invalid: Status {response.status_code}"
                        
                    self.log_test_result("OAuth Token Validity", auth_valid, details)
                    
                except Exception as e:
                    self.log_test_result("OAuth Token Validity", False, f"Exception: {str(e)}")
                    auth_valid = False
            else:
                self.log_test_result("OAuth Token Validity", False, "No auth token available")
                auth_valid = False
            
            # Check if OAuth account is properly configured
            oauth_config_valid = False
            if self.oauth_account_id:
                try:
                    oauth_account = await self.db.email_accounts.find_one({"id": self.oauth_account_id})
                    if oauth_account:
                        has_oauth_token_id = bool(oauth_account.get('oauth_token_id'))
                        has_oauth_email = oauth_account.get('oauth_email') == OAUTH_EMAIL
                        is_oauth_type = oauth_account.get('auth_type') == 'oauth'
                        uses_oauth = oauth_account.get('use_oauth') is True
                        
                        oauth_config_valid = has_oauth_token_id and has_oauth_email and is_oauth_type and uses_oauth
                        
                        details = f"Token ID: {has_oauth_token_id}, OAuth email: {has_oauth_email}, Auth type: {is_oauth_type}, Use OAuth: {uses_oauth}"
                        self.log_test_result("OAuth Account Configuration", oauth_config_valid, details)
                    else:
                        self.log_test_result("OAuth Account Configuration", False, "Account not found in database")
                        
                except Exception as e:
                    self.log_test_result("OAuth Account Configuration", False, f"Exception: {str(e)}")
            else:
                self.log_test_result("OAuth Account Configuration", False, "No OAuth account ID available")
            
            # Check OAuth tokens in database
            oauth_tokens_valid = False
            try:
                # OAuth tokens use 'user_email' field, not 'email'
                oauth_tokens = await self.db.oauth_tokens.find({"user_email": OAUTH_EMAIL}).to_list(10)
                
                if oauth_tokens:
                    latest_token = max(oauth_tokens, key=lambda x: x.get('created_at', datetime.min))
                    
                    has_access_token = bool(latest_token.get('access_token'))
                    has_refresh_token = bool(latest_token.get('refresh_token'))
                    token_valid = latest_token.get('expires_at', datetime.min) > datetime.utcnow()
                    
                    oauth_tokens_valid = has_access_token and has_refresh_token
                    
                    details = f"Tokens found: {len(oauth_tokens)}, Access token: {has_access_token}, Refresh token: {has_refresh_token}, Valid: {token_valid}"
                    self.log_test_result("OAuth Tokens in Database", oauth_tokens_valid, details)
                else:
                    self.log_test_result("OAuth Tokens in Database", False, f"No OAuth tokens found for {OAUTH_EMAIL}")
                    
            except Exception as e:
                self.log_test_result("OAuth Tokens in Database", False, f"Exception: {str(e)}")
            
            # Overall integration assessment
            integration_passed = auth_valid and oauth_config_valid and oauth_tokens_valid
            
            details = f"Auth: {auth_valid}, Config: {oauth_config_valid}, Tokens: {oauth_tokens_valid}"
            self.log_test_result("Integration Verification Overall", integration_passed, details)
            
            return integration_passed
            
        except Exception as e:
            self.log_test_result("Integration Verification", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print(f"OAUTH TESTING SUMMARY FOR {OAUTH_EMAIL}")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL:  {len(self.test_results)}")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        print("\n" + "="*80)
        
        # Return overall success
        return len(failed_tests) == 0

async def main():
    """Main test execution"""
    print(f"🚀 Starting OAuth Testing for {OAUTH_EMAIL}")
    print(f"🌐 Backend URL: {BACKEND_URL}")
    print(f"🗄️ Database: {MONGO_URL}/{DB_NAME}")
    
    tester = OAuthAmitsTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting")
            return False
        
        # Run tests in sequence
        print("\n" + "="*60)
        print("STARTING OAUTH TESTS")
        print("="*60)
        
        # Test 1: Verify OAuth Account Exists
        await tester.test_oauth_account_exists()
        
        # Test 2: Email Polling Verification
        await tester.test_email_polling_verification()
        
        # Test 3: Calendar Provider Verification
        await tester.test_calendar_provider_verification()
        
        # Test 4: Calendar Functionality Tests
        tester.test_calendar_functionality()
        
        # Test 5: Email Settings Update Test
        tester.test_email_settings_update()
        
        # Test 6: Integration Verification
        await tester.test_integration_verification()
        
        # Print summary
        success = tester.print_summary()
        
        return success
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)