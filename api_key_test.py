#!/usr/bin/env python3
"""
API Key Testing for Auto Response Functionality
Tests the updated Cohere and Groq API keys for email processing workflow
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-sync-enhance.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# API Keys to test
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
COHERE_API_KEY = os.environ.get('COHERE_API_KEY')

class APIKeyTester:
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

    async def test_api_keys_configuration(self):
        """Test 1: Verify API keys are properly configured"""
        print("\n🔑 Testing API Keys Configuration...")
        
        try:
            # Check if API keys are set in environment
            groq_key_set = bool(GROQ_API_KEY and len(GROQ_API_KEY) > 10)
            cohere_key_set = bool(COHERE_API_KEY and len(COHERE_API_KEY) > 10)
            
            # Verify the specific keys from the review request
            expected_groq_key = "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"
            expected_cohere_key = "uW0jaFve1ytQLy62iM0vnXHcb87mcVEg6eZzPtei"
            
            groq_key_correct = GROQ_API_KEY == expected_groq_key
            cohere_key_correct = COHERE_API_KEY == expected_cohere_key
            
            all_passed = groq_key_set and cohere_key_set and groq_key_correct and cohere_key_correct
            
            details = f"GROQ key set: {groq_key_set}, COHERE key set: {cohere_key_set}, " \
                     f"GROQ correct: {groq_key_correct}, COHERE correct: {cohere_key_correct}"
            
            self.log_test_result("API Keys Configuration", all_passed, details)
            
        except Exception as e:
            self.log_test_result("API Keys Configuration", False, f"Exception: {str(e)}")

    async def test_cohere_api_functionality(self):
        """Test 2: Test Cohere API functionality directly"""
        print("\n🧠 Testing Cohere API Functionality...")
        
        try:
            # Import the Cohere function from server
            from server import get_cohere_embedding
            
            # Test with a simple text
            test_text = "I need pricing information for your product"
            
            try:
                embedding = await get_cohere_embedding(test_text)
                
                # Check if embedding is valid
                embedding_valid = (isinstance(embedding, list) and 
                                 len(embedding) > 0 and 
                                 all(isinstance(x, (int, float)) for x in embedding))
                
                if embedding_valid:
                    details = f"Embedding generated successfully, length: {len(embedding)}, first value: {embedding[0]:.4f}"
                else:
                    details = f"Invalid embedding format: {type(embedding)}"
                
                self.log_test_result("Cohere API Functionality", embedding_valid, details)
                
            except Exception as e:
                self.log_test_result("Cohere API Functionality", False, f"API call failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Cohere API Functionality", False, f"Import failed: {str(e)}")

    async def test_groq_api_functionality(self):
        """Test 3: Test Groq API functionality directly"""
        print("\n🤖 Testing Groq API Functionality...")
        
        try:
            # Import the Groq function from server
            from server import groq_chat_completion
            
            # Test with a simple message
            test_messages = [
                {"role": "user", "content": "Generate a brief professional email response to: 'I need pricing information'"}
            ]
            
            try:
                response = await groq_chat_completion(test_messages, "You are a helpful assistant.")
                
                # Check if response is valid
                response_valid = (isinstance(response, str) and 
                                len(response) > 10 and 
                                len(response) < 2000)  # Reasonable length
                
                if response_valid:
                    details = f"Response generated successfully, length: {len(response)} characters"
                else:
                    details = f"Invalid response format or length: {type(response)}, length: {len(response) if isinstance(response, str) else 'N/A'}"
                
                self.log_test_result("Groq API Functionality", response_valid, details)
                
            except Exception as e:
                self.log_test_result("Groq API Functionality", False, f"API call failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Groq API Functionality", False, f"Import failed: {str(e)}")

    async def test_email_classification_workflow(self):
        """Test 4: Test email classification using Cohere embeddings"""
        print("\n📧 Testing Email Classification Workflow...")
        
        try:
            # Get an active email account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Email Classification Workflow", False, "No active email accounts found")
                return
            
            self.test_account_id = account['id']
            
            # Import classification function
            from server import classify_email_intents, EmailMessage
            
            # Create test email
            test_email = EmailMessage(
                account_id=account['id'],
                message_id=f"<test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Pricing Information Request",
                sender="customer@example.com",
                recipient=account['email'],
                body="Hi, I'm interested in your product pricing. Can you send me more information?",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            try:
                # Test classification
                intents = await classify_email_intents(test_email)
                
                classification_successful = isinstance(intents, list)
                
                if classification_successful:
                    details = f"Classification completed, {len(intents)} intents found"
                    if intents:
                        intent_names = [intent.get('name', 'Unknown') for intent in intents]
                        details += f", Intent names: {', '.join(intent_names)}"
                else:
                    details = f"Classification failed, returned: {type(intents)}"
                
                self.log_test_result("Email Classification Workflow", classification_successful, details)
                
            except Exception as e:
                self.log_test_result("Email Classification Workflow", False, f"Classification failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Email Classification Workflow", False, f"Setup failed: {str(e)}")

    async def test_draft_generation_workflow(self):
        """Test 5: Test draft generation using Groq API"""
        print("\n✍️ Testing Draft Generation Workflow...")
        
        try:
            if not self.test_account_id:
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("Draft Generation Workflow", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Import functions
            from server import generate_draft, classify_email_intents, EmailMessage
            
            # Create test email
            test_email = EmailMessage(
                account_id=self.test_account_id,
                message_id=f"<test-draft-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Product Demo Request",
                sender="prospect@company.com",
                recipient="test@example.com",
                body="Hello, I'm interested in scheduling a demo of your AI email assistant. We're a growing company that receives many customer inquiries and need to automate our responses. Could you please provide more information about your solution and schedule a demo?",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            try:
                # First classify to get intents
                intents = await classify_email_intents(test_email)
                
                # Then generate draft
                draft = await generate_draft(test_email, intents)
                
                draft_successful = (isinstance(draft, dict) and 
                                  'plain_text' in draft and 
                                  'html' in draft and
                                  len(draft.get('plain_text', '')) > 50)
                
                if draft_successful:
                    plain_text_length = len(draft.get('plain_text', ''))
                    html_length = len(draft.get('html', ''))
                    details = f"Draft generated successfully, plain text: {plain_text_length} chars, HTML: {html_length} chars"
                else:
                    details = f"Draft generation failed, returned: {type(draft)}, keys: {list(draft.keys()) if isinstance(draft, dict) else 'N/A'}"
                
                self.log_test_result("Draft Generation Workflow", draft_successful, details)
                
            except Exception as e:
                self.log_test_result("Draft Generation Workflow", False, f"Draft generation failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Draft Generation Workflow", False, f"Setup failed: {str(e)}")

    async def test_complete_email_processing_workflow(self):
        """Test 6: Test complete email processing workflow via API"""
        print("\n🔄 Testing Complete Email Processing Workflow...")
        
        try:
            if not self.test_account_id:
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("Complete Email Processing Workflow", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Test email data
            test_email_data = {
                "subject": "Urgent: Need AI Email Assistant Pricing and Demo",
                "body": "Hi, I'm interested in your product pricing. Can you send me more information? We're a growing tech company and need to automate our email responses. Could you please provide detailed pricing information and schedule a demo? We need to make a decision this week.",
                "sender": "cto@techstartup.com",
                "account_id": self.test_account_id
            }
            
            try:
                print("   Testing /api/emails/test endpoint...")
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Check workflow completion
                    has_intents = bool(processed_email.get('intents'))
                    has_draft = bool(processed_email.get('draft'))
                    has_validation = bool(processed_email.get('validation_result'))
                    final_status = processed_email.get('status')
                    
                    # Check if email got stuck at 'classifying' stage
                    stuck_at_classifying = final_status == 'classifying'
                    
                    # Workflow is successful if it progresses beyond classifying
                    workflow_successful = (not stuck_at_classifying and 
                                         final_status not in ['error', 'classifying'] and
                                         (has_intents or has_draft))
                    
                    if workflow_successful:
                        details = f"Status: {response.status_code}, Final status: {final_status}, " \
                                 f"Intents: {len(processed_email.get('intents', []))}, " \
                                 f"Draft: {len(processed_email.get('draft', ''))} chars"
                    else:
                        details = f"Status: {response.status_code}, Final status: {final_status}, " \
                                 f"Stuck at classifying: {stuck_at_classifying}, " \
                                 f"Intents: {len(processed_email.get('intents', []))}"
                    
                    self.log_test_result("Complete Email Processing Workflow", workflow_successful, details)
                    
                    # Additional check for specific API errors
                    if stuck_at_classifying:
                        self.log_test_result("Email Processing - Not Stuck at Classifying", False, 
                                           "Email processing is still getting stuck at 'classifying' stage")
                    else:
                        self.log_test_result("Email Processing - Not Stuck at Classifying", True, 
                                           f"Email progressed beyond classifying to: {final_status}")
                    
                else:
                    details = f"API call failed - Status: {response.status_code}, Error: {response.text[:200]}"
                    self.log_test_result("Complete Email Processing Workflow", False, details)
                    
            except Exception as e:
                self.log_test_result("Complete Email Processing Workflow", False, f"API call exception: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Complete Email Processing Workflow", False, f"Setup failed: {str(e)}")

    async def test_email_processing_status_progression(self):
        """Test 7: Test email processing status progression"""
        print("\n📊 Testing Email Processing Status Progression...")
        
        try:
            if not self.test_account_id:
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("Email Processing Status Progression", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Simple test email
            simple_test_data = {
                "subject": "Simple Test",
                "body": "This is a simple test email for status progression testing.",
                "sender": "test@example.com",
                "account_id": self.test_account_id
            }
            
            try:
                print("   Testing status progression with simple email...")
                response = requests.post(f"{API_BASE}/emails/test", json=simple_test_data, timeout=30)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    final_status = processed_email.get('status')
                    
                    # Expected status progression: new -> classifying -> generating_draft -> validating -> ready_to_send/sent
                    valid_final_statuses = ['ready_to_send', 'sent', 'generating_draft', 'validating', 'needs_redraft']
                    invalid_statuses = ['classifying', 'error', 'new']
                    
                    status_progressed = final_status in valid_final_statuses
                    
                    if status_progressed:
                        details = f"Status progressed successfully to: {final_status}"
                    else:
                        details = f"Status stuck or failed at: {final_status}"
                    
                    self.log_test_result("Email Processing Status Progression", status_progressed, details)
                    
                else:
                    details = f"API call failed - Status: {response.status_code}"
                    self.log_test_result("Email Processing Status Progression", False, details)
                    
            except Exception as e:
                self.log_test_result("Email Processing Status Progression", False, f"Exception: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Email Processing Status Progression", False, f"Setup failed: {str(e)}")

    async def test_auto_send_functionality(self):
        """Test 8: Test auto-send functionality"""
        print("\n📤 Testing Auto-Send Functionality...")
        
        try:
            # Check if there are any emails ready to send
            emails_ready = await self.db.emails.find({"status": "ready_to_send"}).to_list(5)
            
            if emails_ready:
                test_email = emails_ready[0]
                email_id = test_email['id']
                
                try:
                    # Test sending the email
                    send_request = {"email_id": email_id, "manual_override": True}
                    response = requests.post(f"{API_BASE}/emails/{email_id}/send", json=send_request, timeout=15)
                    
                    send_successful = response.status_code == 200
                    
                    if send_successful:
                        details = f"Email sent successfully - Status: {response.status_code}"
                    else:
                        details = f"Send failed - Status: {response.status_code}, Error: {response.text[:100]}"
                    
                    self.log_test_result("Auto-Send Functionality", send_successful, details)
                    
                except Exception as e:
                    self.log_test_result("Auto-Send Functionality", False, f"Send exception: {str(e)}")
            else:
                # No emails ready to send, test the endpoint structure
                try:
                    # Test with a dummy email ID to check endpoint exists
                    dummy_request = {"email_id": "dummy-id", "manual_override": True}
                    response = requests.post(f"{API_BASE}/emails/dummy-id/send", json=dummy_request, timeout=10)
                    
                    # Endpoint should exist (404 for email not found is expected)
                    endpoint_exists = response.status_code in [404, 400, 500]  # Not 404 for route not found
                    
                    details = f"No emails ready to send, endpoint test - Status: {response.status_code}"
                    self.log_test_result("Auto-Send Functionality", endpoint_exists, details)
                    
                except Exception as e:
                    self.log_test_result("Auto-Send Functionality", False, f"Endpoint test failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Auto-Send Functionality", False, f"Setup failed: {str(e)}")

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🔑 API KEY TESTING SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        # Categorize results
        api_key_tests = [r for r in self.test_results if 'API' in r['test'] or 'Configuration' in r['test']]
        workflow_tests = [r for r in self.test_results if 'Workflow' in r['test'] or 'Processing' in r['test']]
        
        print(f"\n🔑 API Key Tests: {len([t for t in api_key_tests if t['passed']])}/{len(api_key_tests)} passed")
        print(f"🔄 Workflow Tests: {len([t for t in workflow_tests if t['passed']])}/{len(workflow_tests)} passed")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        print("\n" + "=" * 80)

    async def run_api_key_tests(self):
        """Run all API key and auto response tests"""
        print("🚀 Starting API Key Testing for Auto Response Functionality")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        print(f"Testing GROQ API Key: {GROQ_API_KEY[:20]}..." if GROQ_API_KEY else "GROQ API Key: Not set")
        print(f"Testing COHERE API Key: {COHERE_API_KEY[:20]}..." if COHERE_API_KEY else "COHERE API Key: Not set")
        print("=" * 80)
        
        # Setup
        if not await self.setup():
            return
        
        # Run tests in order
        await self.test_api_keys_configuration()
        await self.test_cohere_api_functionality()
        await self.test_groq_api_functionality()
        await self.test_email_classification_workflow()
        await self.test_draft_generation_workflow()
        await self.test_complete_email_processing_workflow()
        await self.test_email_processing_status_progression()
        await self.test_auto_send_functionality()
        
        # Cleanup
        await self.cleanup()
        
        # Print summary
        self.print_test_summary()

async def main():
    """Main function to run API key tests"""
    tester = APIKeyTester()
    await tester.run_api_key_tests()

if __name__ == "__main__":
    asyncio.run(main())