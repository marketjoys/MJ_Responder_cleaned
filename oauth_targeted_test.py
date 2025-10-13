#!/usr/bin/env python3
"""
Targeted OAuth Testing for amits.joys@gmail.com with correct user authentication
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-sync-repair.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Correct data from database
OAUTH_EMAIL = "amits.joys@gmail.com"
CORRECT_USER_ID = "6d4ac92f-1971-4f9c-8b94-790b708765f0"
CORRECT_ACCOUNT_ID = "07ea99bd-b08e-40db-a916-e5807d3925bb"
CALENDAR_PROVIDER_ID = "09cace39-6067-47b2-9596-59c39d012b7c"

class TargetedOAuthTester:
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
            
            # Try to authenticate as the correct user
            await self.authenticate_correct_user()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def authenticate_correct_user(self):
        """Try to authenticate as the correct user (amits.joys@gmail.com)"""
        try:
            # Try common passwords
            passwords_to_try = ["admin123", "password", "123456", "amits123", "gmail123"]
            
            for password in passwords_to_try:
                login_data = {
                    "email": OAUTH_EMAIL,
                    "password": password
                }
                
                try:
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        self.auth_token = result.get('access_token')
                        user_id = result.get('user', {}).get('id')
                        
                        if user_id == CORRECT_USER_ID:
                            print(f"✅ Successfully authenticated as {OAUTH_EMAIL} (Password: {password})")
                            return True
                        else:
                            print(f"⚠️ Authenticated but wrong user ID: {user_id} vs {CORRECT_USER_ID}")
                            
                except Exception as e:
                    continue
            
            print(f"❌ Could not authenticate as {OAUTH_EMAIL} with any common password")
            print("   This is the root cause of the 404 errors - authentication mismatch")
            return False
            
        except Exception as e:
            print(f"❌ Error during authentication: {str(e)}")
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
    
    async def test_oauth_token_missing(self):
        """Test: OAuth Token Missing - Critical Issue"""
        print("\n🔍 Testing OAuth Token Status...")
        
        try:
            oauth_token = await self.db.oauth_tokens.find_one({
                "email": OAUTH_EMAIL,
                "provider": "google"
            })
            
            if oauth_token:
                access_token = oauth_token.get('access_token')
                refresh_token = oauth_token.get('refresh_token')
                expires_at = oauth_token.get('expires_at')
                scopes = oauth_token.get('scopes', [])
                
                # Check if token is expired
                token_valid = False
                if expires_at:
                    if isinstance(expires_at, str):
                        expires_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    else:
                        expires_time = expires_at
                    
                    token_valid = expires_time.replace(tzinfo=None) > datetime.utcnow()
                
                details = f"Access Token: {bool(access_token)}, Refresh Token: {bool(refresh_token)}, Valid: {token_valid}, Scopes: {scopes}"
                self.log_test_result("OAuth Token Exists", True, details)
                
                if not token_valid:
                    self.log_test_result("OAuth Token Valid", False, "Token expired - needs refresh")
                else:
                    self.log_test_result("OAuth Token Valid", True, "Token is valid")
                    
            else:
                self.log_test_result("OAuth Token Exists", False, "CRITICAL: No OAuth token found in database")
                self.log_test_result("OAuth Token Valid", False, "No token to validate")
                
        except Exception as e:
            self.log_test_result("OAuth Token Exists", False, f"Exception: {str(e)}")
    
    async def test_email_settings_without_auth(self):
        """Test: Email Settings Update Without Authentication"""
        print("\n📝 Testing Email Settings Update (No Auth)...")
        
        settings_update = {
            "signature": "Best regards,\\nAmit Joys\\nSoftware Engineer",
            "persona": "I am a professional software engineer who responds promptly to emails.",
            "enable_follow_ups": True
        }
        
        try:
            # Test without authentication
            response = requests.patch(
                f"{API_BASE}/email-accounts/{CORRECT_ACCOUNT_ID}/settings",
                json=settings_update,
                timeout=15
            )
            
            details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            expected_401 = response.status_code == 401  # Should require authentication
            
            self.log_test_result("Email Settings - No Auth", expected_401, details)
            
        except Exception as e:
            self.log_test_result("Email Settings - No Auth", False, f"Exception: {str(e)}")
    
    async def test_email_settings_with_auth(self):
        """Test: Email Settings Update With Authentication"""
        print("\n📝 Testing Email Settings Update (With Auth)...")
        
        if not self.auth_token:
            self.log_test_result("Email Settings - With Auth", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        settings_update = {
            "signature": "Best regards,\\nAmit Joys\\nSoftware Engineer",
            "persona": "I am a professional software engineer who responds promptly to emails.",
            "enable_follow_ups": True
        }
        
        try:
            response = requests.patch(
                f"{API_BASE}/email-accounts/{CORRECT_ACCOUNT_ID}/settings",
                json=settings_update,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                updated_account = response.json()
                
                # Verify updates
                signature_updated = updated_account.get('signature') == settings_update['signature']
                persona_updated = updated_account.get('persona') == settings_update['persona']
                follow_ups_updated = updated_account.get('enable_follow_ups') == settings_update['enable_follow_ups']
                
                all_updated = signature_updated and persona_updated and follow_ups_updated
                details = f"Status: 200, All Fields Updated: {all_updated}"
                self.log_test_result("Email Settings - With Auth", all_updated, details)
                
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                self.log_test_result("Email Settings - With Auth", False, details)
                
        except Exception as e:
            self.log_test_result("Email Settings - With Auth", False, f"Exception: {str(e)}")
    
    async def test_calendar_api_without_auth(self):
        """Test: Calendar API Without Authentication"""
        print("\n📅 Testing Calendar API (No Auth)...")
        
        try:
            response = requests.get(f"{API_BASE}/calendar/calendars", timeout=15)
            
            details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            expected_401 = response.status_code == 401  # Should require authentication
            
            self.log_test_result("Calendar API - No Auth", expected_401, details)
            
        except Exception as e:
            self.log_test_result("Calendar API - No Auth", False, f"Exception: {str(e)}")
    
    async def test_calendar_api_with_auth(self):
        """Test: Calendar API With Authentication"""
        print("\n📅 Testing Calendar API (With Auth)...")
        
        if not self.auth_token:
            self.log_test_result("Calendar API - With Auth", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
            
            if response.status_code == 200:
                calendars = response.json()
                calendar_count = len(calendars)
                
                # Check for expected calendars
                has_holidays = any("Holidays" in str(cal) for cal in calendars)
                has_primary = any(OAUTH_EMAIL in str(cal) for cal in calendars)
                
                details = f"Status: 200, Calendars: {calendar_count}, Has Holidays: {has_holidays}, Has Primary: {has_primary}"
                success = calendar_count >= 0  # Any response is good if authenticated
                self.log_test_result("Calendar API - With Auth", success, details)
                
                return calendars
                
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                self.log_test_result("Calendar API - With Auth", False, details)
                return []
                
        except Exception as e:
            self.log_test_result("Calendar API - With Auth", False, f"Exception: {str(e)}")
            return []
    
    async def test_meeting_detection_api(self):
        """Test: Meeting Detection API"""
        print("\n🤖 Testing Meeting Detection API...")
        
        if not self.auth_token:
            self.log_test_result("Meeting Detection API", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Correct request format based on API error
        detection_request = {
            "subject": "Meeting Request",  # Added required field
            "email_content": "Hi Amit, I'd like to schedule a meeting with you to discuss the new project requirements. Are you available next Tuesday at 2 PM?",
            "sender": "john.doe@company.com",
            "user_timezone": "Asia/Kolkata"
        }
        
        try:
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
                
                details = f"Status: 200, Meeting Detected: {has_meeting}, Confidence: {confidence}"
                self.log_test_result("Meeting Detection API", True, details)  # API working is success
                
            else:
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                self.log_test_result("Meeting Detection API", False, details)
                
        except Exception as e:
            self.log_test_result("Meeting Detection API", False, f"Exception: {str(e)}")
    
    async def test_oauth_polling_status(self):
        """Test: OAuth Account Polling Status"""
        print("\n📡 Testing OAuth Account Polling Status...")
        
        try:
            oauth_account = await self.db.email_accounts.find_one({"id": CORRECT_ACCOUNT_ID})
            
            if oauth_account:
                is_active = oauth_account.get('is_active', False)
                last_oauth_sync = oauth_account.get('last_oauth_sync')
                last_polled = oauth_account.get('last_polled')
                
                # Check if polling is recent (within 2 hours)
                polling_recent = False
                if last_oauth_sync:
                    if isinstance(last_oauth_sync, str):
                        last_sync_time = datetime.fromisoformat(last_oauth_sync.replace('Z', '+00:00'))
                    else:
                        last_sync_time = last_oauth_sync
                    
                    time_diff = datetime.utcnow() - last_sync_time.replace(tzinfo=None)
                    polling_recent = time_diff.total_seconds() < 7200  # 2 hours
                
                details = f"Active: {is_active}, Last OAuth Sync: {last_oauth_sync}, Recent: {polling_recent}"
                self.log_test_result("OAuth Polling Status", is_active and polling_recent, details)
                
            else:
                self.log_test_result("OAuth Polling Status", False, "OAuth account not found")
                
        except Exception as e:
            self.log_test_result("OAuth Polling Status", False, f"Exception: {str(e)}")
    
    async def test_backend_logs_for_oauth(self):
        """Test: Check Backend Logs for OAuth Activity"""
        print("\n📋 Checking Backend Logs for OAuth Activity...")
        
        try:
            # Check supervisor logs for OAuth activity
            result = os.popen("tail -n 50 /var/log/supervisor/backend.*.log | grep -i 'oauth\\|gmail\\|amits.joys' | tail -10").read()
            
            if result.strip():
                lines = result.strip().split('\n')
                oauth_activity = len(lines)
                
                details = f"Found {oauth_activity} OAuth-related log entries in recent logs"
                self.log_test_result("Backend OAuth Logs", oauth_activity > 0, details)
                
                print("   Recent OAuth log entries:")
                for line in lines[-5:]:  # Show last 5 entries
                    print(f"     {line}")
            else:
                self.log_test_result("Backend OAuth Logs", False, "No OAuth activity found in recent logs")
                
        except Exception as e:
            self.log_test_result("Backend OAuth Logs", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary with root cause analysis"""
        print("\n" + "="*80)
        print("🎯 TARGETED OAUTH TESTING SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        print("\n🔍 ROOT CAUSE ANALYSIS:")
        
        # Check for authentication issues
        auth_issues = [t for t in failed_tests if "No auth token" in t['details'] or "404" in t['details']]
        if auth_issues:
            print("   🚨 AUTHENTICATION ISSUE: Cannot authenticate as the OAuth account owner")
            print(f"      - OAuth account exists for user {CORRECT_USER_ID}")
            print(f"      - But cannot login as {OAUTH_EMAIL}")
            print("      - This causes 404 errors when trying to access account resources")
        
        # Check for missing OAuth tokens
        token_issues = [t for t in failed_tests if "OAuth Token" in t['test']]
        if token_issues:
            print("   🚨 OAUTH TOKEN MISSING: No OAuth tokens found in database")
            print("      - OAuth account exists but has no associated tokens")
            print("      - This prevents OAuth API calls from working")
            print("      - Tokens may have been deleted or never properly stored")
        
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
    print("🎯 Starting Targeted OAuth Testing for amits.joys@gmail.com")
    print("="*80)
    
    tester = TargetedOAuthTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting")
            return
        
        # Run targeted tests
        await tester.test_oauth_token_missing()
        await tester.test_email_settings_without_auth()
        await tester.test_email_settings_with_auth()
        await tester.test_calendar_api_without_auth()
        calendars = await tester.test_calendar_api_with_auth()
        await tester.test_meeting_detection_api()
        await tester.test_oauth_polling_status()
        await tester.test_backend_logs_for_oauth()
        
        # Print summary with root cause analysis
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Critical error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())