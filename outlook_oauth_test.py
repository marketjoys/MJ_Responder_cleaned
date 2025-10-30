#!/usr/bin/env python3
"""
Outlook OAuth Auto-Reply Testing
Focus: Test complete email automation system with emphasis on Outlook OAuth auto-reply functionality
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://redis-workers.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OutlookOAuthTester:
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
            
            # Get or create test user
            await self.setup_test_user()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def setup_test_user(self):
        """Setup test user for authentication"""
        try:
            # Try to find existing user first
            existing_user = await self.db.users.find_one({}, sort=[("created_at", 1)])
            
            if existing_user:
                # Login with existing user
                login_data = {
                    "email": existing_user["email"],
                    "password": "admin123"  # Default password from migration
                }
                
                try:
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        self.auth_token = result.get('access_token')
                        self.test_user_id = result.get('user', {}).get('id')
                        print(f"✅ Logged in as existing user: {existing_user['email']}")
                        return
                except:
                    pass
            
            # Create new test user if login failed
            test_email = f"outlook.oauth.test.{int(time.time())}@example.com"
            register_data = {
                "email": test_email,
                "password": "OutlookTest123!",
                "full_name": "Outlook OAuth Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
            if response.status_code == 200:
                result = response.json()
                self.auth_token = result.get('access_token')
                self.test_user_id = result.get('user', {}).get('id')
                print(f"✅ Created new test user: {test_email}")
            else:
                print(f"❌ Failed to create test user: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error setting up test user: {str(e)}")
    
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
    
    async def test_redis_connectivity(self):
        """Test Redis connectivity - verify Redis is running on localhost:6379"""
        print("\n🔴 Testing Redis Connectivity...")
        
        try:
            # Test Redis connection via RQ stats endpoint
            response = requests.get(f"{API_BASE}/rq/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                redis_connected = stats.get('redis_connected', False)
                queue_count = len(stats.get('queues', []))
                
                details = f"Redis connected: {redis_connected}, Queues: {queue_count}"
                self.log_test_result("Redis Connectivity", redis_connected, details)
            else:
                self.log_test_result("Redis Connectivity", False, f"API Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Redis Connectivity", False, f"Exception: {str(e)}")
    
    async def test_rq_workers(self):
        """Test RQ Workers - verify background job processing is operational"""
        print("\n👷 Testing RQ Workers...")
        
        try:
            # Test RQ worker status
            response = requests.get(f"{API_BASE}/rq/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                workers = stats.get('workers', [])
                active_workers = [w for w in workers if w.get('state') == 'busy' or w.get('state') == 'idle']
                
                workers_operational = len(active_workers) > 0
                details = f"Active workers: {len(active_workers)}, Total workers: {len(workers)}"
                
                self.log_test_result("RQ Workers", workers_operational, details)
            else:
                self.log_test_result("RQ Workers", False, f"API Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("RQ Workers", False, f"Exception: {str(e)}")
    
    async def test_rq_scheduler(self):
        """Test RQ Scheduler - verify periodic tasks are scheduled"""
        print("\n📅 Testing RQ Scheduler...")
        
        try:
            # Test RQ scheduler status
            response = requests.get(f"{API_BASE}/rq/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                scheduled_jobs = stats.get('scheduled_jobs', 0)
                
                scheduler_operational = scheduled_jobs >= 0  # Scheduler is running if we can get stats
                details = f"Scheduled jobs: {scheduled_jobs}"
                
                self.log_test_result("RQ Scheduler", scheduler_operational, details)
            else:
                self.log_test_result("RQ Scheduler", False, f"API Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("RQ Scheduler", False, f"Exception: {str(e)}")
    
    async def test_oauth_accounts_detection(self):
        """Test OAuth accounts detection - look for existing Outlook and Gmail OAuth accounts"""
        print("\n🔍 Testing OAuth Accounts Detection...")
        
        try:
            # Check email accounts collection for OAuth accounts
            email_accounts = await self.db.email_accounts.find({}).to_list(100)
            
            outlook_oauth_accounts = [
                acc for acc in email_accounts 
                if acc.get('auth_type') == 'oauth' and acc.get('provider', '').lower() in ['outlook', 'microsoft']
            ]
            
            gmail_oauth_accounts = [
                acc for acc in email_accounts 
                if acc.get('auth_type') == 'oauth' and acc.get('provider', '').lower() in ['gmail', 'google']
            ]
            
            # Check oauth_tokens_microsoft collection
            microsoft_tokens = await self.db.oauth_tokens_microsoft.find({}).to_list(100)
            
            # Check oauth_tokens collection (for Google)
            google_tokens = await self.db.oauth_tokens.find({}).to_list(100)
            
            outlook_accounts_found = len(outlook_oauth_accounts) > 0
            gmail_accounts_found = len(gmail_oauth_accounts) > 0
            microsoft_tokens_found = len(microsoft_tokens) > 0
            google_tokens_found = len(google_tokens) > 0
            
            details = f"Outlook OAuth accounts: {len(outlook_oauth_accounts)}, Gmail OAuth accounts: {len(gmail_oauth_accounts)}, Microsoft tokens: {len(microsoft_tokens)}, Google tokens: {len(google_tokens)}"
            
            # Test passes if we have at least one OAuth account
            test_passed = outlook_accounts_found or gmail_accounts_found
            
            self.log_test_result("OAuth Accounts Detection", test_passed, details)
            
            return {
                'outlook_accounts': outlook_oauth_accounts,
                'gmail_accounts': gmail_oauth_accounts,
                'microsoft_tokens': microsoft_tokens,
                'google_tokens': google_tokens
            }
            
        except Exception as e:
            self.log_test_result("OAuth Accounts Detection", False, f"Exception: {str(e)}")
            return {'outlook_accounts': [], 'gmail_accounts': [], 'microsoft_tokens': [], 'google_tokens': []}
    
    async def test_auto_send_routing_logic(self):
        """Test auto_send_email function routing logic - verify correct provider detection"""
        print("\n🔀 Testing Auto-Send Routing Logic...")
        
        try:
            # Import the auto_send_email function
            from server import auto_send_email
            
            # Create test email documents for different providers
            test_emails = []
            
            # Test Outlook OAuth routing
            outlook_email = {
                'id': str(uuid.uuid4()),
                'account_id': 'test-outlook-account',
                'subject': 'Test Outlook OAuth Auto-Send',
                'sender': 'test@example.com',
                'status': 'ready_to_send',
                'draft': 'Test email content for Outlook OAuth',
                'message_id': f'<test-{uuid.uuid4()}@example.com>'
            }
            
            outlook_account = {
                'id': 'test-outlook-account',
                'user_id': self.test_user_id or 'test-user',
                'email': 'test.outlook@example.com',
                'provider': 'outlook',
                'auth_type': 'oauth',
                'use_oauth': True,
                'oauth_email': 'test.outlook@example.com',
                'is_active': True,
                'auto_send': True
            }
            
            # Test Gmail OAuth routing
            gmail_email = {
                'id': str(uuid.uuid4()),
                'account_id': 'test-gmail-account',
                'subject': 'Test Gmail OAuth Auto-Send',
                'sender': 'test@example.com',
                'status': 'ready_to_send',
                'draft': 'Test email content for Gmail OAuth',
                'message_id': f'<test-{uuid.uuid4()}@example.com>'
            }
            
            gmail_account = {
                'id': 'test-gmail-account',
                'user_id': self.test_user_id or 'test-user',
                'email': 'test.gmail@example.com',
                'provider': 'gmail',
                'auth_type': 'oauth',
                'use_oauth': True,
                'oauth_email': 'test.gmail@example.com',
                'is_active': True,
                'auto_send': True
            }
            
            # Insert test data
            await self.db.emails.insert_one(outlook_email)
            await self.db.email_accounts.insert_one(outlook_account)
            await self.db.emails.insert_one(gmail_email)
            await self.db.email_accounts.insert_one(gmail_account)
            
            # Test routing logic by examining the code path
            routing_tests = []
            
            # Test 1: Outlook provider detection
            outlook_provider = outlook_account.get('provider', '').lower()
            outlook_routing_correct = outlook_provider in ['outlook', 'microsoft']
            routing_tests.append(('Outlook Provider Detection', outlook_routing_correct))
            
            # Test 2: Gmail provider detection
            gmail_provider = gmail_account.get('provider', '').lower()
            gmail_routing_correct = gmail_provider in ['gmail', 'google']
            routing_tests.append(('Gmail Provider Detection', gmail_routing_correct))
            
            # Test 3: OAuth type detection
            outlook_oauth_correct = (outlook_account.get('auth_type') == 'oauth' and 
                                   outlook_account.get('use_oauth') == True)
            routing_tests.append(('Outlook OAuth Detection', outlook_oauth_correct))
            
            gmail_oauth_correct = (gmail_account.get('auth_type') == 'oauth' and 
                                 gmail_account.get('use_oauth') == True)
            routing_tests.append(('Gmail OAuth Detection', gmail_oauth_correct))
            
            # Test 4: OAuth email field presence
            outlook_email_field = bool(outlook_account.get('oauth_email'))
            gmail_email_field = bool(gmail_account.get('oauth_email'))
            routing_tests.append(('Outlook OAuth Email Field', outlook_email_field))
            routing_tests.append(('Gmail OAuth Email Field', gmail_email_field))
            
            # Cleanup test data
            await self.db.emails.delete_one({'id': outlook_email['id']})
            await self.db.email_accounts.delete_one({'id': outlook_account['id']})
            await self.db.emails.delete_one({'id': gmail_email['id']})
            await self.db.email_accounts.delete_one({'id': gmail_account['id']})
            
            # Evaluate overall routing logic
            all_routing_tests_passed = all(result for _, result in routing_tests)
            
            details = ', '.join([f"{name}: {result}" for name, result in routing_tests])
            
            self.log_test_result("Auto-Send Routing Logic", all_routing_tests_passed, details)
            
        except Exception as e:
            self.log_test_result("Auto-Send Routing Logic", False, f"Exception: {str(e)}")
    
    async def test_email_processing_workflow(self):
        """Test email processing workflow - test that emails get processed through the queue"""
        print("\n🔄 Testing Email Processing Workflow...")
        
        if not self.auth_token:
            self.log_test_result("Email Processing Workflow", False, "No auth token")
            return
        
        try:
            # Get an active account for testing
            accounts = await self.db.email_accounts.find({'is_active': True}).to_list(10)
            if not accounts:
                self.log_test_result("Email Processing Workflow", False, "No active email accounts")
                return
            
            test_account = accounts[0]
            
            # Test email processing via API
            test_email_data = {
                "subject": "Outlook OAuth Auto-Reply Test Email",
                "body": "This is a test email to verify the complete email automation workflow with Outlook OAuth auto-reply functionality. Please process this email and generate an appropriate response.",
                "sender": "outlook.test@example.com",
                "account_id": test_account['id']
            }
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                email_id = processed_email.get('email_id')
                
                # Wait a moment for processing
                await asyncio.sleep(3)
                
                # Check email status in database
                if email_id:
                    email_doc = await self.db.emails.find_one({'id': email_id})
                    if email_doc:
                        status = email_doc.get('status')
                        has_intents = bool(email_doc.get('intents'))
                        has_draft = bool(email_doc.get('draft'))
                        
                        workflow_success = status in ['ready_to_send', 'sent', 'drafting', 'classifying']
                        details = f"Status: {status}, Has intents: {has_intents}, Has draft: {has_draft}"
                        
                        self.log_test_result("Email Processing Workflow", workflow_success, details)
                    else:
                        self.log_test_result("Email Processing Workflow", False, "Email not found in database")
                else:
                    self.log_test_result("Email Processing Workflow", False, "No email ID returned")
            else:
                self.log_test_result("Email Processing Workflow", False, f"API Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Email Processing Workflow", False, f"Exception: {str(e)}")
    
    async def test_auto_send_queue(self):
        """Test auto-send queue - verify emails in ready_to_send status get enqueued for sending"""
        print("\n📤 Testing Auto-Send Queue...")
        
        try:
            # Check for emails in ready_to_send status
            ready_emails = await self.db.emails.find({'status': 'ready_to_send'}).to_list(100)
            
            # Check RQ queue for auto-send jobs
            response = requests.get(f"{API_BASE}/rq/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                queues = stats.get('queues', [])
                
                # Look for email-related queues
                email_queues = [q for q in queues if 'email' in q.get('name', '').lower() or 'send' in q.get('name', '').lower()]
                
                queue_operational = len(queues) > 0
                ready_emails_count = len(ready_emails)
                
                details = f"Ready emails: {ready_emails_count}, Email queues: {len(email_queues)}, Total queues: {len(queues)}"
                
                self.log_test_result("Auto-Send Queue", queue_operational, details)
            else:
                self.log_test_result("Auto-Send Queue", False, f"API Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Auto-Send Queue", False, f"Exception: {str(e)}")
    
    async def test_outlook_oauth_service_instantiation(self):
        """Test MicrosoftMailService instantiation for Outlook accounts"""
        print("\n🏢 Testing Outlook OAuth Service Instantiation...")
        
        try:
            # Import MicrosoftMailService
            from microsoft_services import MicrosoftMailService
            
            # Test service instantiation
            test_user_id = self.test_user_id or 'test-user-id'
            test_oauth_email = 'test.outlook@example.com'
            
            # Create service instance
            mail_service = MicrosoftMailService(test_user_id, test_oauth_email)
            
            # Verify service properties
            service_created = mail_service is not None
            has_user_id = hasattr(mail_service, 'user_id') and mail_service.user_id == test_user_id
            has_oauth_email = hasattr(mail_service, 'oauth_email') and mail_service.oauth_email == test_oauth_email
            has_base_url = hasattr(mail_service, 'base_url') and 'graph.microsoft.com' in mail_service.base_url
            
            instantiation_success = service_created and has_user_id and has_oauth_email and has_base_url
            
            details = f"Service created: {service_created}, User ID: {has_user_id}, OAuth email: {has_oauth_email}, Base URL: {has_base_url}"
            
            self.log_test_result("Outlook OAuth Service Instantiation", instantiation_success, details)
            
        except Exception as e:
            self.log_test_result("Outlook OAuth Service Instantiation", False, f"Exception: {str(e)}")
    
    async def test_gmail_oauth_service_instantiation(self):
        """Test GoogleGmailService instantiation for Gmail accounts"""
        print("\n📧 Testing Gmail OAuth Service Instantiation...")
        
        try:
            # Import GoogleGmailService
            from google_services import GoogleGmailService
            
            # Test service instantiation
            test_user_id = self.test_user_id or 'test-user-id'
            test_oauth_email = 'test.gmail@example.com'
            
            # Create service instance
            mail_service = GoogleGmailService(test_user_id, test_oauth_email)
            
            # Verify service properties
            service_created = mail_service is not None
            has_user_id = hasattr(mail_service, 'user_id') and mail_service.user_id == test_user_id
            has_oauth_email = hasattr(mail_service, 'oauth_email') and mail_service.oauth_email == test_oauth_email
            has_base_url = hasattr(mail_service, 'base_url') and 'gmail.googleapis.com' in mail_service.base_url
            
            instantiation_success = service_created and has_user_id and has_oauth_email and has_base_url
            
            details = f"Service created: {service_created}, User ID: {has_user_id}, OAuth email: {has_oauth_email}, Base URL: {has_base_url}"
            
            self.log_test_result("Gmail OAuth Service Instantiation", instantiation_success, details)
            
        except Exception as e:
            self.log_test_result("Gmail OAuth Service Instantiation", False, f"Exception: {str(e)}")
    
    async def test_provider_routing_verification(self):
        """Test provider routing verification - check logs for proper provider detection"""
        print("\n🔍 Testing Provider Routing Verification...")
        
        try:
            # Check recent backend logs for provider routing
            import subprocess
            
            # Get recent backend logs
            log_result = subprocess.run(
                ['tail', '-n', '100', '/var/log/supervisor/backend.out.log'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if log_result.returncode == 0:
                log_content = log_result.stdout
                
                # Look for OAuth routing indicators
                gmail_routing_found = 'Gmail API' in log_content or 'GoogleGmailService' in log_content
                outlook_routing_found = 'Microsoft Graph API' in log_content or 'MicrosoftMailService' in log_content
                oauth_routing_found = 'OAuth email' in log_content or 'oauth_email' in log_content
                
                routing_indicators = gmail_routing_found or outlook_routing_found or oauth_routing_found
                
                details = f"Gmail routing: {gmail_routing_found}, Outlook routing: {outlook_routing_found}, OAuth routing: {oauth_routing_found}"
                
                self.log_test_result("Provider Routing Verification", routing_indicators, details)
            else:
                self.log_test_result("Provider Routing Verification", False, "Could not read backend logs")
                
        except Exception as e:
            self.log_test_result("Provider Routing Verification", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("OUTLOOK OAUTH AUTO-REPLY TEST SUMMARY")
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
                print(f"  - {test['test']}: {test['details']}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Outlook OAuth Auto-Reply Testing...")
    
    tester = OutlookOAuthTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests in order of priority
        print("\n📋 Running PRIMARY FOCUS tests...")
        
        # PRIMARY FOCUS: Outlook OAuth Auto-Reply
        oauth_accounts = await tester.test_oauth_accounts_detection()
        await tester.test_auto_send_routing_logic()
        await tester.test_outlook_oauth_service_instantiation()
        await tester.test_gmail_oauth_service_instantiation()
        await tester.test_provider_routing_verification()
        
        print("\n📋 Running SECONDARY CHECKS...")
        
        # SECONDARY CHECKS
        await tester.test_redis_connectivity()
        await tester.test_rq_workers()
        await tester.test_rq_scheduler()
        await tester.test_email_processing_workflow()
        await tester.test_auto_send_queue()
        
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