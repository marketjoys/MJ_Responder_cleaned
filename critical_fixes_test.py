#!/usr/bin/env python3
"""
Critical Fixes Testing for OAuth Email Sending, Meeting Detection, and Threading
Testing the three specific fixes requested in the review:
1. OAuth Email Sending (with proper threading)
2. Meeting Detection and Calendar Event Creation  
3. Email Threading with proper References and threadId
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://component-check-2.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test data from review request
TEST_EMAIL_ID = "0829a464-4f93-4a6b-beca-c2f420f775b1"
TEST_MEETING_INTENT_ID = "3375f79a-9258-40db-87e1-61e87e96578c"
TEST_USER_EMAIL = "amits.joys@gmail.com"
TEST_OAUTH_EMAIL = "sharinara68@gmail.com"

class CriticalFixesTester:
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
            
            # Authenticate as the test user
            await self.authenticate_test_user()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def authenticate_test_user(self):
        """Authenticate as the test user amits.joys@gmail.com"""
        try:
            # Try to find the user in database
            user = await self.db.users.find_one({"email": TEST_USER_EMAIL})
            if not user:
                print(f"❌ Test user {TEST_USER_EMAIL} not found in database")
                return False
            
            # Try to login (assuming password is admin123 or similar)
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": "admin123"
            }
            
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                self.auth_token = result.get('access_token')
                self.test_user_id = result.get('user', {}).get('id')
                print(f"✅ Authenticated as user: {TEST_USER_EMAIL}")
                return True
            else:
                print(f"❌ Authentication failed for {TEST_USER_EMAIL}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error authenticating test user: {str(e)}")
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
    
    async def test_1_oauth_email_auto_send(self):
        """TEST 1: Trigger auto-send for stuck email with OAuth and proper threading"""
        print("\n🔍 TEST 1: OAuth Email Auto-Send with Threading...")
        
        try:
            # Check if the specific email exists
            email = await self.db.emails.find_one({"id": TEST_EMAIL_ID})
            if not email:
                self.log_test_result("OAuth Email Auto-Send", False, f"Email {TEST_EMAIL_ID} not found in database")
                return
            
            print(f"   Found email: {email.get('subject', 'No subject')} from {email.get('sender', 'Unknown')}")
            print(f"   Current status: {email.get('status', 'Unknown')}")
            
            # Verify email is ready_to_send
            if email.get('status') != 'ready_to_send':
                self.log_test_result("OAuth Email Auto-Send", False, f"Email status is {email.get('status')}, expected ready_to_send")
                return
            
            # Get the email account
            account = await self.db.email_accounts.find_one({"id": email.get('account_id')})
            if not account:
                self.log_test_result("OAuth Email Auto-Send", False, "Email account not found")
                return
            
            print(f"   Account: {account.get('email')} (OAuth: {account.get('auth_type') == 'oauth'})")
            
            # Verify it's an OAuth account
            if account.get('auth_type') != 'oauth':
                self.log_test_result("OAuth Email Auto-Send", False, "Account is not OAuth type")
                return
            
            # Check OAuth token exists
            oauth_token = await self.db.oauth_tokens.find_one({
                "user_id": account.get('user_id'),
                "email": account.get('oauth_email')
            })
            
            if not oauth_token:
                self.log_test_result("OAuth Email Auto-Send", False, "OAuth token not found")
                return
            
            print(f"   OAuth token found for: {oauth_token.get('email')}")
            
            # Trigger auto-send via API
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
            
            try:
                # Use the send email endpoint
                send_data = {
                    "email_id": TEST_EMAIL_ID,
                    "manual_override": False
                }
                
                response = requests.post(f"{API_BASE}/emails/{TEST_EMAIL_ID}/send", 
                                       json=send_data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    print("   ✅ Email send request successful")
                    
                    # Wait a moment for processing
                    await asyncio.sleep(3)
                    
                    # Check if email status changed to sent
                    updated_email = await self.db.emails.find_one({"id": TEST_EMAIL_ID})
                    if updated_email and updated_email.get('status') == 'sent':
                        # Check if sent_at timestamp was set
                        sent_at = updated_email.get('sent_at')
                        threading_check = self.check_threading_headers(updated_email)
                        
                        details = f"Status changed to 'sent', sent_at: {sent_at}, Threading: {threading_check}"
                        self.log_test_result("OAuth Email Auto-Send", True, details)
                    else:
                        current_status = updated_email.get('status') if updated_email else 'not found'
                        self.log_test_result("OAuth Email Auto-Send", False, f"Status not changed to sent: {current_status}")
                
                else:
                    error_msg = response.text[:200] if response.text else "No error message"
                    self.log_test_result("OAuth Email Auto-Send", False, f"Send failed: {response.status_code} - {error_msg}")
            
            except Exception as e:
                self.log_test_result("OAuth Email Auto-Send", False, f"Send request failed: {str(e)}")
        
        except Exception as e:
            self.log_test_result("OAuth Email Auto-Send", False, f"Exception: {str(e)}")
    
    def check_threading_headers(self, email_doc):
        """Check if email has proper threading headers"""
        try:
            # Check for threading fields in the email document
            has_in_reply_to = bool(email_doc.get('in_reply_to'))
            has_references = bool(email_doc.get('references'))
            has_thread_id = bool(email_doc.get('thread_id'))
            
            return f"In-Reply-To: {has_in_reply_to}, References: {has_references}, ThreadId: {has_thread_id}"
        except:
            return "Unable to check threading headers"
    
    async def test_2_meeting_detection_and_calendar_creation(self):
        """TEST 2: Verify meeting intent and create calendar event"""
        print("\n🔍 TEST 2: Meeting Detection and Calendar Event Creation...")
        
        try:
            # Check if the specific meeting intent exists
            meeting_intent = await self.db.meeting_intents.find_one({"id": TEST_MEETING_INTENT_ID})
            if not meeting_intent:
                self.log_test_result("Meeting Detection & Calendar Creation", False, f"Meeting intent {TEST_MEETING_INTENT_ID} not found")
                return
            
            print(f"   Found meeting intent: confidence {meeting_intent.get('confidence', 0)}")
            print(f"   Meeting text: {meeting_intent.get('meeting_text', 'No text')[:100]}...")
            
            # Verify confidence is above 0.5 threshold
            confidence = meeting_intent.get('confidence', 0)
            if confidence < 0.5:
                self.log_test_result("Meeting Detection & Calendar Creation", False, f"Confidence {confidence} below 0.5 threshold")
                return
            
            # Check if calendar event was created
            calendar_events = await self.db.calendar_events.find({
                "meeting_intent_id": TEST_MEETING_INTENT_ID
            }).to_list(10)
            
            if calendar_events:
                event = calendar_events[0]
                print(f"   ✅ Calendar event found: {event.get('title', 'No title')}")
                print(f"   Event details: start_time={event.get('start_time')}, end_time={event.get('end_time')}")
                
                # Verify event has required fields
                has_title = bool(event.get('title'))
                has_start_time = bool(event.get('start_time'))
                has_end_time = bool(event.get('end_time'))
                has_external_id = bool(event.get('external_event_id'))
                
                if has_title and has_start_time and has_end_time:
                    details = f"Confidence: {confidence}, Event created with required fields, External ID: {has_external_id}"
                    self.log_test_result("Meeting Detection & Calendar Creation", True, details)
                else:
                    missing_fields = []
                    if not has_title: missing_fields.append("title")
                    if not has_start_time: missing_fields.append("start_time")
                    if not has_end_time: missing_fields.append("end_time")
                    
                    details = f"Event missing fields: {', '.join(missing_fields)}"
                    self.log_test_result("Meeting Detection & Calendar Creation", False, details)
            else:
                # Try to trigger calendar event creation manually
                print("   No calendar event found, attempting to create...")
                
                headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
                
                try:
                    response = requests.post(f"{API_BASE}/calendar/meeting-intents/{TEST_MEETING_INTENT_ID}/confirm",
                                           headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        print("   ✅ Calendar event creation triggered")
                        
                        # Wait and check again
                        await asyncio.sleep(3)
                        calendar_events = await self.db.calendar_events.find({
                            "meeting_intent_id": TEST_MEETING_INTENT_ID
                        }).to_list(10)
                        
                        if calendar_events:
                            event = calendar_events[0]
                            details = f"Event created after manual trigger: {event.get('title', 'No title')}"
                            self.log_test_result("Meeting Detection & Calendar Creation", True, details)
                        else:
                            self.log_test_result("Meeting Detection & Calendar Creation", False, "Event creation triggered but no event found in DB")
                    else:
                        error_msg = response.text[:200] if response.text else "No error message"
                        self.log_test_result("Meeting Detection & Calendar Creation", False, f"Manual creation failed: {response.status_code} - {error_msg}")
                
                except Exception as e:
                    self.log_test_result("Meeting Detection & Calendar Creation", False, f"Manual creation error: {str(e)}")
        
        except Exception as e:
            self.log_test_result("Meeting Detection & Calendar Creation", False, f"Exception: {str(e)}")
    
    async def test_3_email_threading_verification(self):
        """TEST 3: Verify threading headers in sent emails"""
        print("\n🔍 TEST 3: Email Threading Headers Verification...")
        
        try:
            # Get the test email again to check final state
            email = await self.db.emails.find_one({"id": TEST_EMAIL_ID})
            if not email:
                self.log_test_result("Email Threading Verification", False, f"Email {TEST_EMAIL_ID} not found")
                return
            
            print(f"   Email status: {email.get('status', 'Unknown')}")
            
            # Check threading headers
            in_reply_to = email.get('in_reply_to', '')
            references = email.get('references', '')
            thread_id = email.get('thread_id', '')
            message_id = email.get('message_id', '')
            
            print(f"   In-Reply-To: {in_reply_to[:50]}..." if in_reply_to else "   In-Reply-To: Not set")
            print(f"   References: {references[:50]}..." if references else "   References: Not set")
            print(f"   Thread ID: {thread_id}")
            print(f"   Message ID: {message_id}")
            
            # For OAuth/Gmail API, check if threadId parameter would be included
            has_proper_threading = bool(in_reply_to) and bool(thread_id)
            
            if email.get('status') == 'sent':
                # Check if the email was sent with proper threading
                if has_proper_threading:
                    details = f"Sent with threading - In-Reply-To: {bool(in_reply_to)}, References: {bool(references)}, ThreadId: {bool(thread_id)}"
                    self.log_test_result("Email Threading Verification", True, details)
                else:
                    missing = []
                    if not in_reply_to: missing.append("In-Reply-To")
                    if not references: missing.append("References")
                    if not thread_id: missing.append("ThreadId")
                    
                    details = f"Email sent but missing threading headers: {', '.join(missing)}"
                    self.log_test_result("Email Threading Verification", False, details)
            else:
                # Email not sent yet, check if threading headers are prepared
                if has_proper_threading:
                    details = f"Threading headers prepared - In-Reply-To: {bool(in_reply_to)}, ThreadId: {bool(thread_id)}"
                    self.log_test_result("Email Threading Verification", True, details)
                else:
                    details = f"Email not sent and threading headers not properly set"
                    self.log_test_result("Email Threading Verification", False, details)
        
        except Exception as e:
            self.log_test_result("Email Threading Verification", False, f"Exception: {str(e)}")
    
    async def test_oauth_infrastructure(self):
        """Verify OAuth infrastructure is working"""
        print("\n🔍 OAuth Infrastructure Verification...")
        
        try:
            # Check user exists
            user = await self.db.users.find_one({"email": TEST_USER_EMAIL})
            user_exists = bool(user)
            
            # Check OAuth email account exists
            oauth_account = await self.db.email_accounts.find_one({
                "user_id": user.get('id') if user else None,
                "auth_type": "oauth",
                "oauth_email": TEST_OAUTH_EMAIL
            })
            oauth_account_exists = bool(oauth_account)
            
            # Check OAuth token exists
            oauth_token = await self.db.oauth_tokens.find_one({
                "user_id": user.get('id') if user else None,
                "email": TEST_OAUTH_EMAIL
            })
            oauth_token_exists = bool(oauth_token)
            
            # Check calendar provider exists
            calendar_provider = await self.db.calendar_providers.find_one({
                "user_id": user.get('id') if user else None,
                "oauth_email": TEST_OAUTH_EMAIL
            })
            calendar_provider_exists = bool(calendar_provider)
            
            all_infrastructure_ready = (user_exists and oauth_account_exists and 
                                      oauth_token_exists and calendar_provider_exists)
            
            details = f"User: {user_exists}, OAuth Account: {oauth_account_exists}, " \
                     f"OAuth Token: {oauth_token_exists}, Calendar Provider: {calendar_provider_exists}"
            
            self.log_test_result("OAuth Infrastructure", all_infrastructure_ready, details)
            
            if user:
                print(f"   User ID: {user.get('id')}")
            if oauth_account:
                print(f"   OAuth Account: {oauth_account.get('email')} (Active: {oauth_account.get('is_active')})")
            if oauth_token:
                print(f"   OAuth Token: {oauth_token.get('email')} (Expires: {oauth_token.get('expires_at')})")
            if calendar_provider:
                print(f"   Calendar Provider: {calendar_provider.get('provider_type')} (Active: {calendar_provider.get('is_active')})")
        
        except Exception as e:
            self.log_test_result("OAuth Infrastructure", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("CRITICAL FIXES TEST SUMMARY")
        print("="*60)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"  - {test['test']}: {test['details']}")

async def main():
    """Main test execution"""
    print("🚀 Starting Critical Fixes Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test User: {TEST_USER_EMAIL}")
    print(f"OAuth Email: {TEST_OAUTH_EMAIL}")
    print(f"Test Email ID: {TEST_EMAIL_ID}")
    print(f"Test Meeting Intent ID: {TEST_MEETING_INTENT_ID}")
    
    tester = CriticalFixesTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run infrastructure check first
        await tester.test_oauth_infrastructure()
        
        # Run the three critical tests
        await tester.test_1_oauth_email_auto_send()
        await tester.test_2_meeting_detection_and_calendar_creation()
        await tester.test_3_email_threading_verification()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())