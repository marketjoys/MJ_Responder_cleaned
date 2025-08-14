#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Email Assistant System
Tests connection health, seed data, email processing workflow, polling system, and API endpoints
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
from email_services import EmailPollingService, EmailConnection, EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://mail-sync-repair.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class EmailAssistantTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.polling_service = None
        
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
        if self.polling_service:
            self.polling_service.stop_polling()
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
    
    async def test_connection_health_check(self):
        """Test 1: Connection Health Check - IMAP connection pooling and reuse"""
        print("\n🔍 Testing Connection Health Check...")
        
        try:
            # Get active email accounts
            accounts = await self.db.email_accounts.find({"is_active": True}).to_list(10)
            if not accounts:
                self.log_test_result("Connection Health Check", False, "No active email accounts found")
                return
            
            account = accounts[0]
            print(f"Testing connection for: {account['email']}")
            
            # Test 1a: Create connection
            connection1 = EmailConnection(account)
            connect_result1 = connection1.connect_imap()
            
            if not connect_result1:
                self.log_test_result("Connection Health Check", False, "Failed to establish initial IMAP connection")
                return
            
            # Test 1b: Check connection health
            health_check1 = connection1._is_connection_healthy()
            
            # Test 1c: Create second connection to same account (should reuse)
            connection2 = EmailConnection(account)
            connect_result2 = connection2.connect_imap()
            
            # Test 1d: Verify both connections work
            health_check2 = connection2._is_connection_healthy()
            
            # Test 1e: Test connection reuse in polling service
            self.polling_service = EmailPollingService(MONGO_URL, DB_NAME)
            
            # Simulate multiple polls to test connection reuse
            await self.polling_service._poll_account(account)
            initial_connections = len(self.polling_service.connections)
            
            await self.polling_service._poll_account(account)
            final_connections = len(self.polling_service.connections)
            
            # Cleanup
            connection1.disconnect_imap()
            connection2.disconnect_imap()
            
            # Evaluate results
            all_passed = (connect_result1 and health_check1 and connect_result2 and 
                         health_check2 and initial_connections == final_connections == 1)
            
            details = f"Initial connect: {connect_result1}, Health1: {health_check1}, " \
                     f"Second connect: {connect_result2}, Health2: {health_check2}, " \
                     f"Connection reuse: {initial_connections == final_connections}"
            
            self.log_test_result("Connection Health Check", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Connection Health Check", False, f"Exception: {str(e)}")
    
    async def test_seed_data_verification(self):
        """Test 2: Seed Data Verification - intents, knowledge base, email accounts"""
        print("\n🌱 Testing Seed Data Verification...")
        
        try:
            # Test 2a: Check intents with embeddings
            intents = await self.db.intents.find().to_list(100)
            intents_with_embeddings = [i for i in intents if i.get('embedding')]
            
            intent_test_passed = len(intents) >= 5 and len(intents_with_embeddings) == len(intents)
            
            # Test 2b: Check knowledge base entries with embeddings
            kb_items = await self.db.knowledge_base.find().to_list(100)
            kb_with_embeddings = [kb for kb in kb_items if kb.get('embedding')]
            
            kb_test_passed = len(kb_items) >= 5 and len(kb_with_embeddings) == len(kb_items)
            
            # Test 2c: Check email accounts
            email_accounts = await self.db.email_accounts.find().to_list(100)
            active_accounts = [acc for acc in email_accounts if acc.get('is_active', False)]
            
            accounts_test_passed = len(email_accounts) >= 1 and len(active_accounts) >= 1
            
            # Test 2d: Verify intent classification works
            if intents_with_embeddings:
                test_email_body = "I need help with your product pricing and want to schedule a demo"
                
                # Import classification function
                from server import classify_email_intents
                classified_intents = await classify_email_intents(test_email_body)
                
                classification_test_passed = len(classified_intents) > 0
            else:
                classification_test_passed = False
            
            # Test 2e: Verify knowledge base retrieval
            if kb_with_embeddings:
                from server import get_knowledge_context
                kb_context = await get_knowledge_context("pricing information")
                
                kb_retrieval_test_passed = "knowledge" in kb_context.lower() or "pricing" in kb_context.lower()
            else:
                kb_retrieval_test_passed = False
            
            all_passed = (intent_test_passed and kb_test_passed and accounts_test_passed and 
                         classification_test_passed and kb_retrieval_test_passed)
            
            details = f"Intents: {len(intents)}/{len(intents_with_embeddings)} with embeddings, " \
                     f"KB: {len(kb_items)}/{len(kb_with_embeddings)} with embeddings, " \
                     f"Accounts: {len(email_accounts)}/{len(active_accounts)} active, " \
                     f"Classification: {classification_test_passed}, KB retrieval: {kb_retrieval_test_passed}"
            
            self.log_test_result("Seed Data Verification", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Seed Data Verification", False, f"Exception: {str(e)}")
    
    async def test_email_processing_workflow(self):
        """Test 3: Email Processing Workflow - classification, draft generation, validation, auto-send"""
        print("\n🤖 Testing Email Processing Workflow...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Email Processing Workflow", False, "No active email accounts")
                return
            
            # Create test email
            test_email = EmailMessage(
                account_id=account['id'],
                message_id=f"<test-workflow-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Product Inquiry - Need Pricing Information",
                sender="business.inquiry@example.com",
                recipient=account['email'],
                body="Hello, I'm interested in your AI email assistant product. Could you please provide pricing information and schedule a demo? We're a growing company looking to automate our email responses. Thank you!",
                body_html="<p>Hello, I'm interested in your AI email assistant product. Could you please provide pricing information and schedule a demo? We're a growing company looking to automate our email responses. Thank you!</p>",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Insert test email
            await self.db.emails.insert_one(test_email.dict())
            
            # Test 3a: Email Classification
            from server import classify_email_intents
            intents = await classify_email_intents(test_email.body)
            
            classification_passed = len(intents) > 0
            
            # Test 3b: Draft Generation
            from server import generate_draft
            draft = await generate_draft(test_email, intents)
            
            draft_passed = (draft.get('plain_text') and len(draft['plain_text']) > 50 and 
                           draft.get('html') and len(draft['html']) > 50)
            
            # Test 3c: Draft Validation
            from server import validate_draft
            validation = await validate_draft(test_email, draft, intents)
            
            validation_passed = validation.get('status') in ['PASS', 'FAIL']
            
            # Test 3d: Complete AI Workflow
            if not self.polling_service:
                self.polling_service = EmailPollingService(MONGO_URL, DB_NAME)
            
            await self.polling_service._process_email_ai_workflow(test_email.id)
            
            # Check final result
            processed_email = await self.db.emails.find_one({"id": test_email.id})
            workflow_passed = (processed_email and 
                             processed_email.get('status') in ['ready_to_send', 'needs_redraft', 'sent'] and
                             processed_email.get('intents') and
                             processed_email.get('draft') and
                             processed_email.get('validation_result'))
            
            # Test 3e: Auto-send capability (without actually sending)
            if processed_email and processed_email.get('status') == 'ready_to_send':
                # Test the auto-send logic without actually sending
                connection = EmailConnection(account)
                auto_send_ready = (processed_email.get('draft') and 
                                 processed_email.get('sender') and
                                 processed_email.get('subject'))
            else:
                auto_send_ready = True  # If not ready to send, that's also valid
            
            all_passed = (classification_passed and draft_passed and validation_passed and 
                         workflow_passed and auto_send_ready)
            
            details = f"Classification: {len(intents) if intents else 0} intents, " \
                     f"Draft: {len(draft.get('plain_text', '')) if draft else 0} chars, " \
                     f"Validation: {validation.get('status') if validation else 'None'}, " \
                     f"Final status: {processed_email.get('status') if processed_email else 'None'}"
            
            self.log_test_result("Email Processing Workflow", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Processing Workflow", False, f"Exception: {str(e)}")
    
    async def test_polling_system(self):
        """Test 4: Polling System - running status, UID tracking, error handling, logging"""
        print("\n📡 Testing Polling System...")
        
        try:
            # Test 4a: Polling service initialization
            if not self.polling_service:
                self.polling_service = EmailPollingService(MONGO_URL, DB_NAME)
            
            init_passed = self.polling_service is not None
            
            # Test 4b: UID tracking
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Polling System", False, "No active email accounts")
                return
            
            original_uid = account.get('last_uid', 0)
            
            # Simulate polling
            await self.polling_service._poll_account(account)
            
            # Check if UID was updated
            updated_account = await self.db.email_accounts.find_one({"id": account['id']})
            uid_tracking_passed = updated_account.get('last_polled') is not None
            
            # Test 4c: Connection management
            connections_before = len(self.polling_service.connections)
            await self.polling_service._poll_account(account)
            connections_after = len(self.polling_service.connections)
            
            connection_mgmt_passed = connections_before <= connections_after <= 1
            
            # Test 4d: Error handling (test with invalid account)
            invalid_account = account.copy()
            invalid_account['password'] = 'invalid_password'
            invalid_account['id'] = 'invalid_account_id'
            
            try:
                await self.polling_service._poll_account(invalid_account)
                error_handling_passed = True  # Should not crash
            except Exception:
                error_handling_passed = False
            
            # Test 4e: Service status
            status_before = self.polling_service.is_running
            
            # Start polling briefly
            polling_task = asyncio.create_task(self.polling_service.start_polling())
            await asyncio.sleep(2)  # Let it run briefly
            
            status_during = self.polling_service.is_running
            
            # Stop polling
            self.polling_service.stop_polling()
            await asyncio.sleep(1)
            
            status_after = self.polling_service.is_running
            
            # Cancel the task
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            
            status_mgmt_passed = (not status_before and status_during and not status_after)
            
            all_passed = (init_passed and uid_tracking_passed and connection_mgmt_passed and 
                         error_handling_passed and status_mgmt_passed)
            
            details = f"Init: {init_passed}, UID tracking: {uid_tracking_passed}, " \
                     f"Connection mgmt: {connection_mgmt_passed}, Error handling: {error_handling_passed}, " \
                     f"Status mgmt: {status_mgmt_passed}"
            
            self.log_test_result("Polling System", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Polling System", False, f"Exception: {str(e)}")
    
    def test_api_endpoints(self):
        """Test 5: API Endpoints - dashboard stats, polling status, intents, knowledge base, email accounts"""
        print("\n🌐 Testing API Endpoints...")
        
        try:
            # Test 5a: GET /api/dashboard/stats
            try:
                response = requests.get(f"{API_BASE}/dashboard/stats", timeout=10)
                stats_passed = (response.status_code == 200 and 
                               'total_emails' in response.json() and
                               'polling_status' in response.json())
                stats_details = f"Status: {response.status_code}"
            except Exception as e:
                stats_passed = False
                stats_details = f"Error: {str(e)}"
            
            # Test 5b: GET /api/polling/status
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                polling_status_passed = (response.status_code == 200 and 
                                       'status' in response.json())
                polling_details = f"Status: {response.status_code}, Response: {response.json().get('status', 'unknown')}"
            except Exception as e:
                polling_status_passed = False
                polling_details = f"Error: {str(e)}"
            
            # Test 5c: GET /api/intents
            try:
                response = requests.get(f"{API_BASE}/intents", timeout=10)
                intents_passed = (response.status_code == 200 and 
                                isinstance(response.json(), list))
                intents_details = f"Status: {response.status_code}, Count: {len(response.json()) if response.status_code == 200 else 0}"
            except Exception as e:
                intents_passed = False
                intents_details = f"Error: {str(e)}"
            
            # Test 5d: GET /api/knowledge-base
            try:
                response = requests.get(f"{API_BASE}/knowledge-base", timeout=10)
                kb_passed = (response.status_code == 200 and 
                           isinstance(response.json(), list))
                kb_details = f"Status: {response.status_code}, Count: {len(response.json()) if response.status_code == 200 else 0}"
            except Exception as e:
                kb_passed = False
                kb_details = f"Error: {str(e)}"
            
            # Test 5e: GET /api/email-accounts
            try:
                response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
                accounts_passed = (response.status_code == 200 and 
                                 isinstance(response.json(), list))
                accounts_details = f"Status: {response.status_code}, Count: {len(response.json()) if response.status_code == 200 else 0}"
            except Exception as e:
                accounts_passed = False
                accounts_details = f"Error: {str(e)}"
            
            # Test 5f: POST /api/emails/test
            try:
                test_data = {
                    "subject": "API Test Email",
                    "body": "This is a test email for API endpoint testing",
                    "sender": "api.test@example.com",
                    "account_id": "test-account-id"
                }
                
                # First get a real account ID
                accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
                if accounts_response.status_code == 200 and accounts_response.json():
                    test_data["account_id"] = accounts_response.json()[0]["id"]
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=15)
                test_email_passed = response.status_code in [200, 201]
                test_email_details = f"Status: {response.status_code}"
            except Exception as e:
                test_email_passed = False
                test_email_details = f"Error: {str(e)}"
            
            all_passed = (stats_passed and polling_status_passed and intents_passed and 
                         kb_passed and accounts_passed and test_email_passed)
            
            # Log individual endpoint results
            self.log_test_result("API - Dashboard Stats", stats_passed, stats_details)
            self.log_test_result("API - Polling Status", polling_status_passed, polling_details)
            self.log_test_result("API - Intents", intents_passed, intents_details)
            self.log_test_result("API - Knowledge Base", kb_passed, kb_details)
            self.log_test_result("API - Email Accounts", accounts_passed, accounts_details)
            self.log_test_result("API - Test Email Processing", test_email_passed, test_email_details)
            
            details = f"Stats: {stats_passed}, Polling: {polling_status_passed}, " \
                     f"Intents: {intents_passed}, KB: {kb_passed}, " \
                     f"Accounts: {accounts_passed}, Test Email: {test_email_passed}"
            
            self.log_test_result("API Endpoints", all_passed, details)
            
        except Exception as e:
            self.log_test_result("API Endpoints", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
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
            print(f"   {test['status']}: {test['test']}")
            if test['details']:
                print(f"      {test['details']}")
        
        print("\n" + "="*80)

async def main():
    """Main test function"""
    print("🚀 Starting Comprehensive Email Assistant Backend Tests")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print(f"🗄️  Database: {MONGO_URL}/{DB_NAME}")
    print("="*80)
    
    tester = EmailAssistantTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Failed to setup test environment")
            return
        
        # Run all tests
        await tester.test_connection_health_check()
        await tester.test_seed_data_verification()
        await tester.test_email_processing_workflow()
        await tester.test_polling_system()
        tester.test_api_endpoints()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Critical error in test execution: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())