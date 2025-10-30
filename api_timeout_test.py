#!/usr/bin/env python3
"""
Focused API Timeout Fix Testing for Production Readiness
Tests the /api/emails/test endpoint timeout fix with Redis fallback and follow-up cancellation
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid
import concurrent.futures
import threading

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://setup-redis-sync.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class APITimeoutTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.test_account = None
        
    async def setup(self):
        """Setup database connection and get test account"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            
            # Get the default test account (rohushanshinde@gmail.com)
            account = await self.db.email_accounts.find_one({"email": "rohushanshinde@gmail.com"})
            if not account:
                # Get any active account
                account = await self.db.email_accounts.find_one({"is_active": True})
            
            if not account:
                print("❌ No active email accounts found")
                return False
                
            self.test_account = account
            print(f"✅ Using test account: {account['email']}")
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
    
    def test_api_timeout_fix_immediate_response(self):
        """Test 1: API Timeout Fix - /api/emails/test returns immediately (within 3 seconds)"""
        print("\n🚀 Testing API Timeout Fix - Immediate Response...")
        
        if not self.test_account:
            self.log_test_result("API Timeout Fix - Immediate Response", False, "No test account available")
            return
        
        test_email_data = {
            "subject": "API Timeout Test - Immediate Response",
            "body": "Testing the API timeout fix with Redis fallback. This should return immediately with background processing.",
            "sender": "timeout.test@example.com",
            "account_id": self.test_account['id']
        }
        
        try:
            print("   Sending request to /api/emails/test...")
            start_time = time.time()
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=10)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"   Response time: {response_time:.2f} seconds")
            
            # Check if response is immediate (within 3 seconds)
            immediate_response = response_time <= 3.0
            
            # Check response structure
            if response.status_code in [200, 201]:
                response_data = response.json()
                has_email_id = 'email_id' in response_data
                has_status_queued = response_data.get('status') == 'queued'
                has_processing_method = 'processing_method' in response_data
                processing_method = response_data.get('processing_method', '')
                
                print(f"   Response data: {response_data}")
                print(f"   Processing method: {processing_method}")
                
                # Check if it's using background_tasks fallback (expected when Redis unavailable)
                using_fallback = processing_method == 'background_tasks'
                
                structure_correct = has_email_id and has_status_queued and has_processing_method
                
                all_passed = immediate_response and structure_correct
                
                details = f"Response time: {response_time:.2f}s, Status: {response.status_code}, " \
                         f"Structure correct: {structure_correct}, Processing: {processing_method}, " \
                         f"Using fallback: {using_fallback}"
                
                # Store email_id for polling test
                self.test_email_id = response_data.get('email_id')
                
            else:
                all_passed = False
                details = f"Response time: {response_time:.2f}s, Status: {response.status_code}, " \
                         f"Error: {response.text[:200]}"
                self.test_email_id = None
            
            self.log_test_result("API Timeout Fix - Immediate Response", all_passed, details)
            
        except Exception as e:
            self.log_test_result("API Timeout Fix - Immediate Response", False, f"Exception: {str(e)}")
            self.test_email_id = None
    
    def test_background_processing_polling(self):
        """Test 2: Background Processing - Poll email status and verify workflow progression"""
        print("\n📊 Testing Background Processing - Status Polling...")
        
        if not hasattr(self, 'test_email_id') or not self.test_email_id:
            self.log_test_result("Background Processing - Status Polling", False, "No test email ID from previous test")
            return
        
        try:
            print(f"   Polling email status for ID: {self.test_email_id}")
            
            # Poll for up to 60 seconds to see status progression
            max_polls = 12  # 12 polls * 5 seconds = 60 seconds max
            poll_interval = 5
            status_progression = []
            
            for poll_count in range(max_polls):
                try:
                    response = requests.get(f"{API_BASE}/emails/{self.test_email_id}", timeout=10)
                    
                    if response.status_code == 200:
                        email_data = response.json()
                        current_status = email_data.get('status', 'unknown')
                        status_progression.append(current_status)
                        
                        print(f"   Poll {poll_count + 1}: Status = {current_status}")
                        
                        # Check if we've reached a final status
                        if current_status in ['ready_to_send', 'sent', 'error', 'send_failed']:
                            print(f"   Final status reached: {current_status}")
                            break
                            
                        # Check for expected progression
                        if current_status in ['classifying', 'generating_draft', 'validating']:
                            print(f"   Processing stage: {current_status}")
                    else:
                        print(f"   Poll {poll_count + 1}: HTTP {response.status_code}")
                        status_progression.append(f"HTTP_{response.status_code}")
                    
                    if poll_count < max_polls - 1:  # Don't sleep on last iteration
                        time.sleep(poll_interval)
                        
                except Exception as e:
                    print(f"   Poll {poll_count + 1}: Error - {str(e)}")
                    status_progression.append(f"ERROR_{str(e)[:20]}")
            
            # Analyze status progression
            unique_statuses = list(dict.fromkeys(status_progression))  # Remove duplicates while preserving order
            print(f"   Status progression: {' → '.join(unique_statuses)}")
            
            # Check if processing progressed beyond 'queued'
            processing_started = any(status in ['classifying', 'generating_draft', 'validating', 'ready_to_send', 'sent'] 
                                   for status in unique_statuses)
            
            # Check if we saw expected workflow stages
            expected_stages = ['queued', 'classifying', 'generating_draft', 'validating']
            workflow_progression = any(stage in unique_statuses for stage in expected_stages[1:])  # Skip 'queued'
            
            # Final status check
            final_status = unique_statuses[-1] if unique_statuses else 'unknown'
            completed_successfully = final_status in ['ready_to_send', 'sent']
            
            all_passed = processing_started and workflow_progression
            
            details = f"Progression: {' → '.join(unique_statuses)}, " \
                     f"Processing started: {processing_started}, " \
                     f"Workflow progression: {workflow_progression}, " \
                     f"Final status: {final_status}"
            
            self.log_test_result("Background Processing - Status Polling", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Background Processing - Status Polling", False, f"Exception: {str(e)}")
    
    def test_concurrent_requests_no_blocking(self):
        """Test 3: Concurrent Requests - Ensure no blocking with 2-3 concurrent requests"""
        print("\n🔄 Testing Concurrent Requests - No Blocking...")
        
        if not self.test_account:
            self.log_test_result("Concurrent Requests - No Blocking", False, "No test account available")
            return
        
        def send_test_request(request_id):
            """Send a single test request"""
            test_data = {
                "subject": f"Concurrent Test {request_id}",
                "body": f"Testing concurrent request {request_id} for non-blocking behavior.",
                "sender": f"concurrent.test{request_id}@example.com",
                "account_id": self.test_account['id']
            }
            
            start_time = time.time()
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=10)
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code in [200, 201],
                    'response_data': response.json() if response.status_code in [200, 201] else None,
                    'error': None
                }
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                return {
                    'request_id': request_id,
                    'status_code': 0,
                    'response_time': response_time,
                    'success': False,
                    'response_data': None,
                    'error': str(e)
                }
        
        try:
            print("   Sending 3 concurrent requests...")
            
            # Use ThreadPoolExecutor to send concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all requests simultaneously
                futures = [executor.submit(send_test_request, i+1) for i in range(3)]
                
                # Collect results
                results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    results.append(result)
                    print(f"   Request {result['request_id']}: {result['response_time']:.2f}s, "
                          f"Status: {result['status_code']}, Success: {result['success']}")
            
            # Sort results by request_id for consistent reporting
            results.sort(key=lambda x: x['request_id'])
            
            # Analyze results
            all_successful = all(r['success'] for r in results)
            all_fast = all(r['response_time'] <= 5.0 for r in results)  # All should be fast (non-blocking)
            max_response_time = max(r['response_time'] for r in results)
            avg_response_time = sum(r['response_time'] for r in results) / len(results)
            
            # Check if all requests returned immediately (non-blocking behavior)
            non_blocking = all_fast and max_response_time <= 5.0
            
            all_passed = all_successful and non_blocking
            
            details = f"All successful: {all_successful}, Non-blocking: {non_blocking}, " \
                     f"Max time: {max_response_time:.2f}s, Avg time: {avg_response_time:.2f}s"
            
            self.log_test_result("Concurrent Requests - No Blocking", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Concurrent Requests - No Blocking", False, f"Exception: {str(e)}")
    
    async def test_follow_up_cancellation_email_normalization(self):
        """Test 4: Follow-up Cancellation - Email normalization functions still work"""
        print("\n📧 Testing Follow-up Cancellation - Email Normalization...")
        
        try:
            # Import the normalization function
            sys.path.append('/app/backend')
            from server import normalize_email_for_matching
            
            # Test various email normalization scenarios
            test_cases = [
                # Gmail aliases (+ tags)
                ("testuser+sales@gmail.com", "testuser@gmail.com"),
                ("user+tag+more@gmail.com", "user@gmail.com"),
                
                # Gmail dots
                ("test.user@gmail.com", "testuser@gmail.com"),
                ("t.e.s.t.u.s.e.r@gmail.com", "testuser@gmail.com"),
                
                # Case insensitive
                ("TEST@EXAMPLE.COM", "test@example.com"),
                ("User@Example.Com", "user@example.com"),
                
                # Combined cases
                ("Test.User+Tag@Gmail.Com", "testuser@gmail.com"),
                
                # Non-Gmail (should only normalize case)
                ("User@Yahoo.Com", "user@yahoo.com"),
                ("TEST+tag@outlook.com", "test+tag@outlook.com"),  # Non-Gmail keeps + tags
            ]
            
            all_passed = True
            failed_cases = []
            
            for input_email, expected_output in test_cases:
                try:
                    normalized = normalize_email_for_matching(input_email)
                    if normalized == expected_output:
                        print(f"   ✅ {input_email} → {normalized}")
                    else:
                        print(f"   ❌ {input_email} → {normalized} (expected: {expected_output})")
                        all_passed = False
                        failed_cases.append(f"{input_email} → {normalized} (expected: {expected_output})")
                except Exception as e:
                    print(f"   ❌ {input_email} → ERROR: {str(e)}")
                    all_passed = False
                    failed_cases.append(f"{input_email} → ERROR: {str(e)}")
            
            # Test the cancellation logic with normalized emails
            print("   Testing follow-up cancellation logic...")
            
            # Create a test scenario in database
            test_email_id = str(uuid.uuid4())
            test_thread_id = f"thread-{uuid.uuid4()}"
            
            # Create a test follow-up
            follow_up_data = {
                "id": str(uuid.uuid4()),
                "original_email_id": test_email_id,
                "account_id": self.test_account['id'] if self.test_account else "test-account",
                "user_id": "test-user",
                "thread_id": test_thread_id,
                "recipient_email": "test.user+sales@gmail.com",  # Email with dots and + tag
                "subject": "Follow-up Test",
                "status": "pending",
                "follow_up_number": 1,
                "scheduled_time": datetime.utcnow() + timedelta(hours=24),
                "created_at": datetime.utcnow()
            }
            
            await self.db.follow_up_emails.insert_one(follow_up_data)
            
            # Test cancellation with normalized email
            from server import cancel_follow_ups_for_recipient
            
            # This should match the follow-up even though the email format is different
            cancelled_count = await cancel_follow_ups_for_recipient(
                "testuser@gmail.com",  # Normalized version
                test_thread_id
            )
            
            cancellation_worked = cancelled_count > 0
            
            # Cleanup
            await self.db.follow_up_emails.delete_one({"id": follow_up_data["id"]})
            
            print(f"   Follow-up cancellation test: {cancelled_count} follow-ups cancelled")
            
            overall_passed = all_passed and cancellation_worked
            
            details = f"Normalization: {len(test_cases) - len(failed_cases)}/{len(test_cases)} passed, " \
                     f"Cancellation: {cancellation_worked}, Failed cases: {len(failed_cases)}"
            
            if failed_cases:
                details += f", Failures: {'; '.join(failed_cases[:3])}"  # Show first 3 failures
            
            self.log_test_result("Follow-up Cancellation - Email Normalization", overall_passed, details)
            
        except Exception as e:
            self.log_test_result("Follow-up Cancellation - Email Normalization", False, f"Exception: {str(e)}")
    
    def test_redis_fallback_logging(self):
        """Test 5: Redis Fallback - Check for fallback logging messages"""
        print("\n🔄 Testing Redis Fallback - Logging Messages...")
        
        try:
            # Check backend logs for fallback messages
            import subprocess
            
            # Get recent backend logs
            try:
                result = subprocess.run(
                    ['tail', '-n', '100', '/var/log/supervisor/backend.out.log'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    log_content = result.stdout
                    
                    # Look for fallback messages
                    fallback_messages = [
                        "falling back to background tasks",
                        "RQ enqueue failed",
                        "Redis connection failed",
                        "background_tasks",
                        "BackgroundTasks fallback"
                    ]
                    
                    found_messages = []
                    for message in fallback_messages:
                        if message.lower() in log_content.lower():
                            found_messages.append(message)
                    
                    # Look for Redis connection errors
                    redis_errors = [
                        "Error 99 connecting to localhost:6379",
                        "Cannot assign requested address",
                        "Connection refused"
                    ]
                    
                    found_errors = []
                    for error in redis_errors:
                        if error in log_content:
                            found_errors.append(error)
                    
                    has_fallback_logs = len(found_messages) > 0
                    has_redis_errors = len(found_errors) > 0
                    
                    print(f"   Found fallback messages: {found_messages}")
                    print(f"   Found Redis errors: {found_errors}")
                    
                    # The system should be using fallback when Redis is unavailable
                    fallback_working = has_fallback_logs or has_redis_errors
                    
                    details = f"Fallback logs: {has_fallback_logs}, Redis errors: {has_redis_errors}, " \
                             f"Messages: {', '.join(found_messages[:3])}"
                    
                    self.log_test_result("Redis Fallback - Logging Messages", fallback_working, details)
                    
                else:
                    self.log_test_result("Redis Fallback - Logging Messages", False, 
                                       f"Could not read backend logs: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                self.log_test_result("Redis Fallback - Logging Messages", False, "Log reading timeout")
            except FileNotFoundError:
                self.log_test_result("Redis Fallback - Logging Messages", False, "Backend log file not found")
                
        except Exception as e:
            self.log_test_result("Redis Fallback - Logging Messages", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 API TIMEOUT FIX & FOLLOW-UP CANCELLATION TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        print("\n✅ PASSED TESTS:")
        for test in passed_tests:
            print(f"   • {test['test']}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting API Timeout Fix & Follow-up Cancellation Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = APITimeoutTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        print(f"\n🎯 FOCUSED TESTING AS REQUESTED:")
        print("1. API Timeout Fix with Fallback - /api/emails/test Endpoint")
        print("2. Verify Follow-up Cancellation Still Works")
        print("3. Test with default account (rohushanshinde@gmail.com)")
        print("4. Complete testing in under 5 minutes")
        
        # Run focused tests as requested
        tester.test_api_timeout_fix_immediate_response()
        tester.test_background_processing_polling()
        tester.test_concurrent_requests_no_blocking()
        await tester.test_follow_up_cancellation_email_normalization()
        tester.test_redis_fallback_logging()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())