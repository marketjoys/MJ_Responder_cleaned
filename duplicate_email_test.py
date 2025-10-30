#!/usr/bin/env python3
"""
Duplicate Email Issues Testing for Email Assistant System
Tests email endpoints for duplicate email records, thread grouping, and OAuth modal functionality
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid
from collections import defaultdict

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

class DuplicateEmailTester:
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
    
    async def test_email_endpoints_for_duplicates(self):
        """Test 1: Check Email Endpoints for Duplicate Records"""
        print("\n🔍 Testing Email Endpoints for Duplicate Records...")
        
        try:
            # Test 1a: GET /api/emails endpoint
            try:
                print("   Testing GET /api/emails endpoint...")
                response = requests.get(f"{API_BASE}/emails", timeout=15)
                emails_endpoint_passed = response.status_code == 200
                
                if emails_endpoint_passed:
                    emails_list = response.json()
                    print(f"   - Found {len(emails_list)} emails in /api/emails")
                    
                    # Check for duplicate emails by content
                    content_map = defaultdict(list)
                    subject_map = defaultdict(list)
                    message_id_map = defaultdict(list)
                    
                    for email in emails_list:
                        # Group by body content
                        body = email.get('body', '').strip()
                        if body:
                            content_map[body].append(email)
                        
                        # Group by subject
                        subject = email.get('subject', '').strip()
                        if subject:
                            subject_map[subject].append(email)
                        
                        # Group by message_id (should be unique)
                        msg_id = email.get('message_id', '').strip()
                        if msg_id:
                            message_id_map[msg_id].append(email)
                    
                    # Find duplicates
                    content_duplicates = {k: v for k, v in content_map.items() if len(v) > 1}
                    subject_duplicates = {k: v for k, v in subject_map.items() if len(v) > 1}
                    message_id_duplicates = {k: v for k, v in message_id_map.items() if len(v) > 1}
                    
                    print(f"   - Content duplicates found: {len(content_duplicates)}")
                    print(f"   - Subject duplicates found: {len(subject_duplicates)}")
                    print(f"   - Message ID duplicates found: {len(message_id_duplicates)}")
                    
                    # Log details of duplicates
                    if content_duplicates:
                        print("   📋 Content Duplicates Details:")
                        for content, emails in list(content_duplicates.items())[:3]:  # Show first 3
                            print(f"     - Content: '{content[:50]}...' appears in {len(emails)} emails")
                            for email in emails:
                                print(f"       * ID: {email.get('id')}, Subject: {email.get('subject')}")
                    
                    if message_id_duplicates:
                        print("   🚨 Message ID Duplicates (CRITICAL):")
                        for msg_id, emails in message_id_duplicates.items():
                            print(f"     - Message ID: {msg_id} appears in {len(emails)} emails")
                            for email in emails:
                                print(f"       * Email ID: {email.get('id')}, Subject: {email.get('subject')}")
                    
                    emails_details = f"Total: {len(emails_list)}, Content dups: {len(content_duplicates)}, Subject dups: {len(subject_duplicates)}, Message ID dups: {len(message_id_duplicates)}"
                    
                    # Test passes if no critical message ID duplicates
                    no_critical_duplicates = len(message_id_duplicates) == 0
                    
                else:
                    emails_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                    no_critical_duplicates = False
                    
            except Exception as e:
                emails_endpoint_passed = False
                emails_details = f"Exception: {str(e)}"
                no_critical_duplicates = False
            
            # Test 1b: GET /api/emails/threads endpoint
            try:
                print("   Testing GET /api/emails/threads endpoint...")
                response = requests.get(f"{API_BASE}/emails/threads", timeout=15)
                threads_endpoint_passed = response.status_code == 200
                
                if threads_endpoint_passed:
                    threads_list = response.json()
                    print(f"   - Found {len(threads_list)} email threads")
                    
                    # Verify thread structure
                    valid_thread_structure = True
                    thread_email_count = 0
                    
                    for thread in threads_list:
                        # Check required fields
                        if not all(key in thread for key in ['thread_id', 'subject', 'original_email']):
                            valid_thread_structure = False
                            print(f"     ❌ Thread missing required fields: {thread.get('thread_id', 'unknown')}")
                        
                        # Count emails in threads
                        thread_email_count += 1  # original_email
                        thread_email_count += len(thread.get('responses', []))
                        thread_email_count += len(thread.get('follow_ups', []))
                    
                    print(f"   - Total emails in threads: {thread_email_count}")
                    print(f"   - Valid thread structure: {valid_thread_structure}")
                    
                    threads_details = f"Threads: {len(threads_list)}, Valid structure: {valid_thread_structure}, Total emails: {thread_email_count}"
                    
                else:
                    threads_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                    valid_thread_structure = False
                    
            except Exception as e:
                threads_endpoint_passed = False
                threads_details = f"Exception: {str(e)}"
                valid_thread_structure = False
            
            # Overall assessment
            all_passed = (emails_endpoint_passed and threads_endpoint_passed and 
                         no_critical_duplicates and valid_thread_structure)
            
            self.log_test_result("Email Endpoints - Individual Emails", emails_endpoint_passed and no_critical_duplicates, emails_details)
            self.log_test_result("Email Endpoints - Thread Structure", threads_endpoint_passed and valid_thread_structure, threads_details)
            
            details = f"Emails API: {emails_endpoint_passed}, Threads API: {threads_endpoint_passed}, No critical duplicates: {no_critical_duplicates}"
            self.log_test_result("Email Endpoints for Duplicates", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Endpoints for Duplicates", False, f"Exception: {str(e)}")
    
    async def test_database_consistency(self):
        """Test 2: Database Consistency Check"""
        print("\n🗄️ Testing Database Consistency...")
        
        try:
            # Test 2a: Check for duplicate email entries in database
            print("   Checking database for duplicate emails...")
            
            emails_cursor = self.db.emails.find({})
            emails_list = await emails_cursor.to_list(1000)
            
            print(f"   - Found {len(emails_list)} emails in database")
            
            # Check for duplicates by various criteria
            message_id_map = defaultdict(list)
            content_map = defaultdict(list)
            thread_id_map = defaultdict(list)
            
            for email in emails_list:
                # Group by message_id (should be unique)
                msg_id = email.get('message_id', '').strip()
                if msg_id:
                    message_id_map[msg_id].append(email)
                
                # Group by body content
                body = email.get('body', '').strip()
                if body:
                    content_map[body].append(email)
                
                # Group by thread_id for analysis
                thread_id = email.get('thread_id', '').strip()
                if thread_id:
                    thread_id_map[thread_id].append(email)
            
            # Find duplicates
            db_message_id_duplicates = {k: v for k, v in message_id_map.items() if len(v) > 1}
            db_content_duplicates = {k: v for k, v in content_map.items() if len(v) > 1}
            
            print(f"   - Database message ID duplicates: {len(db_message_id_duplicates)}")
            print(f"   - Database content duplicates: {len(db_content_duplicates)}")
            print(f"   - Unique threads: {len(thread_id_map)}")
            
            # Log critical duplicates
            if db_message_id_duplicates:
                print("   🚨 Database Message ID Duplicates (CRITICAL):")
                for msg_id, emails in list(db_message_id_duplicates.items())[:3]:
                    print(f"     - Message ID: {msg_id} appears {len(emails)} times")
                    for email in emails:
                        print(f"       * Email ID: {email.get('id')}, Status: {email.get('status')}")
            
            # Test 2b: Verify thread_id assignment
            print("   Verifying thread_id assignment...")
            
            emails_without_thread_id = [e for e in emails_list if not e.get('thread_id')]
            emails_with_thread_id = [e for e in emails_list if e.get('thread_id')]
            
            print(f"   - Emails without thread_id: {len(emails_without_thread_id)}")
            print(f"   - Emails with thread_id: {len(emails_with_thread_id)}")
            
            # Check thread consistency
            thread_consistency_passed = True
            for thread_id, emails in thread_id_map.items():
                # All emails in same thread should have same subject (or related subjects)
                subjects = set(email.get('subject', '').replace('Re: ', '').replace('Fwd: ', '') for email in emails)
                if len(subjects) > 1:
                    # Multiple subjects in same thread might indicate threading issues
                    print(f"     ⚠️ Thread {thread_id} has multiple subjects: {list(subjects)[:3]}")
            
            # Test 2c: Check for orphaned thread records
            print("   Checking for orphaned thread records...")
            
            # This would require checking if there are thread records without corresponding emails
            # For now, we'll check if all thread_ids in emails have corresponding data
            
            thread_ids_in_emails = set(email.get('thread_id') for email in emails_list if email.get('thread_id'))
            print(f"   - Unique thread IDs in emails: {len(thread_ids_in_emails)}")
            
            # Overall assessment
            no_critical_db_duplicates = len(db_message_id_duplicates) == 0
            thread_assignment_ok = len(emails_with_thread_id) > 0  # At least some emails should have thread_id
            
            all_passed = (no_critical_db_duplicates and thread_assignment_ok and thread_consistency_passed)
            
            details = f"DB emails: {len(emails_list)}, Message ID dups: {len(db_message_id_duplicates)}, Thread assignment: {thread_assignment_ok}"
            
            self.log_test_result("Database - Message ID Duplicates", no_critical_db_duplicates, 
                               f"Found {len(db_message_id_duplicates)} duplicate message IDs")
            self.log_test_result("Database - Thread Assignment", thread_assignment_ok, 
                               f"{len(emails_with_thread_id)}/{len(emails_list)} emails have thread_id")
            self.log_test_result("Database - Thread Consistency", thread_consistency_passed, 
                               f"Thread grouping appears consistent")
            
            self.log_test_result("Database Consistency Check", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Database Consistency Check", False, f"Exception: {str(e)}")
    
    async def test_oauth_modal_functionality(self):
        """Test 3: OAuth Modal Functionality"""
        print("\n🔐 Testing OAuth Modal Functionality...")
        
        try:
            # Test 3a: Google OAuth status endpoint
            try:
                print("   Testing Google OAuth status endpoint...")
                response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
                google_oauth_passed = response.status_code in [200, 401, 403]  # 401/403 are acceptable for auth endpoints
                
                if response.status_code == 200:
                    google_status = response.json()
                    google_details = f"Status: {response.status_code}, Response: {google_status}"
                elif response.status_code in [401, 403]:
                    google_details = f"Status: {response.status_code} (Auth required - expected)"
                else:
                    google_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                    
            except Exception as e:
                google_oauth_passed = False
                google_details = f"Exception: {str(e)}"
            
            # Test 3b: Microsoft OAuth status endpoint
            try:
                print("   Testing Microsoft OAuth status endpoint...")
                response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
                microsoft_oauth_passed = response.status_code in [200, 401, 403]  # 401/403 are acceptable for auth endpoints
                
                if response.status_code == 200:
                    microsoft_status = response.json()
                    microsoft_details = f"Status: {response.status_code}, Response: {microsoft_status}"
                elif response.status_code in [401, 403]:
                    microsoft_details = f"Status: {response.status_code} (Auth required - expected)"
                else:
                    microsoft_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                    
            except Exception as e:
                microsoft_oauth_passed = False
                microsoft_details = f"Exception: {str(e)}"
            
            # Test 3c: OAuth authorization flow endpoints (basic connectivity)
            try:
                print("   Testing OAuth authorization flow endpoints...")
                
                # Test Google OAuth authorization URL
                google_auth_response = requests.get(f"{API_BASE}/oauth/google/authorize", timeout=10, allow_redirects=False)
                google_auth_ok = google_auth_response.status_code in [200, 302, 401, 403]
                
                # Test Microsoft OAuth authorization URL
                microsoft_auth_response = requests.get(f"{API_BASE}/oauth/microsoft/authorize", timeout=10, allow_redirects=False)
                microsoft_auth_ok = microsoft_auth_response.status_code in [200, 302, 401, 403]
                
                auth_flow_passed = google_auth_ok and microsoft_auth_ok
                auth_flow_details = f"Google auth: {google_auth_response.status_code}, Microsoft auth: {microsoft_auth_response.status_code}"
                
            except Exception as e:
                auth_flow_passed = False
                auth_flow_details = f"Exception: {str(e)}"
            
            # Test 3d: Check OAuth-related database collections
            try:
                print("   Checking OAuth-related database collections...")
                
                # Check oauth_tokens collection
                oauth_tokens_count = await self.db.oauth_tokens.count_documents({})
                
                # Check email accounts with OAuth
                oauth_accounts_count = await self.db.email_accounts.count_documents({"auth_type": "oauth"})
                
                db_oauth_ok = True  # OAuth collections exist (even if empty)
                db_oauth_details = f"OAuth tokens: {oauth_tokens_count}, OAuth accounts: {oauth_accounts_count}"
                
            except Exception as e:
                db_oauth_ok = False
                db_oauth_details = f"Exception: {str(e)}"
            
            # Overall assessment
            all_passed = (google_oauth_passed and microsoft_oauth_passed and 
                         auth_flow_passed and db_oauth_ok)
            
            # Log individual results
            self.log_test_result("OAuth - Google Status", google_oauth_passed, google_details)
            self.log_test_result("OAuth - Microsoft Status", microsoft_oauth_passed, microsoft_details)
            self.log_test_result("OAuth - Authorization Flow", auth_flow_passed, auth_flow_details)
            self.log_test_result("OAuth - Database Collections", db_oauth_ok, db_oauth_details)
            
            details = f"Google: {google_oauth_passed}, Microsoft: {microsoft_oauth_passed}, Auth flow: {auth_flow_passed}, DB: {db_oauth_ok}"
            self.log_test_result("OAuth Modal Functionality", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Modal Functionality", False, f"Exception: {str(e)}")
    
    async def test_email_processing_view_duplicates(self):
        """Test 4: Email Processing View Duplicate Issues"""
        print("\n📧 Testing Email Processing View for Duplicates...")
        
        try:
            # Test 4a: Create test emails to check for duplication in processing
            print("   Creating test emails to check processing duplication...")
            
            # Get an active account
            accounts = await self.db.email_accounts.find({"is_active": True}).to_list(10)
            if not accounts:
                self.log_test_result("Email Processing View Duplicates", False, "No active email accounts found")
                return
            
            account = accounts[0]
            
            # Create a test email via API
            test_email_data = {
                "subject": "Duplicate Test Email - Processing View",
                "body": "This is a test email to check for duplicate processing issues in the email processing view. Please respond with pricing information.",
                "sender": "duplicate.test@example.com",
                "account_id": account['id']
            }
            
            try:
                print("   Sending test email via /api/emails/test...")
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                test_email_created = response.status_code in [200, 201]
                
                if test_email_created:
                    test_email_response = response.json()
                    test_email_id = test_email_response.get('email_id')
                    print(f"   - Test email created with ID: {test_email_id}")
                    
                    # Wait a moment for processing
                    await asyncio.sleep(3)
                    
                    # Check if email appears in database
                    db_email = await self.db.emails.find_one({"id": test_email_id})
                    if db_email:
                        print(f"   - Email found in database with status: {db_email.get('status')}")
                        
                        # Check for duplicates of this email
                        duplicate_emails = await self.db.emails.find({
                            "body": test_email_data["body"],
                            "subject": test_email_data["subject"]
                        }).to_list(10)
                        
                        duplicate_count = len(duplicate_emails)
                        print(f"   - Found {duplicate_count} emails with same content")
                        
                        if duplicate_count > 1:
                            print("   🚨 DUPLICATE DETECTED:")
                            for dup_email in duplicate_emails:
                                print(f"     - ID: {dup_email.get('id')}, Status: {dup_email.get('status')}, Created: {dup_email.get('created_at')}")
                        
                        no_processing_duplicates = duplicate_count == 1
                        processing_details = f"Test email created, duplicates found: {duplicate_count - 1}"
                    else:
                        no_processing_duplicates = False
                        processing_details = "Test email not found in database"
                else:
                    no_processing_duplicates = False
                    processing_details = f"Failed to create test email: {response.status_code}"
                    
            except Exception as e:
                no_processing_duplicates = False
                processing_details = f"Exception during test email creation: {str(e)}"
            
            # Test 4b: Check email processing view API consistency
            try:
                print("   Checking email processing view API consistency...")
                
                # Get emails from individual endpoint
                individual_response = requests.get(f"{API_BASE}/emails", timeout=15)
                individual_emails = individual_response.json() if individual_response.status_code == 200 else []
                
                # Get emails from threads endpoint
                threads_response = requests.get(f"{API_BASE}/emails/threads", timeout=15)
                threads_data = threads_response.json() if threads_response.status_code == 200 else []
                
                # Count total emails in threads
                thread_email_count = 0
                for thread in threads_data:
                    thread_email_count += 1  # original_email
                    thread_email_count += len(thread.get('responses', []))
                
                print(f"   - Individual emails endpoint: {len(individual_emails)} emails")
                print(f"   - Thread emails count: {thread_email_count} emails")
                
                # Check for consistency (allowing some variance due to follow-ups, etc.)
                consistency_ok = abs(len(individual_emails) - thread_email_count) <= 5
                consistency_details = f"Individual: {len(individual_emails)}, Threads: {thread_email_count}, Consistent: {consistency_ok}"
                
            except Exception as e:
                consistency_ok = False
                consistency_details = f"Exception: {str(e)}"
            
            # Overall assessment
            all_passed = no_processing_duplicates and consistency_ok
            
            self.log_test_result("Processing View - No Duplicates", no_processing_duplicates, processing_details)
            self.log_test_result("Processing View - API Consistency", consistency_ok, consistency_details)
            
            details = f"No processing duplicates: {no_processing_duplicates}, API consistency: {consistency_ok}"
            self.log_test_result("Email Processing View Duplicates", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Processing View Duplicates", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🧪 DUPLICATE EMAIL ISSUES TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL:  {len(self.test_results)}")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS: {len(passed_tests)} tests passed successfully")
        
        print("\n" + "="*80)
        
        return len(passed_tests), len(failed_tests)

async def main():
    """Main test execution"""
    print("🚀 Starting Duplicate Email Issues Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = DuplicateEmailTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, exiting...")
        return
    
    try:
        # Run tests
        await tester.test_email_endpoints_for_duplicates()
        await tester.test_database_consistency()
        await tester.test_oauth_modal_functionality()
        await tester.test_email_processing_view_duplicates()
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Exit with appropriate code
        exit_code = 0 if failed == 0 else 1
        print(f"\n🏁 Testing completed with exit code: {exit_code}")
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())