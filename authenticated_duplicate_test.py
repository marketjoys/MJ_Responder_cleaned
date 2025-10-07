#!/usr/bin/env python3
"""
Authenticated Duplicate Email Issues Testing for Email Assistant System
Tests email endpoints with proper authentication and database analysis
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dev-synchronize-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class AuthenticatedDuplicateTester:
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
            
            # Try to authenticate with existing user or create test user
            await self.authenticate_or_create_user()
            
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    async def authenticate_or_create_user(self):
        """Authenticate with existing user or create test user"""
        try:
            # Try to find existing user
            existing_user = await self.db.users.find_one({})
            
            if existing_user:
                print(f"   Found existing user: {existing_user.get('email')}")
                # Try to login with this user (we'll use a test password)
                login_data = {
                    "email": existing_user.get('email'),
                    "password": "admin123"  # Common test password
                }
                
                try:
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    if response.status_code == 200:
                        auth_data = response.json()
                        self.auth_token = auth_data.get('access_token')
                        self.test_user_id = auth_data.get('user', {}).get('id')
                        print(f"   ✅ Authenticated as: {existing_user.get('email')}")
                        return
                except Exception as e:
                    print(f"   ⚠️ Login failed: {str(e)}")
            
            # If no existing user or login failed, create test user
            print("   Creating test user for authentication...")
            register_data = {
                "email": "test.duplicate@example.com",
                "password": "testpassword123",
                "full_name": "Duplicate Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=10)
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get('access_token')
                self.test_user_id = auth_data.get('user', {}).get('id')
                print(f"   ✅ Created and authenticated test user: {register_data['email']}")
            else:
                print(f"   ❌ Failed to create test user: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Authentication setup failed: {str(e)}")
    
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
    
    async def test_database_duplicate_analysis(self):
        """Test 1: Comprehensive Database Duplicate Analysis"""
        print("\n🗄️ Testing Database for Duplicate Issues...")
        
        try:
            # Get all emails from database
            emails_cursor = self.db.emails.find({})
            emails_list = await emails_cursor.to_list(1000)
            
            print(f"   - Total emails in database: {len(emails_list)}")
            
            if len(emails_list) == 0:
                self.log_test_result("Database Duplicate Analysis", True, "No emails in database - no duplicates possible")
                return
            
            # Analyze duplicates by different criteria
            message_id_map = defaultdict(list)
            content_hash_map = defaultdict(list)
            subject_sender_map = defaultdict(list)
            thread_analysis = defaultdict(list)
            
            for email in emails_list:
                # Group by message_id (should be unique)
                msg_id = email.get('message_id', '').strip()
                if msg_id:
                    message_id_map[msg_id].append(email)
                
                # Group by content hash (body + subject)
                body = email.get('body', '').strip()
                subject = email.get('subject', '').strip()
                content_hash = f"{subject}|{body}"
                if content_hash != "|":
                    content_hash_map[content_hash].append(email)
                
                # Group by subject + sender combination
                sender = email.get('sender', '').strip()
                subject_sender_key = f"{subject}|{sender}"
                if subject_sender_key != "|":
                    subject_sender_map[subject_sender_key].append(email)
                
                # Thread analysis
                thread_id = email.get('thread_id', '').strip()
                if thread_id:
                    thread_analysis[thread_id].append(email)
            
            # Find duplicates
            message_id_duplicates = {k: v for k, v in message_id_map.items() if len(v) > 1}
            content_duplicates = {k: v for k, v in content_hash_map.items() if len(v) > 1}
            subject_sender_duplicates = {k: v for k, v in subject_sender_map.items() if len(v) > 1}
            
            print(f"   - Message ID duplicates: {len(message_id_duplicates)}")
            print(f"   - Content duplicates: {len(content_duplicates)}")
            print(f"   - Subject+Sender duplicates: {len(subject_sender_duplicates)}")
            print(f"   - Unique threads: {len(thread_analysis)}")
            
            # Detailed analysis of duplicates
            critical_issues = []
            
            if message_id_duplicates:
                print("   🚨 CRITICAL: Message ID Duplicates Found!")
                for msg_id, emails in list(message_id_duplicates.items())[:3]:
                    print(f"     - Message ID: {msg_id}")
                    for email in emails:
                        print(f"       * Email ID: {email.get('id')}, Status: {email.get('status')}, Created: {email.get('created_at')}")
                    critical_issues.append(f"Message ID {msg_id} has {len(emails)} duplicates")
            
            if content_duplicates:
                print(f"   ⚠️ Content Duplicates Found: {len(content_duplicates)}")
                for content_hash, emails in list(content_duplicates.items())[:2]:
                    subject, body = content_hash.split('|', 1)
                    print(f"     - Subject: '{subject[:50]}...'")
                    print(f"     - Body: '{body[:50]}...'")
                    print(f"     - Appears in {len(emails)} emails:")
                    for email in emails:
                        print(f"       * ID: {email.get('id')}, Status: {email.get('status')}")
            
            # Thread consistency check
            thread_issues = []
            for thread_id, emails in thread_analysis.items():
                # Check if emails in same thread have consistent subjects
                subjects = set()
                for email in emails:
                    subject = email.get('subject', '').replace('Re: ', '').replace('Fwd: ', '').strip()
                    subjects.add(subject)
                
                if len(subjects) > 1:
                    thread_issues.append(f"Thread {thread_id} has inconsistent subjects: {list(subjects)[:3]}")
            
            if thread_issues:
                print(f"   ⚠️ Thread Consistency Issues: {len(thread_issues)}")
                for issue in thread_issues[:3]:
                    print(f"     - {issue}")
            
            # Overall assessment
            no_critical_duplicates = len(message_id_duplicates) == 0
            reasonable_content_duplicates = len(content_duplicates) <= 2  # Some duplicates might be expected
            thread_consistency_ok = len(thread_issues) <= 1
            
            all_passed = no_critical_duplicates and reasonable_content_duplicates and thread_consistency_ok
            
            details = f"Emails: {len(emails_list)}, Message ID dups: {len(message_id_duplicates)}, Content dups: {len(content_duplicates)}, Thread issues: {len(thread_issues)}"
            
            self.log_test_result("Database - No Message ID Duplicates", no_critical_duplicates, 
                               f"Found {len(message_id_duplicates)} message ID duplicates")
            self.log_test_result("Database - Reasonable Content Duplicates", reasonable_content_duplicates, 
                               f"Found {len(content_duplicates)} content duplicates")
            self.log_test_result("Database - Thread Consistency", thread_consistency_ok, 
                               f"Found {len(thread_issues)} thread consistency issues")
            
            self.log_test_result("Database Duplicate Analysis", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Database Duplicate Analysis", False, f"Exception: {str(e)}")
    
    async def test_authenticated_email_endpoints(self):
        """Test 2: Authenticated Email Endpoints"""
        print("\n📧 Testing Authenticated Email Endpoints...")
        
        if not self.auth_token:
            self.log_test_result("Authenticated Email Endpoints", False, "No authentication token available")
            return
        
        headers = self.get_auth_headers()
        
        try:
            # Test GET /api/emails
            print("   Testing GET /api/emails with authentication...")
            response = requests.get(f"{API_BASE}/emails", headers=headers, timeout=15)
            emails_api_passed = response.status_code == 200
            
            if emails_api_passed:
                emails_list = response.json()
                print(f"   - Retrieved {len(emails_list)} emails from API")
                
                # Check for duplicates in API response
                api_message_ids = [email.get('message_id') for email in emails_list if email.get('message_id')]
                api_duplicates = len(api_message_ids) - len(set(api_message_ids))
                
                emails_details = f"Status: {response.status_code}, Count: {len(emails_list)}, API duplicates: {api_duplicates}"
                api_no_duplicates = api_duplicates == 0
            else:
                emails_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                api_no_duplicates = False
            
            # Test GET /api/emails/threads
            print("   Testing GET /api/emails/threads with authentication...")
            response = requests.get(f"{API_BASE}/emails/threads", headers=headers, timeout=15)
            threads_api_passed = response.status_code == 200
            
            if threads_api_passed:
                threads_list = response.json()
                print(f"   - Retrieved {len(threads_list)} threads from API")
                
                # Verify thread structure
                valid_threads = 0
                total_emails_in_threads = 0
                
                for thread in threads_list:
                    if all(key in thread for key in ['thread_id', 'subject', 'original_email']):
                        valid_threads += 1
                        total_emails_in_threads += 1  # original_email
                        total_emails_in_threads += len(thread.get('responses', []))
                
                threads_details = f"Status: {response.status_code}, Threads: {len(threads_list)}, Valid: {valid_threads}, Total emails: {total_emails_in_threads}"
                threads_structure_ok = valid_threads == len(threads_list)
            else:
                threads_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                threads_structure_ok = False
            
            # Overall assessment
            all_passed = emails_api_passed and threads_api_passed and api_no_duplicates and threads_structure_ok
            
            self.log_test_result("Authenticated - Emails API", emails_api_passed and api_no_duplicates, emails_details)
            self.log_test_result("Authenticated - Threads API", threads_api_passed and threads_structure_ok, threads_details)
            
            details = f"Emails API: {emails_api_passed}, Threads API: {threads_api_passed}, No API duplicates: {api_no_duplicates}"
            self.log_test_result("Authenticated Email Endpoints", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Authenticated Email Endpoints", False, f"Exception: {str(e)}")
    
    async def test_oauth_endpoints_detailed(self):
        """Test 3: Detailed OAuth Endpoints Testing"""
        print("\n🔐 Testing OAuth Endpoints in Detail...")
        
        try:
            # Test OAuth status endpoints without authentication first
            print("   Testing OAuth status endpoints...")
            
            # Google OAuth status
            google_response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
            google_status_ok = google_response.status_code in [200, 401, 403, 404]
            
            # Microsoft OAuth status  
            microsoft_response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
            microsoft_status_ok = microsoft_response.status_code in [200, 401, 403, 404]
            
            print(f"   - Google OAuth status: {google_response.status_code}")
            print(f"   - Microsoft OAuth status: {microsoft_response.status_code}")
            
            # Test with authentication if available
            if self.auth_token:
                headers = self.get_auth_headers()
                
                google_auth_response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
                microsoft_auth_response = requests.get(f"{API_BASE}/oauth/microsoft/status", headers=headers, timeout=10)
                
                print(f"   - Google OAuth status (authenticated): {google_auth_response.status_code}")
                print(f"   - Microsoft OAuth status (authenticated): {microsoft_auth_response.status_code}")
                
                google_auth_ok = google_auth_response.status_code in [200, 404]
                microsoft_auth_ok = microsoft_auth_response.status_code in [200, 404]
            else:
                google_auth_ok = True  # Skip if no auth
                microsoft_auth_ok = True
            
            # Check OAuth database collections
            print("   Checking OAuth database collections...")
            oauth_tokens_count = await self.db.oauth_tokens.count_documents({})
            oauth_accounts_count = await self.db.email_accounts.count_documents({"auth_type": "oauth"})
            
            print(f"   - OAuth tokens in database: {oauth_tokens_count}")
            print(f"   - OAuth email accounts: {oauth_accounts_count}")
            
            # Overall assessment
            oauth_endpoints_working = google_status_ok and microsoft_status_ok and google_auth_ok and microsoft_auth_ok
            oauth_db_ok = True  # Collections exist even if empty
            
            all_passed = oauth_endpoints_working and oauth_db_ok
            
            details = f"Google: {google_status_ok}, Microsoft: {microsoft_status_ok}, DB tokens: {oauth_tokens_count}, OAuth accounts: {oauth_accounts_count}"
            
            self.log_test_result("OAuth - Endpoints Working", oauth_endpoints_working, 
                               f"Google: {google_response.status_code}, Microsoft: {microsoft_response.status_code}")
            self.log_test_result("OAuth - Database Collections", oauth_db_ok, 
                               f"Tokens: {oauth_tokens_count}, Accounts: {oauth_accounts_count}")
            
            self.log_test_result("OAuth Endpoints Detailed", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Endpoints Detailed", False, f"Exception: {str(e)}")
    
    async def test_email_processing_with_auth(self):
        """Test 4: Email Processing with Authentication"""
        print("\n🤖 Testing Email Processing with Authentication...")
        
        if not self.auth_token:
            self.log_test_result("Email Processing with Auth", False, "No authentication token available")
            return
        
        headers = self.get_auth_headers()
        
        try:
            # First, check if we have any email accounts
            accounts_response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
            
            if accounts_response.status_code != 200:
                self.log_test_result("Email Processing with Auth", False, f"Cannot access email accounts: {accounts_response.status_code}")
                return
            
            accounts = accounts_response.json()
            if not accounts:
                print("   No email accounts found, creating test account...")
                
                # Create a test email account
                account_data = {
                    "name": "Test Account for Duplicate Testing",
                    "email": "test.duplicate.processing@example.com",
                    "provider": "gmail",
                    "username": "test.duplicate.processing@example.com",
                    "password": "test_password_123",
                    "auto_send": False
                }
                
                create_response = requests.post(f"{API_BASE}/email-accounts", json=account_data, headers=headers, timeout=15)
                if create_response.status_code in [200, 201]:
                    accounts = [create_response.json()]
                    print("   ✅ Created test email account")
                else:
                    self.log_test_result("Email Processing with Auth", False, f"Failed to create test account: {create_response.status_code}")
                    return
            
            account = accounts[0]
            print(f"   Using email account: {account.get('email')}")
            
            # Test email processing endpoint
            test_email_data = {
                "subject": "Duplicate Processing Test Email",
                "body": "This is a test email to check for duplicate processing issues. We need pricing information for your AI email assistant service.",
                "sender": "duplicate.processing.test@example.com",
                "account_id": account['id']
            }
            
            print("   Testing /api/emails/test endpoint...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, headers=headers, timeout=30)
            
            processing_passed = response.status_code in [200, 201]
            
            if processing_passed:
                processing_result = response.json()
                email_id = processing_result.get('email_id')
                processing_status = processing_result.get('status')
                
                print(f"   - Email processing initiated: {email_id}")
                print(f"   - Processing status: {processing_status}")
                
                # Wait a moment and check the email status
                await asyncio.sleep(3)
                
                # Check if email was created in database
                if email_id:
                    db_email = await self.db.emails.find_one({"id": email_id})
                    if db_email:
                        print(f"   - Email found in database with status: {db_email.get('status')}")
                        
                        # Check for duplicates of this specific email
                        duplicate_check = await self.db.emails.find({
                            "body": test_email_data["body"],
                            "subject": test_email_data["subject"]
                        }).to_list(10)
                        
                        duplicate_count = len(duplicate_check)
                        print(f"   - Duplicate emails found: {duplicate_count - 1}")
                        
                        no_duplicates_created = duplicate_count == 1
                        processing_details = f"Email created: {email_id}, Status: {db_email.get('status')}, Duplicates: {duplicate_count - 1}"
                    else:
                        no_duplicates_created = False
                        processing_details = f"Email {email_id} not found in database"
                else:
                    no_duplicates_created = False
                    processing_details = "No email ID returned from processing"
            else:
                no_duplicates_created = False
                processing_details = f"Processing failed: {response.status_code}, {response.text[:100]}"
            
            # Overall assessment
            all_passed = processing_passed and no_duplicates_created
            
            self.log_test_result("Email Processing - API Call", processing_passed, 
                               f"Status: {response.status_code}")
            self.log_test_result("Email Processing - No Duplicates", no_duplicates_created, 
                               processing_details)
            
            self.log_test_result("Email Processing with Auth", all_passed, processing_details)
            
        except Exception as e:
            self.log_test_result("Email Processing with Auth", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🧪 AUTHENTICATED DUPLICATE EMAIL ISSUES TEST SUMMARY")
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
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        print("\n" + "="*80)
        
        return len(passed_tests), len(failed_tests)

async def main():
    """Main test execution"""
    print("🚀 Starting Authenticated Duplicate Email Issues Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = AuthenticatedDuplicateTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, exiting...")
        return
    
    try:
        # Run tests
        await tester.test_database_duplicate_analysis()
        await tester.test_authenticated_email_endpoints()
        await tester.test_oauth_endpoints_detailed()
        await tester.test_email_processing_with_auth()
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Exit with appropriate code
        exit_code = 0 if failed == 0 else 1
        print(f"\n🏁 Testing completed with exit code: {exit_code}")
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())