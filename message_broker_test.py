#!/usr/bin/env python3
"""
Message Broker & Follow-up System Testing
Tests Redis + RQ message broker implementation and follow-up creation/cancellation
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://calendar-agent-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
TEST_ACCOUNT_ID = "bd01f57c-c070-44fa-80ec-eaea95de2c9f"  # rohushanshinde@gmail.com

class MessageBrokerTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        
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
    
    async def test_message_broker_verification(self):
        """Test 1: Message Broker Verification - RQ enabled and working"""
        print("\n🔍 Testing Message Broker Verification...")
        
        try:
            # Test 1a: GET /api/dashboard/stats - verify message_broker.enabled is true
            try:
                response = requests.get(f"{API_BASE}/dashboard/stats", timeout=15)
                if response.status_code == 200:
                    stats = response.json()
                    message_broker_enabled = stats.get('message_broker', {}).get('enabled', False)
                    broker_status_passed = message_broker_enabled
                    broker_details = f"Status: {response.status_code}, Enabled: {message_broker_enabled}"
                else:
                    broker_status_passed = False
                    broker_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            except Exception as e:
                broker_status_passed = False
                broker_details = f"Error: {str(e)}"
            
            # Test 1b: Check queue stats (email_processing, follow_up, background queues)
            try:
                if broker_status_passed:
                    queue_stats = stats.get('message_broker', {}).get('queue_stats', {})
                    has_email_queue = 'email_processing' in queue_stats
                    has_follow_up_queue = 'follow_up' in queue_stats
                    has_background_queue = 'background' in queue_stats
                    redis_connected = queue_stats.get('redis_connected', False)
                    
                    queue_stats_passed = (has_email_queue and has_follow_up_queue and 
                                        has_background_queue and redis_connected)
                    queue_details = f"Email queue: {has_email_queue}, Follow-up queue: {has_follow_up_queue}, Background queue: {has_background_queue}, Redis: {redis_connected}"
                else:
                    queue_stats_passed = False
                    queue_details = "Skipped - broker status failed"
            except Exception as e:
                queue_stats_passed = False
                queue_details = f"Error: {str(e)}"
            
            # Test 1c: Test Redis connection directly
            try:
                import redis
                redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
                redis_conn = redis.Redis.from_url(redis_url, decode_responses=True)
                redis_ping = redis_conn.ping()
                redis_direct_passed = redis_ping
                redis_details = f"Direct Redis ping: {redis_ping}"
            except Exception as e:
                redis_direct_passed = False
                redis_details = f"Redis connection error: {str(e)}"
            
            all_passed = broker_status_passed and queue_stats_passed and redis_direct_passed
            
            # Log individual results
            self.log_test_result("Message Broker - Status", broker_status_passed, broker_details)
            self.log_test_result("Message Broker - Queue Stats", queue_stats_passed, queue_details)
            self.log_test_result("Message Broker - Redis Connection", redis_direct_passed, redis_details)
            
            details = f"Broker enabled: {broker_status_passed}, Queue stats: {queue_stats_passed}, Redis: {redis_direct_passed}"
            self.log_test_result("Message Broker Verification", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Message Broker Verification", False, f"Exception: {str(e)}")
    
    async def test_email_processing_with_rq(self):
        """Test 2: Email Processing with RQ - verify emails are processed through RQ"""
        print("\n🤖 Testing Email Processing with RQ...")
        
        try:
            # Test 2a: POST /api/emails/test with valid account_id
            test_email_data = {
                "subject": "RQ Test: Product Inquiry and Pricing Request",
                "body": "Hello! I'm interested in your AI email automation solution. Could you please provide detailed pricing information and schedule a demo? We need to automate our customer support responses and are looking for a reliable solution. Thank you!",
                "sender": "rq.test@techcompany.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            try:
                print(f"   Testing email processing via RQ with account: {TEST_ACCOUNT_ID}")
                start_time = time.time()
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                processing_time = time.time() - start_time
                
                rq_processing_passed = response.status_code in [200, 201]
                
                if rq_processing_passed:
                    processed_email = response.json()
                    email_id = processed_email.get('id')
                    final_status = processed_email.get('status')
                    has_intents = bool(processed_email.get('intents'))
                    has_draft = bool(processed_email.get('draft'))
                    
                    rq_details = f"Status: {response.status_code}, Time: {processing_time:.1f}s, Final status: {final_status}, Intents: {len(processed_email.get('intents', []))}, Draft: {len(processed_email.get('draft', ''))}"
                    
                    # Check if email reached ready_to_send or sent status
                    workflow_completed = final_status in ['ready_to_send', 'sent', 'needs_redraft']
                    
                else:
                    rq_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    workflow_completed = False
                    email_id = None
                    
            except Exception as e:
                rq_processing_passed = False
                rq_details = f"Error: {str(e)}"
                workflow_completed = False
                email_id = None
            
            # Test 2b: Check backend logs for "Enqueued email processing" message
            try:
                # Check supervisor logs for RQ enqueueing
                import subprocess
                log_result = subprocess.run(
                    ['tail', '-n', '50', '/var/log/supervisor/backend.out.log'],
                    capture_output=True, text=True, timeout=10
                )
                
                if log_result.returncode == 0:
                    log_content = log_result.stdout
                    has_enqueue_message = "Enqueued email processing" in log_content
                    has_rq_task_message = "[RQ Task]" in log_content
                    
                    log_verification_passed = has_enqueue_message or has_rq_task_message
                    log_details = f"Enqueue message: {has_enqueue_message}, RQ task message: {has_rq_task_message}"
                else:
                    log_verification_passed = False
                    log_details = f"Log check failed: {log_result.stderr}"
                    
            except Exception as e:
                log_verification_passed = False
                log_details = f"Log check error: {str(e)}"
            
            # Test 2c: Verify email in database with proper status progression
            db_verification_passed = False
            if email_id:
                try:
                    # Check email in database
                    email_doc = await self.db.emails.find_one({"id": email_id})
                    if email_doc:
                        db_status = email_doc.get('status')
                        has_processed_at = email_doc.get('processed_at') is not None
                        has_intents_db = bool(email_doc.get('intents'))
                        
                        db_verification_passed = (db_status in ['ready_to_send', 'sent', 'needs_redraft'] and 
                                                has_processed_at)
                        db_details = f"DB Status: {db_status}, Processed: {has_processed_at}, Intents: {has_intents_db}"
                    else:
                        db_details = "Email not found in database"
                except Exception as e:
                    db_details = f"DB check error: {str(e)}"
            else:
                db_details = "Skipped - no email ID"
            
            all_passed = rq_processing_passed and workflow_completed and log_verification_passed and db_verification_passed
            
            # Log individual results
            self.log_test_result("RQ Processing - API Test", rq_processing_passed, rq_details)
            self.log_test_result("RQ Processing - Workflow Complete", workflow_completed, f"Email reached final status: {workflow_completed}")
            self.log_test_result("RQ Processing - Log Verification", log_verification_passed, log_details)
            self.log_test_result("RQ Processing - Database Verification", db_verification_passed, db_details)
            
            details = f"API: {rq_processing_passed}, Workflow: {workflow_completed}, Logs: {log_verification_passed}, DB: {db_verification_passed}"
            self.log_test_result("Email Processing with RQ", all_passed, details)
            
            # Store email_id for follow-up tests
            self.test_email_id = email_id if rq_processing_passed else None
            
        except Exception as e:
            self.log_test_result("Email Processing with RQ", False, f"Exception: {str(e)}")
            self.test_email_id = None
    
    async def test_follow_up_creation_auto_send(self):
        """Test 3: Follow-up Creation on Auto-Send - verify follow-ups created for auto-sent emails"""
        print("\n📅 Testing Follow-up Creation on Auto-Send...")
        
        try:
            # Test 3a: Find an auto-sent email or create one
            auto_sent_emails = await self.db.emails.find({
                "status": "sent",
                "account_id": TEST_ACCOUNT_ID
            }).sort("sent_at", -1).limit(5).to_list(5)
            
            if not auto_sent_emails:
                # Create and auto-send an email for testing
                test_email_data = {
                    "subject": "Auto-Send Follow-up Test: Product Demo Request",
                    "body": "Hi! I'm very interested in your AI email solution and would like to schedule a product demo. Could you please send me available time slots? We're looking to implement this for our customer service team. Thanks!",
                    "sender": "autosend.test@company.com",
                    "account_id": TEST_ACCOUNT_ID
                }
                
                try:
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    if response.status_code in [200, 201]:
                        test_email = response.json()
                        test_email_id = test_email.get('id')
                        
                        # Wait a moment for processing
                        await asyncio.sleep(3)
                        
                        # Check if it was auto-sent
                        updated_email = await self.db.emails.find_one({"id": test_email_id})
                        if updated_email and updated_email.get('status') == 'sent':
                            auto_sent_emails = [updated_email]
                        else:
                            auto_sent_emails = []
                    else:
                        auto_sent_emails = []
                except Exception as e:
                    print(f"   Failed to create test email: {str(e)}")
                    auto_sent_emails = []
            
            if not auto_sent_emails:
                self.log_test_result("Follow-up Creation Auto-Send", False, "No auto-sent emails available for testing")
                return
            
            test_email = auto_sent_emails[0]
            test_email_id = test_email['id']
            print(f"   Testing follow-up creation for auto-sent email: {test_email['subject']}")
            
            # Test 3b: Check if follow-ups were created via RQ
            try:
                # Wait a moment for RQ to process follow-up creation
                await asyncio.sleep(5)
                
                follow_ups = await self.db.follow_up_emails.find({
                    "original_email_id": test_email_id
                }).to_list(10)
                
                follow_up_created = len(follow_ups) > 0
                
                if follow_up_created:
                    follow_up = follow_ups[0]
                    correct_recipient = follow_up.get('recipient_email') == test_email.get('sender')
                    correct_status = follow_up.get('status') == 'pending'
                    has_scheduled_time = follow_up.get('scheduled_time') is not None
                    correct_thread = follow_up.get('thread_id') == test_email.get('thread_id')
                    
                    follow_up_details = f"Created: {len(follow_ups)} follow-ups, Recipient: {correct_recipient}, Status: {correct_status}, Scheduled: {has_scheduled_time}, Thread: {correct_thread}"
                    follow_up_quality = correct_recipient and correct_status and has_scheduled_time and correct_thread
                else:
                    follow_up_details = "No follow-ups created"
                    follow_up_quality = False
                    
            except Exception as e:
                follow_up_created = False
                follow_up_quality = False
                follow_up_details = f"Error checking follow-ups: {str(e)}"
            
            # Test 3c: Verify follow-up creation was enqueued via RQ
            try:
                # Check logs for follow-up enqueueing
                import subprocess
                log_result = subprocess.run(
                    ['tail', '-n', '100', '/var/log/supervisor/backend.out.log'],
                    capture_output=True, text=True, timeout=10
                )
                
                if log_result.returncode == 0:
                    log_content = log_result.stdout
                    has_follow_up_enqueue = "Enqueued follow-up creation" in log_content
                    has_follow_up_task = "[RQ Task] Creating follow-up" in log_content
                    
                    rq_enqueue_passed = has_follow_up_enqueue or has_follow_up_task
                    rq_details = f"Enqueue message: {has_follow_up_enqueue}, Task message: {has_follow_up_task}"
                else:
                    rq_enqueue_passed = False
                    rq_details = f"Log check failed: {log_result.stderr}"
                    
            except Exception as e:
                rq_enqueue_passed = False
                rq_details = f"Log check error: {str(e)}"
            
            # Test 3d: GET /api/follow-ups to verify via API
            try:
                response = requests.get(f"{API_BASE}/follow-ups", timeout=15)
                if response.status_code == 200:
                    all_follow_ups = response.json()
                    test_follow_ups = [f for f in all_follow_ups if f.get('original_email_id') == test_email_id]
                    
                    api_verification_passed = len(test_follow_ups) > 0
                    api_details = f"Status: {response.status_code}, Total follow-ups: {len(all_follow_ups)}, Test follow-ups: {len(test_follow_ups)}"
                else:
                    api_verification_passed = False
                    api_details = f"Status: {response.status_code}"
            except Exception as e:
                api_verification_passed = False
                api_details = f"API error: {str(e)}"
            
            all_passed = follow_up_created and follow_up_quality and rq_enqueue_passed and api_verification_passed
            
            # Log individual results
            self.log_test_result("Auto-Send Follow-up - Creation", follow_up_created, f"Follow-ups created: {follow_up_created}")
            self.log_test_result("Auto-Send Follow-up - Quality", follow_up_quality, follow_up_details)
            self.log_test_result("Auto-Send Follow-up - RQ Enqueue", rq_enqueue_passed, rq_details)
            self.log_test_result("Auto-Send Follow-up - API Verification", api_verification_passed, api_details)
            
            details = f"Created: {follow_up_created}, Quality: {follow_up_quality}, RQ: {rq_enqueue_passed}, API: {api_verification_passed}"
            self.log_test_result("Follow-up Creation Auto-Send", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Follow-up Creation Auto-Send", False, f"Exception: {str(e)}")
    
    async def test_follow_up_creation_manual_send(self):
        """Test 4: Follow-up Creation on Manual Send - THE KEY FIX"""
        print("\n📤 Testing Follow-up Creation on Manual Send (KEY FIX)...")
        
        try:
            # Test 4a: Find or create an email ready for manual send
            ready_emails = await self.db.emails.find({
                "status": "ready_to_send",
                "account_id": TEST_ACCOUNT_ID
            }).limit(1).to_list(1)
            
            if not ready_emails:
                # Create an email and get it to ready_to_send status
                test_email_data = {
                    "subject": "Manual Send Follow-up Test: Service Inquiry",
                    "body": "Hello! I'm interested in your email automation service. Could you provide more details about your pricing plans and implementation process? We're a mid-size company looking to improve our customer communication. Thank you!",
                    "sender": "manual.test@business.com",
                    "account_id": TEST_ACCOUNT_ID
                }
                
                try:
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    if response.status_code in [200, 201]:
                        test_email = response.json()
                        test_email_id = test_email.get('id')
                        
                        # Wait for processing
                        await asyncio.sleep(5)
                        
                        # Check if it's ready to send
                        updated_email = await self.db.emails.find_one({"id": test_email_id})
                        if updated_email and updated_email.get('status') in ['ready_to_send', 'needs_redraft']:
                            ready_emails = [updated_email]
                        else:
                            ready_emails = []
                    else:
                        ready_emails = []
                except Exception as e:
                    print(f"   Failed to create test email: {str(e)}")
                    ready_emails = []
            
            if not ready_emails:
                self.log_test_result("Follow-up Creation Manual Send", False, "No emails ready for manual send")
                return
            
            test_email = ready_emails[0]
            test_email_id = test_email['id']
            print(f"   Testing manual send for email: {test_email['subject']}")
            
            # Test 4b: POST /api/emails/{email_id}/send for manual send
            try:
                send_request = {"manual_override": False}
                response = requests.post(f"{API_BASE}/emails/{test_email_id}/send", json=send_request, timeout=30)
                
                manual_send_passed = response.status_code == 200
                
                if manual_send_passed:
                    send_details = f"Status: {response.status_code}, Message: {response.json().get('message', 'Success')}"
                    
                    # Wait for email to be marked as sent
                    await asyncio.sleep(3)
                    
                    # Verify email status changed to sent
                    sent_email = await self.db.emails.find_one({"id": test_email_id})
                    email_sent = sent_email and sent_email.get('status') == 'sent'
                    
                else:
                    send_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    email_sent = False
                    
            except Exception as e:
                manual_send_passed = False
                email_sent = False
                send_details = f"Send error: {str(e)}"
            
            # Test 4c: Verify follow-up creation was enqueued for manual send
            try:
                # Wait for RQ to process follow-up creation
                await asyncio.sleep(5)
                
                # Check logs for manual send follow-up enqueueing
                import subprocess
                log_result = subprocess.run(
                    ['tail', '-n', '100', '/var/log/supervisor/backend.out.log'],
                    capture_output=True, text=True, timeout=10
                )
                
                if log_result.returncode == 0:
                    log_content = log_result.stdout
                    has_manual_follow_up_enqueue = "Enqueued follow-up creation for manual send" in log_content
                    has_follow_up_created_log = "Created follow-up schedule for manual send" in log_content
                    
                    manual_rq_passed = has_manual_follow_up_enqueue or has_follow_up_created_log
                    manual_rq_details = f"Manual enqueue: {has_manual_follow_up_enqueue}, Created log: {has_follow_up_created_log}"
                else:
                    manual_rq_passed = False
                    manual_rq_details = f"Log check failed: {log_result.stderr}"
                    
            except Exception as e:
                manual_rq_passed = False
                manual_rq_details = f"Log check error: {str(e)}"
            
            # Test 4d: Check /api/follow-ups to see if follow-ups were created
            try:
                await asyncio.sleep(3)  # Wait for follow-up creation
                
                follow_ups = await self.db.follow_up_emails.find({
                    "original_email_id": test_email_id
                }).to_list(10)
                
                manual_follow_up_created = len(follow_ups) > 0
                
                if manual_follow_up_created:
                    follow_up = follow_ups[0]
                    correct_recipient = follow_up.get('recipient_email') == test_email.get('sender')
                    correct_status = follow_up.get('status') == 'pending'
                    has_scheduled_time = follow_up.get('scheduled_time') is not None
                    
                    manual_follow_up_details = f"Created: {len(follow_ups)} follow-ups, Recipient: {correct_recipient}, Status: {correct_status}, Scheduled: {has_scheduled_time}"
                    manual_follow_up_quality = correct_recipient and correct_status and has_scheduled_time
                else:
                    manual_follow_up_details = "No follow-ups created for manual send"
                    manual_follow_up_quality = False
                    
            except Exception as e:
                manual_follow_up_created = False
                manual_follow_up_quality = False
                manual_follow_up_details = f"Error checking manual follow-ups: {str(e)}"
            
            # Test 4e: API verification
            try:
                response = requests.get(f"{API_BASE}/follow-ups", timeout=15)
                if response.status_code == 200:
                    all_follow_ups = response.json()
                    manual_test_follow_ups = [f for f in all_follow_ups if f.get('original_email_id') == test_email_id]
                    
                    manual_api_passed = len(manual_test_follow_ups) > 0
                    manual_api_details = f"Status: {response.status_code}, Manual follow-ups: {len(manual_test_follow_ups)}"
                else:
                    manual_api_passed = False
                    manual_api_details = f"Status: {response.status_code}"
            except Exception as e:
                manual_api_passed = False
                manual_api_details = f"API error: {str(e)}"
            
            all_passed = (manual_send_passed and email_sent and manual_rq_passed and 
                         manual_follow_up_created and manual_follow_up_quality and manual_api_passed)
            
            # Log individual results
            self.log_test_result("Manual Send - Email Sent", manual_send_passed and email_sent, send_details)
            self.log_test_result("Manual Send - RQ Enqueue", manual_rq_passed, manual_rq_details)
            self.log_test_result("Manual Send - Follow-up Created", manual_follow_up_created, f"Follow-ups created: {manual_follow_up_created}")
            self.log_test_result("Manual Send - Follow-up Quality", manual_follow_up_quality, manual_follow_up_details)
            self.log_test_result("Manual Send - API Verification", manual_api_passed, manual_api_details)
            
            details = f"Sent: {manual_send_passed and email_sent}, RQ: {manual_rq_passed}, Created: {manual_follow_up_created}, Quality: {manual_follow_up_quality}, API: {manual_api_passed}"
            self.log_test_result("Follow-up Creation Manual Send", all_passed, details)
            
            # Store for cancellation test
            self.manual_test_email_id = test_email_id if manual_follow_up_created else None
            
        except Exception as e:
            self.log_test_result("Follow-up Creation Manual Send", False, f"Exception: {str(e)}")
            self.manual_test_email_id = None
    
    async def test_follow_up_cancellation_on_reply(self):
        """Test 5: Follow-up Cancellation on Reply - verify follow-ups cancelled when customer replies"""
        print("\n🔄 Testing Follow-up Cancellation on Reply...")
        
        try:
            # Test 5a: Create a test scenario - Customer sends email → System responds → Customer replies
            
            # Step 1: Customer sends initial inquiry
            customer_email = "customer.reply.test@company.com"
            initial_inquiry = {
                "subject": "Follow-up Cancellation Test: Product Information Request",
                "body": "Hello! I'm interested in learning more about your AI email automation platform. Could you please send me detailed information about your features and pricing? We're evaluating different solutions for our customer service team. Thank you!",
                "sender": customer_email,
                "account_id": TEST_ACCOUNT_ID
            }
            
            try:
                print("   Step 1: Customer sends initial inquiry...")
                response = requests.post(f"{API_BASE}/emails/test", json=initial_inquiry, timeout=45)
                if response.status_code in [200, 201]:
                    initial_email = response.json()
                    initial_email_id = initial_email.get('id')
                    thread_id = initial_email.get('thread_id')
                    
                    # Wait for processing and auto-send
                    await asyncio.sleep(8)
                    
                    # Check if email was sent
                    sent_email = await self.db.emails.find_one({"id": initial_email_id})
                    initial_sent = sent_email and sent_email.get('status') == 'sent'
                    
                    print(f"   Initial email sent: {initial_sent}")
                else:
                    initial_sent = False
                    initial_email_id = None
                    thread_id = None
            except Exception as e:
                print(f"   Failed to create initial inquiry: {str(e)}")
                initial_sent = False
                initial_email_id = None
                thread_id = None
            
            if not initial_sent:
                self.log_test_result("Follow-up Cancellation on Reply", False, "Failed to create initial customer inquiry")
                return
            
            # Step 2: Wait for follow-up to be created
            print("   Step 2: Waiting for follow-up creation...")
            await asyncio.sleep(10)
            
            follow_ups_before = await self.db.follow_up_emails.find({
                "original_email_id": initial_email_id,
                "recipient_email": customer_email
            }).to_list(10)
            
            follow_up_created = len(follow_ups_before) > 0
            print(f"   Follow-ups created: {len(follow_ups_before)}")
            
            if not follow_up_created:
                self.log_test_result("Follow-up Cancellation on Reply", False, "No follow-ups created for initial email")
                return
            
            # Step 3: Customer replies to the thread
            print("   Step 3: Customer replies to thread...")
            customer_reply = {
                "subject": f"Re: {initial_inquiry['subject']}",
                "body": "Thank you for your response! I've reviewed the information and have a few follow-up questions. Could we schedule a call to discuss our specific requirements? I'm available next week for a demo. Looking forward to hearing from you.",
                "sender": customer_email,
                "account_id": TEST_ACCOUNT_ID
            }
            
            try:
                # Create customer reply in same thread
                reply_email_obj = {
                    "id": str(uuid.uuid4()),
                    "account_id": TEST_ACCOUNT_ID,
                    "message_id": f"<reply-{uuid.uuid4()}@company.com>",
                    "thread_id": thread_id,  # Same thread as original
                    "subject": customer_reply['subject'],
                    "sender": customer_reply['sender'],
                    "recipient": f"test@{TEST_ACCOUNT_ID}.com",
                    "body": customer_reply['body'],
                    "body_html": "",
                    "received_at": datetime.utcnow(),
                    "in_reply_to": sent_email.get('message_id', ''),
                    "references": sent_email.get('message_id', ''),
                    "status": "new",
                    "intents": [],
                    "draft": "",
                    "draft_html": "",
                    "validation_result": None,
                    "processed_at": None,
                    "sent_at": None,
                    "error": None,
                    "created_at": datetime.utcnow()
                }
                
                # Insert reply directly into database to simulate received reply
                await self.db.emails.insert_one(reply_email_obj)
                reply_email_id = reply_email_obj['id']
                
                # Process the reply to trigger follow-up cancellation
                from server import process_email_async
                await process_email_async(reply_email_id)
                
                reply_processed = True
                print(f"   Customer reply processed: {reply_email_id}")
                
            except Exception as e:
                print(f"   Failed to process customer reply: {str(e)}")
                reply_processed = False
                reply_email_id = None
            
            if not reply_processed:
                self.log_test_result("Follow-up Cancellation on Reply", False, "Failed to process customer reply")
                return
            
            # Step 4: Wait for follow-up cancellation processing
            print("   Step 4: Waiting for follow-up cancellation...")
            await asyncio.sleep(5)
            
            # Test 5b: Verify follow-ups are cancelled (status="cancelled", response_received=true)
            try:
                follow_ups_after = await self.db.follow_up_emails.find({
                    "original_email_id": initial_email_id,
                    "recipient_email": customer_email
                }).to_list(10)
                
                cancelled_follow_ups = [f for f in follow_ups_after if f.get('status') == 'cancelled']
                response_received_follow_ups = [f for f in follow_ups_after if f.get('response_received') == True]
                
                cancellation_worked = len(cancelled_follow_ups) > 0
                response_detected = len(response_received_follow_ups) > 0
                
                cancellation_details = f"Total follow-ups: {len(follow_ups_after)}, Cancelled: {len(cancelled_follow_ups)}, Response detected: {len(response_received_follow_ups)}"
                
            except Exception as e:
                cancellation_worked = False
                response_detected = False
                cancellation_details = f"Error checking cancellation: {str(e)}"
            
            # Test 5c: Check logs for cancellation processing
            try:
                import subprocess
                log_result = subprocess.run(
                    ['tail', '-n', '100', '/var/log/supervisor/backend.out.log'],
                    capture_output=True, text=True, timeout=10
                )
                
                if log_result.returncode == 0:
                    log_content = log_result.stdout
                    has_cancellation_log = "cancelled follow-up" in log_content.lower()
                    has_response_detection = "response detected" in log_content.lower()
                    
                    log_verification_passed = has_cancellation_log or has_response_detection
                    log_details = f"Cancellation log: {has_cancellation_log}, Response detection: {has_response_detection}"
                else:
                    log_verification_passed = False
                    log_details = f"Log check failed: {log_result.stderr}"
                    
            except Exception as e:
                log_verification_passed = False
                log_details = f"Log check error: {str(e)}"
            
            # Test 5d: Verify thread detection worked correctly
            try:
                # Check that reply is in same thread
                reply_email_doc = await self.db.emails.find_one({"id": reply_email_id})
                thread_match = reply_email_doc and reply_email_doc.get('thread_id') == thread_id
                
                thread_details = f"Thread match: {thread_match}, Original thread: {thread_id}, Reply thread: {reply_email_doc.get('thread_id') if reply_email_doc else 'None'}"
                
            except Exception as e:
                thread_match = False
                thread_details = f"Thread check error: {str(e)}"
            
            all_passed = (follow_up_created and reply_processed and cancellation_worked and 
                         response_detected and log_verification_passed and thread_match)
            
            # Log individual results
            self.log_test_result("Cancellation - Follow-up Created", follow_up_created, f"Initial follow-ups: {len(follow_ups_before)}")
            self.log_test_result("Cancellation - Reply Processed", reply_processed, f"Customer reply processed: {reply_processed}")
            self.log_test_result("Cancellation - Follow-ups Cancelled", cancellation_worked, cancellation_details)
            self.log_test_result("Cancellation - Response Detected", response_detected, f"Response received flag set: {response_detected}")
            self.log_test_result("Cancellation - Log Verification", log_verification_passed, log_details)
            self.log_test_result("Cancellation - Thread Detection", thread_match, thread_details)
            
            details = f"Created: {follow_up_created}, Reply: {reply_processed}, Cancelled: {cancellation_worked}, Response: {response_detected}, Logs: {log_verification_passed}, Thread: {thread_match}"
            self.log_test_result("Follow-up Cancellation on Reply", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Follow-up Cancellation on Reply", False, f"Exception: {str(e)}")
    
    async def test_queue_stats_and_monitoring(self):
        """Test 6: Queue Stats and Monitoring - verify queue statistics are available"""
        print("\n📊 Testing Queue Stats and Monitoring...")
        
        try:
            # Test 6a: GET /api/dashboard/stats for queue information
            try:
                response = requests.get(f"{API_BASE}/dashboard/stats", timeout=15)
                if response.status_code == 200:
                    stats = response.json()
                    message_broker = stats.get('message_broker', {})
                    queue_stats = message_broker.get('queue_stats', {})
                    
                    has_email_queue_stats = 'email_processing' in queue_stats
                    has_follow_up_queue_stats = 'follow_up' in queue_stats
                    has_background_queue_stats = 'background' in queue_stats
                    
                    if has_email_queue_stats:
                        email_queue = queue_stats['email_processing']
                        email_queue_complete = all(key in email_queue for key in ['count', 'failed', 'finished', 'started'])
                    else:
                        email_queue_complete = False
                    
                    dashboard_stats_passed = (has_email_queue_stats and has_follow_up_queue_stats and 
                                            has_background_queue_stats and email_queue_complete)
                    dashboard_details = f"Email queue: {has_email_queue_stats}, Follow-up queue: {has_follow_up_queue_stats}, Background queue: {has_background_queue_stats}, Complete stats: {email_queue_complete}"
                else:
                    dashboard_stats_passed = False
                    dashboard_details = f"Status: {response.status_code}"
            except Exception as e:
                dashboard_stats_passed = False
                dashboard_details = f"Error: {str(e)}"
            
            # Test 6b: Direct queue stats check
            try:
                # Import RQ components
                from tasks import get_queue_stats
                direct_stats = get_queue_stats()
                
                has_all_queues = all(queue in direct_stats for queue in ['email_processing', 'follow_up', 'background'])
                redis_connected = direct_stats.get('redis_connected', False)
                
                direct_stats_passed = has_all_queues and redis_connected
                direct_details = f"All queues: {has_all_queues}, Redis connected: {redis_connected}"
                
                # Log queue counts
                if has_all_queues:
                    email_count = direct_stats['email_processing']['count']
                    follow_up_count = direct_stats['follow_up']['count']
                    background_count = direct_stats['background']['count']
                    print(f"   Queue counts - Email: {email_count}, Follow-up: {follow_up_count}, Background: {background_count}")
                
            except Exception as e:
                direct_stats_passed = False
                direct_details = f"Error: {str(e)}"
            
            # Test 6c: Worker status check
            try:
                # Check if RQ workers are running
                import subprocess
                ps_result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True, text=True, timeout=10
                )
                
                if ps_result.returncode == 0:
                    ps_output = ps_result.stdout
                    rq_workers_running = 'rq worker' in ps_output or 'tasks.py' in ps_output
                    worker_details = f"RQ workers running: {rq_workers_running}"
                else:
                    rq_workers_running = False
                    worker_details = "Failed to check worker processes"
                    
            except Exception as e:
                rq_workers_running = False
                worker_details = f"Worker check error: {str(e)}"
            
            # Test 6d: Redis connection health
            try:
                import redis
                redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
                redis_conn = redis.Redis.from_url(redis_url, decode_responses=True)
                
                # Test basic Redis operations
                redis_ping = redis_conn.ping()
                redis_info = redis_conn.info()
                redis_memory = redis_info.get('used_memory_human', 'Unknown')
                
                redis_health_passed = redis_ping
                redis_health_details = f"Ping: {redis_ping}, Memory: {redis_memory}"
                
            except Exception as e:
                redis_health_passed = False
                redis_health_details = f"Redis health error: {str(e)}"
            
            all_passed = (dashboard_stats_passed and direct_stats_passed and 
                         rq_workers_running and redis_health_passed)
            
            # Log individual results
            self.log_test_result("Queue Stats - Dashboard", dashboard_stats_passed, dashboard_details)
            self.log_test_result("Queue Stats - Direct Check", direct_stats_passed, direct_details)
            self.log_test_result("Queue Stats - Workers Running", rq_workers_running, worker_details)
            self.log_test_result("Queue Stats - Redis Health", redis_health_passed, redis_health_details)
            
            details = f"Dashboard: {dashboard_stats_passed}, Direct: {direct_stats_passed}, Workers: {rq_workers_running}, Redis: {redis_health_passed}"
            self.log_test_result("Queue Stats and Monitoring", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Queue Stats and Monitoring", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("MESSAGE BROKER & FOLLOW-UP SYSTEM TEST SUMMARY")
        print("="*80)
        
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
                print(f"  - {test['test']}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Message Broker & Follow-up System Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Account ID: {TEST_ACCOUNT_ID}")
    
    tester = MessageBrokerTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests in sequence
        print("\n" + "="*80)
        print("STARTING COMPREHENSIVE MESSAGE BROKER TESTING")
        print("="*80)
        
        # Test 1: Message Broker Verification
        await tester.test_message_broker_verification()
        
        # Test 2: Email Processing with RQ
        await tester.test_email_processing_with_rq()
        
        # Test 3: Follow-up Creation on Auto-Send
        await tester.test_follow_up_creation_auto_send()
        
        # Test 4: Follow-up Creation on Manual Send (KEY FIX)
        await tester.test_follow_up_creation_manual_send()
        
        # Test 5: Follow-up Cancellation on Reply
        await tester.test_follow_up_cancellation_on_reply()
        
        # Test 6: Queue Stats and Monitoring
        await tester.test_queue_stats_and_monitoring()
        
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