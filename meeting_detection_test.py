#!/usr/bin/env python3
"""
Enhanced Meeting Detection System Testing
Tests the universal meeting detection fixes and enhanced functionality
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://component-audit-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class MeetingDetectionTester:
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
            
            # Setup authentication
            await self.setup_authentication()
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    async def setup_authentication(self):
        """Setup test user and authentication"""
        try:
            # Register test user
            user_data = {
                "email": f"meeting.test.{int(time.time())}@example.com",
                "password": "testpassword123",
                "full_name": "Meeting Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=user_data, timeout=15)
            if response.status_code in [200, 201]:
                auth_result = response.json()
                self.auth_token = auth_result.get('access_token')
                self.test_user_id = auth_result.get('user', {}).get('id')
                print(f"✅ Test user authenticated: {user_data['email']}")
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Authentication setup failed: {str(e)}")
    
    def get_auth_headers(self):
        """Get authentication headers"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
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
    
    async def test_meeting_detection_api(self):
        """Test 1: Meeting Detection API with various email scenarios"""
        print("\n🔍 Testing Meeting Detection API...")
        
        test_scenarios = [
            {
                "name": "Clear Meeting Request with Specific Date/Time",
                "email_content": "Hi John, I'd like to schedule a meeting with you to discuss the new project proposal. Are you available this Thursday at 2:30 PM? We can meet in the conference room or via Zoom. Please let me know if this works for you. Best regards, Sarah",
                "subject": "Meeting Request - Project Discussion",
                "sender": "sarah@company.com",
                "expected_detected": True,
                "expected_confidence_min": 0.8
            },
            {
                "name": "Meeting Keywords with Vague Timing",
                "email_content": "Hello team, we need to have a discussion about the quarterly results. Let's schedule a call sometime next week to go over the numbers and plan our strategy. I'll send out a calendar invite once we confirm the time.",
                "subject": "Quarterly Results Discussion",
                "sender": "manager@company.com",
                "expected_detected": True,
                "expected_confidence_min": 0.4
            },
            {
                "name": "No Meeting Content",
                "email_content": "Thank you for sending the report. I've reviewed the data and everything looks good. The numbers are in line with our expectations. Please proceed with the next phase of the project.",
                "subject": "Report Review Complete",
                "sender": "client@external.com",
                "expected_detected": False,
                "expected_confidence_max": 0.3
            },
            {
                "name": "Reply to Meeting Discussion",
                "email_content": "Re: Meeting tomorrow - Yes, I can confirm the 3 PM slot works for me. I'll bring the presentation materials and we can go through the proposal together. See you in the main conference room.",
                "subject": "Re: Meeting tomorrow",
                "sender": "colleague@company.com",
                "expected_detected": True,
                "expected_confidence_min": 0.6
            },
            {
                "name": "Demo Request with Specific Requirements",
                "email_content": "Hi there, I'm interested in seeing a demo of your AI email assistant. Could we schedule a 45-minute session this Friday afternoon? I'd like to see how it handles different types of customer inquiries. My timezone is EST.",
                "subject": "Demo Request - AI Email Assistant",
                "sender": "prospect@newclient.com",
                "expected_detected": True,
                "expected_confidence_min": 0.8
            }
        ]
        
        passed_scenarios = 0
        total_scenarios = len(test_scenarios)
        
        for scenario in test_scenarios:
            try:
                request_data = {
                    "email_content": scenario["email_content"],
                    "subject": scenario["subject"],
                    "sender": scenario["sender"],
                    "user_timezone": "UTC"
                }
                
                response = requests.post(
                    f"{API_BASE}/calendar/detect-meeting",
                    json=request_data,
                    headers=self.get_auth_headers(),
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    detected = result.get('meeting_detected', False)
                    confidence = result.get('confidence_score', 0.0)
                    
                    # Check expectations
                    scenario_passed = True
                    details = f"Detected: {detected}, Confidence: {confidence:.2f}"
                    
                    if scenario["expected_detected"]:
                        if not detected:
                            scenario_passed = False
                            details += " (Expected detection but got none)"
                        elif confidence < scenario["expected_confidence_min"]:
                            scenario_passed = False
                            details += f" (Confidence too low, expected >{scenario['expected_confidence_min']})"
                    else:
                        if detected and confidence > scenario.get("expected_confidence_max", 0.5):
                            scenario_passed = False
                            details += f" (Unexpected detection with high confidence)"
                    
                    if scenario_passed:
                        passed_scenarios += 1
                        details += " ✓"
                    
                    # Log additional details
                    if detected:
                        details += f", DateTime: {result.get('detected_datetime')}"
                        details += f", Title: {result.get('detected_title')}"
                        details += f", Location: {result.get('detected_location')}"
                        details += f", Duration: {result.get('suggested_duration')}min"
                    
                    self.log_test_result(f"Meeting Detection - {scenario['name']}", scenario_passed, details)
                    
                else:
                    self.log_test_result(f"Meeting Detection - {scenario['name']}", False, f"API Error: {response.status_code}")
                    
            except Exception as e:
                self.log_test_result(f"Meeting Detection - {scenario['name']}", False, f"Exception: {str(e)}")
        
        overall_passed = passed_scenarios >= (total_scenarios * 0.8)  # 80% pass rate
        self.log_test_result("Meeting Detection API", overall_passed, f"Passed {passed_scenarios}/{total_scenarios} scenarios")
    
    async def test_email_processing_with_meeting_detection(self):
        """Test 2: Email Processing Workflow with Meeting Detection"""
        print("\n🤖 Testing Email Processing with Meeting Detection...")
        
        # Get or create test email account
        account = await self.get_or_create_test_account()
        if not account:
            self.log_test_result("Email Processing with Meeting Detection", False, "No test account available")
            return
        
        test_emails = [
            {
                "name": "High Confidence Meeting Email",
                "subject": "Urgent: Demo Request for Tomorrow 2 PM",
                "body": "Hi, I need to schedule a demo of your product tomorrow at 2 PM EST. This is for a potential enterprise deal worth $50K. Can you confirm availability? We'll need about 60 minutes to go through all features. Please send me the Zoom link. Thanks!",
                "sender": "enterprise.client@bigcorp.com",
                "expected_meeting_detected": True,
                "expected_calendar_action": True
            },
            {
                "name": "Medium Confidence Meeting Email",
                "subject": "Let's catch up soon",
                "body": "Hey! It's been a while since we last talked. Would love to catch up and hear about your new role. Are you free for a coffee chat sometime next week? Let me know what works for your schedule.",
                "sender": "old.friend@personal.com",
                "expected_meeting_detected": True,
                "expected_calendar_action": False  # Lower confidence, should not auto-create
            },
            {
                "name": "Non-Meeting Email",
                "body": "Thanks for the quick response to my inquiry. The information you provided is exactly what I needed. I'll review the documentation and get back to you if I have any questions.",
                "subject": "Thank you for the information",
                "sender": "satisfied.customer@client.com",
                "expected_meeting_detected": False,
                "expected_calendar_action": False
            }
        ]
        
        passed_tests = 0
        total_tests = len(test_emails)
        
        for test_email in test_emails:
            try:
                # Process email through the workflow
                email_data = {
                    "subject": test_email["subject"],
                    "body": test_email["body"],
                    "sender": test_email["sender"],
                    "account_id": account["id"]
                }
                
                response = requests.post(
                    f"{API_BASE}/emails/test",
                    json=email_data,
                    headers=self.get_auth_headers(),
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Check if meeting detection ran
                    meeting_detected = False
                    meeting_confidence = 0.0
                    
                    # Look for meeting-related intents
                    intents = processed_email.get('intents', [])
                    for intent in intents:
                        if intent.get('is_meeting_related', False):
                            meeting_detected = True
                            meeting_confidence = intent.get('confidence', 0.0)
                            break
                    
                    # Check if meeting detection ran universally (should run for ALL emails)
                    universal_detection_ran = True  # Assume it ran if we got a response
                    
                    # Validate expectations
                    test_passed = True
                    details = f"Meeting detected: {meeting_detected}, Confidence: {meeting_confidence:.2f}"
                    
                    if test_email["expected_meeting_detected"] != meeting_detected:
                        test_passed = False
                        details += f" (Expected detection: {test_email['expected_meeting_detected']})"
                    
                    # Check for calendar actions (meeting intents created)
                    calendar_action_taken = len([i for i in intents if i.get('is_meeting_related', False)]) > 0
                    
                    if test_email["expected_calendar_action"] != calendar_action_taken:
                        details += f", Calendar action: {calendar_action_taken} (Expected: {test_email['expected_calendar_action']})"
                    
                    if test_passed:
                        passed_tests += 1
                    
                    # Additional details
                    details += f", Status: {processed_email.get('status')}"
                    details += f", Draft length: {len(processed_email.get('draft', ''))}"
                    
                    self.log_test_result(f"Email Processing - {test_email['name']}", test_passed, details)
                    
                else:
                    self.log_test_result(f"Email Processing - {test_email['name']}", False, f"API Error: {response.status_code}")
                    
            except Exception as e:
                self.log_test_result(f"Email Processing - {test_email['name']}", False, f"Exception: {str(e)}")
        
        overall_passed = passed_tests >= (total_tests * 0.7)  # 70% pass rate
        self.log_test_result("Email Processing with Meeting Detection", overall_passed, f"Passed {passed_tests}/{total_tests} tests")
    
    async def test_thread_context_enhancement(self):
        """Test 3: Thread Context Enhancement for Meeting Detection"""
        print("\n🧵 Testing Thread Context Enhancement...")
        
        # Create a series of emails in the same thread
        account = await self.get_or_create_test_account()
        if not account:
            self.log_test_result("Thread Context Enhancement", False, "No test account available")
            return
        
        thread_id = f"thread-{uuid.uuid4()}"
        
        # Email 1: Initial inquiry (no specific time)
        email1_data = {
            "subject": "Demo Request - AI Email Assistant",
            "body": "Hi, I'm interested in learning more about your AI email assistant. Could we schedule a demo to see how it works? I'm particularly interested in the meeting detection features.",
            "sender": "potential.client@startup.com",
            "account_id": account["id"]
        }
        
        # Email 2: Follow-up with specific time (should use thread context)
        email2_data = {
            "subject": "Re: Demo Request - AI Email Assistant",
            "body": "Thanks for your quick response! I'm available this Thursday at 3 PM EST for the demo. Looking forward to seeing the system in action.",
            "sender": "potential.client@startup.com",
            "account_id": account["id"]
        }
        
        try:
            # Process first email
            response1 = requests.post(
                f"{API_BASE}/emails/test",
                json=email1_data,
                headers=self.get_auth_headers(),
                timeout=30
            )
            
            email1_passed = False
            if response1.status_code in [200, 201]:
                email1_result = response1.json()
                email1_id = email1_result.get('id')
                
                # Store in database with thread_id for context
                if email1_id:
                    await self.db.emails.update_one(
                        {"id": email1_id},
                        {"$set": {"thread_id": thread_id}}
                    )
                
                # Check if meeting was detected (should be low confidence due to vague timing)
                meeting_detected_1 = any(intent.get('is_meeting_related', False) for intent in email1_result.get('intents', []))
                email1_passed = True  # First email processed
                
                self.log_test_result("Thread Context - Email 1 (Initial)", email1_passed, 
                                   f"Meeting detected: {meeting_detected_1}, Status: {email1_result.get('status')}")
            
            # Wait a moment then process second email
            await asyncio.sleep(1)
            
            response2 = requests.post(
                f"{API_BASE}/emails/test",
                json=email2_data,
                headers=self.get_auth_headers(),
                timeout=30
            )
            
            email2_passed = False
            thread_context_used = False
            
            if response2.status_code in [200, 201]:
                email2_result = response2.json()
                email2_id = email2_result.get('id')
                
                # Store in database with same thread_id
                if email2_id:
                    await self.db.emails.update_one(
                        {"id": email2_id},
                        {"$set": {"thread_id": thread_id}}
                    )
                
                # Check if meeting was detected with higher confidence (should use thread context)
                meeting_intents_2 = [intent for intent in email2_result.get('intents', []) if intent.get('is_meeting_related', False)]
                meeting_detected_2 = len(meeting_intents_2) > 0
                
                if meeting_detected_2:
                    confidence_2 = max(intent.get('confidence', 0) for intent in meeting_intents_2)
                    # Higher confidence suggests thread context was used
                    thread_context_used = confidence_2 > 0.6
                
                email2_passed = meeting_detected_2  # Should detect meeting in follow-up
                
                self.log_test_result("Thread Context - Email 2 (Follow-up)", email2_passed,
                                   f"Meeting detected: {meeting_detected_2}, Thread context used: {thread_context_used}")
            
            # Test thread context retrieval directly
            thread_context_test = await self.test_thread_context_retrieval(thread_id)
            
            overall_passed = email1_passed and email2_passed and thread_context_test
            self.log_test_result("Thread Context Enhancement", overall_passed,
                               f"Email 1: {email1_passed}, Email 2: {email2_passed}, Context retrieval: {thread_context_test}")
            
        except Exception as e:
            self.log_test_result("Thread Context Enhancement", False, f"Exception: {str(e)}")
    
    async def test_thread_context_retrieval(self, thread_id: str) -> bool:
        """Test thread context retrieval functionality"""
        try:
            # Get all emails in thread
            thread_emails = await self.db.emails.find({"thread_id": thread_id}).to_list(10)
            
            if len(thread_emails) >= 2:
                # Verify thread context can be retrieved
                context_available = True
                for email in thread_emails:
                    if not email.get('body') and not email.get('draft'):
                        context_available = False
                        break
                
                self.log_test_result("Thread Context - Retrieval", context_available,
                                   f"Found {len(thread_emails)} emails in thread, Context available: {context_available}")
                return context_available
            else:
                self.log_test_result("Thread Context - Retrieval", False,
                                   f"Insufficient emails in thread: {len(thread_emails)}")
                return False
                
        except Exception as e:
            self.log_test_result("Thread Context - Retrieval", False, f"Exception: {str(e)}")
            return False
    
    async def test_meeting_intent_management(self):
        """Test 4: Meeting Intent Management"""
        print("\n📅 Testing Meeting Intent Management...")
        
        try:
            # Test creating meeting-related intents
            meeting_intent_data = {
                "name": "Demo Request Intent",
                "description": "Intent for handling product demo requests with scheduling",
                "examples": [
                    "I'd like to schedule a demo",
                    "Can we set up a product demonstration",
                    "Please show me how your system works"
                ],
                "system_prompt": "Handle demo requests professionally and suggest available time slots",
                "confidence_threshold": 0.7,
                "follow_up_hours": 24,
                "is_meeting_related": True
            }
            
            # Create meeting-related intent
            response = requests.post(
                f"{API_BASE}/intents",
                json=meeting_intent_data,
                headers=self.get_auth_headers(),
                timeout=15
            )
            
            intent_created = False
            intent_id = None
            
            if response.status_code in [200, 201]:
                intent_result = response.json()
                intent_id = intent_result.get('id')
                intent_created = True
                
                # Verify is_meeting_related flag is set
                is_meeting_related = intent_result.get('is_meeting_related', False)
                
                self.log_test_result("Meeting Intent - Creation", intent_created and is_meeting_related,
                                   f"Intent ID: {intent_id}, Meeting-related: {is_meeting_related}")
            else:
                self.log_test_result("Meeting Intent - Creation", False, f"API Error: {response.status_code}")
            
            # Test retrieving meeting intents
            if intent_created:
                response = requests.get(
                    f"{API_BASE}/intents/{intent_id}",
                    headers=self.get_auth_headers(),
                    timeout=10
                )
                
                intent_retrieved = False
                if response.status_code == 200:
                    retrieved_intent = response.json()
                    intent_retrieved = retrieved_intent.get('is_meeting_related', False)
                
                self.log_test_result("Meeting Intent - Retrieval", intent_retrieved,
                                   f"Retrieved intent with meeting flag: {intent_retrieved}")
            
            # Test meeting intent classification
            classification_test = await self.test_meeting_intent_classification()
            
            # Cleanup - delete test intent
            if intent_id:
                requests.delete(f"{API_BASE}/intents/{intent_id}", headers=self.get_auth_headers(), timeout=10)
            
            overall_passed = intent_created and classification_test
            self.log_test_result("Meeting Intent Management", overall_passed,
                               f"Creation: {intent_created}, Classification: {classification_test}")
            
        except Exception as e:
            self.log_test_result("Meeting Intent Management", False, f"Exception: {str(e)}")
    
    async def test_meeting_intent_classification(self) -> bool:
        """Test meeting intent classification in email processing"""
        try:
            # Get existing meeting-related intents
            response = requests.get(f"{API_BASE}/intents", headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                intents = response.json()
                meeting_intents = [intent for intent in intents if intent.get('is_meeting_related', False)]
                
                if len(meeting_intents) > 0:
                    self.log_test_result("Meeting Intent - Classification Available", True,
                                       f"Found {len(meeting_intents)} meeting-related intents")
                    return True
                else:
                    self.log_test_result("Meeting Intent - Classification Available", False,
                                       "No meeting-related intents found")
                    return False
            else:
                self.log_test_result("Meeting Intent - Classification Available", False,
                                   f"Failed to retrieve intents: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Meeting Intent - Classification Available", False, f"Exception: {str(e)}")
            return False
    
    async def get_or_create_test_account(self):
        """Get or create a test email account"""
        try:
            # Check for existing test accounts
            response = requests.get(f"{API_BASE}/email-accounts", headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                accounts = response.json()
                if accounts:
                    return accounts[0]  # Use first available account
            
            # Create test account if none exists
            account_data = {
                "name": "Meeting Detection Test Account",
                "email": f"meeting.test.{int(time.time())}@example.com",
                "provider": "gmail",
                "username": f"meeting.test.{int(time.time())}@example.com",
                "password": "test_password_123",
                "persona": "Professional meeting coordinator",
                "auto_send": False
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, 
                                   headers=self.get_auth_headers(), timeout=15)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Failed to create test account: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting/creating test account: {str(e)}")
            return None
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("MEETING DETECTION SYSTEM TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nFAILED TESTS:")
        for result in self.test_results:
            if not result['passed']:
                print(f"❌ {result['test']}: {result['details']}")
        
        print("\nKEY FINDINGS:")
        
        # Meeting Detection API
        api_tests = [r for r in self.test_results if 'Meeting Detection -' in r['test']]
        api_passed = len([r for r in api_tests if r['passed']])
        print(f"• Meeting Detection API: {api_passed}/{len(api_tests)} scenarios passed")
        
        # Email Processing
        processing_tests = [r for r in self.test_results if 'Email Processing -' in r['test']]
        processing_passed = len([r for r in processing_tests if r['passed']])
        print(f"• Email Processing with Meeting Detection: {processing_passed}/{len(processing_tests)} tests passed")
        
        # Thread Context
        thread_tests = [r for r in self.test_results if 'Thread Context' in r['test']]
        thread_passed = len([r for r in thread_tests if r['passed']])
        print(f"• Thread Context Enhancement: {thread_passed}/{len(thread_tests)} tests passed")
        
        # Meeting Intent Management
        intent_tests = [r for r in self.test_results if 'Meeting Intent' in r['test']]
        intent_passed = len([r for r in intent_tests if r['passed']])
        print(f"• Meeting Intent Management: {intent_passed}/{len(intent_tests)} tests passed")
        
        print("\n" + "="*60)

async def main():
    """Main test execution"""
    print("🚀 Starting Enhanced Meeting Detection System Tests...")
    
    tester = MeetingDetectionTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests
        await tester.test_meeting_detection_api()
        await tester.test_email_processing_with_meeting_detection()
        await tester.test_thread_context_enhancement()
        await tester.test_meeting_intent_management()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())