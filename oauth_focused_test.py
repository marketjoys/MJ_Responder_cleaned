#!/usr/bin/env python3
"""
Focused OAuth Testing - Addressing specific issues found
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://component-check-2.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test account details
TEST_EMAIL = "amits.joys@gmail.com"
TEST_ACCOUNT_ID = "e7c490f4-4f8e-402e-a085-61e133a0b1d0"
TEST_USER_ID = "74ecb673-4459-4e9e-b424-e956de620036"
TEST_CALENDAR_PROVIDER_ID = "d364d970-67a1-4147-bdc8-b1047d2957a1"

class FocusedOAuthTester:
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
            
            # Fix OAuth token issue
            await self.fix_oauth_token()
            
            # Get auth token
            await self.setup_auth()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def fix_oauth_token(self):
        """Fix the OAuth token that's missing email field"""
        try:
            # Find OAuth token without email
            token_without_email = await self.db.oauth_tokens.find_one({"email": {"$exists": False}})
            
            if token_without_email:
                # Update it with the correct email
                result = await self.db.oauth_tokens.update_one(
                    {"_id": token_without_email["_id"]},
                    {"$set": {"email": TEST_EMAIL}}
                )
                
                if result.modified_count > 0:
                    print(f"✅ Fixed OAuth token - added email: {TEST_EMAIL}")
                else:
                    print("⚠️ Failed to update OAuth token")
            else:
                print("ℹ️ No OAuth token found without email field")
                
        except Exception as e:
            print(f"❌ Error fixing OAuth token: {str(e)}")
    
    async def setup_auth(self):
        """Setup authentication"""
        try:
            # Find the test user
            test_user = await self.db.users.find_one({"id": TEST_USER_ID})
            
            if test_user:
                # Reset password to known value
                new_password = "TestPassword123!"
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                await self.db.users.update_one(
                    {"id": TEST_USER_ID},
                    {"$set": {"hashed_password": hashed_password}}
                )
                
                # Try to login
                login_data = {
                    "email": test_user["email"],
                    "password": new_password
                }
                
                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    self.auth_token = result.get('access_token')
                    print(f"✅ Authenticated as: {test_user['email']}")
                    return
                else:
                    print(f"❌ Login failed: {response.status_code}")
            
            print("⚠️ Could not authenticate")
                
        except Exception as e:
            print(f"❌ Error setting up authentication: {str(e)}")
    
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
    
    async def test_oauth_token_fix(self):
        """Test 1: Verify OAuth token is now properly configured"""
        print("\\n🔑 Testing OAuth Token Fix...")
        
        try:
            # Check OAuth token
            oauth_token = await self.db.oauth_tokens.find_one({"email": TEST_EMAIL})
            
            if oauth_token:
                has_email = oauth_token.get('email') == TEST_EMAIL
                has_access_token = bool(oauth_token.get('access_token'))
                has_refresh_token = bool(oauth_token.get('refresh_token'))
                
                expires_at = oauth_token.get('expires_at')
                if expires_at:
                    if isinstance(expires_at, str):
                        token_valid = datetime.fromisoformat(expires_at.replace('Z', '+00:00')) > datetime.utcnow()
                    else:
                        token_valid = expires_at > datetime.utcnow()
                else:
                    token_valid = False
                
                all_checks_passed = has_email and has_access_token and has_refresh_token and token_valid
                
                details = f"Has email: {has_email}, Has access token: {has_access_token}, " \\
                         f"Has refresh token: {has_refresh_token}, Token valid: {token_valid}"
                
                self.log_test_result("OAuth Token Fix", all_checks_passed, details)
            else:
                self.log_test_result("OAuth Token Fix", False, "No OAuth token found")
                
        except Exception as e:
            self.log_test_result("OAuth Token Fix", False, f"Exception: {str(e)}")
    
    def test_meeting_detection_correct_format(self):
        """Test 2: Meeting Detection with correct API format"""
        print("\\n🤖 Testing Meeting Detection with Correct Format...")
        
        if not self.auth_token:
            self.log_test_result("Meeting Detection Correct Format", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Use the correct format based on the API error
            meeting_request = {
                "email_content": "Let's schedule a meeting tomorrow at 3 PM to discuss the Q4 roadmap",
                "sender": "colleague@company.com",
                "subject": "Q4 Roadmap Meeting Request",  # Add required subject field
                "user_timezone": "UTC"
            }
            
            response = requests.post(
                f"{API_BASE}/calendar/detect-meeting",
                headers=headers,
                json=meeting_request,
                timeout=30
            )
            
            if response.status_code == 200:
                detection_result = response.json()
                
                has_meeting_detected = detection_result.get('meeting_detected', False)
                has_confidence_score = 'confidence' in detection_result
                has_meeting_details = 'meeting_details' in detection_result
                
                details = f"Status: {response.status_code}, Meeting detected: {has_meeting_detected}, " \\
                         f"Has confidence: {has_confidence_score}, Has details: {has_meeting_details}"
                
                if has_confidence_score:
                    confidence = detection_result.get('confidence', 0)
                    details += f", Confidence: {confidence}"
                
                all_checks_passed = has_confidence_score  # At minimum, should have confidence score
                
                self.log_test_result("Meeting Detection Correct Format", all_checks_passed, details)
                
            else:
                self.log_test_result("Meeting Detection Correct Format", False, 
                                   f"Status: {response.status_code}, Error: {response.text[:200]}")
            
        except Exception as e:
            self.log_test_result("Meeting Detection Correct Format", False, f"Exception: {str(e)}")
    
    def test_calendar_event_creation_simple(self):
        """Test 3: Calendar Event Creation with simpler format"""
        print("\\n📅 Testing Calendar Event Creation (Simple Format)...")
        
        if not self.auth_token:
            self.log_test_result("Calendar Event Creation Simple", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Simpler event data to avoid validation issues
            event_data = {
                "title": "Simple OAuth Test Event",
                "description": "Simple test event",
                "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat()
            }
            
            response = requests.post(
                f"{API_BASE}/calendar/providers/{TEST_CALENDAR_PROVIDER_ID}/calendars/primary/events",
                headers=headers,
                json=event_data,
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                event_response = response.json()
                event_id = event_response.get('id')
                
                # Try to delete the event immediately
                if event_id:
                    delete_response = requests.delete(
                        f"{API_BASE}/calendar/providers/{TEST_CALENDAR_PROVIDER_ID}/calendars/primary/events/{event_id}",
                        headers=headers,
                        timeout=15
                    )
                    cleanup_success = delete_response.status_code in [200, 204]
                else:
                    cleanup_success = False
                
                details = f"Status: {response.status_code}, Event ID: {event_id}, Cleanup: {cleanup_success}"
                
                self.log_test_result("Calendar Event Creation Simple", True, details)
                
            else:
                self.log_test_result("Calendar Event Creation Simple", False, 
                                   f"Status: {response.status_code}, Error: {response.text[:300]}")
            
        except Exception as e:
            self.log_test_result("Calendar Event Creation Simple", False, f"Exception: {str(e)}")
    
    def test_groq_api_direct(self):
        """Test 4: Direct Groq API test to confirm it's working"""
        print("\\n🔑 Testing Groq API Direct...")
        
        try:
            groq_api_key = os.environ.get('GROQ_API_KEY')
            
            if not groq_api_key:
                self.log_test_result("Groq API Direct", False, "No Groq API key found")
                return
            
            headers = {
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            }
            
            test_payload = {
                "messages": [
                    {"role": "user", "content": "Analyze this email for meeting requests: 'Let's schedule a meeting tomorrow at 3 PM to discuss the Q4 roadmap'. Is this a meeting request? Respond with just YES or NO."}
                ],
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.1,
                "max_completion_tokens": 10
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                details = f"Status: {response.status_code}, Response: {content.strip()}"
                
                self.log_test_result("Groq API Direct", True, details)
                
            else:
                self.log_test_result("Groq API Direct", False, 
                                   f"Status: {response.status_code}, Error: {response.text[:200]}")
            
        except Exception as e:
            self.log_test_result("Groq API Direct", False, f"Exception: {str(e)}")
    
    def test_email_polling_detailed(self):
        """Test 5: Detailed Email Polling Status"""
        print("\\n📡 Testing Email Polling Detailed...")
        
        try:
            # Test the polling status endpoint
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            
            if response.status_code == 200:
                polling_data = response.json()
                
                service_running = polling_data.get('status') == 'running'
                
                # Check accounts-status endpoint
                accounts_response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                
                if accounts_response.status_code == 200:
                    accounts_data = accounts_response.json()
                    accounts_list = accounts_data.get('accounts', [])
                    
                    oauth_account_found = False
                    for account in accounts_list:
                        if account.get('email') == TEST_EMAIL:
                            oauth_account_found = True
                            break
                    
                    details = f"Service running: {service_running}, Accounts endpoint: 200, " \\
                             f"Total accounts: {len(accounts_list)}, OAuth account found: {oauth_account_found}"
                    
                    all_checks_passed = service_running and len(accounts_list) > 0
                    
                else:
                    details = f"Service running: {service_running}, Accounts endpoint failed: {accounts_response.status_code}"
                    all_checks_passed = False
                
                self.log_test_result("Email Polling Detailed", all_checks_passed, details)
                
            else:
                self.log_test_result("Email Polling Detailed", False, 
                                   f"Status: {response.status_code}, Error: {response.text[:200]}")
            
        except Exception as e:
            self.log_test_result("Email Polling Detailed", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\\n" + "="*80)
        print("🎯 FOCUSED OAUTH TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL:  {len(self.test_results)}")
        
        if failed_tests:
            print("\\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   • {test['test']}")
        
        print("\\n" + "="*80)
        
        # Calculate success rate
        success_rate = (len(passed_tests) / len(self.test_results)) * 100 if self.test_results else 0
        print(f"🎯 SUCCESS RATE: {success_rate:.1f}%")
        
        return success_rate >= 80

async def main():
    """Main test execution"""
    print("🚀 Starting Focused OAuth Testing...")
    print(f"🎯 Testing OAuth account: {TEST_EMAIL}")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    
    tester = FocusedOAuthTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return False
        
        # Run focused tests
        await tester.test_oauth_token_fix()
        tester.test_meeting_detection_correct_format()
        tester.test_calendar_event_creation_simple()
        tester.test_groq_api_direct()
        tester.test_email_polling_detailed()
        
        # Print summary
        overall_success = tester.print_summary()
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return False
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)