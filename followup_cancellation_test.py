#!/usr/bin/env python3
"""
Follow-up Cancellation System Comprehensive Testing
Tests follow-up status, thread detection, response detection logic, and background services
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://account-auth-repair.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FollowUpCancellationTester:
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
    
    async def test_follow_up_status_check(self):
        """Test 1: Follow-up Status Check - Query database to see current follow-ups and their statuses"""
        print("\n🔍 Testing Follow-up Status Check...")
        
        try:
            # Test 1a: GET /api/follow-ups - check all follow-ups status
            try:
                response = requests.get(f"{API_BASE}/follow-ups", timeout=15)
                api_passed = response.status_code == 200
                
                if api_passed:
                    follow_ups = response.json()
                    print(f"   Found {len(follow_ups)} follow-ups via API")
                    
                    # Analyze follow-up statuses
                    status_counts = {}
                    pending_count = 0
                    cancelled_count = 0
                    sent_count = 0
                    
                    for follow_up in follow_ups:
                        status = follow_up.get('status', 'unknown')
                        status_counts[status] = status_counts.get(status, 0) + 1
                        
                        if status == 'pending':
                            pending_count += 1
                        elif status == 'cancelled':
                            cancelled_count += 1
                        elif status == 'sent':
                            sent_count += 1
                    
                    api_details = f"Total: {len(follow_ups)}, Pending: {pending_count}, Cancelled: {cancelled_count}, Sent: {sent_count}"
                    print(f"   Status breakdown: {status_counts}")
                    
                else:
                    api_details = f"API failed with status {response.status_code}: {response.text[:200]}"
                    
            except Exception as e:
                api_passed = False
                api_details = f"API error: {str(e)}"
            
            # Test 1b: Direct database query for follow-ups
            try:
                db_follow_ups = await self.db.follow_up_emails.find().to_list(1000)
                db_passed = True
                
                db_status_counts = {}
                db_pending_count = 0
                db_cancelled_count = 0
                
                for follow_up in db_follow_ups:
                    status = follow_up.get('status', 'unknown')
                    db_status_counts[status] = db_status_counts.get(status, 0) + 1
                    
                    if status == 'pending':
                        db_pending_count += 1
                    elif status == 'cancelled':
                        db_cancelled_count += 1
                
                db_details = f"DB Total: {len(db_follow_ups)}, Pending: {db_pending_count}, Cancelled: {db_cancelled_count}"
                print(f"   DB Status breakdown: {db_status_counts}")
                
                # Check for stuck pending follow-ups (older than 48 hours)
                stuck_follow_ups = []
                cutoff_time = datetime.utcnow() - timedelta(hours=48)
                
                for follow_up in db_follow_ups:
                    if (follow_up.get('status') == 'pending' and 
                        follow_up.get('created_at', datetime.utcnow()) < cutoff_time):
                        stuck_follow_ups.append(follow_up)
                
                if stuck_follow_ups:
                    print(f"   ⚠️  Found {len(stuck_follow_ups)} potentially stuck pending follow-ups")
                    for stuck in stuck_follow_ups[:3]:  # Show first 3
                        print(f"      - ID: {stuck.get('id')}, Created: {stuck.get('created_at')}, Thread: {stuck.get('thread_id')}")
                
            except Exception as e:
                db_passed = False
                db_details = f"DB error: {str(e)}"
            
            # Test 1c: Follow-up analytics endpoint
            try:
                response = requests.get(f"{API_BASE}/follow-ups/analytics", timeout=10)
                analytics_passed = response.status_code == 200
                
                if analytics_passed:
                    analytics = response.json()
                    analytics_details = f"Analytics: {analytics}"
                    print(f"   Analytics: {analytics}")
                else:
                    analytics_details = f"Analytics failed: {response.status_code}"
                    
            except Exception as e:
                analytics_passed = False
                analytics_details = f"Analytics error: {str(e)}"
            
            all_passed = api_passed and db_passed and analytics_passed
            
            details = f"API: {api_details}, DB: {db_details}, Analytics: {analytics_details}"
            
            self.log_test_result("Follow-up Status Check", all_passed, details)
            
            # Store results for later tests
            self.follow_ups_data = {
                'api_follow_ups': follow_ups if api_passed else [],
                'db_follow_ups': db_follow_ups if db_passed else [],
                'pending_count': pending_count if api_passed else 0
            }
            
        except Exception as e:
            self.log_test_result("Follow-up Status Check", False, f"Exception: {str(e)}")
    
    async def test_thread_detection(self):
        """Test 2: Thread Detection - Test how thread IDs are generated and matched for email conversations"""
        print("\n🧵 Testing Thread Detection...")
        
        try:
            # Test 2a: GET /api/emails/threads - examine thread structures and relationships
            try:
                response = requests.get(f"{API_BASE}/emails/threads", timeout=15)
                threads_api_passed = response.status_code == 200
                
                if threads_api_passed:
                    threads = response.json()
                    print(f"   Found {len(threads)} email threads via API")
                    
                    # Analyze thread structures
                    threads_with_responses = 0
                    active_follow_ups = 0
                    
                    for thread in threads:
                        if thread.get('has_response', False):
                            threads_with_responses += 1
                        if thread.get('follow_ups_active', True):
                            active_follow_ups += 1
                    
                    threads_details = f"Total: {len(threads)}, With responses: {threads_with_responses}, Active follow-ups: {active_follow_ups}"
                    
                    # Show sample thread structure
                    if threads:
                        sample_thread = threads[0]
                        print(f"   Sample thread structure: ID={sample_thread.get('thread_id')}, Subject={sample_thread.get('subject')}, Participants={len(sample_thread.get('participants', []))}")
                        
                else:
                    threads_details = f"Threads API failed: {response.status_code}"
                    
            except Exception as e:
                threads_api_passed = False
                threads_details = f"Threads API error: {str(e)}"
            
            # Test 2b: GET /api/emails - check individual emails for proper thread_id assignment
            try:
                response = requests.get(f"{API_BASE}/emails", timeout=15)
                emails_api_passed = response.status_code == 200
                
                if emails_api_passed:
                    emails = response.json()
                    print(f"   Found {len(emails)} emails via API")
                    
                    # Analyze thread ID consistency
                    emails_with_thread_id = 0
                    unique_thread_ids = set()
                    
                    for email in emails:
                        if email.get('thread_id'):
                            emails_with_thread_id += 1
                            unique_thread_ids.add(email.get('thread_id'))
                    
                    emails_details = f"Total: {len(emails)}, With thread_id: {emails_with_thread_id}, Unique threads: {len(unique_thread_ids)}"
                    
                else:
                    emails_details = f"Emails API failed: {response.status_code}"
                    
            except Exception as e:
                emails_api_passed = False
                emails_details = f"Emails API error: {str(e)}"
            
            # Test 2c: Direct database analysis of thread relationships
            try:
                # Check emails collection for thread consistency
                db_emails = await self.db.emails.find().to_list(1000)
                
                thread_id_mapping = {}
                for email in db_emails:
                    thread_id = email.get('thread_id')
                    if thread_id:
                        if thread_id not in thread_id_mapping:
                            thread_id_mapping[thread_id] = []
                        thread_id_mapping[thread_id].append({
                            'id': email.get('id'),
                            'subject': email.get('subject'),
                            'sender': email.get('sender'),
                            'message_id': email.get('message_id'),
                            'in_reply_to': email.get('in_reply_to'),
                            'references': email.get('references')
                        })
                
                # Check follow-ups collection for thread consistency
                db_follow_ups = await self.db.follow_up_emails.find().to_list(1000)
                
                follow_up_threads = set()
                orphaned_follow_ups = 0
                
                for follow_up in db_follow_ups:
                    thread_id = follow_up.get('thread_id')
                    if thread_id:
                        follow_up_threads.add(thread_id)
                        # Check if thread exists in emails
                        if thread_id not in thread_id_mapping:
                            orphaned_follow_ups += 1
                
                db_analysis_passed = True
                db_analysis_details = f"Email threads: {len(thread_id_mapping)}, Follow-up threads: {len(follow_up_threads)}, Orphaned follow-ups: {orphaned_follow_ups}"
                
                print(f"   Thread analysis: {db_analysis_details}")
                
                # Show thread relationship examples
                if thread_id_mapping:
                    sample_thread_id = list(thread_id_mapping.keys())[0]
                    sample_emails = thread_id_mapping[sample_thread_id]
                    print(f"   Sample thread {sample_thread_id} has {len(sample_emails)} emails")
                    
            except Exception as e:
                db_analysis_passed = False
                db_analysis_details = f"DB analysis error: {str(e)}"
            
            all_passed = threads_api_passed and emails_api_passed and db_analysis_passed
            
            details = f"Threads API: {threads_details}, Emails API: {emails_details}, DB Analysis: {db_analysis_details}"
            
            self.log_test_result("Thread Detection", all_passed, details)
            
            # Store thread data for later tests
            self.thread_data = {
                'thread_id_mapping': thread_id_mapping if db_analysis_passed else {},
                'follow_up_threads': follow_up_threads if db_analysis_passed else set(),
                'orphaned_follow_ups': orphaned_follow_ups if db_analysis_passed else 0
            }
            
        except Exception as e:
            self.log_test_result("Thread Detection", False, f"Exception: {str(e)}")
    
    async def test_response_detection_logic(self):
        """Test 3: Response Detection Logic - Test the real-time cancellation in process_email_async()"""
        print("\n🔍 Testing Response Detection Logic...")
        
        try:
            # Test 3a: Create a test email thread and follow-up scenario
            # Get an active email account
            accounts = await self.db.email_accounts.find({"is_active": True}).to_list(10)
            if not accounts:
                self.log_test_result("Response Detection Logic", False, "No active email accounts found")
                return
            
            account = accounts[0]
            test_thread_id = f"test-thread-{uuid.uuid4()}"
            
            # Create original email
            original_email = {
                "id": str(uuid.uuid4()),
                "account_id": account['id'],
                "message_id": f"<original-{uuid.uuid4()}@test.com>",
                "thread_id": test_thread_id,
                "subject": "Test Follow-up Cancellation",
                "sender": "customer@example.com",
                "recipient": account['email'],
                "body": "I need information about your pricing.",
                "body_html": "<p>I need information about your pricing.</p>",
                "received_at": datetime.utcnow(),
                "status": "sent",
                "created_at": datetime.utcnow()
            }
            
            await self.db.emails.insert_one(original_email)
            
            # Create a pending follow-up for this thread
            follow_up = {
                "id": str(uuid.uuid4()),
                "original_email_id": original_email['id'],
                "account_id": account['id'],
                "user_id": "test-user-id",
                "thread_id": test_thread_id,
                "recipient_email": "customer@example.com",
                "subject": "Re: Test Follow-up Cancellation",
                "status": "pending",
                "follow_up_number": 1,
                "scheduled_time": datetime.utcnow() + timedelta(hours=24),
                "draft_content": "Following up on your pricing inquiry...",
                "response_received": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await self.db.follow_up_emails.insert_one(follow_up)
            print(f"   Created test follow-up: {follow_up['id']}")
            
            # Test 3b: Simulate a reply email that should cancel the follow-up
            reply_email = {
                "id": str(uuid.uuid4()),
                "account_id": account['id'],
                "message_id": f"<reply-{uuid.uuid4()}@test.com>",
                "thread_id": test_thread_id,  # Same thread ID
                "subject": "Re: Test Follow-up Cancellation",
                "sender": "customer@example.com",  # Same sender as original
                "recipient": account['email'],
                "body": "Thank you for the information. I'm interested in the premium plan.",
                "body_html": "<p>Thank you for the information. I'm interested in the premium plan.</p>",
                "received_at": datetime.utcnow(),
                "in_reply_to": original_email['message_id'],
                "references": original_email['message_id'],
                "status": "new",
                "created_at": datetime.utcnow()
            }
            
            await self.db.emails.insert_one(reply_email)
            print(f"   Created test reply email: {reply_email['id']}")
            
            # Test 3c: Process the reply email through the system
            try:
                # Import and call process_email_async
                sys.path.append('/app/backend')
                from server import process_email_async
                
                print("   Processing reply email through process_email_async...")
                await process_email_async(reply_email['id'])
                
                # Wait a moment for processing
                await asyncio.sleep(2)
                
                # Check if follow-up was cancelled
                updated_follow_up = await self.db.follow_up_emails.find_one({"id": follow_up['id']})
                
                if updated_follow_up:
                    follow_up_cancelled = updated_follow_up.get('status') == 'cancelled'
                    response_detected = updated_follow_up.get('response_received', False)
                    
                    process_test_passed = follow_up_cancelled or response_detected
                    process_details = f"Follow-up status: {updated_follow_up.get('status')}, Response detected: {response_detected}"
                    
                    print(f"   Follow-up after processing: Status={updated_follow_up.get('status')}, Response received={response_detected}")
                    
                else:
                    process_test_passed = False
                    process_details = "Follow-up not found after processing"
                    
            except Exception as e:
                process_test_passed = False
                process_details = f"Processing error: {str(e)}"
                print(f"   Processing error: {str(e)}")
            
            # Test 3d: Test response detection criteria
            try:
                # Check if the system correctly identifies this as a response
                # Same thread_id, same sender, received after original
                
                criteria_passed = True
                criteria_details = []
                
                # Thread ID match
                thread_match = reply_email['thread_id'] == original_email['thread_id']
                criteria_details.append(f"Thread match: {thread_match}")
                
                # Sender match
                sender_match = reply_email['sender'] == original_email['sender']
                criteria_details.append(f"Sender match: {sender_match}")
                
                # Timing (reply after original)
                timing_correct = reply_email['received_at'] > original_email['received_at']
                criteria_details.append(f"Timing correct: {timing_correct}")
                
                # In-reply-to header
                reply_to_match = reply_email.get('in_reply_to') == original_email['message_id']
                criteria_details.append(f"Reply-to match: {reply_to_match}")
                
                criteria_test_passed = thread_match and sender_match and timing_correct
                criteria_test_details = ", ".join(criteria_details)
                
                print(f"   Response detection criteria: {criteria_test_details}")
                
            except Exception as e:
                criteria_test_passed = False
                criteria_test_details = f"Criteria test error: {str(e)}"
            
            # Cleanup test data
            await self.db.emails.delete_one({"id": original_email['id']})
            await self.db.emails.delete_one({"id": reply_email['id']})
            await self.db.follow_up_emails.delete_one({"id": follow_up['id']})
            
            all_passed = process_test_passed and criteria_test_passed
            
            details = f"Processing: {process_details}, Criteria: {criteria_test_details}"
            
            self.log_test_result("Response Detection Logic", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Response Detection Logic", False, f"Exception: {str(e)}")
    
    async def test_background_service(self):
        """Test 4: Background Service - Test the periodic response_detection_service() that runs every 5 minutes"""
        print("\n⏰ Testing Background Service...")
        
        try:
            # Test 4a: Check if background service is running
            # Look for evidence of the service in logs or database
            
            # Check recent follow-up updates that might indicate background processing
            recent_time = datetime.utcnow() - timedelta(minutes=30)
            recent_updates = await self.db.follow_up_emails.find({
                "updated_at": {"$gte": recent_time}
            }).to_list(100)
            
            background_activity = len(recent_updates) > 0
            
            print(f"   Found {len(recent_updates)} follow-up updates in last 30 minutes")
            
            # Test 4b: Check for cancelled follow-ups (evidence of response detection)
            cancelled_follow_ups = await self.db.follow_up_emails.find({
                "status": "cancelled"
            }).to_list(100)
            
            cancellation_activity = len(cancelled_follow_ups) > 0
            
            print(f"   Found {len(cancelled_follow_ups)} cancelled follow-ups")
            
            # Test 4c: Analyze response_received flags
            follow_ups_with_responses = await self.db.follow_up_emails.find({
                "response_received": True
            }).to_list(100)
            
            response_detection_activity = len(follow_ups_with_responses) > 0
            
            print(f"   Found {len(follow_ups_with_responses)} follow-ups with detected responses")
            
            # Test 4d: Check for follow-ups that should have been processed
            # Find pending follow-ups with recent email activity in their threads
            pending_follow_ups = await self.db.follow_up_emails.find({
                "status": "pending"
            }).to_list(100)
            
            potentially_missed = 0
            
            for follow_up in pending_follow_ups:
                thread_id = follow_up.get('thread_id')
                if thread_id:
                    # Check for recent emails in this thread
                    recent_emails = await self.db.emails.find({
                        "thread_id": thread_id,
                        "received_at": {"$gte": follow_up.get('created_at', datetime.utcnow())}
                    }).to_list(10)
                    
                    # Check if any are from the same sender as the follow-up recipient
                    recipient_email = follow_up.get('recipient_email')
                    if recipient_email:
                        for email in recent_emails:
                            if email.get('sender', '').lower() == recipient_email.lower():
                                potentially_missed += 1
                                break
            
            print(f"   Found {potentially_missed} potentially missed response detections")
            
            # Test 4e: Service effectiveness analysis
            total_follow_ups = await self.db.follow_up_emails.count_documents({})
            pending_follow_ups_count = await self.db.follow_up_emails.count_documents({"status": "pending"})
            cancelled_follow_ups_count = len(cancelled_follow_ups)
            
            if total_follow_ups > 0:
                cancellation_rate = (cancelled_follow_ups_count / total_follow_ups) * 100
                pending_rate = (pending_follow_ups_count / total_follow_ups) * 100
            else:
                cancellation_rate = 0
                pending_rate = 0
            
            service_effectiveness = cancellation_rate > 0 and potentially_missed < (pending_follow_ups_count * 0.1)  # Less than 10% missed
            
            effectiveness_details = f"Total: {total_follow_ups}, Pending: {pending_follow_ups_count} ({pending_rate:.1f}%), Cancelled: {cancelled_follow_ups_count} ({cancellation_rate:.1f}%), Potentially missed: {potentially_missed}"
            
            print(f"   Service effectiveness: {effectiveness_details}")
            
            all_passed = (background_activity or cancellation_activity or response_detection_activity) and service_effectiveness
            
            details = f"Recent activity: {background_activity}, Cancellations: {cancellation_activity}, Response detection: {response_detection_activity}, Effectiveness: {service_effectiveness}, {effectiveness_details}"
            
            self.log_test_result("Background Service", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Background Service", False, f"Exception: {str(e)}")
    
    async def test_database_queries(self):
        """Test 5: Database Queries - Check if pending follow-ups exist and analyze thread relationships"""
        print("\n🗄️ Testing Database Queries...")
        
        try:
            # Test 5a: Complex query for pending follow-ups with thread analysis
            pending_with_threads = await self.db.follow_up_emails.aggregate([
                {"$match": {"status": "pending"}},
                {"$lookup": {
                    "from": "emails",
                    "localField": "thread_id",
                    "foreignField": "thread_id",
                    "as": "thread_emails"
                }},
                {"$addFields": {
                    "thread_email_count": {"$size": "$thread_emails"},
                    "latest_email_date": {"$max": "$thread_emails.received_at"}
                }}
            ]).to_list(1000)
            
            complex_query_passed = True
            
            print(f"   Found {len(pending_with_threads)} pending follow-ups with thread data")
            
            # Analyze results
            follow_ups_with_recent_activity = 0
            follow_ups_without_threads = 0
            
            for follow_up in pending_with_threads:
                thread_count = follow_up.get('thread_email_count', 0)
                latest_date = follow_up.get('latest_email_date')
                
                if thread_count == 0:
                    follow_ups_without_threads += 1
                
                if latest_date and latest_date > follow_up.get('created_at', datetime.utcnow()):
                    follow_ups_with_recent_activity += 1
            
            query_analysis = f"With recent activity: {follow_ups_with_recent_activity}, Without threads: {follow_ups_without_threads}"
            print(f"   Analysis: {query_analysis}")
            
            # Test 5b: Thread relationship integrity check
            thread_integrity_issues = []
            
            # Check for follow-ups with invalid thread references
            all_follow_ups = await self.db.follow_up_emails.find().to_list(1000)
            all_thread_ids = set()
            
            for follow_up in all_follow_ups:
                thread_id = follow_up.get('thread_id')
                if thread_id:
                    all_thread_ids.add(thread_id)
            
            # Check if these threads exist in emails collection
            for thread_id in all_thread_ids:
                email_count = await self.db.emails.count_documents({"thread_id": thread_id})
                if email_count == 0:
                    thread_integrity_issues.append(thread_id)
            
            integrity_passed = len(thread_integrity_issues) == 0
            integrity_details = f"Orphaned threads: {len(thread_integrity_issues)}"
            
            print(f"   Thread integrity: {integrity_details}")
            
            # Test 5c: Response detection query patterns
            # Find follow-ups that should be cancelled based on thread activity
            should_be_cancelled = []
            
            for follow_up in pending_with_threads:
                thread_emails = follow_up.get('thread_emails', [])
                recipient_email = follow_up.get('recipient_email', '').lower()
                follow_up_created = follow_up.get('created_at', datetime.utcnow())
                
                # Check for emails from recipient after follow-up was created
                for email in thread_emails:
                    email_sender = email.get('sender', '').lower()
                    email_received = email.get('received_at', datetime.utcnow())
                    
                    if (email_sender == recipient_email and 
                        email_received > follow_up_created):
                        should_be_cancelled.append(follow_up['id'])
                        break
            
            detection_query_passed = True
            detection_details = f"Should be cancelled: {len(should_be_cancelled)}"
            
            print(f"   Response detection query: {detection_details}")
            
            # Test 5d: Performance of key queries
            import time
            
            # Time critical queries
            start_time = time.time()
            pending_count = await self.db.follow_up_emails.count_documents({"status": "pending"})
            pending_query_time = time.time() - start_time
            
            start_time = time.time()
            recent_emails = await self.db.emails.find({
                "received_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
            }).to_list(100)
            recent_emails_query_time = time.time() - start_time
            
            performance_passed = pending_query_time < 1.0 and recent_emails_query_time < 2.0
            performance_details = f"Pending query: {pending_query_time:.3f}s, Recent emails: {recent_emails_query_time:.3f}s"
            
            print(f"   Query performance: {performance_details}")
            
            all_passed = complex_query_passed and integrity_passed and detection_query_passed and performance_passed
            
            details = f"Complex query: {complex_query_passed}, Integrity: {integrity_details}, Detection: {detection_details}, Performance: {performance_details}"
            
            self.log_test_result("Database Queries", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Database Queries", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("FOLLOW-UP CANCELLATION SYSTEM TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {(len(passed_tests)/len(self.test_results)*100):.1f}%")
        
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
    print("🚀 Starting Follow-up Cancellation System Comprehensive Testing...")
    
    tester = FollowUpCancellationTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, exiting...")
        return
    
    try:
        # Run all tests
        await tester.test_follow_up_status_check()
        await tester.test_thread_detection()
        await tester.test_response_detection_logic()
        await tester.test_background_service()
        await tester.test_database_queries()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())