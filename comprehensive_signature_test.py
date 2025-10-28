#!/usr/bin/env python3
"""
Comprehensive Signature Processing Test - Test all review requirements
"""
import asyncio
import sys
import os
import requests
import json
import re
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://redis-worker-setup.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Expected API Keys from review request
EXPECTED_GROQ_KEY = "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"
EXPECTED_COHERE_KEY = "8vXdpspVCVDmAb4w5f2ccZp89aFeG8qNR4DYRywS"

class ComprehensiveSignatureTester:
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
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
    
    async def test_1_api_keys_validation(self):
        """Test 1: Email processing workflow with new API keys"""
        print("\n🔑 Test 1: API Keys Validation")
        
        try:
            # Check environment variables
            current_groq_key = os.environ.get('GROQ_API_KEY', '')
            current_cohere_key = os.environ.get('COHERE_API_KEY', '')
            
            groq_key_correct = current_groq_key == EXPECTED_GROQ_KEY
            cohere_key_correct = current_cohere_key == EXPECTED_COHERE_KEY
            
            # Test API functionality
            from server import groq_chat_completion, get_cohere_embedding
            
            # Test Groq
            groq_response = await groq_chat_completion([{"role": "user", "content": "Say 'API working'"}])
            groq_functional = "API working" in groq_response or len(groq_response) > 5
            
            # Test Cohere
            cohere_embedding = await get_cohere_embedding("test embedding")
            cohere_functional = isinstance(cohere_embedding, list) and len(cohere_embedding) > 100
            
            all_passed = groq_key_correct and cohere_key_correct and groq_functional and cohere_functional
            
            details = f"Groq key correct: {groq_key_correct}, functional: {groq_functional}; " \
                     f"Cohere key correct: {cohere_key_correct}, functional: {cohere_functional}"
            
            self.log_result("API Keys Validation", all_passed, details)
            return all_passed
            
        except Exception as e:
            self.log_result("API Keys Validation", False, f"Exception: {str(e)}")
            return False
    
    async def test_2_signature_html_processing(self):
        """Test 2: Signature HTML processing - verify no double-encoding of <br> tags"""
        print("\n📝 Test 2: Signature HTML Processing")
        
        try:
            # Test different signature formats
            test_signatures = [
                {
                    "name": "HTML with BR tags",
                    "signature": "Best regards,<br>John Smith<br>Senior Developer<br>john.smith@company.com"
                },
                {
                    "name": "Plain text",
                    "signature": "Best regards,\nJohn Smith\nSenior Developer\njohn.smith@company.com"
                },
                {
                    "name": "Mixed HTML",
                    "signature": "<p>Best regards,<br><strong>John Smith</strong></p><p>Email: john.smith@company.com</p>"
                }
            ]
            
            all_tests_passed = True
            test_details = []
            
            for sig_test in test_signatures:
                # Create test account
                account_data = {
                    "name": f"Test Account - {sig_test['name']}",
                    "email": f"test.{sig_test['name'].lower().replace(' ', '.')}@example.com",
                    "provider": "gmail",
                    "username": f"test.{sig_test['name'].lower().replace(' ', '.')}@example.com",
                    "password": "test_password",
                    "persona": "Professional and helpful",
                    "signature": sig_test['signature'],
                    "auto_send": False
                }
                
                response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
                if response.status_code not in [200, 201]:
                    all_tests_passed = False
                    test_details.append(f"{sig_test['name']}: Account creation failed")
                    continue
                
                account = response.json()
                account_id = account['id']
                
                # Test email processing
                test_email_data = {
                    "subject": f"Signature Test - {sig_test['name']}",
                    "body": "Hello! I need information about your services. Please provide pricing details. Thank you!",
                    "sender": f"customer.{sig_test['name'].lower().replace(' ', '.')}@example.com",
                    "account_id": account_id
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    draft_html = result.get('draft_html', '')
                    draft_plain = result.get('draft', '')
                    
                    # Check for double-encoding issues
                    no_double_encoding = ('&lt;br&gt;' not in draft_html and 
                                        '&amp;' not in draft_html and
                                        '&lt;' not in draft_html)
                    
                    # Check BR tag count (should be reasonable)
                    br_count = draft_html.lower().count('<br')
                    reasonable_br_count = br_count < 20
                    
                    # Check signature inclusion
                    signature_keywords = ['regards', 'john', 'smith']
                    signature_in_html = any(kw.lower() in draft_html.lower() for kw in signature_keywords)
                    signature_in_plain = any(kw.lower() in draft_plain.lower() for kw in signature_keywords)
                    
                    test_passed = (no_double_encoding and reasonable_br_count and 
                                 signature_in_html and signature_in_plain)
                    
                    if not test_passed:
                        all_tests_passed = False
                    
                    test_details.append(f"{sig_test['name']}: {'PASS' if test_passed else 'FAIL'} "
                                      f"(no double-encoding: {no_double_encoding}, "
                                      f"BR count: {br_count}, signature included: {signature_in_html})")
                else:
                    all_tests_passed = False
                    test_details.append(f"{sig_test['name']}: Email processing failed ({response.status_code})")
                
                # Cleanup account
                try:
                    requests.delete(f"{API_BASE}/email-accounts/{account_id}", timeout=10)
                except:
                    pass
            
            details = "; ".join(test_details)
            self.log_result("Signature HTML Processing", all_tests_passed, details)
            return all_tests_passed
            
        except Exception as e:
            self.log_result("Signature HTML Processing", False, f"Exception: {str(e)}")
            return False
    
    async def test_3_validate_final_email_function(self):
        """Test 3: validate_final_email function handling"""
        print("\n🔍 Test 3: validate_final_email Function")
        
        try:
            from server import EmailMessage, validate_final_email
            
            # Get account with signature
            account = await self.db.email_accounts.find_one({"signature": {"$ne": ""}})
            if not account:
                self.log_result("validate_final_email Function", False, "No account with signature found")
                return False
            
            # Create test email
            test_email = EmailMessage(
                account_id=account['id'],
                message_id=f"<validate-test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Validate Function Test",
                sender="validate.test@example.com",
                recipient=account['email'],
                body="I need information about your services and pricing. Please help!",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Test draft
            test_draft = {
                'plain_text': "Thank you for your inquiry. We offer comprehensive services with competitive pricing.",
                'html': "<p>Thank you for your inquiry. We offer comprehensive services with competitive pricing.</p>"
            }
            
            # Call validate_final_email
            validation_result = await validate_final_email(test_email, test_draft, [], account)
            
            # Check results
            has_status = 'status' in validation_result
            has_final_content = 'final_plain_text' in validation_result and 'final_html' in validation_result
            signature_included = False
            no_double_encoding = True
            
            if has_final_content:
                final_plain = validation_result['final_plain_text']
                final_html = validation_result['final_html']
                
                # Check signature inclusion
                signature_keywords = ['regards', 'assistant', 'team']
                signature_included = any(kw.lower() in final_plain.lower() for kw in signature_keywords)
                
                # Check for double-encoding
                no_double_encoding = ('&lt;br&gt;' not in final_html and 
                                    '&amp;' not in final_html)
            
            function_passed = has_status and has_final_content and signature_included and no_double_encoding
            
            details = f"Has status: {has_status}, has final content: {has_final_content}, " \
                     f"signature included: {signature_included}, no double-encoding: {no_double_encoding}"
            
            self.log_result("validate_final_email Function", function_passed, details)
            return function_passed
            
        except Exception as e:
            self.log_result("validate_final_email Function", False, f"Exception: {str(e)}")
            return False
    
    async def test_4_plain_text_html_generation(self):
        """Test 4: Both plain text and HTML email generation"""
        print("\n📧 Test 4: Plain Text and HTML Generation")
        
        try:
            # Get account
            accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
            if accounts_response.status_code != 200 or not accounts_response.json():
                self.log_result("Plain Text and HTML Generation", False, "No accounts available")
                return False
            
            account = accounts_response.json()[0]
            account_id = account['id']
            
            # Test email
            test_data = {
                "subject": "Plain Text and HTML Test",
                "body": "Hello! I'm interested in your services. Could you provide information about your offerings, pricing, and availability? I would also like to know about your support options and any trial periods you might offer. Thank you for your time!",
                "sender": "format.test@example.com",
                "account_id": account_id
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                draft_plain = result.get('draft', '')
                draft_html = result.get('draft_html', '')
                
                # Check both formats have content
                has_plain_content = len(draft_plain) > 100
                has_html_content = len(draft_html) > 100
                
                # Check HTML structure
                has_html_tags = ('<p>' in draft_html or '<br' in draft_html)
                
                # Check signature in both formats
                signature_keywords = ['regards', 'assistant', 'team']
                signature_in_plain = any(kw.lower() in draft_plain.lower() for kw in signature_keywords)
                signature_in_html = any(kw.lower() in draft_html.lower() for kw in signature_keywords)
                
                # Check for proper formatting
                no_double_encoding = ('&lt;' not in draft_html and '&gt;' not in draft_html)
                
                generation_passed = (has_plain_content and has_html_content and has_html_tags and 
                                   signature_in_plain and signature_in_html and no_double_encoding)
                
                details = f"Plain content: {len(draft_plain)} chars, HTML content: {len(draft_html)} chars, " \
                         f"HTML tags: {has_html_tags}, signature in both: {signature_in_plain and signature_in_html}, " \
                         f"no double-encoding: {no_double_encoding}"
                
                self.log_result("Plain Text and HTML Generation", generation_passed, details)
                return generation_passed
            else:
                self.log_result("Plain Text and HTML Generation", False, f"API call failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Plain Text and HTML Generation", False, f"Exception: {str(e)}")
            return False
    
    async def test_5_complete_workflow_endpoint(self):
        """Test 5: Complete workflow via /api/emails/test endpoint"""
        print("\n🔄 Test 5: Complete Workflow Endpoint")
        
        try:
            # Get account
            accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
            if accounts_response.status_code != 200 or not accounts_response.json():
                self.log_result("Complete Workflow Endpoint", False, "No accounts available")
                return False
            
            account = accounts_response.json()[0]
            account_id = account['id']
            
            # Comprehensive test email
            test_data = {
                "subject": "Complete Workflow Test: Product Inquiry and Demo Request",
                "body": """Hello,

I hope this email finds you well. I'm writing on behalf of our growing technology company to inquire about your AI Email Assistant solution.

We're currently processing over 300 customer inquiries daily and are looking for an automated solution that can help us:

1. Classify incoming emails by intent and priority
2. Generate professional, contextual responses
3. Handle follow-up communications effectively
4. Maintain our brand voice and tone

Could you please provide:
- Detailed pricing information for different service tiers
- Information about implementation timeline and requirements
- A demo or trial access to test the system
- Details about your support and training options

We have budget allocated for this project and are looking to make a decision within the next few weeks. Our team is particularly interested in how your system handles complex customer inquiries while maintaining personalization.

Please let me know your availability for a call to discuss this further. We're excited about the potential of working together.

Thank you for your time and consideration.""",
                "sender": "procurement@techcompany.com",
                "account_id": account_id
            }
            
            print("   Processing comprehensive test email...")
            import time
            start_time = time.time()
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=45)
            processing_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                # Check workflow completion
                has_intents = len(result.get('intents', [])) > 0
                has_draft = len(result.get('draft', '')) > 100
                has_draft_html = len(result.get('draft_html', '')) > 100
                has_validation = result.get('validation_result') is not None
                
                final_status = result.get('status', '')
                workflow_completed = final_status in ['ready_to_send', 'sent', 'needs_redraft']
                
                # Check signature processing
                draft_html = result.get('draft_html', '')
                draft_plain = result.get('draft', '')
                
                signature_keywords = ['regards', 'assistant', 'team']
                signature_processed = any(kw.lower() in draft_plain.lower() for kw in signature_keywords)
                
                # Check for proper HTML structure and no double-encoding
                proper_html = ('<p>' in draft_html and '</p>' in draft_html) or '<br' in draft_html
                no_encoding_issues = ('&lt;br&gt;' not in draft_html and 
                                    '&amp;' not in draft_html and
                                    draft_html.count('<br') < 15)
                
                # Performance check
                reasonable_time = processing_time < 40
                
                workflow_passed = (has_intents and has_draft and has_draft_html and 
                                 has_validation and workflow_completed and 
                                 signature_processed and proper_html and 
                                 no_encoding_issues and reasonable_time)
                
                details = f"Intents: {len(result.get('intents', []))}, draft: {len(result.get('draft', ''))} chars, " \
                         f"HTML: {len(draft_html)} chars, status: {final_status}, " \
                         f"time: {processing_time:.1f}s, signature: {signature_processed}, " \
                         f"no encoding issues: {no_encoding_issues}"
                
                self.log_result("Complete Workflow Endpoint", workflow_passed, details)
                return workflow_passed
            else:
                self.log_result("Complete Workflow Endpoint", False, f"Request failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Complete Workflow Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("COMPREHENSIVE SIGNATURE PROCESSING TEST RESULTS")
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
                print(f"  - {test['test']}")
                if test['details']:
                    print(f"    Details: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"  - {test['test']}")
        
        # Overall assessment
        critical_tests = ["API Keys Validation", "Signature HTML Processing", "validate_final_email Function", "Complete Workflow Endpoint"]
        critical_passed = all(any(r['test'] == ct and r['passed'] for r in self.test_results) for ct in critical_tests)
        
        print(f"\n🎯 OVERALL ASSESSMENT:")
        if critical_passed and len(failed_tests) == 0:
            print("✅ ALL SIGNATURE PROCESSING FIXES WORKING CORRECTLY")
            print("   - New API keys are functional")
            print("   - Signature HTML processing works without double-encoding")
            print("   - validate_final_email function properly handles signatures")
            print("   - Both plain text and HTML generation include signatures")
            print("   - Complete workflow endpoint processes signatures correctly")
        elif critical_passed:
            print("⚠️  SIGNATURE PROCESSING MOSTLY WORKING")
            print("   - Critical functionality is working")
            print("   - Some minor issues detected")
        else:
            print("❌ SIGNATURE PROCESSING HAS ISSUES")
            print("   - Critical functionality needs attention")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🧪 Starting Comprehensive Signature Processing Tests...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Testing against API keys: Groq: {EXPECTED_GROQ_KEY[:20]}..., Cohere: {EXPECTED_COHERE_KEY[:20]}...")
    
    tester = ComprehensiveSignatureTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run all tests
        await tester.test_1_api_keys_validation()
        await tester.test_2_signature_html_processing()
        await tester.test_3_validate_final_email_function()
        await tester.test_4_plain_text_html_generation()
        await tester.test_5_complete_workflow_endpoint()
        
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