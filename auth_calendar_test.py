#!/usr/bin/env python3
"""
Focused Authentication and Calendar Testing
Tests the new authentication system and calendar integration features
"""
import requests
import json
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://calendar-sync-hub-3.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class AuthCalendarTester:
    def __init__(self):
        self.auth_token = None
        self.test_user_id = None
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "passed": passed,
            "details": details
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def test_authentication_system(self):
        """Test Authentication System"""
        print("\n🔐 Testing AUTHENTICATION SYSTEM...")
        
        # Test user registration
        test_email = f"test.auth.{int(time.time())}@example.com"
        register_data = {
            "email": test_email,
            "password": "TestPassword123!",
            "full_name": "Test Authentication User"
        }
        
        try:
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
            register_passed = response.status_code in [200, 201]
            if register_passed:
                register_response = response.json()
                self.auth_token = register_response.get('access_token')
                self.test_user_id = register_response.get('user', {}).get('id')
                self.log_result("Auth Registration", True, f"User ID: {self.test_user_id}")
            else:
                self.log_result("Auth Registration", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Auth Registration", False, f"Error: {str(e)}")
            return False
        
        # Test user login
        login_data = {
            "email": test_email,
            "password": "TestPassword123!"
        }
        
        try:
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=15)
            login_passed = response.status_code == 200
            self.log_result("Auth Login", login_passed, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Auth Login", False, f"Error: {str(e)}")
        
        # Test user profile
        if self.auth_token:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            try:
                response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
                profile_passed = response.status_code == 200
                if profile_passed:
                    profile_data = response.json()
                    has_quota_info = 'quota_info' in profile_data
                    self.log_result("Auth Profile", True, f"Has quota info: {has_quota_info}")
                else:
                    self.log_result("Auth Profile", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_result("Auth Profile", False, f"Error: {str(e)}")
        
        # Test JWT validation with invalid token
        try:
            invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
            response = requests.get(f"{API_BASE}/auth/me", headers=invalid_headers, timeout=10)
            jwt_validation_passed = response.status_code == 401
            self.log_result("JWT Validation", jwt_validation_passed, f"Invalid token status: {response.status_code}")
        except Exception as e:
            self.log_result("JWT Validation", False, f"Error: {str(e)}")
        
        return True
    
    def test_calendar_provider_management(self):
        """Test Calendar Provider Management"""
        print("\n📅 Testing CALENDAR PROVIDER MANAGEMENT...")
        
        if not self.auth_token:
            self.log_result("Calendar Provider Management", False, "No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test create calendar provider
        provider_data = {
            "provider_type": "google",
            "provider_name": "Test Google Calendar",
            "credentials": {
                "client_id": "test_client_id_12345",
                "client_secret": "test_client_secret_67890"
            },
            "timezone": "UTC"
        }
        
        try:
            response = requests.post(f"{API_BASE}/calendar/providers", json=provider_data, headers=headers, timeout=15)
            create_passed = response.status_code in [200, 201]
            if create_passed:
                created_provider = response.json()
                provider_id = created_provider.get('id')
                self.log_result("Calendar Provider Create", True, f"Provider ID: {provider_id}")
                
                # Test list providers
                response = requests.get(f"{API_BASE}/calendar/providers", headers=headers, timeout=10)
                list_passed = response.status_code == 200
                if list_passed:
                    providers_list = response.json()
                    self.log_result("Calendar Provider List", True, f"Count: {len(providers_list)}")
                else:
                    self.log_result("Calendar Provider List", False, f"Status: {response.status_code}")
                
                # Test get calendars
                response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
                calendars_passed = response.status_code == 200
                if calendars_passed:
                    calendars_data = response.json()
                    self.log_result("Calendar Get Calendars", True, f"Providers: {len(calendars_data)}")
                else:
                    self.log_result("Calendar Get Calendars", False, f"Status: {response.status_code}")
                
                # Test delete provider
                response = requests.delete(f"{API_BASE}/calendar/providers/{provider_id}", headers=headers, timeout=10)
                delete_passed = response.status_code in [200, 204]
                self.log_result("Calendar Provider Delete", delete_passed, f"Status: {response.status_code}")
                
                return True
            else:
                self.log_result("Calendar Provider Create", False, f"Status: {response.status_code}, Error: {response.text[:200]}")
                return False
        except Exception as e:
            self.log_result("Calendar Provider Create", False, f"Error: {str(e)}")
            return False
    
    def test_calendar_operations(self):
        """Test Calendar Operations"""
        print("\n🗓️ Testing CALENDAR OPERATIONS...")
        
        if not self.auth_token:
            self.log_result("Calendar Operations", False, "No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Setup: Create a test provider
        provider_data = {
            "provider_type": "google",
            "provider_name": "Test Calendar Operations",
            "credentials": {
                "client_id": "test_operations_client",
                "client_secret": "test_operations_secret"
            },
            "timezone": "UTC"
        }
        
        setup_response = requests.post(f"{API_BASE}/calendar/providers", json=provider_data, headers=headers, timeout=15)
        if setup_response.status_code not in [200, 201]:
            self.log_result("Calendar Operations Setup", False, "Failed to create test provider")
            return False
        
        provider_id = setup_response.json().get('id')
        calendar_id = "primary"  # Mock service uses 'primary' as default calendar
        
        # Test create event
        event_start = datetime.utcnow() + timedelta(hours=2)
        event_end = event_start + timedelta(hours=1)
        
        event_data = {
            "title": "Test Calendar Event",
            "description": "This is a test event for calendar operations testing",
            "start_time": event_start.isoformat() + "Z",
            "end_time": event_end.isoformat() + "Z",
            "timezone": "UTC",
            "location": "Test Location",
            "attendees": ["test1@example.com", "test2@example.com"]
        }
        
        try:
            response = requests.post(f"{API_BASE}/calendar/providers/{provider_id}/calendars/{calendar_id}/events", 
                                   json=event_data, headers=headers, timeout=15)
            create_event_passed = response.status_code in [200, 201]
            if create_event_passed:
                created_event = response.json()
                event_id = created_event.get('id')
                self.log_result("Calendar Event Create", True, f"Event ID: {event_id}")
                
                # Test get events
                response = requests.get(f"{API_BASE}/calendar/providers/{provider_id}/calendars/{calendar_id}/events", 
                                      headers=headers, timeout=10)
                get_events_passed = response.status_code == 200
                if get_events_passed:
                    events_list = response.json()
                    self.log_result("Calendar Event Get", True, f"Events count: {len(events_list)}")
                else:
                    self.log_result("Calendar Event Get", False, f"Status: {response.status_code}")
                
                # Test update event
                if event_id:
                    update_data = {
                        "title": "Updated Test Calendar Event",
                        "description": "This event has been updated"
                    }
                    
                    response = requests.put(f"{API_BASE}/calendar/providers/{provider_id}/calendars/{calendar_id}/events/{event_id}", 
                                          json=update_data, headers=headers, timeout=15)
                    update_passed = response.status_code == 200
                    self.log_result("Calendar Event Update", update_passed, f"Status: {response.status_code}")
                    
                    # Test delete event
                    response = requests.delete(f"{API_BASE}/calendar/providers/{provider_id}/calendars/{calendar_id}/events/{event_id}", 
                                             headers=headers, timeout=10)
                    delete_passed = response.status_code in [200, 204]
                    self.log_result("Calendar Event Delete", delete_passed, f"Status: {response.status_code}")
                
            else:
                self.log_result("Calendar Event Create", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Calendar Event Create", False, f"Error: {str(e)}")
        
        # Cleanup: Delete test provider
        try:
            requests.delete(f"{API_BASE}/calendar/providers/{provider_id}", headers=headers, timeout=10)
        except:
            pass
        
        return True
    
    def test_meeting_detection(self):
        """Test Meeting Detection and Calendar Agent"""
        print("\n🤖 Testing MEETING DETECTION AND CALENDAR AGENT...")
        
        if not self.auth_token:
            self.log_result("Meeting Detection", False, "No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test meeting detection
        meeting_detection_data = {
            "email_content": "Hi there! I'd like to schedule a meeting with you tomorrow at 2:00 PM to discuss our project. We can meet in the conference room or via Zoom. Let me know if this works for you. Thanks!",
            "sender": "colleague@company.com",
            "subject": "Meeting Request - Project Discussion",
            "user_timezone": "UTC"
        }
        
        try:
            response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_detection_data, headers=headers, timeout=30)
            detect_passed = response.status_code == 200
            if detect_passed:
                detection_result = response.json()
                meeting_detected = detection_result.get('meeting_detected', False)
                confidence = detection_result.get('confidence_score', 0.0)
                self.log_result("Meeting Detection", True, f"Detected: {meeting_detected}, Confidence: {confidence:.2f}")
            else:
                self.log_result("Meeting Detection", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Meeting Detection", False, f"Error: {str(e)}")
        
        # Test get meeting intents
        try:
            response = requests.get(f"{API_BASE}/calendar/meeting-intents", headers=headers, timeout=10)
            intents_passed = response.status_code == 200
            if intents_passed:
                intents_list = response.json()
                self.log_result("Meeting Intents List", True, f"Intents count: {len(intents_list)}")
            else:
                self.log_result("Meeting Intents List", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Meeting Intents List", False, f"Error: {str(e)}")
        
        # Test no meeting detection
        try:
            no_meeting_data = {
                "email_content": "Thanks for the information. I'll review the documents and get back to you soon. Have a great day!",
                "sender": "colleague@company.com",
                "subject": "Re: Document Review",
                "user_timezone": "UTC"
            }
            
            response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=no_meeting_data, headers=headers, timeout=30)
            no_meeting_passed = response.status_code == 200
            if no_meeting_passed:
                no_meeting_result = response.json()
                no_meeting_detected = not no_meeting_result.get('meeting_detected', True)
                self.log_result("No Meeting Detection", True, f"Correctly detected no meeting: {no_meeting_detected}")
            else:
                self.log_result("No Meeting Detection", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("No Meeting Detection", False, f"Error: {str(e)}")
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("📊 AUTHENTICATION & CALENDAR TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📈 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        print("\n📋 DETAILED RESULTS:")
        for test in self.test_results:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"   {status}: {test['test']}")
            if test['details']:
                print(f"      {test['details']}")
        
        print("\n" + "="*80)

def main():
    """Main test function"""
    print("🚀 Starting Authentication & Calendar System Tests")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print("="*80)
    
    tester = AuthCalendarTester()
    
    try:
        # Run authentication tests
        if tester.test_authentication_system():
            # Run calendar tests
            tester.test_calendar_provider_management()
            tester.test_calendar_operations()
            tester.test_meeting_detection()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Critical error in test execution: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()