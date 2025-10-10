#!/usr/bin/env python3
"""
Focused Backend Testing for Critical Fixes
Tests core functionality without relying on external AI services
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-fix-3.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FocusedBackendTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.test_account_id = None
        
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
    
    async def test_email_account_creation_with_signature(self):
        """Test 1: Email Account Creation with Signature Field"""
        print("\n📧 Testing Email Account Creation with Signature...")
        
        try:
            # Test creating account with signature
            account_data = {
                "name": "Signature Test Account",
                "email": "signature.test@company.com",
                "provider": "gmail",
                "username": "signature.test@company.com",
                "password": "test_password_123",
                "persona": "Professional customer service representative",
                "signature": "Best regards,\n\nMike Thompson\nCustomer Success Manager\nInnovative Solutions Inc.\n📧 mike.thompson@company.com\n📞 +1 (555) 987-6543\n🌐 www.innovativesolutions.com",
                "auto_send": False,
                "enable_follow_ups": True
            }
            
            print("   Creating account with signature...")
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
            
            if response.status_code in [200, 201]:
                created_account = response.json()
                account_id = created_account.get('id')
                
                # Verify account creation
                account_created = account_id is not None
                password_masked = created_account.get('password') == '***'
                
                # Retrieve account to verify signature storage
                if account_id:
                    get_response = requests.get(f"{API_BASE}/email-accounts/{account_id}", timeout=10)
                    if get_response.status_code == 200:
                        retrieved_account = get_response.json()
                        
                        # Check signature field presence
                        has_signature_field = 'signature' in retrieved_account
                        has_persona_field = 'persona' in retrieved_account
                        has_follow_up_config = 'enable_follow_ups' in retrieved_account
                        
                        # Store for later tests
                        self.test_account_id = account_id
                        
                        account_creation_successful = (
                            account_created and password_masked and has_signature_field and has_persona_field
                        )
                        
                        details = f"Account created: {account_created}, Password masked: {password_masked}, Signature field: {has_signature_field}, Persona field: {has_persona_field}, Follow-up config: {has_follow_up_config}"
                        
                    else:
                        account_creation_successful = False
                        details = f"Failed to retrieve created account: {get_response.status_code}"
                else:
                    account_creation_successful = False
                    details = "No account ID returned"
                
                self.log_test_result("Email Account Creation with Signature", account_creation_successful, details)
                
            else:
                self.log_test_result("Email Account Creation with Signature", False, f"Account creation failed: {response.status_code}, {response.text[:200]}")
                
        except Exception as e:
            self.log_test_result("Email Account Creation with Signature", False, f"Exception: {str(e)}")
    
    async def test_email_test_endpoint_basic(self):
        """Test 2: Basic Email Test Endpoint Functionality"""
        print("\n🧪 Testing Email Test Endpoint (Basic)...")
        
        if not self.test_account_id:
            self.log_test_result("Email Test Endpoint Basic", False, "No test account available")
            return
        
        try:
            # Test basic endpoint functionality with simple data
            test_email_data = {
                "subject": "Simple Test Email",
                "body": "This is a basic test email to verify endpoint functionality.",
                "sender": "test@example.com",
                "account_id": self.test_account_id
            }
            
            print("   Testing /api/emails/test endpoint...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=15)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check basic response structure
                has_id = 'id' in processed_email
                has_status = 'status' in processed_email
                has_subject = processed_email.get('subject') == test_email_data['subject']
                has_sender = processed_email.get('sender') == test_email_data['sender']
                has_body = processed_email.get('body') == test_email_data['body']
                has_account_id = processed_email.get('account_id') == self.test_account_id
                
                # Check if email was stored in database
                if has_id:
                    email_in_db = await self.db.emails.find_one({"id": processed_email['id']})
                    stored_in_db = email_in_db is not None
                else:
                    stored_in_db = False
                
                endpoint_working = (
                    has_id and has_status and has_subject and has_sender and 
                    has_body and has_account_id and stored_in_db
                )
                
                details = f"ID: {has_id}, Status: {has_status}, Subject: {has_subject}, Sender: {has_sender}, Body: {has_body}, Account: {has_account_id}, DB: {stored_in_db}"
                
                self.log_test_result("Email Test Endpoint Basic", endpoint_working, details)
                
                # Store email ID for further tests
                if has_id:
                    self.test_email_id = processed_email['id']
                
            else:
                self.log_test_result("Email Test Endpoint Basic", False, f"HTTP {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            self.log_test_result("Email Test Endpoint Basic", False, f"Exception: {str(e)}")
    
    async def test_validate_final_email_function_exists(self):
        """Test 3: Verify validate_final_email function exists and is used"""
        print("\n🔍 Testing validate_final_email Function...")
        
        try:
            # Check if the function exists in the codebase
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            # Check for validate_final_email function definition
            has_validate_final_email = 'def validate_final_email(' in server_code
            
            # Check for validate_final_email usage
            validate_final_email_used = 'validate_final_email(' in server_code and server_code.count('validate_final_email(') > 1
            
            # Check for old validate_draft function (should still exist but not be the primary one)
            has_validate_draft = 'def validate_draft(' in server_code
            
            # Check that validate_final_email is called in email processing
            validate_final_in_processing = 'await validate_final_email(' in server_code
            
            function_implementation_correct = (
                has_validate_final_email and validate_final_email_used and 
                validate_final_in_processing
            )
            
            details = f"validate_final_email defined: {has_validate_final_email}, Used: {validate_final_email_used}, In processing: {validate_final_in_processing}, validate_draft exists: {has_validate_draft}"
            
            self.log_test_result("validate_final_email Function", function_implementation_correct, details)
            
        except Exception as e:
            self.log_test_result("validate_final_email Function", False, f"Exception: {str(e)}")
    
    async def test_signature_processing_in_validation(self):
        """Test 4: Verify signature is processed in validation"""
        print("\n📝 Testing Signature Processing in Validation...")
        
        try:
            # Check the validate_final_email function implementation
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            # Find the validate_final_email function
            validate_final_start = server_code.find('async def validate_final_email(')
            if validate_final_start == -1:
                self.log_test_result("Signature Processing in Validation", False, "validate_final_email function not found")
                return
            
            # Extract the function (find the next function definition)
            next_function = server_code.find('\nasync def ', validate_final_start + 1)
            if next_function == -1:
                next_function = server_code.find('\ndef ', validate_final_start + 1)
            
            if next_function != -1:
                validate_final_function = server_code[validate_final_start:next_function]
            else:
                validate_final_function = server_code[validate_final_start:]
            
            # Check if signature is processed in the function
            processes_signature = 'signature' in validate_final_function.lower()
            creates_final_content = 'final_plain_text' in validate_final_function or 'final_html' in validate_final_function
            adds_signature_to_draft = '+=' in validate_final_function and 'signature' in validate_final_function
            
            # Check for HTML signature processing
            processes_html_signature = 'html_signature' in validate_final_function or 'html.escape' in validate_final_function
            
            signature_processing_implemented = (
                processes_signature and creates_final_content and 
                (adds_signature_to_draft or processes_html_signature)
            )
            
            details = f"Processes signature: {processes_signature}, Creates final content: {creates_final_content}, Adds signature: {adds_signature_to_draft}, HTML processing: {processes_html_signature}"
            
            self.log_test_result("Signature Processing in Validation", signature_processing_implemented, details)
            
        except Exception as e:
            self.log_test_result("Signature Processing in Validation", False, f"Exception: {str(e)}")
    
    async def test_follow_up_system_structure(self):
        """Test 5: Verify Follow-up System Structure"""
        print("\n📅 Testing Follow-up System Structure...")
        
        try:
            # Check database collections for follow-up system
            collections = await self.db.list_collection_names()
            
            # Check for follow-up related collections
            has_follow_up_emails = 'follow_up_emails' in collections
            has_follow_up_config = 'follow_up_config' in collections or 'follow_up_configs' in collections
            
            # Check for follow-up models in code
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            has_follow_up_models = 'class FollowUpEmail(' in server_code and 'class FollowUpConfig(' in server_code
            has_follow_up_fields = 'enable_follow_ups' in server_code and 'follow_up_hours_override' in server_code
            
            # Check for follow-up endpoints (even if they don't work due to AI issues)
            has_follow_up_endpoints = '/follow-up' in server_code or 'follow_up' in server_code
            
            # Test basic follow-up configuration endpoint
            try:
                follow_up_config = {
                    "global_follow_up_hours": 24,
                    "max_follow_ups": 2,
                    "auto_follow_up": True
                }
                config_response = requests.post(f"{API_BASE}/follow-up/config", json=follow_up_config, timeout=10)
                config_endpoint_exists = config_response.status_code != 404
            except:
                config_endpoint_exists = False
            
            follow_up_system_implemented = (
                has_follow_up_models and has_follow_up_fields and 
                (has_follow_up_emails or has_follow_up_config or config_endpoint_exists)
            )
            
            details = f"DB collections: follow_up_emails={has_follow_up_emails}, Models: {has_follow_up_models}, Fields: {has_follow_up_fields}, Endpoints: {config_endpoint_exists}"
            
            self.log_test_result("Follow-up System Structure", follow_up_system_implemented, details)
            
        except Exception as e:
            self.log_test_result("Follow-up System Structure", False, f"Exception: {str(e)}")
    
    async def test_automatic_response_mechanism_structure(self):
        """Test 6: Verify Automatic Response Mechanism Structure"""
        print("\n🤖 Testing Automatic Response Mechanism Structure...")
        
        try:
            # Check for email processing workflow in code
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            # Check for key components of automatic response
            has_email_processing = 'process_email_async' in server_code or 'async def process_email' in server_code
            has_intent_classification = 'classify_email_intents' in server_code
            has_draft_generation = 'generate_draft' in server_code
            has_validation = 'validate_final_email' in server_code or 'validate_draft' in server_code
            
            # Check for email sending functionality
            has_send_email = 'send_email' in server_code and 'smtp' in server_code.lower()
            
            # Check for auto-send configuration
            has_auto_send_config = 'auto_send' in server_code
            
            # Check email status workflow
            has_status_workflow = 'ready_to_send' in server_code and 'sent' in server_code
            
            # Test if email processing endpoint exists and responds
            try:
                # Test with minimal data to avoid AI processing issues
                minimal_test = {
                    "subject": "Test",
                    "body": "Test",
                    "sender": "test@test.com",
                    "account_id": self.test_account_id or "test-id"
                }
                response = requests.post(f"{API_BASE}/emails/test", json=minimal_test, timeout=5)
                endpoint_responds = response.status_code != 404
            except:
                endpoint_responds = False
            
            automatic_response_implemented = (
                has_email_processing and has_intent_classification and 
                has_draft_generation and has_validation and 
                has_auto_send_config and endpoint_responds
            )
            
            details = f"Processing: {has_email_processing}, Classification: {has_intent_classification}, Draft: {has_draft_generation}, Validation: {has_validation}, Auto-send: {has_auto_send_config}, Endpoint: {endpoint_responds}"
            
            self.log_test_result("Automatic Response Mechanism Structure", automatic_response_implemented, details)
            
        except Exception as e:
            self.log_test_result("Automatic Response Mechanism Structure", False, f"Exception: {str(e)}")
    
    async def test_database_schema_updates(self):
        """Test 7: Verify Database Schema Updates for New Features"""
        print("\n🗄️ Testing Database Schema Updates...")
        
        try:
            # Check email accounts collection for new fields
            if self.test_account_id:
                account = await self.db.email_accounts.find_one({"id": self.test_account_id})
                if account:
                    has_signature_field = 'signature' in account
                    has_persona_field = 'persona' in account
                    has_follow_up_fields = 'enable_follow_ups' in account
                    has_auto_send_field = 'auto_send' in account
                else:
                    has_signature_field = has_persona_field = has_follow_up_fields = has_auto_send_field = False
            else:
                # Check any account
                sample_account = await self.db.email_accounts.find_one()
                if sample_account:
                    has_signature_field = 'signature' in sample_account
                    has_persona_field = 'persona' in sample_account
                    has_follow_up_fields = 'enable_follow_ups' in sample_account
                    has_auto_send_field = 'auto_send' in sample_account
                else:
                    has_signature_field = has_persona_field = has_follow_up_fields = has_auto_send_field = False
            
            # Check emails collection for new fields
            sample_email = await self.db.emails.find_one()
            if sample_email:
                has_draft_html_field = 'draft_html' in sample_email
                has_validation_result_field = 'validation_result' in sample_email
                has_intents_field = 'intents' in sample_email
            else:
                has_draft_html_field = has_validation_result_field = has_intents_field = False
            
            # Check collections exist
            collections = await self.db.list_collection_names()
            has_emails_collection = 'emails' in collections
            has_accounts_collection = 'email_accounts' in collections
            has_intents_collection = 'intents' in collections
            has_kb_collection = 'knowledge_base' in collections
            
            schema_updated = (
                has_signature_field and has_persona_field and 
                has_draft_html_field and has_validation_result_field and
                has_emails_collection and has_accounts_collection
            )
            
            details = f"Account fields: signature={has_signature_field}, persona={has_persona_field}, follow_up={has_follow_up_fields}, auto_send={has_auto_send_field}; Email fields: html={has_draft_html_field}, validation={has_validation_result_field}; Collections: emails={has_emails_collection}, accounts={has_accounts_collection}"
            
            self.log_test_result("Database Schema Updates", schema_updated, details)
            
        except Exception as e:
            self.log_test_result("Database Schema Updates", False, f"Exception: {str(e)}")
    
    async def cleanup_test_account(self):
        """Cleanup test account"""
        if self.test_account_id:
            try:
                requests.delete(f"{API_BASE}/email-accounts/{self.test_account_id}", timeout=10)
                print(f"✅ Cleaned up test account: {self.test_account_id}")
            except:
                print(f"⚠️  Could not cleanup test account: {self.test_account_id}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("FOCUSED BACKEND TEST SUMMARY")
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
    print("🚀 Starting Focused Backend Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    print("Note: This test focuses on structure and basic functionality, avoiding AI-dependent features due to Groq API capacity issues.")
    
    tester = FocusedBackendTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run focused tests
        await tester.test_email_account_creation_with_signature()
        await tester.test_email_test_endpoint_basic()
        await tester.test_validate_final_email_function_exists()
        await tester.test_signature_processing_in_validation()
        await tester.test_follow_up_system_structure()
        await tester.test_automatic_response_mechanism_structure()
        await tester.test_database_schema_updates()
        
        # Cleanup
        await tester.cleanup_test_account()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Critical error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())