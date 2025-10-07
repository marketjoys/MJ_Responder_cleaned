#!/usr/bin/env python3
"""
Signature HTML Processing Test - Focused testing for signature double-encoding fixes
Tests the specific issues mentioned in the review request:
1. Email processing workflow with new API keys
2. Signature HTML processing - verify <br> tags don't get double-encoded
3. validate_final_email function for HTML signature handling
4. Both plain text and HTML email generation
5. Complete workflow via /api/emails/test endpoint
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime
import uuid
import re

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

# New API Keys from review request
EXPECTED_GROQ_KEY = "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"
EXPECTED_COHERE_KEY = "8vXdpspVCVDmAb4w5f2ccZp89aFeG8qNR4DYRywS"

class SignatureProcessingTester:
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
    
    async def test_api_keys_validation(self):
        """Test 1: Verify new API keys are correctly configured"""
        print("\n🔑 Testing API Keys Validation...")
        
        try:
            # Check environment variables
            current_groq_key = os.environ.get('GROQ_API_KEY', '')
            current_cohere_key = os.environ.get('COHERE_API_KEY', '')
            
            groq_key_correct = current_groq_key == EXPECTED_GROQ_KEY
            cohere_key_correct = current_cohere_key == EXPECTED_COHERE_KEY
            
            # Test Groq API functionality
            groq_functional = False
            try:
                from server import groq_chat_completion
                test_messages = [{"role": "user", "content": "Say 'API test successful'"}]
                response = await groq_chat_completion(test_messages)
                groq_functional = "API test successful" in response or len(response) > 10
            except Exception as e:
                print(f"   Groq API test failed: {str(e)}")
            
            # Test Cohere API functionality
            cohere_functional = False
            try:
                from server import get_cohere_embedding
                embedding = await get_cohere_embedding("test text for embedding")
                cohere_functional = isinstance(embedding, list) and len(embedding) > 100
            except Exception as e:
                print(f"   Cohere API test failed: {str(e)}")
            
            all_passed = groq_key_correct and cohere_key_correct and groq_functional and cohere_functional
            
            details = f"Groq key: {groq_key_correct} (functional: {groq_functional}), " \
                     f"Cohere key: {cohere_key_correct} (functional: {cohere_functional})"
            
            self.log_test_result("API Keys Validation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("API Keys Validation", False, f"Exception: {str(e)}")
    
    async def test_signature_html_processing(self):
        """Test 2: Signature HTML Processing - verify no double-encoding of <br> tags"""
        print("\n📝 Testing Signature HTML Processing...")
        
        try:
            # Create test account with HTML signature containing <br> tags
            test_signature_html = """<p>Best regards,<br>John Smith<br>Senior Developer</p>
<p>TechCorp Solutions<br>Email: john.smith@techcorp.com<br>Phone: +1-555-0123</p>"""
            
            account_data = {
                "name": "Signature Test Account",
                "email": "signature.test@example.com",
                "provider": "gmail",
                "username": "signature.test@example.com",
                "password": "test_signature_password",
                "persona": "Professional and helpful",
                "signature": test_signature_html,
                "auto_send": False
            }
            
            # Create account
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
            account_created = response.status_code in [200, 201]
            
            if account_created:
                created_account = response.json()
                self.test_account_id = created_account.get('id')
                print(f"   Created test account: {self.test_account_id}")
            else:
                self.log_test_result("Signature HTML Processing", False, f"Failed to create test account: {response.status_code}")
                return
            
            # Test email processing with signature
            test_email_data = {
                "subject": "Signature HTML Processing Test",
                "body": "Hello! I need information about your services. Please provide details about pricing and availability. Thank you!",
                "sender": "customer@example.com",
                "account_id": self.test_account_id
            }
            
            print("   Processing test email with HTML signature...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
            email_processed = response.status_code in [200, 201]
            
            if email_processed:
                processed_email = response.json()
                
                # Check for signature in final email
                draft_html = processed_email.get('draft_html', '')
                draft_plain = processed_email.get('draft', '')
                
                # Test for double-encoding issues
                double_br_pattern = r'<br\s*/?>\s*<br\s*/?>'  # Look for consecutive <br> tags
                excessive_br_count = len(re.findall(r'<br\s*/?>', draft_html, re.IGNORECASE))
                
                # Check if signature is properly included
                signature_in_html = 'john.smith@techcorp.com' in draft_html.lower()
                signature_in_plain = 'john.smith@techcorp.com' in draft_plain.lower()
                
                # Check for proper HTML structure (no double-encoding)
                no_double_encoding = '&lt;br&gt;' not in draft_html and '&amp;' not in draft_html
                
                # Validate final email structure
                validation_result = processed_email.get('validation_result', {})
                validation_passed = validation_result.get('status') in ['PASS', 'APPROVED']
                
                signature_processing_passed = (signature_in_html and signature_in_plain and 
                                             no_double_encoding and excessive_br_count < 20)
                
                details = f"HTML signature included: {signature_in_html}, " \
                         f"Plain signature included: {signature_in_plain}, " \
                         f"No double-encoding: {no_double_encoding}, " \
                         f"BR count: {excessive_br_count}, " \
                         f"Validation: {validation_passed}"
                
                self.log_test_result("Signature HTML Processing", signature_processing_passed, details)
                
                # Additional detailed logging for debugging
                print(f"   Draft HTML length: {len(draft_html)}")
                print(f"   Draft plain length: {len(draft_plain)}")
                print(f"   Validation status: {validation_result.get('status', 'None')}")
                
            else:
                self.log_test_result("Signature HTML Processing", False, f"Email processing failed: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Signature HTML Processing", False, f"Exception: {str(e)}")
    
    async def test_validate_final_email_function(self):
        """Test 3: validate_final_email function - direct testing of signature handling"""
        print("\n🔍 Testing validate_final_email Function...")
        
        try:
            # Import required functions
            from server import EmailMessage, validate_final_email
            
            # Get test account
            if not self.test_account_id:
                accounts = await self.db.email_accounts.find().to_list(10)
                if accounts:
                    self.test_account_id = accounts[0]['id']
                else:
                    self.log_test_result("validate_final_email Function", False, "No test account available")
                    return
            
            account = await self.db.email_accounts.find_one({"id": self.test_account_id})
            if not account:
                self.log_test_result("validate_final_email Function", False, "Test account not found")
                return
            
            # Create test email message
            test_email = EmailMessage(
                account_id=self.test_account_id,
                message_id=f"<validate-test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Validate Final Email Test",
                sender="validation.test@example.com",
                recipient=account['email'],
                body="I'm interested in your product. Can you provide more information about pricing and features?",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Create test draft with potential signature issues
            test_draft = {
                'plain_text': "Thank you for your inquiry about our product.\n\nWe offer competitive pricing and comprehensive features.",
                'html': "<p>Thank you for your inquiry about our product.</p><p>We offer competitive pricing and comprehensive features.</p>"
            }
            
            # Test intents (empty for this test)
            test_intents = []
            
            # Call validate_final_email function directly
            validation_result = await validate_final_email(test_email, test_draft, test_intents, account)
            
            # Check validation results
            validation_completed = validation_result is not None
            has_status = 'status' in validation_result if validation_result else False
            has_feedback = 'feedback' in validation_result if validation_result else False
            
            # Check if signature was properly processed
            final_content_check = True
            if validation_result and 'final_plain_text' in validation_result:
                final_plain = validation_result['final_plain_text']
                final_html = validation_result.get('final_html', '')
                
                # Check for signature inclusion
                signature_included = account.get('signature', '') in final_plain or account.get('signature', '') in final_html
                
                # Check for double-encoding issues
                no_double_encoding = '&lt;br&gt;' not in final_html and '&amp;' not in final_html
                
                final_content_check = signature_included and no_double_encoding
            
            function_passed = validation_completed and has_status and has_feedback and final_content_check
            
            details = f"Validation completed: {validation_completed}, " \
                     f"Has status: {has_status}, " \
                     f"Has feedback: {has_feedback}, " \
                     f"Content check: {final_content_check}"
            
            if validation_result:
                details += f", Status: {validation_result.get('status', 'None')}"
            
            self.log_test_result("validate_final_email Function", function_passed, details)
            
        except Exception as e:
            self.log_test_result("validate_final_email Function", False, f"Exception: {str(e)}")
    
    async def test_plain_text_html_generation(self):
        """Test 4: Both plain text and HTML email generation with signatures"""
        print("\n📧 Testing Plain Text and HTML Email Generation...")
        
        try:
            # Test with different signature formats
            test_cases = [
                {
                    "name": "HTML Signature with BR tags",
                    "signature": "Best regards,<br>Jane Doe<br>Marketing Manager<br>jane.doe@company.com"
                },
                {
                    "name": "Plain Text Signature",
                    "signature": "Best regards,\nJane Doe\nMarketing Manager\njane.doe@company.com"
                },
                {
                    "name": "Mixed HTML Signature",
                    "signature": "<p>Best regards,<br><strong>Jane Doe</strong><br><em>Marketing Manager</em></p><p>Email: jane.doe@company.com<br>Phone: +1-555-0123</p>"
                }
            ]
            
            all_tests_passed = True
            test_details = []
            
            for i, test_case in enumerate(test_cases):
                try:
                    # Update test account signature
                    if self.test_account_id:
                        update_data = {
                            "name": "Signature Format Test Account",
                            "email": "format.test@example.com",
                            "provider": "gmail",
                            "username": "format.test@example.com",
                            "password": "test_format_password",
                            "persona": "Professional and helpful",
                            "signature": test_case["signature"],
                            "auto_send": False
                        }
                        
                        response = requests.put(f"{API_BASE}/email-accounts/{self.test_account_id}", 
                                              json=update_data, timeout=15)
                        
                        if response.status_code != 200:
                            all_tests_passed = False
                            test_details.append(f"{test_case['name']}: Update failed")
                            continue
                    
                    # Test email processing
                    test_email_data = {
                        "subject": f"Format Test {i+1}: {test_case['name']}",
                        "body": "Hello! I'm interested in your services. Could you please provide more information about your offerings and pricing? I look forward to hearing from you soon.",
                        "sender": f"format.test{i+1}@example.com",
                        "account_id": self.test_account_id
                    }
                    
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        draft_html = processed_email.get('draft_html', '')
                        draft_plain = processed_email.get('draft', '')
                        
                        # Check both formats have content
                        has_html_content = len(draft_html) > 100
                        has_plain_content = len(draft_plain) > 100
                        
                        # Check signature inclusion
                        signature_in_html = any(word in draft_html.lower() for word in ['jane', 'doe', 'marketing'])
                        signature_in_plain = any(word in draft_plain.lower() for word in ['jane', 'doe', 'marketing'])
                        
                        # Check for proper HTML formatting
                        proper_html = '<p>' in draft_html or '<br' in draft_html
                        
                        # Check for no double-encoding
                        no_double_encoding = '&lt;' not in draft_html and '&gt;' not in draft_html
                        
                        case_passed = (has_html_content and has_plain_content and 
                                     signature_in_html and signature_in_plain and 
                                     proper_html and no_double_encoding)
                        
                        if not case_passed:
                            all_tests_passed = False
                        
                        test_details.append(f"{test_case['name']}: {'PASS' if case_passed else 'FAIL'} "
                                          f"(HTML: {len(draft_html)}, Plain: {len(draft_plain)})")
                        
                    else:
                        all_tests_passed = False
                        test_details.append(f"{test_case['name']}: Processing failed ({response.status_code})")
                        
                except Exception as e:
                    all_tests_passed = False
                    test_details.append(f"{test_case['name']}: Exception - {str(e)}")
            
            details = "; ".join(test_details)
            self.log_test_result("Plain Text and HTML Generation", all_tests_passed, details)
            
        except Exception as e:
            self.log_test_result("Plain Text and HTML Generation", False, f"Exception: {str(e)}")
    
    async def test_complete_workflow_endpoint(self):
        """Test 5: Complete workflow via /api/emails/test endpoint"""
        print("\n🔄 Testing Complete Workflow via /api/emails/test...")
        
        try:
            # Comprehensive test email that should trigger multiple intents
            comprehensive_test_data = {
                "subject": "Comprehensive Test: Product Inquiry, Demo Request, and Pricing Information",
                "body": """Hello,

I hope this email finds you well. I'm writing to inquire about your AI Email Assistant solution for our growing technology company.

We're currently handling over 500 customer inquiries per day manually, and we're looking for an automated solution that can:

1. Classify incoming emails by intent
2. Generate professional, contextual responses
3. Handle follow-up communications
4. Integrate with our existing systems

Could you please provide:
- Detailed pricing information for different tiers
- A demo or trial access to test the system
- Information about implementation timeline
- Technical requirements and integration options

We have a budget allocated for this project and are looking to make a decision within the next two weeks. Our team is particularly interested in how your system handles complex customer inquiries and maintains brand voice consistency.

Please let me know your availability for a call to discuss this further. We're excited about the potential of working together.

Thank you for your time and consideration.

Best regards,
Sarah Johnson
CTO, TechInnovate Solutions
sarah.johnson@techinnovate.com
+1-555-0199""",
                "sender": "sarah.johnson@techinnovate.com",
                "account_id": self.test_account_id
            }
            
            print("   Processing comprehensive test email...")
            start_time = time.time()
            
            response = requests.post(f"{API_BASE}/emails/test", json=comprehensive_test_data, timeout=60)
            
            processing_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check workflow completion
                has_intents = len(processed_email.get('intents', [])) > 0
                has_draft = len(processed_email.get('draft', '')) > 100
                has_draft_html = len(processed_email.get('draft_html', '')) > 100
                has_validation = processed_email.get('validation_result') is not None
                
                final_status = processed_email.get('status', '')
                workflow_completed = final_status in ['ready_to_send', 'sent', 'needs_redraft']
                
                # Check signature processing
                draft_html = processed_email.get('draft_html', '')
                draft_plain = processed_email.get('draft', '')
                
                # Look for signature elements
                signature_processed = any(word in draft_html.lower() or word in draft_plain.lower() 
                                        for word in ['regards', 'best', 'sincerely'])
                
                # Check for proper HTML structure
                proper_html_structure = ('<p>' in draft_html and '</p>' in draft_html) or '<br' in draft_html
                
                # Check for no double-encoding issues
                no_encoding_issues = ('&lt;br&gt;' not in draft_html and 
                                    '&amp;' not in draft_html and
                                    draft_html.count('<br') < 15)  # Reasonable BR tag count
                
                # Performance check
                reasonable_processing_time = processing_time < 50  # Should complete within 50 seconds
                
                workflow_passed = (has_intents and has_draft and has_draft_html and 
                                 has_validation and workflow_completed and 
                                 signature_processed and proper_html_structure and 
                                 no_encoding_issues and reasonable_processing_time)
                
                details = f"Intents: {len(processed_email.get('intents', []))}, " \
                         f"Draft length: {len(processed_email.get('draft', ''))}, " \
                         f"HTML length: {len(draft_html)}, " \
                         f"Status: {final_status}, " \
                         f"Processing time: {processing_time:.1f}s, " \
                         f"Signature processed: {signature_processed}, " \
                         f"No encoding issues: {no_encoding_issues}"
                
                self.log_test_result("Complete Workflow Endpoint", workflow_passed, details)
                
                # Additional detailed logging
                print(f"   Processing completed in {processing_time:.1f} seconds")
                print(f"   Final status: {final_status}")
                print(f"   Intents found: {len(processed_email.get('intents', []))}")
                if processed_email.get('validation_result'):
                    print(f"   Validation status: {processed_email['validation_result'].get('status', 'None')}")
                
            else:
                self.log_test_result("Complete Workflow Endpoint", False, 
                                   f"Request failed: {response.status_code}, Response: {response.text[:200]}")
                
        except Exception as e:
            self.log_test_result("Complete Workflow Endpoint", False, f"Exception: {str(e)}")
    
    async def cleanup_test_account(self):
        """Cleanup: Remove test account"""
        if self.test_account_id:
            try:
                response = requests.delete(f"{API_BASE}/email-accounts/{self.test_account_id}", timeout=10)
                if response.status_code in [200, 204]:
                    print(f"✅ Cleaned up test account: {self.test_account_id}")
                else:
                    print(f"⚠️  Failed to cleanup test account: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Cleanup error: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("SIGNATURE HTML PROCESSING TEST SUMMARY")
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
    print("🧪 Starting Signature HTML Processing Tests...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Expected Groq Key: {EXPECTED_GROQ_KEY[:20]}...")
    print(f"Expected Cohere Key: {EXPECTED_COHERE_KEY[:20]}...")
    
    tester = SignatureProcessingTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests in sequence
        await tester.test_api_keys_validation()
        await tester.test_signature_html_processing()
        await tester.test_validate_final_email_function()
        await tester.test_plain_text_html_generation()
        await tester.test_complete_workflow_endpoint()
        
        # Cleanup
        await tester.cleanup_test_account()
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Print summary and cleanup
        tester.print_summary()
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())