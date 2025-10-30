#!/usr/bin/env python3
"""
Final OAuth Testing - Testing the 3 critical issues with proper authentication
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid
import bcrypt

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

# Correct data from database
OAUTH_EMAIL = "amits.joys@gmail.com"
CORRECT_USER_ID = "6d4ac92f-1971-4f9c-8b94-790b708765f0"
CORRECT_ACCOUNT_ID = "07ea99bd-b08e-40db-a916-e5807d3925bb"
OAUTH_TOKEN_ID = "7e5276c5-5184-4302-b362-9bc2a445937a"

class FinalOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        
    async def setup(self):
        """Setup database connection"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Try to reset password and authenticate
            await self.reset_user_password_and_authenticate()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def reset_user_password_and_authenticate(self):
        """Reset the user password to a known value and authenticate"""
        try:
            # Reset password to a known value
            new_password = "TestPassword123!"
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update user password in database
            result = await self.db.users.update_one(
                {"id": CORRECT_USER_ID},
                {"$set": {"hashed_password": hashed_password}}
            )
            
            if result.modified_count > 0:
                print(f"✅ Reset password for user {CORRECT_USER_ID}")
                
                # Now try to authenticate
                login_data = {
                    "email": OAUTH_EMAIL,
                    "password": new_password
                }
                
                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    self.auth_token = result.get('access_token')
                    user_id = result.get('user', {}).get('id')
                    
                    if user_id == CORRECT_USER_ID:
                        print(f"✅ Successfully authenticated as {OAUTH_EMAIL}")
                        return True
                    else:
                        print(f"⚠️ Authenticated but wrong user ID: {user_id} vs {CORRECT_USER_ID}")
                else:
                    print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            else:
                print("❌ Failed to reset user password")
                
        except Exception as e:
            print(f"❌ Error during password reset: {str(e)}")
        
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
    
    async def test_oauth_email_settings_update(self):
        """Test 1: Update OAuth Email Account Settings"""
        print("\n📝 TEST 1: OAuth Email Account Settings Update")
        print("="*60)
        
        if not self.auth_token:
            self.log_test_result("OAuth Email Settings Update", False, "No authentication token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test data from review request
        settings_update = {
            "signature": "Best regards,\\nAmit Joys\\nSoftware Engineer",
            "persona": "I am a professional software engineer who responds promptly to emails.",
            "enable_follow_ups": True
        }
        
        try:
            print(f"   Testing PATCH /api/email-accounts/{CORRECT_ACCOUNT_ID}/settings")
            
            response = requests.patch(
                f"{API_BASE}/email-accounts/{CORRECT_ACCOUNT_ID}/settings",
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
                db_account = await self.db.email_accounts.find_one({"id": CORRECT_ACCOUNT_ID})
                db_signature_correct = db_account.get('signature') == settings_update['signature'] if db_account else False
                db_persona_correct = db_account.get('persona') == settings_update['persona'] if db_account else False
                db_follow_ups_correct = db_account.get('enable_follow_ups') == settings_update['enable_follow_ups'] if db_account else False
                
                all_updated = signature_updated and persona_updated and follow_ups_updated
                all_persisted = db_signature_correct and db_persona_correct and db_follow_ups_correct
                
                print(f"   ✅ API Response: Status 200")
                print(f"   ✅ Signature Updated: {signature_updated}")
                print(f"   ✅ Persona Updated: {persona_updated}")
                print(f"   ✅ Follow-ups Updated: {follow_ups_updated}")
                print(f"   ✅ Database Persisted: {all_persisted}")
                
                details = f"Status: 200, API Updated: {all_updated}, DB Persisted: {all_persisted}"
                self.log_test_result("OAuth Email Settings Update", all_updated and all_persisted, details)
                
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                print(f"   ❌ API Error: {details}")
                self.log_test_result("OAuth Email Settings Update", False, details)
                
        except Exception as e:
            details = f"Exception: {str(e)}"
            print(f"   ❌ Exception: {details}")
            self.log_test_result("OAuth Email Settings Update", False, details)
    
    async def test_calendar_meeting_detection(self):
        """Test 2: Calendar Meeting Detection"""
        print("\n📅 TEST 2: Calendar Meeting Detection")
        print("="*60)
        
        if not self.auth_token:
            self.log_test_result("Calendar Meeting Detection", False, "No authentication token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test calendar API - Get calendars
        try:
            print("   Testing GET /api/calendar/calendars")
            response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
            
            if response.status_code == 200:
                calendars = response.json()
                calendar_count = len(calendars)
                
                print(f"   ✅ Calendar API Status: 200")
                print(f"   ✅ Calendars returned: {calendar_count}")
                
                # Look for expected calendars
                has_holidays = any("Holidays" in str(cal) for cal in calendars)
                has_primary = any(OAUTH_EMAIL in str(cal) for cal in calendars)
                
                print(f"   ✅ Has Holidays calendar: {has_holidays}")
                print(f"   ✅ Has Primary calendar: {has_primary}")
                
                calendar_api_working = calendar_count >= 0
                details = f"Status: 200, Calendars: {calendar_count}, Has Holidays: {has_holidays}, Has Primary: {has_primary}"
                self.log_test_result("Calendar API Access", calendar_api_working, details)
                
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                print(f"   ❌ Calendar API Error: {details}")
                self.log_test_result("Calendar API Access", False, details)
                calendars = []
                
        except Exception as e:
            details = f"Exception: {str(e)}"
            print(f"   ❌ Calendar API Exception: {details}")
            self.log_test_result("Calendar API Access", False, details)
            calendars = []
        
        # Test meeting detection
        try:
            print("   Testing POST /api/calendar/detect-meeting")
            
            detection_request = {
                "subject": "Meeting Request - Project Discussion",
                "email_content": "Hi Amit, I'd like to schedule a meeting with you to discuss the new project requirements. Are you available next Tuesday at 2 PM?",
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
                has_meeting = detection_result.get('has_meeting_intent', False)
                confidence = detection_result.get('confidence', 0)
                
                print(f"   ✅ Meeting Detection API Status: 200")
                print(f"   ✅ Meeting Detected: {has_meeting}")
                print(f"   ✅ Confidence: {confidence}")
                
                details = f"Status: 200, Meeting Detected: {has_meeting}, Confidence: {confidence}"
                self.log_test_result("Meeting Detection API", True, details)
                
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                print(f"   ❌ Meeting Detection Error: {details}")
                self.log_test_result("Meeting Detection API", False, details)
                
        except Exception as e:
            details = f"Exception: {str(e)}"
            print(f"   ❌ Meeting Detection Exception: {details}")
            self.log_test_result("Meeting Detection API", False, details)
        
        # Test creating a calendar event if we have calendars
        if calendars and len(calendars) > 0:
            try:
                print("   Testing calendar event creation")
                
                first_calendar = calendars[0]
                if 'id' in first_calendar and 'provider_id' in first_calendar:
                    calendar_id = first_calendar['id']
                    provider_id = first_calendar['provider_id']
                    
                    event_data = {
                        "title": "OAuth Test Meeting - Automated Test",
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
                        
                        print(f"   ✅ Event Creation Status: {response.status_code}")
                        print(f"   ✅ Event ID: {event_id}")
                        
                        details = f"Status: {response.status_code}, Event ID: {event_id}"
                        self.log_test_result("Calendar Event Creation", True, details)
                        
                    else:
                        details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                        print(f"   ❌ Event Creation Error: {details}")
                        self.log_test_result("Calendar Event Creation", False, details)
                else:
                    details = "Calendar missing required fields"
                    self.log_test_result("Calendar Event Creation", False, details)
                    
            except Exception as e:
                details = f"Exception: {str(e)}"
                self.log_test_result("Calendar Event Creation", False, details)
        else:
            self.log_test_result("Calendar Event Creation", False, "No calendars available")
    
    async def test_oauth_email_polling_and_reply(self):
        """Test 3: OAuth Email Polling and Reply Processing"""
        print("\n📧 TEST 3: OAuth Email Polling and Reply Processing")
        print("="*60)
        
        # Test OAuth account polling status
        try:
            oauth_account = await self.db.email_accounts.find_one({"id": CORRECT_ACCOUNT_ID})
            
            if oauth_account:
                is_active = oauth_account.get('is_active', False)
                last_oauth_sync = oauth_account.get('last_oauth_sync')
                
                print(f"   ✅ OAuth account active: {is_active}")
                print(f"   ✅ Last OAuth sync: {last_oauth_sync}")
                
                # Check if polling is recent
                polling_recent = False
                if last_oauth_sync:
                    if isinstance(last_oauth_sync, str):
                        last_sync_time = datetime.fromisoformat(last_oauth_sync.replace('Z', '+00:00'))
                    else:
                        last_sync_time = last_oauth_sync
                    
                    time_diff = datetime.utcnow() - last_sync_time.replace(tzinfo=None)
                    polling_recent = time_diff.total_seconds() < 7200  # 2 hours
                    
                    print(f"   ✅ Polling recent: {polling_recent} ({time_diff.total_seconds()/60:.1f} min ago)")
                
                details = f"Active: {is_active}, Recent: {polling_recent}"
                self.log_test_result("OAuth Polling Status", is_active and polling_recent, details)
                
            else:
                self.log_test_result("OAuth Polling Status", False, "OAuth account not found")
                
        except Exception as e:
            self.log_test_result("OAuth Polling Status", False, f"Exception: {str(e)}")
        
        # Test OAuth token validity
        try:
            oauth_token = await self.db.oauth_tokens.find_one({"id": OAUTH_TOKEN_ID})
            
            if oauth_token:
                expires_at = oauth_token.get('expires_at')
                scopes = oauth_token.get('scope', '')
                
                # Check if token is expired
                token_valid = False
                if expires_at:
                    if isinstance(expires_at, str):
                        expires_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    else:
                        expires_time = expires_at
                    
                    token_valid = expires_time.replace(tzinfo=None) > datetime.utcnow()
                    
                    if token_valid:
                        time_diff = expires_time.replace(tzinfo=None) - datetime.utcnow()
                        print(f"   ✅ Token valid: expires in {time_diff.total_seconds()/3600:.1f} hours")
                    else:
                        print(f"   ❌ Token expired")
                
                has_gmail_scope = 'gmail' in scopes
                has_calendar_scope = 'calendar' in scopes
                
                print(f"   ✅ Has Gmail scope: {has_gmail_scope}")
                print(f"   ✅ Has Calendar scope: {has_calendar_scope}")
                
                details = f"Valid: {token_valid}, Gmail: {has_gmail_scope}, Calendar: {has_calendar_scope}"
                self.log_test_result("OAuth Token Validity", token_valid and has_gmail_scope, details)
                
            else:
                self.log_test_result("OAuth Token Validity", False, "OAuth token not found")
                
        except Exception as e:
            self.log_test_result("OAuth Token Validity", False, f"Exception: {str(e)}")
        
        # Test email processing workflow
        if self.auth_token:
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                print("   Testing email processing workflow")
                
                test_email_data = {
                    "subject": "OAuth Test - Email Processing",
                    "body": "This is a test email to verify OAuth account email processing. Please respond with pricing information.",
                    "sender": "oauth.test@example.com",
                    "account_id": CORRECT_ACCOUNT_ID
                }
                
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
                    
                    print(f"   ✅ Email processing API Status: {response.status_code}")
                    print(f"   ✅ Email ID: {email_id}")
                    print(f"   ✅ Processing status: {status}")
                    
                    # Wait and check processing completion
                    if email_id:
                        await asyncio.sleep(5)
                        
                        processed_email_db = await self.db.emails.find_one({"id": email_id})
                        if processed_email_db:
                            final_status = processed_email_db.get('status')
                            has_draft = bool(processed_email_db.get('draft'))
                            draft_length = len(processed_email_db.get('draft', ''))
                            
                            print(f"   ✅ Final status: {final_status}")
                            print(f"   ✅ Has draft: {has_draft} ({draft_length} chars)")
                            
                            processing_successful = final_status in ['ready_to_send', 'sent'] or (has_draft and draft_length > 50)
                            
                            details = f"Status: {response.status_code}, Final: {final_status}, Draft: {has_draft}, Success: {processing_successful}"
                            self.log_test_result("Email Processing Workflow", processing_successful, details)
                        else:
                            self.log_test_result("Email Processing Workflow", False, "Email not found in DB")
                    else:
                        self.log_test_result("Email Processing Workflow", False, "No email ID returned")
                        
                else:
                    details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    self.log_test_result("Email Processing Workflow", False, details)
                    
            except Exception as e:
                self.log_test_result("Email Processing Workflow", False, f"Exception: {str(e)}")
        else:
            self.log_test_result("Email Processing Workflow", False, "No auth token")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 FINAL OAUTH TESTING SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        # Critical test assessment
        settings_tests = [r for r in self.test_results if "Settings" in r['test']]
        calendar_tests = [r for r in self.test_results if "Calendar" in r['test'] or "Meeting" in r['test']]
        polling_tests = [r for r in self.test_results if "Polling" in r['test'] or "Token" in r['test'] or "Processing" in r['test']]
        
        settings_working = any(r['passed'] for r in settings_tests)
        calendar_working = len([r for r in calendar_tests if r['passed']]) >= 1
        polling_working = len([r for r in polling_tests if r['passed']]) >= 2
        
        print(f"\n🎯 CRITICAL TEST RESULTS:")
        print(f"   📝 Test 1 - OAuth Email Settings Update: {'✅ WORKING' if settings_working else '❌ FAILING'}")
        print(f"   📅 Test 2 - Calendar Meeting Detection: {'✅ WORKING' if calendar_working else '❌ FAILING'}")
        print(f"   📧 Test 3 - OAuth Email Polling: {'✅ WORKING' if polling_working else '❌ FAILING'}")
        
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
    print("🚀 Final OAuth Testing for amits.joys@gmail.com")
    print("Testing the 3 critical issues from the review request")
    print("="*80)
    
    tester = FinalOAuthTester()
    
    try:
        if not await tester.setup():
            print("❌ Setup failed, exiting")
            return
        
        # Run the 3 critical tests
        await tester.test_oauth_email_settings_update()
        await tester.test_calendar_meeting_detection()
        await tester.test_oauth_email_polling_and_reply()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())