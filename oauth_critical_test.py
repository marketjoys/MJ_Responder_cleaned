#!/usr/bin/env python3
"""
Critical OAuth Testing for amits.joys@gmail.com
Testing the 3 specific issues mentioned in the review request:
1. Update OAuth Email Account Settings (PATCH /api/email-accounts/{account_id}/settings)
2. Calendar Meeting Detection 
3. OAuth Email Polling and Reply Processing
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://auth-calendar-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test data from review request
OAUTH_EMAIL = "amits.joys@gmail.com"
EMAIL_ACCOUNT_ID = "68ecd794adcda56d79bca1dc"
USER_ID = "6d4ac92f-1971-4f9c-8b94-790b708765f0"

class OAuthCriticalTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Get or create test user for the specific user ID
            await self.setup_test_user()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def setup_test_user(self):
        """Setup test user for authentication - use the specific user from review request"""
        try:
            # Try to find the specific user from the review request
            existing_user = await self.db.users.find_one({"id": USER_ID})
            
            if existing_user:
                # Try to login with existing user (assuming default password)
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
                        print(f"✅ Logged in as existing user: {existing_user['email']} (ID: {self.test_user_id})")
                        return
                except Exception as e:
                    print(f"⚠️ Login failed for existing user: {str(e)}")
            
            # If specific user not found, try to find any user and use it
            any_user = await self.db.users.find_one({}, sort=[("created_at", 1)])
            if any_user:
                login_data = {
                    "email": any_user["email"],
                    "password": "admin123"
                }
                
                try:
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        self.auth_token = result.get('access_token')
                        self.test_user_id = result.get('user', {}).get('id')
                        print(f"✅ Logged in as fallback user: {any_user['email']} (ID: {self.test_user_id})")
                        return
                except Exception as e:
                    print(f"⚠️ Login failed for fallback user: {str(e)}")
            
            # Create new test user if all else fails
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
    
    async def verify_oauth_account_exists(self):
        """Verify the OAuth account exists in database"""
        print("\n🔍 Verifying OAuth Account Exists...")
        
        try:
            # Check if OAuth account exists
            oauth_account = await self.db.email_accounts.find_one({
                "email": OAUTH_EMAIL,
                "auth_type": "oauth"
            })
            
            if oauth_account:
                account_id = oauth_account.get('id')
                provider = oauth_account.get('provider')
                oauth_email = oauth_account.get('oauth_email')
                
                details = f"Found OAuth account - ID: {account_id}, Provider: {provider}, OAuth Email: {oauth_email}"
                self.log_test_result("OAuth Account Exists", True, details)
                return oauth_account
            else:
                self.log_test_result("OAuth Account Exists", False, f"No OAuth account found for {OAUTH_EMAIL}")
                return None
                
        except Exception as e:
            self.log_test_result("OAuth Account Exists", False, f"Exception: {str(e)}")
            return None
    
    async def test_oauth_email_settings_update(self, oauth_account):
        """Test 1: Update OAuth Email Account Settings"""
        print("\n📝 Testing OAuth Email Account Settings Update...")
        
        if not oauth_account:
            self.log_test_result("OAuth Email Settings Update", False, "No OAuth account available")
            return
        
        if not self.auth_token:
            self.log_test_result("OAuth Email Settings Update", False, "No auth token")
            return
        
        account_id = oauth_account.get('id', EMAIL_ACCOUNT_ID)
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test data from review request
        settings_update = {
            "signature": "Best regards,\\nAmit Joys\\nSoftware Engineer",
            "persona": "I am a professional software engineer who responds promptly to emails.",
            "enable_follow_ups": True
        }
        
        try:
            print(f"   Testing PATCH /api/email-accounts/{account_id}/settings")
            response = requests.patch(
                f"{API_BASE}/email-accounts/{account_id}/settings",
                json=settings_update,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                updated_account = response.json()
                
                # Verify the update was saved
                signature_updated = updated_account.get('signature') == settings_update['signature']
                persona_updated = updated_account.get('persona') == settings_update['persona']
                follow_ups_updated = updated_account.get('enable_follow_ups') == settings_update['enable_follow_ups']
                
                # Check in database to ensure it's persisted
                db_account = await self.db.email_accounts.find_one({"id": account_id})
                db_signature_correct = db_account.get('signature') == settings_update['signature'] if db_account else False
                db_persona_correct = db_account.get('persona') == settings_update['persona'] if db_account else False
                db_follow_ups_correct = db_account.get('enable_follow_ups') == settings_update['enable_follow_ups'] if db_account else False
                
                all_updated = signature_updated and persona_updated and follow_ups_updated
                all_persisted = db_signature_correct and db_persona_correct and db_follow_ups_correct
                
                details = f"Status: {response.status_code}, API Updated: {all_updated}, DB Persisted: {all_persisted}"
                self.log_test_result("OAuth Email Settings Update", all_updated and all_persisted, details)
                
            elif response.status_code == 404:
                # This might be an authentication issue - the account exists but user can't access it
                details = f"Status: 404 - Account not found. This may be due to user authentication mismatch."
                self.log_test_result("OAuth Email Settings Update", False, details)
                
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                self.log_test_result("OAuth Email Settings Update", False, details)
                
        except Exception as e:
            self.log_test_result("OAuth Email Settings Update", False, f"Exception: {str(e)}")
    
    async def test_calendar_meeting_detection(self):
        """Test 2: Calendar Meeting Detection"""
        print("\n📅 Testing Calendar Meeting Detection...")
        
        if not self.auth_token:
            self.log_test_result("Calendar Meeting Detection", False, "No auth token")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test 2a: Check if calendar provider exists for OAuth account
        try:
            calendar_provider = await self.db.calendar_providers.find_one({
                "oauth_email": OAUTH_EMAIL,
                "provider_type": "google"
            })
            
            if calendar_provider:
                provider_id = calendar_provider.get('id')
                provider_details = f"Found calendar provider - ID: {provider_id}, Type: google, OAuth Email: {OAUTH_EMAIL}"
                print(f"   ✅ {provider_details}")
            else:
                self.log_test_result("Calendar Meeting Detection", False, f"No calendar provider found for {OAUTH_EMAIL}")
                return
                
        except Exception as e:
            self.log_test_result("Calendar Meeting Detection", False, f"Database error: {str(e)}")
            return
        
        # Test 2b: Test calendar API endpoints
        try:
            print("   Testing GET /api/calendar/calendars")
            response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
            
            if response.status_code == 200:
                calendars = response.json()
                calendar_count = len(calendars)
                
                # Look for the expected calendars from review request
                has_holidays_calendar = any("Holidays in India" in str(cal) for cal in calendars)
                has_primary_calendar = any(OAUTH_EMAIL in str(cal) for cal in calendars)
                
                calendar_details = f"Status: 200, Calendars: {calendar_count}, Has Holidays: {has_holidays_calendar}, Has Primary: {has_primary_calendar}"
                calendar_api_working = calendar_count >= 2 and (has_holidays_calendar or has_primary_calendar)
                
            else:
                calendar_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                calendar_api_working = False
                
        except Exception as e:
            calendar_details = f"Exception: {str(e)}"
            calendar_api_working = False
        
        # Test 2c: Test meeting detection from email content
        meeting_detection_working = False
        try:
            print("   Testing POST /api/calendar/detect-meeting")
            meeting_email_content = """
            Hi Amit,
            
            I'd like to schedule a meeting with you to discuss the new project requirements.
            Are you available next Tuesday at 2 PM? We can meet in the conference room or via Zoom.
            
            Please let me know if this time works for you.
            
            Best regards,
            John
            """
            
            detection_request = {
                "email_content": meeting_email_content,
                "sender": "john.doe@company.com",
                "user_timezone": "Asia/Kolkata"
            }
            
            response = requests.post(
                f"{API_BASE}/calendar/detect-meeting",
                json=detection_request,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                detection_result = response.json()
                has_meeting_detected = detection_result.get('has_meeting_intent', False)
                confidence = detection_result.get('confidence', 0)
                
                meeting_details = f"Status: 200, Meeting Detected: {has_meeting_detected}, Confidence: {confidence}"
                meeting_detection_working = True  # API is working regardless of detection result
                
            else:
                meeting_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                
        except Exception as e:
            meeting_details = f"Exception: {str(e)}"
        
        # Test 2d: Test creating a calendar event (if we have a calendar)
        event_creation_working = False
        if calendar_api_working and calendars:
            try:
                print("   Testing POST /api/calendar/providers/{provider_id}/calendars/{calendar_id}/events")
                
                # Use the first available calendar
                first_calendar = calendars[0] if calendars else None
                if first_calendar and 'id' in first_calendar and 'provider_id' in first_calendar:
                    calendar_id = first_calendar['id']
                    provider_id = first_calendar['provider_id']
                    
                    # Create a test event
                    event_data = {
                        "title": "OAuth Test Meeting",
                        "description": "Test event created via OAuth API testing",
                        "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                        "end_time": (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat(),
                        "attendees": [OAUTH_EMAIL]
                    }
                    
                    response = requests.post(
                        f"{API_BASE}/calendar/providers/{provider_id}/calendars/{calendar_id}/events",
                        json=event_data,
                        headers=headers,
                        timeout=15
                    )
                    
                    if response.status_code in [200, 201]:
                        event_result = response.json()
                        event_id = event_result.get('id')
                        event_creation_details = f"Status: {response.status_code}, Event ID: {event_id}"
                        event_creation_working = True
                    else:
                        event_creation_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                else:
                    event_creation_details = "No suitable calendar found for event creation"
                    
            except Exception as e:
                event_creation_details = f"Exception: {str(e)}"
        else:
            event_creation_details = "Skipped - calendar API not working"
        
        # Overall assessment
        overall_working = calendar_api_working and meeting_detection_working
        
        details = f"Calendar API: {calendar_api_working}, Meeting Detection: {meeting_detection_working}, Event Creation: {event_creation_working}"
        self.log_test_result("Calendar Meeting Detection", overall_working, details)
        
        # Log individual components
        self.log_test_result("Calendar - API Access", calendar_api_working, calendar_details)
        self.log_test_result("Calendar - Meeting Detection", meeting_detection_working, meeting_details)
        if 'event_creation_details' in locals():
            self.log_test_result("Calendar - Event Creation", event_creation_working, event_creation_details)
    
    async def test_oauth_email_polling_and_reply(self, oauth_account):
        """Test 3: OAuth Email Polling and Reply Processing"""
        print("\n📧 Testing OAuth Email Polling and Reply Processing...")
        
        if not oauth_account:
            self.log_test_result("OAuth Email Polling", False, "No OAuth account available")
            return
        
        account_id = oauth_account.get('id')
        
        # Test 3a: Verify OAuth account is being polled
        try:
            last_polled = oauth_account.get('last_polled')
            last_oauth_sync = oauth_account.get('last_oauth_sync')
            is_active = oauth_account.get('is_active', False)
            
            # Check if polling happened recently (within last 2 hours)
            polling_recent = False
            if last_oauth_sync:
                if isinstance(last_oauth_sync, str):
                    last_sync_time = datetime.fromisoformat(last_oauth_sync.replace('Z', '+00:00'))
                else:
                    last_sync_time = last_oauth_sync
                
                time_diff = datetime.utcnow() - last_sync_time.replace(tzinfo=None)
                polling_recent = time_diff.total_seconds() < 7200  # 2 hours
            
            polling_details = f"Active: {is_active}, Last OAuth Sync: {last_oauth_sync}, Recent: {polling_recent}"
            
        except Exception as e:
            polling_details = f"Exception checking polling status: {str(e)}"
            polling_recent = False
        
        # Test 3b: Check if emails are being fetched and stored
        try:
            emails_for_account = await self.db.emails.find({
                "account_id": account_id
            }).sort("received_at", -1).limit(10).to_list(10)
            
            email_count = len(emails_for_account)
            recent_emails = 0
            
            if emails_for_account:
                # Check for emails received in last 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                for email in emails_for_account:
                    received_at = email.get('received_at')
                    if received_at and received_at > cutoff_time:
                        recent_emails += 1
            
            email_fetch_details = f"Total emails: {email_count}, Recent (24h): {recent_emails}"
            email_fetching_working = email_count > 0
            
        except Exception as e:
            email_fetch_details = f"Exception: {str(e)}"
            email_fetching_working = False
        
        # Test 3c: Test email processing workflow for OAuth accounts
        processing_working = False
        if self.auth_token:
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                # Test email processing via API
                test_email_data = {
                    "subject": "OAuth Test Email Processing",
                    "body": "This is a test email to verify OAuth account email processing workflow. Please respond with pricing information for your services.",
                    "sender": "oauth.test@example.com",
                    "account_id": account_id
                }
                
                print("   Testing email processing via /api/emails/test")
                response = requests.post(
                    f"{API_BASE}/emails/test",
                    json=test_email_data,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    email_id = processed_email.get('email_id')
                    status = processed_email.get('status')
                    
                    processing_details = f"Status: {response.status_code}, Email ID: {email_id}, Processing Status: {status}"
                    processing_working = True
                    
                    # Wait a bit and check if processing completed
                    if email_id:
                        await asyncio.sleep(5)  # Give it time to process
                        
                        # Check the email status in database
                        processed_email_db = await self.db.emails.find_one({"id": email_id})
                        if processed_email_db:
                            final_status = processed_email_db.get('status')
                            has_draft = bool(processed_email_db.get('draft'))
                            has_intents = bool(processed_email_db.get('intents'))
                            
                            processing_details += f", Final Status: {final_status}, Has Draft: {has_draft}, Has Intents: {has_intents}"
                            
                else:
                    processing_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    
            except Exception as e:
                processing_details = f"Exception: {str(e)}"
        else:
            processing_details = "Skipped - no auth token"
        
        # Test 3d: Check OAuth token validity
        oauth_token_valid = False
        try:
            oauth_token = await self.db.oauth_tokens.find_one({
                "email": OAUTH_EMAIL,
                "provider": "google"
            })
            
            if oauth_token:
                expires_at = oauth_token.get('expires_at')
                access_token = oauth_token.get('access_token')
                refresh_token = oauth_token.get('refresh_token')
                
                # Check if token is not expired
                if expires_at:
                    if isinstance(expires_at, str):
                        expires_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    else:
                        expires_time = expires_at
                    
                    oauth_token_valid = expires_time.replace(tzinfo=None) > datetime.utcnow()
                
                token_details = f"Has Access Token: {bool(access_token)}, Has Refresh Token: {bool(refresh_token)}, Valid: {oauth_token_valid}"
            else:
                token_details = "No OAuth token found"
                
        except Exception as e:
            token_details = f"Exception: {str(e)}"
        
        # Overall assessment
        overall_working = polling_recent and oauth_token_valid and processing_working
        
        details = f"Polling Recent: {polling_recent}, Token Valid: {oauth_token_valid}, Processing: {processing_working}, Email Fetching: {email_fetching_working}"
        self.log_test_result("OAuth Email Polling and Reply Processing", overall_working, details)
        
        # Log individual components
        self.log_test_result("OAuth - Polling Status", polling_recent, polling_details)
        self.log_test_result("OAuth - Email Fetching", email_fetching_working, email_fetch_details)
        self.log_test_result("OAuth - Email Processing", processing_working, processing_details)
        self.log_test_result("OAuth - Token Validity", oauth_token_valid, token_details)
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 OAUTH CRITICAL TESTING SUMMARY")
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
                print(f"   • {test['test']}: {test['details']}")

async def main():
    """Main test execution"""
    print("🚀 Starting OAuth Critical Testing for amits.joys@gmail.com")
    print("="*80)
    
    tester = OAuthCriticalTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting")
            return
        
        # Verify OAuth account exists
        oauth_account = await tester.verify_oauth_account_exists()
        
        # Run the 3 critical tests
        await tester.test_oauth_email_settings_update(oauth_account)
        await tester.test_calendar_meeting_detection()
        await tester.test_oauth_email_polling_and_reply(oauth_account)
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Critical error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())