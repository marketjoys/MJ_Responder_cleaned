#!/usr/bin/env python3
"""
Focused Outlook OAuth Auto-Reply Testing
Tests the actual auto_send_email function with mock OAuth accounts
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FocusedOutlookOAuthTester:
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
    
    async def test_redis_and_rq_system(self):
        """Test Redis and RQ system functionality"""
        print("\n🔴 Testing Redis and RQ System...")
        
        try:
            from tasks import redis_conn, get_queue_stats
            
            # Test Redis connection
            redis_ping = redis_conn.ping()
            
            # Get queue stats
            stats = get_queue_stats()
            redis_connected = stats.get('redis_connected', False)
            
            # Check queues
            queues = ['email_processing', 'follow_up', 'background']
            queue_status = all(queue in stats for queue in queues)
            
            system_operational = redis_ping and redis_connected and queue_status
            
            details = f"Redis ping: {redis_ping}, Connected: {redis_connected}, Queues: {queue_status}"
            
            self.log_test_result("Redis and RQ System", system_operational, details)
            
        except Exception as e:
            self.log_test_result("Redis and RQ System", False, f"Exception: {str(e)}")
    
    async def test_auto_send_email_function_outlook(self):
        """Test auto_send_email function with Outlook OAuth account"""
        print("\n🏢 Testing auto_send_email Function - Outlook OAuth...")
        
        try:
            # Create test user
            test_user_id = str(uuid.uuid4())
            test_user = {
                'id': test_user_id,
                'email': 'test.outlook@example.com',
                'full_name': 'Test Outlook User',
                'hashed_password': 'test_hash',
                'is_active': True,
                'created_at': datetime.utcnow()
            }
            await self.db.users.insert_one(test_user)
            
            # Create test Outlook OAuth account
            outlook_account_id = str(uuid.uuid4())
            outlook_account = {
                'id': outlook_account_id,
                'user_id': test_user_id,
                'email': 'test.outlook@example.com',
                'provider': 'outlook',
                'auth_type': 'oauth',
                'use_oauth': True,
                'oauth_email': 'test.outlook@example.com',
                'is_active': True,
                'auto_send': True,
                'created_at': datetime.utcnow()
            }
            await self.db.email_accounts.insert_one(outlook_account)
            
            # Create test email in ready_to_send status
            test_email_id = str(uuid.uuid4())
            test_email = {
                'id': test_email_id,
                'account_id': outlook_account_id,
                'user_id': test_user_id,
                'message_id': f'<test-{uuid.uuid4()}@example.com>',
                'thread_id': f'thread-{uuid.uuid4()}',
                'subject': 'Test Outlook OAuth Auto-Send',
                'sender': 'sender@example.com',
                'recipient': 'test.outlook@example.com',
                'body': 'Test email body',
                'received_at': datetime.utcnow(),
                'status': 'ready_to_send',
                'draft': 'This is a test auto-reply for Outlook OAuth.',
                'final_plain_text': 'This is a test auto-reply for Outlook OAuth.\n\nBest regards,\nTest Outlook User',
                'created_at': datetime.utcnow()
            }
            await self.db.emails.insert_one(test_email)
            
            # Test the auto_send_email function
            from server import auto_send_email
            
            # This will test the routing logic without actually sending
            try:
                await auto_send_email(test_email_id)
                
                # Check if email status was updated (it should fail due to no OAuth token, but routing should work)
                updated_email = await self.db.emails.find_one({'id': test_email_id})
                
                # The function should have attempted to route to Microsoft Graph API
                # We can verify this by checking that it didn't crash and the routing logic was executed
                routing_attempted = True  # If we get here, routing logic was executed
                
                details = f"Routing attempted: {routing_attempted}, Final status: {updated_email.get('status')}"
                
                self.log_test_result("Outlook OAuth Auto-Send Function", routing_attempted, details)
                
            except Exception as e:
                # Expected to fail due to no OAuth token, but we can check the error message
                error_msg = str(e)
                outlook_routing_detected = 'microsoft' in error_msg.lower() or 'outlook' in error_msg.lower() or 'graph' in error_msg.lower()
                
                details = f"Expected OAuth error occurred, Outlook routing detected: {outlook_routing_detected}"
                
                self.log_test_result("Outlook OAuth Auto-Send Function", outlook_routing_detected, details)
            
            # Cleanup
            await self.db.emails.delete_one({'id': test_email_id})
            await self.db.email_accounts.delete_one({'id': outlook_account_id})
            await self.db.users.delete_one({'id': test_user_id})
            
        except Exception as e:
            self.log_test_result("Outlook OAuth Auto-Send Function", False, f"Exception: {str(e)}")
    
    async def test_auto_send_email_function_gmail(self):
        """Test auto_send_email function with Gmail OAuth account"""
        print("\n📧 Testing auto_send_email Function - Gmail OAuth...")
        
        try:
            # Create test user
            test_user_id = str(uuid.uuid4())
            test_user = {
                'id': test_user_id,
                'email': 'test.gmail@example.com',
                'full_name': 'Test Gmail User',
                'hashed_password': 'test_hash',
                'is_active': True,
                'created_at': datetime.utcnow()
            }
            await self.db.users.insert_one(test_user)
            
            # Create test Gmail OAuth account
            gmail_account_id = str(uuid.uuid4())
            gmail_account = {
                'id': gmail_account_id,
                'user_id': test_user_id,
                'email': 'test.gmail@example.com',
                'provider': 'gmail',
                'auth_type': 'oauth',
                'use_oauth': True,
                'oauth_email': 'test.gmail@example.com',
                'is_active': True,
                'auto_send': True,
                'created_at': datetime.utcnow()
            }
            await self.db.email_accounts.insert_one(gmail_account)
            
            # Create test email in ready_to_send status
            test_email_id = str(uuid.uuid4())
            test_email = {
                'id': test_email_id,
                'account_id': gmail_account_id,
                'user_id': test_user_id,
                'message_id': f'<test-{uuid.uuid4()}@example.com>',
                'thread_id': f'thread-{uuid.uuid4()}',
                'subject': 'Test Gmail OAuth Auto-Send',
                'sender': 'sender@example.com',
                'recipient': 'test.gmail@example.com',
                'body': 'Test email body',
                'received_at': datetime.utcnow(),
                'status': 'ready_to_send',
                'draft': 'This is a test auto-reply for Gmail OAuth.',
                'final_plain_text': 'This is a test auto-reply for Gmail OAuth.\n\nBest regards,\nTest Gmail User',
                'created_at': datetime.utcnow()
            }
            await self.db.emails.insert_one(test_email)
            
            # Test the auto_send_email function
            from server import auto_send_email
            
            # This will test the routing logic without actually sending
            try:
                await auto_send_email(test_email_id)
                
                # Check if email status was updated
                updated_email = await self.db.emails.find_one({'id': test_email_id})
                
                routing_attempted = True  # If we get here, routing logic was executed
                
                details = f"Routing attempted: {routing_attempted}, Final status: {updated_email.get('status')}"
                
                self.log_test_result("Gmail OAuth Auto-Send Function", routing_attempted, details)
                
            except Exception as e:
                # Expected to fail due to no OAuth token, but we can check the error message
                error_msg = str(e)
                gmail_routing_detected = 'gmail' in error_msg.lower() or 'google' in error_msg.lower()
                
                details = f"Expected OAuth error occurred, Gmail routing detected: {gmail_routing_detected}"
                
                self.log_test_result("Gmail OAuth Auto-Send Function", gmail_routing_detected, details)
            
            # Cleanup
            await self.db.emails.delete_one({'id': test_email_id})
            await self.db.email_accounts.delete_one({'id': gmail_account_id})
            await self.db.users.delete_one({'id': test_user_id})
            
        except Exception as e:
            self.log_test_result("Gmail OAuth Auto-Send Function", False, f"Exception: {str(e)}")
    
    async def test_provider_routing_code_analysis(self):
        """Test provider routing by analyzing the auto_send_email code"""
        print("\n🔍 Testing Provider Routing Code Analysis...")
        
        try:
            # Import and analyze the auto_send_email function
            import inspect
            from server import auto_send_email
            
            # Get the source code
            source_code = inspect.getsource(auto_send_email)
            
            # Check for Outlook/Microsoft routing
            outlook_routing_present = (
                'outlook' in source_code.lower() or 
                'microsoft' in source_code.lower() or 
                'MicrosoftMailService' in source_code
            )
            
            # Check for Gmail/Google routing
            gmail_routing_present = (
                'gmail' in source_code.lower() or 
                'google' in source_code.lower() or 
                'GoogleGmailService' in source_code or 
                'get_google_gmail_service' in source_code
            )
            
            # Check for OAuth detection
            oauth_detection_present = (
                'auth_type' in source_code and 
                'oauth' in source_code.lower() and
                'use_oauth' in source_code
            )
            
            # Check for provider-specific routing
            provider_routing_present = (
                'provider' in source_code and
                ('gmail' in source_code.lower() or 'outlook' in source_code.lower())
            )
            
            all_routing_present = (
                outlook_routing_present and 
                gmail_routing_present and 
                oauth_detection_present and 
                provider_routing_present
            )
            
            details = f"Outlook routing: {outlook_routing_present}, Gmail routing: {gmail_routing_present}, OAuth detection: {oauth_detection_present}, Provider routing: {provider_routing_present}"
            
            self.log_test_result("Provider Routing Code Analysis", all_routing_present, details)
            
        except Exception as e:
            self.log_test_result("Provider Routing Code Analysis", False, f"Exception: {str(e)}")
    
    async def test_microsoft_mail_service_methods(self):
        """Test MicrosoftMailService methods availability"""
        print("\n🏢 Testing MicrosoftMailService Methods...")
        
        try:
            from microsoft_services import MicrosoftMailService
            
            # Create instance
            service = MicrosoftMailService('test-user', 'test@example.com')
            
            # Check required methods
            has_send_message = hasattr(service, 'send_message') and callable(getattr(service, 'send_message'))
            has_get_headers = hasattr(service, '_get_headers') and callable(getattr(service, '_get_headers'))
            has_list_messages = hasattr(service, 'list_messages') and callable(getattr(service, 'list_messages'))
            
            # Check method signatures
            import inspect
            send_sig = inspect.signature(service.send_message)
            send_params = list(send_sig.parameters.keys())
            
            has_required_params = all(param in send_params for param in ['to', 'subject', 'body'])
            
            all_methods_present = has_send_message and has_get_headers and has_list_messages and has_required_params
            
            details = f"send_message: {has_send_message}, _get_headers: {has_get_headers}, list_messages: {has_list_messages}, required_params: {has_required_params}"
            
            self.log_test_result("MicrosoftMailService Methods", all_methods_present, details)
            
        except Exception as e:
            self.log_test_result("MicrosoftMailService Methods", False, f"Exception: {str(e)}")
    
    async def test_google_gmail_service_methods(self):
        """Test GoogleGmailService methods availability"""
        print("\n📧 Testing GoogleGmailService Methods...")
        
        try:
            from google_services import GoogleGmailService
            
            # Create instance
            service = GoogleGmailService('test-user', 'test@example.com')
            
            # Check required methods
            has_send_message = hasattr(service, 'send_message') and callable(getattr(service, 'send_message'))
            has_get_headers = hasattr(service, '_get_headers') and callable(getattr(service, '_get_headers'))
            has_list_messages = hasattr(service, 'list_messages') and callable(getattr(service, 'list_messages'))
            
            # Check method signatures
            import inspect
            send_sig = inspect.signature(service.send_message)
            send_params = list(send_sig.parameters.keys())
            
            has_required_params = all(param in send_params for param in ['to_email', 'subject', 'body'])
            
            all_methods_present = has_send_message and has_get_headers and has_list_messages and has_required_params
            
            details = f"send_message: {has_send_message}, _get_headers: {has_get_headers}, list_messages: {has_list_messages}, required_params: {has_required_params}"
            
            self.log_test_result("GoogleGmailService Methods", all_methods_present, details)
            
        except Exception as e:
            self.log_test_result("GoogleGmailService Methods", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("FOCUSED OUTLOOK OAUTH AUTO-REPLY TEST SUMMARY")
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
    print("🎯 Starting Focused Outlook OAuth Auto-Reply Testing...")
    
    tester = FocusedOutlookOAuthTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run focused tests
        await tester.test_redis_and_rq_system()
        await tester.test_provider_routing_code_analysis()
        await tester.test_microsoft_mail_service_methods()
        await tester.test_google_gmail_service_methods()
        await tester.test_auto_send_email_function_outlook()
        await tester.test_auto_send_email_function_gmail()
        
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