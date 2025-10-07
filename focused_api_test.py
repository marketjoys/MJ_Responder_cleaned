#!/usr/bin/env python3
"""
Focused API Testing for Auto Response Functionality
Tests specific scenarios mentioned in the review request
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dev-restart-setup.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FocusedAPITester:
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

    async def test_api_key_verification(self):
        """Test 1: Verify the specific API keys from review request are working"""
        print("\n🔑 Testing Specific API Keys from Review Request...")
        
        try:
            # Test Cohere API key directly
            import httpx
            
            cohere_key = "uW0jaFve1ytQLy62iM0vnXHcb87mcVEg6eZzPtei"
            groq_key = "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"
            
            # Test Cohere API
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.cohere.com/v1/embed",
                        headers={
                            "Authorization": f"Bearer {cohere_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "embed-english-v3.0",
                            "texts": ["Test API key functionality"],
                            "input_type": "classification",
                            "truncate": "NONE"
                        },
                        timeout=15
                    )
                    cohere_working = response.status_code == 200
                    cohere_details = f"Status: {response.status_code}"
                    if cohere_working:
                        result = response.json()
                        cohere_details += f", Embedding length: {len(result['embeddings'][0])}"
            except Exception as e:
                cohere_working = False
                cohere_details = f"Error: {str(e)}"
            
            # Test Groq API
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {groq_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "messages": [{"role": "user", "content": "Say 'API key test successful'"}],
                            "model": "deepseek-r1-distill-llama-70b",
                            "temperature": 0.1,
                            "max_completion_tokens": 50
                        },
                        timeout=15
                    )
                    groq_working = response.status_code == 200
                    groq_details = f"Status: {response.status_code}"
                    if groq_working:
                        result = response.json()
                        groq_details += f", Response: {result['choices'][0]['message']['content'][:50]}"
                    elif response.status_code == 429:
                        groq_details += " (Rate limited - but key is valid)"
                        groq_working = True  # Rate limit means key is valid
            except Exception as e:
                groq_working = False
                groq_details = f"Error: {str(e)}"
            
            all_passed = cohere_working and groq_working
            
            self.log_test_result("Cohere API Key Verification", cohere_working, cohere_details)
            self.log_test_result("Groq API Key Verification", groq_working, groq_details)
            self.log_test_result("API Key Verification", all_passed, f"Cohere: {cohere_working}, Groq: {groq_working}")
            
        except Exception as e:
            self.log_test_result("API Key Verification", False, f"Exception: {str(e)}")

    async def test_classify_email_intents_function(self):
        """Test 2: Test classify_email_intents function specifically"""
        print("\n🎯 Testing classify_email_intents Function...")
        
        try:
            # Get an active email account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("classify_email_intents Function", False, "No active email accounts found")
                return
            
            self.test_account_id = account['id']
            
            # Import the function
            from server import classify_email_intents, EmailMessage
            
            # Create test email message
            test_email = EmailMessage(
                account_id=account['id'],
                message_id=f"<test-classify-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Product Pricing Information Request",
                sender="customer@company.com",
                recipient=account['email'],
                body="Hi, I'm interested in your product pricing. Can you send me more information about your AI email assistant? We need detailed pricing and would like to schedule a demo.",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            try:
                # Test classification
                intents = await classify_email_intents(test_email)
                
                classification_successful = isinstance(intents, list)
                
                if classification_successful:
                    details = f"Classification completed successfully, {len(intents)} intents found"
                    if intents:
                        for intent in intents:
                            details += f"\n      - {intent.get('name', 'Unknown')}: {intent.get('confidence', 0):.3f}"
                else:
                    details = f"Classification failed, returned: {type(intents)}"
                
                self.log_test_result("classify_email_intents Function", classification_successful, details)
                
            except Exception as e:
                self.log_test_result("classify_email_intents Function", False, f"Function call failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("classify_email_intents Function", False, f"Setup failed: {str(e)}")

    async def test_generate_draft_function(self):
        """Test 3: Test generate_draft function specifically"""
        print("\n✍️ Testing generate_draft Function...")
        
        try:
            if not self.test_account_id:
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("generate_draft Function", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Import functions
            from server import generate_draft, classify_email_intents, EmailMessage
            
            # Create test email
            test_email = EmailMessage(
                account_id=self.test_account_id,
                message_id=f"<test-draft-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Product Information Request",
                sender="prospect@company.com",
                recipient="test@example.com",
                body="Hello, I'm interested in your AI email assistant. Could you please provide more information about pricing and features?",
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
                                  'html' in draft)
                
                if draft_successful:
                    plain_text = draft.get('plain_text', '')
                    html_text = draft.get('html', '')
                    reasoning = draft.get('reasoning', '')
                    
                    details = f"Draft generated successfully\n"
                    details += f"      - Plain text length: {len(plain_text)} chars\n"
                    details += f"      - HTML length: {len(html_text)} chars\n"
                    details += f"      - Reasoning: {reasoning}"
                    
                    # Check if draft has meaningful content
                    has_content = len(plain_text) > 20 and 'Dear' in plain_text or 'Hello' in plain_text
                    if not has_content:
                        draft_successful = False
                        details += f"\n      - WARNING: Draft appears to have minimal content"
                else:
                    details = f"Draft generation failed, returned: {type(draft)}"
                    if isinstance(draft, dict):
                        details += f", keys: {list(draft.keys())}"
                
                self.log_test_result("generate_draft Function", draft_successful, details)
                
            except Exception as e:
                self.log_test_result("generate_draft Function", False, f"Function call failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("generate_draft Function", False, f"Setup failed: {str(e)}")

    async def test_process_email_async_workflow(self):
        """Test 4: Test complete process_email_async workflow"""
        print("\n🔄 Testing process_email_async Workflow...")
        
        try:
            if not self.test_account_id:
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("process_email_async Workflow", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Import the function
            from server import process_email_async, EmailMessage
            
            # Create test email and store in database
            test_email = EmailMessage(
                account_id=self.test_account_id,
                message_id=f"<test-process-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Product Demo Request",
                sender="customer@techcompany.com",
                recipient="test@example.com",
                body="Hi, I'm interested in your product pricing. Can you send me more information?",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Store in database
            await self.db.emails.insert_one(test_email.dict())
            
            try:
                # Process the email
                await process_email_async(test_email.id)
                
                # Check the result
                processed_email = await self.db.emails.find_one({"id": test_email.id})
                
                if processed_email:
                    final_status = processed_email.get('status')
                    has_intents = bool(processed_email.get('intents'))
                    has_draft = bool(processed_email.get('draft'))
                    has_validation = bool(processed_email.get('validation_result'))
                    
                    # Success if email progressed beyond 'new' status
                    workflow_successful = final_status != 'new' and final_status != 'error'
                    
                    details = f"Email processed to status: {final_status}\n"
                    details += f"      - Has intents: {has_intents} ({len(processed_email.get('intents', []))} found)\n"
                    details += f"      - Has draft: {has_draft} ({len(processed_email.get('draft', ''))} chars)\n"
                    details += f"      - Has validation: {has_validation}"
                    
                    if final_status == 'classifying':
                        workflow_successful = False
                        details += "\n      - WARNING: Email stuck at 'classifying' stage"
                    
                else:
                    workflow_successful = False
                    details = "Email not found in database after processing"
                
                self.log_test_result("process_email_async Workflow", workflow_successful, details)
                
            except Exception as e:
                self.log_test_result("process_email_async Workflow", False, f"Processing failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("process_email_async Workflow", False, f"Setup failed: {str(e)}")

    async def test_emails_test_endpoint_comprehensive(self):
        """Test 5: Test /api/emails/test endpoint comprehensively"""
        print("\n🧪 Testing /api/emails/test Endpoint Comprehensively...")
        
        try:
            if not self.test_account_id:
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("/api/emails/test Endpoint", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Test the specific scenario from review request
            test_email_data = {
                "subject": "Product Pricing Information",
                "body": "Hi, I'm interested in your product pricing. Can you send me more information?",
                "sender": "customer@example.com",
                "account_id": self.test_account_id
            }
            
            try:
                print("   Testing /api/emails/test endpoint with comprehensive monitoring...")
                
                # Record start time
                start_time = time.time()
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                
                # Record end time
                end_time = time.time()
                processing_time = end_time - start_time
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Analyze the response
                    final_status = processed_email.get('status')
                    intents = processed_email.get('intents', [])
                    draft = processed_email.get('draft', '')
                    validation_result = processed_email.get('validation_result')
                    error = processed_email.get('error')
                    
                    # Determine success criteria
                    not_stuck_at_classifying = final_status != 'classifying'
                    has_progressed = final_status not in ['new', 'error']
                    no_503_errors = '503' not in str(error) if error else True
                    reasonable_time = processing_time < 45  # Should complete within 45 seconds
                    
                    endpoint_successful = (not_stuck_at_classifying and has_progressed and 
                                         no_503_errors and reasonable_time)
                    
                    details = f"Processing time: {processing_time:.1f}s, Final status: {final_status}\n"
                    details += f"      - Intents found: {len(intents)}\n"
                    details += f"      - Draft length: {len(draft)} chars\n"
                    details += f"      - Has validation: {bool(validation_result)}\n"
                    details += f"      - Not stuck at classifying: {not_stuck_at_classifying}\n"
                    details += f"      - No 503 errors: {no_503_errors}"
                    
                    if error:
                        details += f"\n      - Error: {str(error)[:100]}"
                    
                else:
                    endpoint_successful = False
                    details = f"HTTP Error - Status: {response.status_code}, Response: {response.text[:200]}"
                
                self.log_test_result("/api/emails/test Endpoint", endpoint_successful, details)
                
            except Exception as e:
                self.log_test_result("/api/emails/test Endpoint", False, f"Request failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("/api/emails/test Endpoint", False, f"Setup failed: {str(e)}")

    async def test_503_service_unavailable_resolution(self):
        """Test 6: Check if 503 Service Unavailable errors are resolved"""
        print("\n🚨 Testing 503 Service Unavailable Error Resolution...")
        
        try:
            # Check recent emails in database for 503 errors
            recent_emails = await self.db.emails.find().sort("created_at", -1).limit(10).to_list(10)
            
            has_503_errors = False
            error_count = 0
            
            for email in recent_emails:
                error = email.get('error', '')
                if '503' in str(error) or 'Service Unavailable' in str(error):
                    has_503_errors = True
                    error_count += 1
            
            # Test with a simple email to see if we still get 503 errors
            if self.test_account_id:
                simple_test_data = {
                    "subject": "Simple Test",
                    "body": "Test for 503 errors",
                    "sender": "test@example.com",
                    "account_id": self.test_account_id
                }
                
                try:
                    response = requests.post(f"{API_BASE}/emails/test", json=simple_test_data, timeout=30)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        current_error = processed_email.get('error', '')
                        has_current_503 = '503' in str(current_error)
                    else:
                        has_current_503 = response.status_code == 503
                        
                except Exception as e:
                    has_current_503 = '503' in str(e)
            else:
                has_current_503 = False
            
            no_503_errors = not has_503_errors and not has_current_503
            
            details = f"Recent 503 errors in DB: {error_count}/10 emails\n"
            details += f"      - Current test has 503 error: {has_current_503}\n"
            details += f"      - 503 errors resolved: {no_503_errors}"
            
            self.log_test_result("503 Service Unavailable Resolution", no_503_errors, details)
            
        except Exception as e:
            self.log_test_result("503 Service Unavailable Resolution", False, f"Check failed: {str(e)}")

    def print_focused_summary(self):
        """Print focused test summary"""
        print("\n" + "=" * 80)
        print("🎯 FOCUSED API TESTING SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        # Key findings
        api_key_tests = [r for r in self.test_results if 'API Key' in r['test']]
        workflow_tests = [r for r in self.test_results if any(x in r['test'] for x in ['Workflow', 'Function', 'Endpoint'])]
        error_resolution_tests = [r for r in self.test_results if '503' in r['test']]
        
        print(f"\n📊 BREAKDOWN:")
        print(f"🔑 API Key Tests: {len([t for t in api_key_tests if t['passed']])}/{len(api_key_tests)} passed")
        print(f"🔄 Workflow Tests: {len([t for t in workflow_tests if t['passed']])}/{len(workflow_tests)} passed")
        print(f"🚨 Error Resolution: {len([t for t in error_resolution_tests if t['passed']])}/{len(error_resolution_tests)} passed")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}")
                if test['details']:
                    print(f"     {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        print("\n" + "=" * 80)

    async def run_focused_tests(self):
        """Run focused tests based on review request"""
        print("🎯 Starting Focused API Testing for Auto Response Functionality")
        print("Testing specific scenarios from review request:")
        print("- API key functionality (Cohere and Groq)")
        print("- classify_email_intents function")
        print("- generate_draft function")
        print("- process_email_async workflow")
        print("- /api/emails/test endpoint")
        print("- 503 Service Unavailable error resolution")
        print("=" * 80)
        
        # Setup
        if not await self.setup():
            return
        
        # Run focused tests
        await self.test_api_key_verification()
        await self.test_classify_email_intents_function()
        await self.test_generate_draft_function()
        await self.test_process_email_async_workflow()
        await self.test_emails_test_endpoint_comprehensive()
        await self.test_503_service_unavailable_resolution()
        
        # Cleanup
        await self.cleanup()
        
        # Print summary
        self.print_focused_summary()

async def main():
    """Main function to run focused tests"""
    tester = FocusedAPITester()
    await tester.run_focused_tests()

if __name__ == "__main__":
    asyncio.run(main())