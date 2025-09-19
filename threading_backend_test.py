#!/usr/bin/env python3
"""
Threading Functionality Backend Testing
Tests the new threading functionality comprehensively including:
1. /api/emails/threads endpoint
2. Response detection logic
3. Follow-up creation with response detection
4. Enhanced email processing workflow with response detection
5. Thread continuity verification
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://thread-continuity.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class ThreadingTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.test_thread_id = None
        self.test_email_ids = []
        self.test_follow_up_ids = []
        
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
        """Cleanup test data and resources"""
        try:
            # Clean up test emails
            if self.test_email_ids:
                await self.db.emails.delete_many({"id": {"$in": self.test_email_ids}})
                print(f"🧹 Cleaned up {len(self.test_email_ids)} test emails")
            
            # Clean up test follow-ups
            if self.test_follow_up_ids:
                await self.db.follow_up_emails.delete_many({"id": {"$in": self.test_follow_up_ids}})
                print(f"🧹 Cleaned up {len(self.test_follow_up_ids)} test follow-ups")
            
            # Clean up test thread
            if self.test_thread_id:
                await self.db.emails.delete_many({"thread_id": self.test_thread_id})
                await self.db.follow_up_emails.delete_many({"thread_id": self.test_thread_id})
                print(f"🧹 Cleaned up test thread: {self.test_thread_id}")
                
            if self.client:
                self.client.close()
        except Exception as e:
            print(f"⚠️ Cleanup error: {str(e)}")
    
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
    
    async def test_threads_endpoint(self):
        """Test 1: /api/emails/threads endpoint functionality"""
        print("\n🧵 Testing /api/emails/threads endpoint...")
        
        try:
            # First, create test thread data
            await self.create_test_thread_data()
            
            # Test 1a: GET /api/emails/threads - Basic functionality
            try:
                response = requests.get(f"{API_BASE}/emails/threads", timeout=15)
                basic_passed = response.status_code == 200
                
                if basic_passed:
                    threads_data = response.json()
                    basic_details = f"Status: {response.status_code}, Threads count: {len(threads_data)}"
                    
                    # Verify response structure
                    if threads_data:
                        sample_thread = threads_data[0]
                        required_fields = ['thread_id', 'subject', 'participants', 'original_email', 
                                         'follow_ups', 'responses', 'has_response', 'follow_ups_active']
                        structure_valid = all(field in sample_thread for field in required_fields)
                        basic_details += f", Structure valid: {structure_valid}"
                        basic_passed = basic_passed and structure_valid
                else:
                    basic_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    
            except Exception as e:
                basic_passed = False
                basic_details = f"Error: {str(e)}"
            
            # Test 1b: Verify thread grouping by thread_id
            thread_grouping_passed = False
            if basic_passed:
                try:
                    # Find our test thread in the response
                    test_thread = None
                    for thread in threads_data:
                        if thread['thread_id'] == self.test_thread_id:
                            test_thread = thread
                            break
                    
                    if test_thread:
                        # Verify original email and responses are properly grouped
                        original_email = test_thread['original_email']
                        responses = test_thread['responses']
                        follow_ups = test_thread['follow_ups']
                        
                        thread_grouping_passed = (
                            original_email['thread_id'] == self.test_thread_id and
                            len(responses) >= 1 and  # Should have at least one response
                            all(r['thread_id'] == self.test_thread_id for r in responses) and
                            len(follow_ups) >= 0  # May or may not have follow-ups
                        )
                        grouping_details = f"Original email thread_id: {original_email['thread_id']}, Responses: {len(responses)}, Follow-ups: {len(follow_ups)}"
                    else:
                        grouping_details = f"Test thread {self.test_thread_id} not found in response"
                        
                except Exception as e:
                    grouping_details = f"Error: {str(e)}"
            else:
                grouping_details = "Skipped - basic test failed"
            
            # Test 1c: Verify response detection in thread structure
            response_detection_passed = False
            if test_thread:
                try:
                    has_response = test_thread['has_response']
                    follow_ups_active = test_thread['follow_ups_active']
                    participants = test_thread['participants']
                    
                    # Should detect response and deactivate follow-ups
                    response_detection_passed = (
                        has_response == True and  # Should detect our test response
                        follow_ups_active == False and  # Should deactivate follow-ups
                        len(participants) >= 2  # Should have multiple participants
                    )
                    detection_details = f"Has response: {has_response}, Follow-ups active: {follow_ups_active}, Participants: {len(participants)}"
                    
                except Exception as e:
                    detection_details = f"Error: {str(e)}"
            else:
                detection_details = "Skipped - test thread not found"
            
            all_passed = basic_passed and thread_grouping_passed and response_detection_passed
            
            # Log individual results
            self.log_test_result("Threads Endpoint - Basic Functionality", basic_passed, basic_details)
            self.log_test_result("Threads Endpoint - Thread Grouping", thread_grouping_passed, grouping_details)
            self.log_test_result("Threads Endpoint - Response Detection", response_detection_passed, detection_details)
            
            overall_details = f"Basic: {basic_passed}, Grouping: {thread_grouping_passed}, Detection: {response_detection_passed}"
            self.log_test_result("Threads Endpoint Functionality", all_passed, overall_details)
            
        except Exception as e:
            self.log_test_result("Threads Endpoint Functionality", False, f"Exception: {str(e)}")
    
    async def test_response_detection_logic(self):
        """Test 2: Response detection logic"""
        print("\n🔍 Testing Response Detection Logic...")
        
        try:
            # Test 2a: Create a new thread without responses
            new_thread_id = f"test-thread-{uuid.uuid4()}"
            await self.create_single_email_thread(new_thread_id)
            
            # Verify no response detected initially
            initial_check_passed = await self.verify_no_response_detected(new_thread_id)
            
            # Test 2b: Add a response from different sender
            response_email_id = await self.add_response_to_thread(new_thread_id)
            
            # Wait a moment for response detection service to process
            await asyncio.sleep(2)
            
            # Test 2c: Verify response detection worked
            response_detected_passed = await self.verify_response_detected(new_thread_id)
            
            # Test 2d: Verify follow-ups were cancelled
            follow_ups_cancelled_passed = await self.verify_follow_ups_cancelled(new_thread_id)
            
            all_passed = initial_check_passed and response_detected_passed and follow_ups_cancelled_passed
            
            # Log individual results
            self.log_test_result("Response Detection - Initial State", initial_check_passed, 
                               "Thread initially has no responses")
            self.log_test_result("Response Detection - Response Added", response_detected_passed, 
                               "Response from different sender detected")
            self.log_test_result("Response Detection - Follow-ups Cancelled", follow_ups_cancelled_passed, 
                               "Pending follow-ups cancelled after response")
            
            overall_details = f"Initial: {initial_check_passed}, Detected: {response_detected_passed}, Cancelled: {follow_ups_cancelled_passed}"
            self.log_test_result("Response Detection Logic", all_passed, overall_details)
            
            # Cleanup this test thread
            await self.db.emails.delete_many({"thread_id": new_thread_id})
            await self.db.follow_up_emails.delete_many({"thread_id": new_thread_id})
            
        except Exception as e:
            self.log_test_result("Response Detection Logic", False, f"Exception: {str(e)}")
    
    async def test_follow_up_creation_with_response_detection(self):
        """Test 3: Follow-up creation with response detection integration"""
        print("\n📅 Testing Follow-up Creation with Response Detection...")
        
        try:
            # Get an active email account for testing
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Follow-up Creation with Response Detection", False, 
                                   "No active email accounts found")
                return
            
            # Test 3a: Create email that should trigger follow-ups
            test_thread_id = f"followup-test-{uuid.uuid4()}"
            original_email_id = await self.create_email_for_follow_up_test(test_thread_id, account['id'])
            
            # Test 3b: Verify follow-ups were created with correct thread_id
            follow_ups_created_passed = await self.verify_follow_ups_created(original_email_id, test_thread_id)
            
            # Test 3c: Simulate response and check follow-ups are cancelled
            response_email_id = await self.add_response_to_thread(test_thread_id, different_sender=True)
            
            # Wait for response detection service
            await asyncio.sleep(3)
            
            # Test 3d: Verify follow-ups were cancelled due to response
            follow_ups_cancelled_after_response = await self.verify_follow_ups_cancelled(test_thread_id)
            
            # Test 3e: Verify thread continuity - same thread_id maintained
            thread_continuity_passed = await self.verify_thread_continuity(test_thread_id, [original_email_id, response_email_id])
            
            all_passed = (follow_ups_created_passed and follow_ups_cancelled_after_response and 
                         thread_continuity_passed)
            
            # Log individual results
            self.log_test_result("Follow-up Creation - Initial Creation", follow_ups_created_passed, 
                               "Follow-ups created with correct thread_id")
            self.log_test_result("Follow-up Creation - Response Cancellation", follow_ups_cancelled_after_response, 
                               "Follow-ups cancelled when response detected")
            self.log_test_result("Follow-up Creation - Thread Continuity", thread_continuity_passed, 
                               "Thread_id maintained across emails and follow-ups")
            
            overall_details = f"Created: {follow_ups_created_passed}, Cancelled: {follow_ups_cancelled_after_response}, Continuity: {thread_continuity_passed}"
            self.log_test_result("Follow-up Creation with Response Detection", all_passed, overall_details)
            
            # Cleanup
            await self.db.emails.delete_many({"thread_id": test_thread_id})
            await self.db.follow_up_emails.delete_many({"thread_id": test_thread_id})
            
        except Exception as e:
            self.log_test_result("Follow-up Creation with Response Detection", False, f"Exception: {str(e)}")
    
    async def test_enhanced_email_processing_workflow(self):
        """Test 4: Enhanced email processing workflow with response detection"""
        print("\n⚙️ Testing Enhanced Email Processing Workflow...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Enhanced Email Processing Workflow", False, 
                                   "No active email accounts found")
                return
            
            # Test 4a: Process email through API with threading
            test_email_data = {
                "subject": "Threading Test - Need Product Information",
                "body": "Hello, I'm interested in your AI email assistant. Could you provide more details about pricing and features? This is for a threading functionality test.",
                "sender": "threading.test@example.com",
                "account_id": account['id']
            }
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                processing_passed = response.status_code in [200, 201]
                
                if processing_passed:
                    processed_email = response.json()
                    email_id = processed_email.get('id')
                    thread_id = processed_email.get('thread_id')
                    
                    # Verify thread_id was assigned
                    thread_assigned = bool(thread_id)
                    
                    # Verify email processing completed
                    processing_completed = processed_email.get('status') not in ['error', 'new']
                    
                    processing_details = f"Status: {response.status_code}, Thread ID: {thread_id}, Processing status: {processed_email.get('status')}"
                else:
                    processing_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    thread_assigned = False
                    processing_completed = False
                    
            except Exception as e:
                processing_passed = False
                processing_details = f"Error: {str(e)}"
                thread_assigned = False
                processing_completed = False
            
            # Test 4b: Verify follow-ups integration with threading
            follow_up_integration_passed = False
            if processing_passed and thread_id:
                try:
                    # Check if follow-ups were created with correct thread_id
                    follow_ups = await self.db.follow_up_emails.find({"thread_id": thread_id}).to_list(10)
                    follow_up_integration_passed = len(follow_ups) > 0
                    integration_details = f"Follow-ups created: {len(follow_ups)} with thread_id: {thread_id}"
                    
                    # Store for cleanup
                    self.test_follow_up_ids.extend([fu['id'] for fu in follow_ups])
                    
                except Exception as e:
                    integration_details = f"Error: {str(e)}"
            else:
                integration_details = "Skipped - email processing failed"
            
            # Test 4c: Test response detection in workflow
            workflow_response_detection_passed = False
            if thread_id:
                try:
                    # Add a response to the thread
                    response_email_id = await self.add_response_to_thread(thread_id, different_sender=True)
                    
                    # Wait for response detection
                    await asyncio.sleep(3)
                    
                    # Check if follow-ups were cancelled
                    remaining_follow_ups = await self.db.follow_up_emails.find({
                        "thread_id": thread_id,
                        "status": "pending"
                    }).to_list(10)
                    
                    workflow_response_detection_passed = len(remaining_follow_ups) == 0
                    workflow_details = f"Remaining pending follow-ups: {len(remaining_follow_ups)}"
                    
                    # Store response email for cleanup
                    self.test_email_ids.append(response_email_id)
                    
                except Exception as e:
                    workflow_details = f"Error: {str(e)}"
            else:
                workflow_details = "Skipped - no thread_id available"
            
            all_passed = (processing_passed and thread_assigned and processing_completed and 
                         follow_up_integration_passed and workflow_response_detection_passed)
            
            # Log individual results
            self.log_test_result("Enhanced Workflow - Email Processing", processing_passed and thread_assigned, 
                               processing_details)
            self.log_test_result("Enhanced Workflow - Follow-up Integration", follow_up_integration_passed, 
                               integration_details)
            self.log_test_result("Enhanced Workflow - Response Detection", workflow_response_detection_passed, 
                               workflow_details)
            
            overall_details = f"Processing: {processing_passed}, Integration: {follow_up_integration_passed}, Detection: {workflow_response_detection_passed}"
            self.log_test_result("Enhanced Email Processing Workflow", all_passed, overall_details)
            
            # Store email for cleanup
            if processing_passed and email_id:
                self.test_email_ids.append(email_id)
            
        except Exception as e:
            self.log_test_result("Enhanced Email Processing Workflow", False, f"Exception: {str(e)}")
    
    async def test_thread_continuity(self):
        """Test 5: Thread continuity verification"""
        print("\n🔗 Testing Thread Continuity...")
        
        try:
            # Test 5a: Create thread with multiple emails
            continuity_thread_id = f"continuity-test-{uuid.uuid4()}"
            email_ids = []
            
            # Create original email
            original_id = await self.create_email_in_thread(
                continuity_thread_id, 
                "original@example.com", 
                "Thread Continuity Test",
                "This is the original email in the thread"
            )
            email_ids.append(original_id)
            
            # Create follow-up emails with same thread_id
            for i in range(2):
                follow_up_id = await self.create_email_in_thread(
                    continuity_thread_id,
                    f"followup{i}@example.com",
                    f"Re: Thread Continuity Test - Follow-up {i+1}",
                    f"This is follow-up email {i+1} in the thread"
                )
                email_ids.append(follow_up_id)
            
            # Test 5b: Verify all emails have same thread_id
            thread_consistency_passed = await self.verify_thread_consistency(continuity_thread_id, email_ids)
            
            # Test 5c: Verify follow-ups maintain thread_id
            account = await self.db.email_accounts.find_one({"is_active": True})
            if account:
                # Import the function to create follow-ups
                sys.path.append('/app/backend')
                from server import create_follow_up_for_email
                
                # Create follow-ups for original email
                await create_follow_up_for_email(original_id, account['id'])
                
                # Verify follow-ups have correct thread_id
                follow_ups = await self.db.follow_up_emails.find({"original_email_id": original_id}).to_list(10)
                follow_up_continuity_passed = all(fu['thread_id'] == continuity_thread_id for fu in follow_ups)
                continuity_details = f"Follow-ups created: {len(follow_ups)}, All have correct thread_id: {follow_up_continuity_passed}"
                
                # Store for cleanup
                self.test_follow_up_ids.extend([fu['id'] for fu in follow_ups])
            else:
                follow_up_continuity_passed = False
                continuity_details = "No active account found for follow-up test"
            
            # Test 5d: Verify threads endpoint shows continuity
            try:
                response = requests.get(f"{API_BASE}/emails/threads", timeout=15)
                if response.status_code == 200:
                    threads = response.json()
                    test_thread = next((t for t in threads if t['thread_id'] == continuity_thread_id), None)
                    
                    if test_thread:
                        endpoint_continuity_passed = (
                            len(test_thread['responses']) >= 2 and  # Should have our follow-up emails
                            test_thread['original_email']['thread_id'] == continuity_thread_id and
                            all(r['thread_id'] == continuity_thread_id for r in test_thread['responses'])
                        )
                        endpoint_details = f"Thread found with {len(test_thread['responses'])} responses, all with correct thread_id"
                    else:
                        endpoint_continuity_passed = False
                        endpoint_details = f"Test thread {continuity_thread_id} not found in threads endpoint"
                else:
                    endpoint_continuity_passed = False
                    endpoint_details = f"Threads endpoint failed: {response.status_code}"
                    
            except Exception as e:
                endpoint_continuity_passed = False
                endpoint_details = f"Error: {str(e)}"
            
            all_passed = thread_consistency_passed and follow_up_continuity_passed and endpoint_continuity_passed
            
            # Log individual results
            self.log_test_result("Thread Continuity - Email Consistency", thread_consistency_passed, 
                               f"All {len(email_ids)} emails have thread_id: {continuity_thread_id}")
            self.log_test_result("Thread Continuity - Follow-up Consistency", follow_up_continuity_passed, 
                               continuity_details)
            self.log_test_result("Thread Continuity - Endpoint Verification", endpoint_continuity_passed, 
                               endpoint_details)
            
            overall_details = f"Email consistency: {thread_consistency_passed}, Follow-up consistency: {follow_up_continuity_passed}, Endpoint verification: {endpoint_continuity_passed}"
            self.log_test_result("Thread Continuity Verification", all_passed, overall_details)
            
            # Cleanup
            await self.db.emails.delete_many({"thread_id": continuity_thread_id})
            await self.db.follow_up_emails.delete_many({"thread_id": continuity_thread_id})
            
        except Exception as e:
            self.log_test_result("Thread Continuity Verification", False, f"Exception: {str(e)}")
    
    # Helper methods
    async def create_test_thread_data(self):
        """Create test thread data for testing"""
        self.test_thread_id = f"test-thread-{uuid.uuid4()}"
        
        # Create original email
        original_email_id = await self.create_email_in_thread(
            self.test_thread_id,
            "customer@example.com",
            "Need Product Information",
            "Hello, I'm interested in your product. Can you provide more details?"
        )
        self.test_email_ids.append(original_email_id)
        
        # Create response email from different sender
        response_email_id = await self.create_email_in_thread(
            self.test_thread_id,
            "support@company.com",
            "Re: Need Product Information",
            "Thank you for your inquiry. Here are the details you requested..."
        )
        self.test_email_ids.append(response_email_id)
        
        # Create follow-up emails
        account = await self.db.email_accounts.find_one({"is_active": True})
        if account:
            sys.path.append('/app/backend')
            from server import create_follow_up_for_email
            await create_follow_up_for_email(original_email_id, account['id'])
            
            # Get created follow-ups for cleanup
            follow_ups = await self.db.follow_up_emails.find({"original_email_id": original_email_id}).to_list(10)
            self.test_follow_up_ids.extend([fu['id'] for fu in follow_ups])
    
    async def create_email_in_thread(self, thread_id: str, sender: str, subject: str, body: str) -> str:
        """Create an email in a specific thread"""
        email_id = str(uuid.uuid4())
        email_doc = {
            "id": email_id,
            "account_id": "test-account",
            "message_id": f"<{email_id}@example.com>",
            "thread_id": thread_id,
            "subject": subject,
            "sender": sender,
            "recipient": "test@company.com",
            "body": body,
            "body_html": f"<p>{body}</p>",
            "received_at": datetime.utcnow(),
            "status": "processed",
            "created_at": datetime.utcnow()
        }
        
        await self.db.emails.insert_one(email_doc)
        return email_id
    
    async def create_single_email_thread(self, thread_id: str) -> str:
        """Create a single email thread for testing"""
        return await self.create_email_in_thread(
            thread_id,
            "test@example.com",
            "Single Email Thread Test",
            "This is a test email for response detection testing"
        )
    
    async def add_response_to_thread(self, thread_id: str, different_sender: bool = True) -> str:
        """Add a response email to an existing thread"""
        sender = "response@different.com" if different_sender else "test@example.com"
        return await self.create_email_in_thread(
            thread_id,
            sender,
            "Re: Response Test",
            "This is a response email to test response detection"
        )
    
    async def verify_no_response_detected(self, thread_id: str) -> bool:
        """Verify that no response is initially detected"""
        try:
            response = requests.get(f"{API_BASE}/emails/threads", timeout=10)
            if response.status_code == 200:
                threads = response.json()
                test_thread = next((t for t in threads if t['thread_id'] == thread_id), None)
                return test_thread and not test_thread.get('has_response', False)
            return False
        except:
            return False
    
    async def verify_response_detected(self, thread_id: str) -> bool:
        """Verify that response is detected"""
        try:
            response = requests.get(f"{API_BASE}/emails/threads", timeout=10)
            if response.status_code == 200:
                threads = response.json()
                test_thread = next((t for t in threads if t['thread_id'] == thread_id), None)
                return test_thread and test_thread.get('has_response', False)
            return False
        except:
            return False
    
    async def verify_follow_ups_cancelled(self, thread_id: str) -> bool:
        """Verify that follow-ups were cancelled"""
        try:
            pending_follow_ups = await self.db.follow_up_emails.find({
                "thread_id": thread_id,
                "status": "pending"
            }).to_list(10)
            return len(pending_follow_ups) == 0
        except:
            return False
    
    async def create_email_for_follow_up_test(self, thread_id: str, account_id: str) -> str:
        """Create an email that should trigger follow-ups"""
        email_id = str(uuid.uuid4())
        email_doc = {
            "id": email_id,
            "account_id": account_id,
            "message_id": f"<{email_id}@example.com>",
            "thread_id": thread_id,
            "subject": "Follow-up Test Email",
            "sender": "followup.test@example.com",
            "recipient": "test@company.com",
            "body": "This email should trigger follow-ups for testing",
            "body_html": "<p>This email should trigger follow-ups for testing</p>",
            "received_at": datetime.utcnow(),
            "status": "ready_to_send",
            "created_at": datetime.utcnow()
        }
        
        await self.db.emails.insert_one(email_doc)
        
        # Trigger follow-up creation
        sys.path.append('/app/backend')
        from server import create_follow_up_for_email
        await create_follow_up_for_email(email_id, account_id)
        
        return email_id
    
    async def verify_follow_ups_created(self, email_id: str, thread_id: str) -> bool:
        """Verify that follow-ups were created with correct thread_id"""
        try:
            follow_ups = await self.db.follow_up_emails.find({
                "original_email_id": email_id,
                "thread_id": thread_id
            }).to_list(10)
            
            # Store for cleanup
            self.test_follow_up_ids.extend([fu['id'] for fu in follow_ups])
            
            return len(follow_ups) > 0
        except:
            return False
    
    async def verify_thread_continuity(self, thread_id: str, email_ids: list) -> bool:
        """Verify thread continuity across emails and follow-ups"""
        try:
            # Check emails have correct thread_id
            emails = await self.db.emails.find({"id": {"$in": email_ids}}).to_list(10)
            emails_correct = all(email['thread_id'] == thread_id for email in emails)
            
            # Check follow-ups have correct thread_id
            follow_ups = await self.db.follow_up_emails.find({"thread_id": thread_id}).to_list(10)
            follow_ups_correct = all(fu['thread_id'] == thread_id for fu in follow_ups)
            
            return emails_correct and follow_ups_correct
        except:
            return False
    
    async def verify_thread_consistency(self, thread_id: str, email_ids: list) -> bool:
        """Verify all emails in the list have the same thread_id"""
        try:
            emails = await self.db.emails.find({"id": {"$in": email_ids}}).to_list(10)
            return all(email['thread_id'] == thread_id for email in emails)
        except:
            return False
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"THREADING FUNCTIONALITY TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print(f"\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result['passed']:
                print(f"  - {result['test']}")

async def main():
    """Main test execution"""
    tester = ThreadingTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        print("🧵 Starting Threading Functionality Tests...")
        print("="*60)
        
        # Run all tests
        await tester.test_threads_endpoint()
        await tester.test_response_detection_logic()
        await tester.test_follow_up_creation_with_response_detection()
        await tester.test_enhanced_email_processing_workflow()
        await tester.test_thread_continuity()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())