#!/usr/bin/env python3
"""
Signature Processing Workflow Testing
Tests the double signature fix and email processing workflow with signatures
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-simplification.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

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
    
    async def create_test_account_with_signature(self):
        """Create a test email account with both HTML and plain text signature"""
        print("\n📧 Creating test email account with signature...")
        
        # HTML signature with formatting
        html_signature = """<div style="font-family: Arial, sans-serif; color: #333;">
<br>
<strong>John Smith</strong><br>
Senior Sales Manager<br>
<a href="mailto:john.smith@company.com">john.smith@company.com</a><br>
Phone: (555) 123-4567<br>
<a href="https://www.company.com" target="_blank">www.company.com</a>
</div>"""
        
        account_data = {
            "name": "Signature Test Account",
            "email": "signature.test@company.com",
            "provider": "gmail",
            "username": "signature.test@company.com",
            "password": "test_signature_password_123",
            "persona": "Professional sales representative",
            "signature": html_signature,
            "auto_send": True,
            "is_active": True
        }
        
        try:
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
            if response.status_code in [200, 201]:
                created_account = response.json()
                self.test_account_id = created_account.get('id')
                self.log_test_result("Create Test Account with Signature", True, 
                                   f"Account ID: {self.test_account_id}")
                return True
            else:
                self.log_test_result("Create Test Account with Signature", False, 
                                   f"Status: {response.status_code}, Error: {response.text}")
                return False
        except Exception as e:
            self.log_test_result("Create Test Account with Signature", False, f"Exception: {str(e)}")
            return False
    
    async def test_validate_final_email_function(self):
        """Test validate_final_email function directly to ensure signature is added correctly"""
        print("\n🔍 Testing validate_final_email function...")
        
        try:
            # Import required functions
            from server import validate_final_email, EmailMessage
            
            # Get the test account
            account = await self.db.email_accounts.find_one({"id": self.test_account_id})
            if not account:
                self.log_test_result("Validate Final Email Function", False, "Test account not found")
                return
            
            # Create test email message
            test_email = EmailMessage(
                account_id=self.test_account_id,
                message_id=f"<validate-test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Test Email for Signature Validation",
                sender="customer@example.com",
                recipient=account['email'],
                body="Hello, I'm interested in your services. Can you provide more information?",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Create test draft (without signature)
            draft = {
                "plain_text": "Dear Customer,\n\nThank you for your interest in our services. I'd be happy to provide more information.\n\nWe offer comprehensive solutions that can help your business grow.",
                "html": "<p>Dear Customer,</p><p>Thank you for your interest in our services. I'd be happy to provide more information.</p><p>We offer comprehensive solutions that can help your business grow.</p>"
            }
            
            # Test intents (empty for this test)
            intents = []
            
            # Call validate_final_email function
            validation_result = await validate_final_email(test_email, draft, intents, account)
            
            # Check if validation result contains final content with signature
            has_final_plain_text = 'final_plain_text' in validation_result
            has_final_html = 'final_html' in validation_result
            
            signature_in_plain = False
            signature_in_html = False
            signature_count_plain = 0
            signature_count_html = 0
            
            if has_final_plain_text:
                final_plain = validation_result['final_plain_text']
                signature_in_plain = 'John Smith' in final_plain and 'Senior Sales Manager' in final_plain
                signature_count_plain = final_plain.count('John Smith')
            
            if has_final_html:
                final_html = validation_result['final_html']
                signature_in_html = 'John Smith' in final_html and 'Senior Sales Manager' in final_html
                signature_count_html = final_html.count('John Smith')
            
            # Check for single signature occurrence (no duplication)
            single_signature_plain = signature_count_plain == 1
            single_signature_html = signature_count_html == 1
            
            all_passed = (has_final_plain_text and has_final_html and 
                         signature_in_plain and signature_in_html and
                         single_signature_plain and single_signature_html)
            
            details = f"Final plain text: {has_final_plain_text}, Final HTML: {has_final_html}, " \
                     f"Signature in plain: {signature_in_plain} (count: {signature_count_plain}), " \
                     f"Signature in HTML: {signature_in_html} (count: {signature_count_html})"
            
            self.log_test_result("Validate Final Email Function", all_passed, details)
            
            # Log the actual content for debugging
            if has_final_plain_text:
                print(f"   Final Plain Text Length: {len(validation_result['final_plain_text'])}")
            if has_final_html:
                print(f"   Final HTML Length: {len(validation_result['final_html'])}")
            
        except Exception as e:
            self.log_test_result("Validate Final Email Function", False, f"Exception: {str(e)}")
    
    async def test_email_processing_with_signature(self):
        """Test complete email processing workflow with signature"""
        print("\n🤖 Testing email processing workflow with signature...")
        
        try:
            # Test email data
            test_email_data = {
                "subject": "Inquiry about your products and services",
                "body": "Hello! I'm interested in learning more about your company's products and services. Could you please send me detailed information about pricing and available packages? I'm particularly interested in your premium offerings. Thank you for your time.",
                "sender": "potential.customer@example.com",
                "account_id": self.test_account_id
            }
            
            print("   Sending test email through /api/emails/test endpoint...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                email_id = processed_email.get('id')
                
                print(f"   ✅ Email processed - ID: {email_id}, Status: {processed_email.get('status')}")
                
                # Check if email has validation result
                has_validation = bool(processed_email.get('validation_result'))
                
                # Check draft content
                draft_content = processed_email.get('draft', '')
                draft_html = processed_email.get('draft_html', '')
                
                # Count signature occurrences in draft
                draft_signature_count = draft_content.count('John Smith') if draft_content else 0
                draft_html_signature_count = draft_html.count('John Smith') if draft_html else 0
                
                # Check validation result for final content
                validation_result = processed_email.get('validation_result', {})
                final_plain_text = validation_result.get('final_plain_text', '')
                final_html = validation_result.get('final_html', '')
                
                # Count signature occurrences in final content
                final_signature_count = final_plain_text.count('John Smith') if final_plain_text else 0
                final_html_signature_count = final_html.count('John Smith') if final_html else 0
                
                # Signature should appear exactly once in final content
                signature_correct_plain = final_signature_count == 1
                signature_correct_html = final_html_signature_count == 1
                
                # Check that signature is not duplicated in draft
                draft_no_duplicate = draft_signature_count <= 1 and draft_html_signature_count <= 1
                
                # Overall validation
                workflow_passed = (has_validation and signature_correct_plain and 
                                 signature_correct_html and draft_no_duplicate)
                
                details = f"Validation: {has_validation}, Draft sig count: {draft_signature_count}/{draft_html_signature_count}, " \
                         f"Final sig count: {final_signature_count}/{final_html_signature_count}, " \
                         f"Status: {processed_email.get('status')}"
                
                self.log_test_result("Email Processing with Signature", workflow_passed, details)
                
                # Additional detailed logging
                print(f"   - Draft length: {len(draft_content)} chars")
                print(f"   - Final plain text length: {len(final_plain_text)} chars")
                print(f"   - Final HTML length: {len(final_html)} chars")
                print(f"   - Validation status: {validation_result.get('status', 'N/A')}")
                
                return email_id, workflow_passed
                
            else:
                self.log_test_result("Email Processing with Signature", False, 
                                   f"API call failed - Status: {response.status_code}, Error: {response.text}")
                return None, False
                
        except Exception as e:
            self.log_test_result("Email Processing with Signature", False, f"Exception: {str(e)}")
            return None, False
    
    async def test_auto_send_email_function(self):
        """Test auto_send_email function to ensure no duplicate signatures"""
        print("\n📤 Testing auto_send_email function...")
        
        try:
            # First process an email to get one ready for sending
            email_id, processing_passed = await self.test_email_processing_with_signature()
            
            if not processing_passed or not email_id:
                self.log_test_result("Auto Send Email Function", False, "No processed email available for testing")
                return
            
            # Get the processed email from database
            processed_email = await self.db.emails.find_one({"id": email_id})
            if not processed_email:
                self.log_test_result("Auto Send Email Function", False, "Processed email not found in database")
                return
            
            # Check if email is ready to send or needs redraft
            email_status = processed_email.get('status')
            print(f"   Email status before send: {email_status}")
            
            if email_status in ['ready_to_send', 'needs_redraft']:
                # Test sending the email
                send_request = {
                    "email_id": email_id,
                    "manual_override": True  # Allow sending even if needs_redraft
                }
                
                try:
                    response = requests.post(f"{API_BASE}/emails/{email_id}/send", json=send_request, timeout=30)
                    send_passed = response.status_code == 200
                    
                    if send_passed:
                        # Check final email status
                        final_email = await self.db.emails.find_one({"id": email_id})
                        final_status = final_email.get('status')
                        sent_at = final_email.get('sent_at')
                        
                        send_successful = final_status == 'sent' and sent_at is not None
                        
                        details = f"Send API: {send_passed}, Final status: {final_status}, Sent at: {sent_at is not None}"
                        self.log_test_result("Auto Send Email Function", send_successful, details)
                        
                    else:
                        self.log_test_result("Auto Send Email Function", False, 
                                           f"Send failed - Status: {response.status_code}, Error: {response.text}")
                        
                except Exception as e:
                    self.log_test_result("Auto Send Email Function", False, f"Send exception: {str(e)}")
            else:
                self.log_test_result("Auto Send Email Function", False, 
                                   f"Email not ready to send - Status: {email_status}")
                
        except Exception as e:
            self.log_test_result("Auto Send Email Function", False, f"Exception: {str(e)}")
    
    async def test_html_vs_plain_text_signatures(self):
        """Test both HTML and plain text signature processing"""
        print("\n📝 Testing HTML vs Plain Text signature processing...")
        
        try:
            # Create account with plain text signature
            plain_text_signature = """
John Smith
Senior Sales Manager
john.smith@company.com
Phone: (555) 123-4567
www.company.com
"""
            
            plain_account_data = {
                "name": "Plain Text Signature Test",
                "email": "plaintext.test@company.com",
                "provider": "gmail",
                "username": "plaintext.test@company.com",
                "password": "plain_test_password",
                "persona": "Professional sales representative",
                "signature": plain_text_signature,
                "auto_send": True,
                "is_active": True
            }
            
            # Create plain text signature account
            response = requests.post(f"{API_BASE}/email-accounts", json=plain_account_data, timeout=15)
            if response.status_code in [200, 201]:
                plain_account_id = response.json().get('id')
                
                # Test email processing with plain text signature
                test_email_data = {
                    "subject": "Plain text signature test",
                    "body": "This is a test for plain text signature processing.",
                    "sender": "test@example.com",
                    "account_id": plain_account_id
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                plain_text_passed = response.status_code in [200, 201]
                
                if plain_text_passed:
                    processed_email = response.json()
                    validation_result = processed_email.get('validation_result', {})
                    final_plain_text = validation_result.get('final_plain_text', '')
                    final_html = validation_result.get('final_html', '')
                    
                    # Check signature appears once in both formats
                    plain_signature_count = final_plain_text.count('John Smith')
                    html_signature_count = final_html.count('John Smith')
                    
                    plain_text_correct = plain_signature_count == 1
                    html_conversion_correct = html_signature_count == 1
                    
                    plain_details = f"Plain text sig count: {plain_signature_count}, HTML sig count: {html_signature_count}"
                else:
                    plain_text_correct = False
                    html_conversion_correct = False
                    plain_details = f"Processing failed - Status: {response.status_code}"
                
                # Test HTML signature (using existing test account)
                html_test_data = {
                    "subject": "HTML signature test",
                    "body": "This is a test for HTML signature processing.",
                    "sender": "test@example.com",
                    "account_id": self.test_account_id
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=html_test_data, timeout=30)
                html_passed = response.status_code in [200, 201]
                
                if html_passed:
                    processed_email = response.json()
                    validation_result = processed_email.get('validation_result', {})
                    final_plain_text = validation_result.get('final_plain_text', '')
                    final_html = validation_result.get('final_html', '')
                    
                    # Check signature appears once in both formats
                    plain_signature_count = final_plain_text.count('John Smith')
                    html_signature_count = final_html.count('John Smith')
                    
                    html_signature_correct = plain_signature_count == 1 and html_signature_count == 1
                    html_details = f"Plain text sig count: {plain_signature_count}, HTML sig count: {html_signature_count}"
                else:
                    html_signature_correct = False
                    html_details = f"Processing failed - Status: {response.status_code}"
                
                # Overall result
                all_passed = plain_text_correct and html_conversion_correct and html_signature_correct
                
                details = f"Plain text: {plain_text_correct}, HTML conversion: {html_conversion_correct}, " \
                         f"HTML signature: {html_signature_correct}"
                
                self.log_test_result("HTML vs Plain Text Signatures", all_passed, details)
                
                # Cleanup plain text account
                requests.delete(f"{API_BASE}/email-accounts/{plain_account_id}", timeout=10)
                
            else:
                self.log_test_result("HTML vs Plain Text Signatures", False, 
                                   "Failed to create plain text signature account")
                
        except Exception as e:
            self.log_test_result("HTML vs Plain Text Signatures", False, f"Exception: {str(e)}")
    
    async def test_validation_agent_status_visibility(self):
        """Test validation agent status visibility in email processing results"""
        print("\n👁️ Testing validation agent status visibility...")
        
        try:
            # Process a test email
            test_email_data = {
                "subject": "Validation status visibility test",
                "body": "This email is to test if validation agent status is properly visible in the processing results.",
                "sender": "validation.test@example.com",
                "account_id": self.test_account_id
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check if validation result is present and contains status
                validation_result = processed_email.get('validation_result')
                has_validation_result = validation_result is not None
                
                validation_status = None
                validation_feedback = None
                coverage_report = None
                
                if has_validation_result:
                    validation_status = validation_result.get('status')
                    validation_feedback = validation_result.get('feedback')
                    coverage_report = validation_result.get('coverage_report')
                
                has_status = validation_status is not None
                has_feedback = validation_feedback is not None
                has_coverage = coverage_report is not None
                
                # Check if validation results are properly stored in database
                email_id = processed_email.get('id')
                db_email = await self.db.emails.find_one({"id": email_id})
                db_validation = db_email.get('validation_result') if db_email else None
                
                db_has_validation = db_validation is not None
                
                all_passed = (has_validation_result and has_status and has_feedback and 
                             has_coverage and db_has_validation)
                
                details = f"Validation result: {has_validation_result}, Status: {has_status}, " \
                         f"Feedback: {has_feedback}, Coverage: {has_coverage}, DB stored: {db_has_validation}"
                
                self.log_test_result("Validation Agent Status Visibility", all_passed, details)
                
                # Log validation details
                if validation_status:
                    print(f"   Validation Status: {validation_status}")
                if validation_feedback:
                    print(f"   Feedback Length: {len(validation_feedback)} chars")
                if coverage_report:
                    print(f"   Coverage Report Length: {len(coverage_report)} chars")
                
            else:
                self.log_test_result("Validation Agent Status Visibility", False, 
                                   f"Email processing failed - Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Validation Agent Status Visibility", False, f"Exception: {str(e)}")
    
    async def cleanup_test_account(self):
        """Cleanup test account"""
        if self.test_account_id:
            try:
                response = requests.delete(f"{API_BASE}/email-accounts/{self.test_account_id}", timeout=10)
                if response.status_code in [200, 204]:
                    print("✅ Test account cleaned up successfully")
                else:
                    print(f"⚠️ Test account cleanup failed: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Test account cleanup error: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("SIGNATURE PROCESSING TEST SUMMARY")
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
        
        print("="*80)

async def main():
    """Main test execution"""
    tester = SignatureProcessingTester()
    
    print("🧪 SIGNATURE PROCESSING WORKFLOW TESTING")
    print("="*60)
    
    # Setup
    if not await tester.setup():
        return
    
    try:
        # Create test account with signature
        if await tester.create_test_account_with_signature():
            
            # Run signature processing tests
            await tester.test_validate_final_email_function()
            await tester.test_email_processing_with_signature()
            await tester.test_auto_send_email_function()
            await tester.test_html_vs_plain_text_signatures()
            await tester.test_validation_agent_status_visibility()
            
            # Cleanup
            await tester.cleanup_test_account()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())