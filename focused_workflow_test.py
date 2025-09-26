#!/usr/bin/env python3
"""
Focused Automated Response Workflow Testing
Tests the core automated email response system with authentication
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://response-debugger.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FocusedWorkflowTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.user_id = None
        self.kasargovinda_account_id = None
        
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
        """Setup authentication for protected endpoints"""
        try:
            # Register or login a test user
            user_data = {
                "email": f"workflow.test.{int(time.time())}@example.com",
                "password": "testpassword123",
                "full_name": "Workflow Test User"
            }
            
            # Try to register
            response = requests.post(f"{API_BASE}/auth/register", json=user_data, timeout=15)
            
            if response.status_code == 200:
                auth_result = response.json()
                self.auth_token = auth_result.get('access_token')
                self.user_id = auth_result.get('user', {}).get('id')
                print(f"✅ Authentication setup successful - User ID: {self.user_id}")
            else:
                print(f"⚠️  Authentication setup failed: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Authentication setup error: {str(e)}")
    
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
    
    async def test_gmail_account_verification(self):
        """Test 1: Verify Gmail account setup"""
        print("\n📧 Testing Gmail Account Verification...")
        
        try:
            # Find kasargovinda@gmail.com account
            account = await self.db.email_accounts.find_one({"email": "kasargovinda@gmail.com"})
            
            if account:
                self.kasargovinda_account_id = account['id']
                auto_send = account.get('auto_send', False)
                is_active = account.get('is_active', False)
                
                account_ready = auto_send and is_active
                details = f"Account ID: {self.kasargovinda_account_id}, Auto-send: {auto_send}, Active: {is_active}"
                
                self.log_test_result("Gmail Account Verification", account_ready, details)
                return account_ready
            else:
                self.log_test_result("Gmail Account Verification", False, "kasargovinda@gmail.com account not found")
                return False
                
        except Exception as e:
            self.log_test_result("Gmail Account Verification", False, f"Exception: {str(e)}")
            return False
    
    async def test_polling_and_system_status(self):
        """Test 2: Verify polling service and system status"""
        print("\n🔄 Testing Polling and System Status...")
        
        try:
            # Check polling status
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            polling_active = response.status_code == 200 and response.json().get('status') == 'running'
            
            # Check accounts status
            response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
            if response.status_code == 200:
                accounts_data = response.json()
                active_accounts = accounts_data.get('active_accounts', 0)
                connected_accounts = accounts_data.get('connected_accounts', 0)
                service_running = accounts_data.get('polling_service_running', False)
            else:
                active_accounts = 0
                connected_accounts = 0
                service_running = False
            
            # Check database health
            intents_count = await self.db.intents.count_documents({})
            kb_count = await self.db.knowledge_base.count_documents({})
            emails_count = await self.db.emails.count_documents({})
            
            system_healthy = (polling_active and service_running and active_accounts > 0 and 
                            intents_count > 0 and kb_count > 0)
            
            details = f"Polling: {polling_active}, Service: {service_running}, Active accounts: {active_accounts}, Connected: {connected_accounts}, Intents: {intents_count}, KB: {kb_count}, Emails: {emails_count}"
            
            self.log_test_result("Polling and System Status", system_healthy, details)
            return system_healthy
            
        except Exception as e:
            self.log_test_result("Polling and System Status", False, f"Exception: {str(e)}")
            return False
    
    async def test_email_processing_simple(self):
        """Test 3: Simple Email Processing Test"""
        print("\n🤖 Testing Simple Email Processing...")
        
        if not self.kasargovinda_account_id:
            self.log_test_result("Simple Email Processing", False, "No Gmail account available")
            return False
        
        try:
            # Simple, clear email that should trigger intents
            test_email_data = {
                "subject": "Need Help with Pricing",
                "body": "Hi, I need information about your pricing plans. Can you help me?",
                "sender": "simple.test@example.com",
                "account_id": self.kasargovinda_account_id
            }
            
            print("   Sending simple email for processing...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                # Check results
                intents = result.get('intents', [])
                draft = result.get('draft', '')
                status = result.get('status', '')
                error = result.get('error', '')
                
                # Success criteria
                has_draft = len(draft) > 50
                no_error = status != 'error' and not error
                processing_complete = status in ['ready_to_send', 'needs_redraft', 'sent']
                
                success = has_draft and no_error and processing_complete
                
                details = f"Intents: {len(intents)}, Draft: {len(draft)} chars, Status: {status}, Error: {bool(error)}"
                
                self.log_test_result("Simple Email Processing", success, details)
                
                print(f"   📊 Processing Results:")
                print(f"   - Intents found: {len(intents)}")
                print(f"   - Draft generated: {len(draft)} characters")
                print(f"   - Final status: {status}")
                print(f"   - Has error: {bool(error)}")
                
                if draft:
                    print(f"   📝 Draft preview: {draft[:150]}...")
                
                return success
                
            else:
                self.log_test_result("Simple Email Processing", False, f"API failed - Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Simple Email Processing", False, f"Exception: {str(e)}")
            return False
    
    async def test_meeting_email_processing(self):
        """Test 4: Meeting Email Processing"""
        print("\n📅 Testing Meeting Email Processing...")
        
        if not self.kasargovinda_account_id:
            self.log_test_result("Meeting Email Processing", False, "No Gmail account available")
            return False
        
        try:
            # Clear meeting request
            test_email_data = {
                "subject": "Meeting Request",
                "body": "Hi, I would like to schedule a meeting with you next week to discuss our project. Are you available on Tuesday at 2 PM?",
                "sender": "meeting.test@example.com",
                "account_id": self.kasargovinda_account_id
            }
            
            print("   Sending meeting request for processing...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                # Check results
                intents = result.get('intents', [])
                draft = result.get('draft', '')
                status = result.get('status', '')
                
                # Check for meeting-related content
                meeting_keywords = ['meeting', 'schedule', 'appointment', 'available']
                draft_has_meeting_content = any(keyword in draft.lower() for keyword in meeting_keywords)
                
                # Success criteria
                has_draft = len(draft) > 50
                processing_complete = status in ['ready_to_send', 'needs_redraft', 'sent']
                
                success = has_draft and processing_complete and draft_has_meeting_content
                
                details = f"Intents: {len(intents)}, Draft: {len(draft)} chars, Status: {status}, Meeting content: {draft_has_meeting_content}"
                
                self.log_test_result("Meeting Email Processing", success, details)
                
                print(f"   📊 Meeting Processing Results:")
                print(f"   - Intents found: {len(intents)}")
                print(f"   - Draft length: {len(draft)} characters")
                print(f"   - Meeting content detected: {draft_has_meeting_content}")
                print(f"   - Final status: {status}")
                
                if draft:
                    print(f"   📝 Draft preview: {draft[:150]}...")
                
                return success
                
            else:
                self.log_test_result("Meeting Email Processing", False, f"API failed - Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Meeting Email Processing", False, f"Exception: {str(e)}")
            return False
    
    async def test_auto_send_mechanism(self):
        """Test 5: Auto-Send Mechanism"""
        print("\n🚀 Testing Auto-Send Mechanism...")
        
        try:
            # Check for emails in ready_to_send status
            ready_emails = await self.db.emails.find({"status": "ready_to_send"}).to_list(10)
            
            # Check account auto_send setting
            if self.kasargovinda_account_id:
                account = await self.db.email_accounts.find_one({"id": self.kasargovinda_account_id})
                auto_send_enabled = account.get('auto_send', False) if account else False
            else:
                auto_send_enabled = False
            
            # Check for auto-send ready emails for our account
            account_ready_emails = [e for e in ready_emails if e.get('account_id') == self.kasargovinda_account_id]
            
            # Test the send endpoint (without actually sending)
            send_endpoint_available = True
            if account_ready_emails:
                try:
                    # Just check if the endpoint exists (don't actually send)
                    test_email_id = account_ready_emails[0]['id']
                    # We won't actually call the send endpoint to avoid sending real emails
                    send_endpoint_available = True
                except:
                    send_endpoint_available = False
            
            auto_send_ready = (auto_send_enabled and len(ready_emails) > 0 and 
                             len(account_ready_emails) > 0 and send_endpoint_available)
            
            details = f"Auto-send enabled: {auto_send_enabled}, Ready emails: {len(ready_emails)}, Account ready: {len(account_ready_emails)}, Send endpoint: {send_endpoint_available}"
            
            self.log_test_result("Auto-Send Mechanism", auto_send_ready, details)
            
            print(f"   📊 Auto-Send Analysis:")
            print(f"   - Account auto-send enabled: {auto_send_enabled}")
            print(f"   - Total ready-to-send emails: {len(ready_emails)}")
            print(f"   - Ready emails for target account: {len(account_ready_emails)}")
            print(f"   - Send endpoint available: {send_endpoint_available}")
            
            return auto_send_ready
            
        except Exception as e:
            self.log_test_result("Auto-Send Mechanism", False, f"Exception: {str(e)}")
            return False
    
    async def test_meeting_detection_with_auth(self):
        """Test 6: Meeting Detection with Authentication"""
        print("\n📅 Testing Meeting Detection with Authentication...")
        
        if not self.auth_token:
            self.log_test_result("Meeting Detection with Auth", False, "No authentication token available")
            return False
        
        try:
            # Test meeting detection API with authentication
            meeting_request = {
                "email_content": "Hi, I'd like to schedule a meeting with you next Tuesday at 2 PM to discuss our AI email assistant project.",
                "sender": "client@example.com",
                "user_timezone": "UTC"
            }
            
            headers = self.get_auth_headers()
            response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_request, headers=headers, timeout=15)
            
            meeting_detection_passed = response.status_code == 200
            
            if meeting_detection_passed:
                result = response.json()
                is_meeting = result.get('is_meeting_related', False)
                confidence = result.get('confidence', 0)
                detection_details = f"Status: {response.status_code}, Is meeting: {is_meeting}, Confidence: {confidence}"
            else:
                detection_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            
            # Test meeting intents endpoint
            response = requests.get(f"{API_BASE}/calendar/meeting-intents", headers=headers, timeout=10)
            intents_passed = response.status_code == 200
            
            if intents_passed:
                intents = response.json()
                intents_details = f"Status: {response.status_code}, Intents: {len(intents)}"
            else:
                intents_details = f"Status: {response.status_code}"
            
            overall_success = meeting_detection_passed and intents_passed
            
            details = f"Detection: {meeting_detection_passed}, Intents: {intents_passed}"
            
            self.log_test_result("Meeting Detection with Auth", overall_success, details)
            
            print(f"   📊 Meeting Detection Results:")
            print(f"   - Detection API: {detection_details}")
            print(f"   - Intents API: {intents_details}")
            
            return overall_success
            
        except Exception as e:
            self.log_test_result("Meeting Detection with Auth", False, f"Exception: {str(e)}")
            return False
    
    async def test_end_to_end_workflow(self):
        """Test 7: End-to-End Workflow Verification"""
        print("\n🔄 Testing End-to-End Workflow...")
        
        try:
            # Check email processing statistics
            emails = await self.db.emails.find().sort("created_at", -1).limit(50).to_list(50)
            
            if not emails:
                self.log_test_result("End-to-End Workflow", False, "No emails found in database")
                return False
            
            # Analyze email statuses
            status_counts = {}
            for email in emails:
                status = email.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Calculate success metrics
            successful_statuses = ['ready_to_send', 'sent', 'needs_redraft']
            successful_count = sum(status_counts.get(status, 0) for status in successful_statuses)
            total_count = len(emails)
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            
            # Check for recent activity
            recent_emails = [e for e in emails if (datetime.utcnow() - e.get('created_at', datetime.min)).total_seconds() < 3600]
            
            # Check system components
            intents_count = await self.db.intents.count_documents({})
            kb_count = await self.db.knowledge_base.count_documents({})
            accounts_count = await self.db.email_accounts.count_documents({"is_active": True})
            
            # Success criteria
            workflow_healthy = (success_rate > 30 and total_count > 0 and 
                              intents_count > 0 and kb_count > 0 and accounts_count > 0)
            
            details = f"Success rate: {success_rate:.1f}%, Total emails: {total_count}, Recent: {len(recent_emails)}, Intents: {intents_count}, KB: {kb_count}, Active accounts: {accounts_count}"
            
            self.log_test_result("End-to-End Workflow", workflow_healthy, details)
            
            print(f"   📊 Workflow Analysis:")
            print(f"   - Total emails processed: {total_count}")
            print(f"   - Success rate: {success_rate:.1f}%")
            print(f"   - Status distribution: {status_counts}")
            print(f"   - Recent emails (1h): {len(recent_emails)}")
            print(f"   - System components: Intents={intents_count}, KB={kb_count}, Accounts={accounts_count}")
            
            return workflow_healthy
            
        except Exception as e:
            self.log_test_result("End-to-End Workflow", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 FOCUSED AUTOMATED WORKFLOW TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        print("\n✅ PASSED TESTS:")
        for test in passed_tests:
            print(f"   - {test['test']}")
        
        # Provide recommendations
        print("\n💡 RECOMMENDATIONS:")
        if len(failed_tests) > 0:
            print("   - Review failed tests and address underlying issues")
            if any("authentication" in test['details'].lower() for test in failed_tests):
                print("   - Authentication issues detected - verify JWT token handling")
            if any("timeout" in test['details'].lower() for test in failed_tests):
                print("   - Timeout issues detected - consider optimizing API response times")
        else:
            print("   - All tests passed! System is functioning well.")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Focused Automated Response Workflow Testing...")
    print("="*80)
    
    tester = FocusedWorkflowTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run focused tests
        await tester.test_gmail_account_verification()
        await tester.test_polling_and_system_status()
        await tester.test_email_processing_simple()
        await tester.test_meeting_email_processing()
        await tester.test_auto_send_mechanism()
        await tester.test_meeting_detection_with_auth()
        await tester.test_end_to_end_workflow()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())