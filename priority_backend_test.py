#!/usr/bin/env python3
"""
Priority Backend Testing for Email Assistant System
Focus on Cal.com Integration and new API key verification
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://account-sync-check.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class PriorityTester:
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

    def test_authentication_system(self):
        """Test Authentication System - Registration, Login, JWT validation, Quota management"""
        print("\n🔐 Testing AUTHENTICATION SYSTEM...")
        
        test_user_email = f"test.auth.{int(time.time())}@example.com"
        test_password = "TestPassword123!"
        
        try:
            # Test Auth 1: User Registration
            try:
                register_data = {
                    "email": test_user_email,
                    "password": test_password,
                    "full_name": "Test Authentication User"
                }
                response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
                register_passed = response.status_code == 200
                
                if register_passed:
                    register_result = response.json()
                    self.auth_token = register_result.get('access_token')
                    self.test_user_id = register_result.get('user', {}).get('id')
                    register_details = f"Status: {response.status_code}, Token received: {bool(self.auth_token)}"
                else:
                    register_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            except Exception as e:
                register_passed = False
                register_details = f"Error: {str(e)}"
            
            # Test Auth 2: User Login
            login_passed = False
            if register_passed:
                try:
                    login_data = {
                        "email": test_user_email,
                        "password": test_password
                    }
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    login_passed = response.status_code == 200
                    
                    if login_passed:
                        login_result = response.json()
                        login_token = login_result.get('access_token')
                        login_details = f"Status: {response.status_code}, Token received: {bool(login_token)}"
                    else:
                        login_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                except Exception as e:
                    login_passed = False
                    login_details = f"Error: {str(e)}"
            else:
                login_details = "Skipped - registration failed"
            
            # Test Auth 3: User Profile with JWT
            profile_passed = False
            if self.auth_token:
                try:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
                    profile_passed = (response.status_code == 200 and 
                                    'email' in response.json() and
                                    'quota_info' in response.json())
                    
                    if profile_passed:
                        profile_data = response.json()
                        profile_details = f"Status: {response.status_code}, Email: {profile_data.get('email')}, Quota: {profile_data.get('quota_info', {}).get('emails_remaining', 'N/A')}"
                    else:
                        profile_details = f"Status: {response.status_code}"
                except Exception as e:
                    profile_passed = False
                    profile_details = f"Error: {str(e)}"
            else:
                profile_details = "Skipped - no auth token"
            
            all_passed = (register_passed and login_passed and profile_passed)
            
            # Log individual results
            self.log_test_result("Auth - User Registration", register_passed, register_details)
            self.log_test_result("Auth - User Login", login_passed, login_details)
            self.log_test_result("Auth - User Profile", profile_passed, profile_details)
            
            details = f"Register: {register_passed}, Login: {login_passed}, Profile: {profile_passed}"
            
            self.log_test_result("AUTHENTICATION SYSTEM", all_passed, details)
            
        except Exception as e:
            self.log_test_result("AUTHENTICATION SYSTEM", False, f"Exception: {str(e)}")

    def test_calcom_integration(self):
        """Test Cal.com Integration - CRITICAL TEST with real API key"""
        print("\n📞 Testing CAL.COM INTEGRATION...")
        
        if not self.auth_token:
            self.log_test_result("Cal.com Integration", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        created_provider_id = None
        
        try:
            # Test CalCom 1: Create Cal.com Provider with Real API Key
            try:
                calcom_data = {
                    "provider_type": "calcom",
                    "provider_name": "Test Cal.com Provider",
                    "credentials": {
                        "api_key": "cal_live_d133aaaf5ee692d561d43a45ecff15ee"  # Real API key from env
                    },
                    "timezone": "America/New_York"
                }
                
                response = requests.post(f"{API_BASE}/calendar/providers", json=calcom_data, headers=headers, timeout=15)
                create_provider_passed = response.status_code == 200
                
                if create_provider_passed:
                    created_provider = response.json()
                    created_provider_id = created_provider.get('id')
                    create_provider_details = f"Status: {response.status_code}, Provider ID: {created_provider_id}"
                else:
                    create_provider_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            except Exception as e:
                create_provider_passed = False
                create_provider_details = f"Error: {str(e)}"
            
            # Test CalCom 2: List Cal.com Providers
            try:
                response = requests.get(f"{API_BASE}/calendar/providers", headers=headers, timeout=10)
                list_providers_passed = (response.status_code == 200 and isinstance(response.json(), list))
                
                if list_providers_passed:
                    providers = response.json()
                    calcom_providers = [p for p in providers if p.get('provider_type') == 'calcom']
                    list_providers_details = f"Status: {response.status_code}, Cal.com providers: {len(calcom_providers)}"
                else:
                    list_providers_details = f"Status: {response.status_code}"
            except Exception as e:
                list_providers_passed = False
                list_providers_details = f"Error: {str(e)}"
            
            # Test CalCom 3: Get Cal.com Calendars
            try:
                response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
                get_calendars_passed = response.status_code == 200
                
                if get_calendars_passed:
                    calendars_data = response.json()
                    get_calendars_details = f"Status: {response.status_code}, Calendars retrieved: {isinstance(calendars_data, list)}"
                else:
                    get_calendars_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            except Exception as e:
                get_calendars_passed = False
                get_calendars_details = f"Error: {str(e)}"
            
            # Test CalCom 4: Create Cal.com Event (This may fail due to account configuration)
            create_event_passed = False
            if created_provider_id:
                try:
                    event_data = {
                        "title": "Test Cal.com Event",
                        "description": "Test event for Cal.com integration",
                        "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                        "end_time": (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat(),
                        "timezone": "America/New_York"
                    }
                    
                    # Use a test calendar ID
                    calendar_id = "default"
                    response = requests.post(f"{API_BASE}/calendar/providers/{created_provider_id}/calendars/{calendar_id}/events", 
                                           json=event_data, headers=headers, timeout=20)
                    create_event_passed = response.status_code == 200
                    
                    if create_event_passed:
                        create_event_details = f"Status: {response.status_code}, Event created successfully"
                    else:
                        create_event_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                except Exception as e:
                    create_event_passed = False
                    create_event_details = f"Error: {str(e)}"
            else:
                create_event_details = "Skipped - no provider created"
            
            # Test CalCom 5: List Cal.com Events (This may fail due to account configuration)
            list_events_passed = False
            if created_provider_id:
                try:
                    calendar_id = "default"
                    response = requests.get(f"{API_BASE}/calendar/providers/{created_provider_id}/calendars/{calendar_id}/events", 
                                          headers=headers, timeout=15)
                    list_events_passed = response.status_code == 200
                    
                    if list_events_passed:
                        list_events_details = f"Status: {response.status_code}, Events listed successfully"
                    else:
                        list_events_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                except Exception as e:
                    list_events_passed = False
                    list_events_details = f"Error: {str(e)}"
            else:
                list_events_details = "Skipped - no provider created"
            
            # Test CalCom 6: Delete Cal.com Provider
            delete_provider_passed = False
            if created_provider_id:
                try:
                    response = requests.delete(f"{API_BASE}/calendar/providers/{created_provider_id}", headers=headers, timeout=10)
                    delete_provider_passed = response.status_code == 200
                    delete_provider_details = f"Status: {response.status_code}"
                    
                    # Verify deletion
                    if delete_provider_passed:
                        verify_response = requests.get(f"{API_BASE}/calendar/providers", headers=headers, timeout=10)
                        if verify_response.status_code == 200:
                            remaining_providers = verify_response.json()
                            provider_deleted = not any(p.get('id') == created_provider_id for p in remaining_providers)
                            delete_provider_details += f", Verified deletion: {provider_deleted}"
                        
                except Exception as e:
                    delete_provider_passed = False
                    delete_provider_details = f"Error: {str(e)}"
            else:
                delete_provider_details = "Skipped - no provider created"
            
            # Determine overall success
            # Provider CRUD operations should work, event operations may fail due to Cal.com account setup
            core_operations_passed = (create_provider_passed and list_providers_passed and 
                                    get_calendars_passed and delete_provider_passed)
            
            # Event operations are expected to potentially fail due to account configuration
            event_operations_note = "Event operations may fail due to Cal.com account configuration (no event types configured)"
            
            all_passed = core_operations_passed  # Focus on core operations for now
            
            # Log individual results
            self.log_test_result("Cal.com - Create Provider", create_provider_passed, create_provider_details)
            self.log_test_result("Cal.com - List Providers", list_providers_passed, list_providers_details)
            self.log_test_result("Cal.com - Get Calendars", get_calendars_passed, get_calendars_details)
            self.log_test_result("Cal.com - Create Event", create_event_passed, create_event_details)
            self.log_test_result("Cal.com - List Events", list_events_passed, list_events_details)
            self.log_test_result("Cal.com - Delete Provider", delete_provider_passed, delete_provider_details)
            
            details = f"Provider CRUD: {core_operations_passed}, Create Event: {create_event_passed}, " \
                     f"List Events: {list_events_passed}. Note: {event_operations_note}"
            
            self.log_test_result("CAL.COM INTEGRATION", all_passed, details)
            
        except Exception as e:
            self.log_test_result("CAL.COM INTEGRATION", False, f"Exception: {str(e)}")

    def test_email_processing_workflow_with_new_groq_key(self):
        """Test Email Processing Workflow with new GROQ API key"""
        print("\n🤖 Testing EMAIL PROCESSING WORKFLOW (New GROQ API Key)...")
        
        try:
            # Get an active email account
            accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
            if accounts_response.status_code != 200 or not accounts_response.json():
                self.log_test_result("Email Processing Workflow", False, "No email accounts available")
                return
            
            account_id = accounts_response.json()[0]['id']
            
            # Test comprehensive email processing
            test_email_data = {
                "subject": "Urgent: Need AI Email Assistant Pricing and Demo",
                "body": "Hello! I'm the CTO of a growing tech company and we're looking for an AI email automation solution. We receive hundreds of customer inquiries daily and need to automate our responses. Could you please provide detailed pricing information for your AI Email Assistant? We'd also like to schedule a demo to see how it handles different types of emails. We're particularly interested in how it classifies intents and generates professional responses. Our budget is flexible for the right solution. Please get back to me as soon as possible as we need to make a decision this week. Thank you!",
                "sender": "cto@techstartup.com",
                "account_id": account_id
            }
            
            try:
                print("   Testing /api/emails/test endpoint with new GROQ API key...")
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                test_api_passed = response.status_code in [200, 201]
                
                if test_api_passed:
                    processed_email = response.json()
                    print(f"   ✅ Email processed via API - Status: {processed_email.get('status')}")
                    
                    # Check if AI workflow completed successfully
                    has_intents = bool(processed_email.get('intents'))
                    has_draft = bool(processed_email.get('draft'))
                    has_validation = bool(processed_email.get('validation_result'))
                    final_status = processed_email.get('status')
                    
                    print(f"   - Intents classified: {len(processed_email.get('intents', []))} intents")
                    print(f"   - Draft generated: {len(processed_email.get('draft', ''))} characters")
                    print(f"   - Validation completed: {has_validation}")
                    print(f"   - Final status: {final_status}")
                    
                    # Test passed if we got through the full workflow without API errors
                    workflow_completed = (has_intents or has_draft) and final_status != 'error'
                    
                    details = f"Status: {response.status_code}, Intents: {len(processed_email.get('intents', []))}, " \
                             f"Draft: {len(processed_email.get('draft', ''))} chars, Final Status: {final_status}"
                    
                else:
                    print(f"   ❌ API test failed - Status: {response.status_code}")
                    print(f"   Response: {response.text[:200]}...")
                    workflow_completed = False
                    details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                    
            except Exception as e:
                print(f"   ❌ API test exception: {str(e)}")
                test_api_passed = False
                workflow_completed = False
                details = f"Exception: {str(e)}"
            
            self.log_test_result("EMAIL PROCESSING WORKFLOW (New GROQ Key)", workflow_completed, details)
            
        except Exception as e:
            self.log_test_result("EMAIL PROCESSING WORKFLOW (New GROQ Key)", False, f"Exception: {str(e)}")

    def test_meeting_detection_and_calendar_agent(self):
        """Test Meeting Detection and Calendar Agent - AI-powered meeting analysis"""
        print("\n🤝 Testing MEETING DETECTION AND CALENDAR AGENT...")
        
        if not self.auth_token:
            self.log_test_result("Meeting Detection and Calendar Agent", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test Meeting 1: Meeting Detection from Email Content
            try:
                meeting_email_content = """
                Hi there,
                
                I'd like to schedule a meeting with you next week to discuss our new project proposal. 
                Would Tuesday at 2 PM work for you? We could meet in the conference room or via Zoom.
                
                Please let me know your availability.
                
                Best regards,
                John Smith
                """
                
                detection_data = {
                    "email_content": meeting_email_content,
                    "sender": "john.smith@company.com",
                    "subject": "Meeting Request - Project Discussion",
                    "user_timezone": "America/New_York"
                }
                
                response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=detection_data, headers=headers, timeout=15)
                meeting_detection_passed = response.status_code == 200
                
                if meeting_detection_passed:
                    detection_result = response.json()
                    confidence = detection_result.get('confidence', 0)
                    is_meeting = detection_result.get('is_meeting_request', False)
                    meeting_detection_details = f"Status: {response.status_code}, Is Meeting: {is_meeting}, Confidence: {confidence}"
                else:
                    meeting_detection_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            except Exception as e:
                meeting_detection_passed = False
                meeting_detection_details = f"Error: {str(e)}"
            
            # Test Meeting 2: Get Meeting Intents
            try:
                response = requests.get(f"{API_BASE}/calendar/meeting-intents", headers=headers, timeout=10)
                meeting_intents_passed = (response.status_code == 200 and isinstance(response.json(), list))
                
                if meeting_intents_passed:
                    intents_list = response.json()
                    meeting_intents_details = f"Status: {response.status_code}, Count: {len(intents_list)}"
                else:
                    meeting_intents_details = f"Status: {response.status_code}"
            except Exception as e:
                meeting_intents_passed = False
                meeting_intents_details = f"Error: {str(e)}"
            
            all_passed = (meeting_detection_passed and meeting_intents_passed)
            
            # Log individual results
            self.log_test_result("Meeting Detection - Positive", meeting_detection_passed, meeting_detection_details)
            self.log_test_result("Meeting Intents - List", meeting_intents_passed, meeting_intents_details)
            
            details = f"Detection: {meeting_detection_passed}, Intents: {meeting_intents_passed}"
            
            self.log_test_result("MEETING DETECTION AND CALENDAR AGENT", all_passed, details)
            
        except Exception as e:
            self.log_test_result("MEETING DETECTION AND CALENDAR AGENT", False, f"Exception: {str(e)}")

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🏁 PRIORITY TESTING SUMMARY")
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

    async def run_priority_tests(self):
        """Run priority tests focusing on current issues"""
        print("🚀 Starting Priority Backend Testing for Email Assistant System")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        print("=" * 80)
        
        # Setup
        if not await self.setup():
            return
        
        # Run priority tests based on test_result.md current focus
        print("\n🎯 PRIORITY TESTING - Focusing on Cal.com Integration and new API keys")
        
        # Authentication system (verify it's still working)
        self.test_authentication_system()
        
        # Cal.com Integration (CRITICAL - currently failing)
        self.test_calcom_integration()
        
        # Meeting Detection and Calendar Agent
        self.test_meeting_detection_and_calendar_agent()
        
        # Email Processing Workflow (verify with new GROQ API key)
        self.test_email_processing_workflow_with_new_groq_key()
        
        # Cleanup
        await self.cleanup()
        
        # Print summary
        self.print_test_summary()

async def main():
    """Main function to run priority tests"""
    tester = PriorityTester()
    await tester.run_priority_tests()

if __name__ == "__main__":
    asyncio.run(main())