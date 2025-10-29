#!/usr/bin/env python3
"""
Critical Backend Fixes Testing for Email Assistant System
Tests signature attachment, validation agent updates, automatic response mechanism, and follow-up system
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://knowledge-base-init.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class CriticalFixesTester:
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
    
    async def setup_test_account_with_signature(self):
        """Setup test email account with signature for testing"""
        print("\n🔧 Setting up test email account with signature...")
        
        try:
            # Create test account with signature
            account_data = {
                "name": "Critical Fixes Test Account",
                "email": "critical.test@techcompany.com",
                "provider": "gmail",
                "username": "critical.test@techcompany.com",
                "password": "test_app_password_123",
                "persona": "Professional AI assistant specializing in technical support and customer service",
                "signature": "Best regards,\nSarah Johnson\nSenior Technical Support Specialist\nTechCompany Solutions\nEmail: sarah.johnson@techcompany.com\nPhone: +1 (555) 123-4567\nWebsite: https://www.techcompany.com",
                "auto_send": False,
                "enable_follow_ups": True,
                "follow_up_hours_override": 24
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
            if response.status_code in [200, 201]:
                created_account = response.json()
                self.test_account_id = created_account.get('id')
                self.log_test_result("Test Account Setup", True, f"Account ID: {self.test_account_id}")
                return True
            else:
                self.log_test_result("Test Account Setup", False, f"Status: {response.status_code}, Error: {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("Test Account Setup", False, f"Exception: {str(e)}")
            return False
    
    async def test_signature_attachment_bug_fix(self):
        """Test 1: Signature Attachment Bug Fix - HTML conversion and proper formatting"""
        print("\n📝 Testing Signature Attachment Bug Fix...")
        
        if not self.test_account_id:
            self.log_test_result("Signature Attachment Bug Fix", False, "No test account available")
            return
        
        try:
            # Test email that should trigger signature attachment
            test_email_data = {
                "subject": "Technical Support Request - Database Connection Issues",
                "body": "Hello, I'm experiencing database connection timeouts in our production environment. The error occurs intermittently and affects about 20% of our user requests. Can you please provide guidance on troubleshooting this issue? We're using PostgreSQL 14 with connection pooling. This is urgent as it's impacting our customers. Thank you for your assistance.",
                "sender": "john.developer@clientcompany.com",
                "account_id": self.test_account_id
            }
            
            print("   Testing /api/emails/test endpoint with signature processing...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check if draft was generated
                draft_plain = processed_email.get('draft', '')
                draft_html = processed_email.get('draft_html', '')
                
                # Verify signature is properly attached
                signature_in_plain = "Sarah Johnson" in draft_plain and "TechCompany Solutions" in draft_plain
                signature_in_html = "Sarah Johnson" in draft_html and "TechCompany Solutions" in draft_html
                
                # Check HTML formatting of signature
                html_has_links = "mailto:" in draft_html or "https://" in draft_html
                html_has_breaks = "<br>" in draft_html or "</p>" in draft_html
                
                # Verify no duplicate signatures
                signature_count_plain = draft_plain.count("Sarah Johnson")
                signature_count_html = draft_html.count("Sarah Johnson")
                no_duplicates = signature_count_plain <= 1 and signature_count_html <= 1
                
                # Check that signature is at the end
                signature_at_end_plain = draft_plain.strip().endswith("https://www.techcompany.com") or draft_plain.strip().endswith("techcompany.com")
                
                all_signature_tests_passed = (
                    signature_in_plain and signature_in_html and 
                    html_has_links and html_has_breaks and 
                    no_duplicates and signature_at_end_plain
                )
                
                details = f"Plain text signature: {signature_in_plain}, HTML signature: {signature_in_html}, HTML formatting: {html_has_links and html_has_breaks}, No duplicates: {no_duplicates}, Proper placement: {signature_at_end_plain}"
                
                self.log_test_result("Signature Attachment Bug Fix", all_signature_tests_passed, details)
                
                # Additional detailed logging
                print(f"   Draft length: {len(draft_plain)} chars (plain), {len(draft_html)} chars (HTML)")
                print(f"   Signature occurrences: {signature_count_plain} (plain), {signature_count_html} (HTML)")
                
            else:
                self.log_test_result("Signature Attachment Bug Fix", False, f"API call failed: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Signature Attachment Bug Fix", False, f"Exception: {str(e)}")
    
    async def test_validation_agent_update(self):
        """Test 2: Validation Agent Update - validate_final_email vs validate_draft"""
        print("\n🔍 Testing Validation Agent Update...")
        
        if not self.test_account_id:
            self.log_test_result("Validation Agent Update", False, "No test account available")
            return
        
        try:
            # Test email that should trigger validation
            test_email_data = {
                "subject": "Product Inquiry - Enterprise License Pricing",
                "body": "Hi there, I'm interested in your enterprise AI email assistant solution for our company of 500+ employees. Could you please provide detailed pricing information, implementation timeline, and available support options? We need to make a decision by next month. Also, do you offer custom integrations with Salesforce and HubSpot?",
                "sender": "procurement@enterprise.com",
                "account_id": self.test_account_id
            }
            
            print("   Testing validation of final email (draft + signature)...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check validation result
                validation_result = processed_email.get('validation_result', {})
                validation_status = validation_result.get('status', 'NONE')
                validation_feedback = validation_result.get('feedback', '')
                
                # Verify validation was performed
                validation_performed = validation_status in ['PASS', 'FAIL', 'NEEDS_IMPROVEMENT']
                
                # Check if validation considered the final email (should mention signature or final content)
                validation_considers_signature = (
                    'signature' in validation_feedback.lower() or 
                    'final email' in validation_feedback.lower() or
                    'complete response' in validation_feedback.lower()
                )
                
                # Verify validation provides meaningful feedback
                meaningful_feedback = len(validation_feedback) > 50
                
                # Check that validation result affects email status
                email_status = processed_email.get('status', '')
                status_reflects_validation = (
                    (validation_status == 'PASS' and email_status in ['ready_to_send', 'sent']) or
                    (validation_status in ['FAIL', 'NEEDS_IMPROVEMENT'] and email_status in ['needs_redraft', 'error'])
                )
                
                all_validation_tests_passed = (
                    validation_performed and meaningful_feedback and 
                    (validation_considers_signature or validation_status == 'PASS')
                )
                
                details = f"Validation performed: {validation_performed}, Status: {validation_status}, Considers final email: {validation_considers_signature}, Meaningful feedback: {meaningful_feedback}"
                
                self.log_test_result("Validation Agent Update", all_validation_tests_passed, details)
                
                # Additional logging
                print(f"   Validation status: {validation_status}")
                print(f"   Email final status: {email_status}")
                print(f"   Feedback length: {len(validation_feedback)} chars")
                
            else:
                self.log_test_result("Validation Agent Update", False, f"API call failed: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Validation Agent Update", False, f"Exception: {str(e)}")
    
    async def test_automatic_response_mechanism(self):
        """Test 3: Automatic Response Mechanism - End-to-end email processing"""
        print("\n🤖 Testing Automatic Response Mechanism...")
        
        if not self.test_account_id:
            self.log_test_result("Automatic Response Mechanism", False, "No test account available")
            return
        
        try:
            # Test comprehensive email processing workflow
            test_email_data = {
                "subject": "Urgent: System Integration Support Needed",
                "body": "Dear Support Team, We are implementing your AI email assistant in our production environment and encountering integration challenges with our existing CRM system. The API responses are inconsistent and we're seeing timeout errors during peak hours. Our development team needs immediate assistance to resolve these issues before our go-live date next week. Can you please schedule a technical consultation call and provide detailed troubleshooting documentation? This is blocking our entire project timeline.",
                "sender": "tech.lead@urgentclient.com",
                "account_id": self.test_account_id
            }
            
            print("   Testing complete email processing workflow...")
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
            processing_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check all workflow stages completed
                has_intents = len(processed_email.get('intents', [])) > 0
                has_draft = len(processed_email.get('draft', '')) > 100  # Substantial response
                has_validation = processed_email.get('validation_result') is not None
                final_status = processed_email.get('status', '')
                
                # Check intent classification quality
                intents = processed_email.get('intents', [])
                high_confidence_intents = [i for i in intents if i.get('confidence', 0) > 0.7]
                
                # Check draft quality
                draft = processed_email.get('draft', '')
                addresses_urgency = any(word in draft.lower() for word in ['urgent', 'immediate', 'priority', 'asap'])
                addresses_technical_issues = any(word in draft.lower() for word in ['integration', 'api', 'timeout', 'crm'])
                provides_next_steps = any(phrase in draft.lower() for phrase in ['schedule', 'call', 'consultation', 'documentation'])
                
                # Check signature integration
                has_signature = "Sarah Johnson" in draft and "TechCompany Solutions" in draft
                
                # Check processing efficiency
                reasonable_processing_time = processing_time < 30  # Should complete within 30 seconds
                
                workflow_completed_successfully = (
                    has_intents and has_draft and has_validation and
                    final_status not in ['error', 'failed'] and
                    addresses_urgency and addresses_technical_issues and
                    has_signature and reasonable_processing_time
                )
                
                details = f"Intents: {len(intents)}, High confidence: {len(high_confidence_intents)}, Draft length: {len(draft)}, Status: {final_status}, Processing time: {processing_time:.2f}s, Addresses urgency: {addresses_urgency}, Technical content: {addresses_technical_issues}"
                
                self.log_test_result("Automatic Response Mechanism", workflow_completed_successfully, details)
                
                # Additional detailed logging
                print(f"   Intent classification: {[i.get('name', 'Unknown') for i in intents[:3]]}")
                print(f"   Validation status: {processed_email.get('validation_result', {}).get('status', 'None')}")
                print(f"   Response addresses key points: Urgency={addresses_urgency}, Technical={addresses_technical_issues}, Next steps={provides_next_steps}")
                
            else:
                self.log_test_result("Automatic Response Mechanism", False, f"API call failed: {response.status_code}, Response: {response.text[:200]}")
                
        except Exception as e:
            self.log_test_result("Automatic Response Mechanism", False, f"Exception: {str(e)}")
    
    async def test_follow_up_system(self):
        """Test 4: Follow-up System - Follow-up email creation and management"""
        print("\n📅 Testing Follow-up System...")
        
        try:
            # First, check if follow-up related endpoints exist
            print("   Testing follow-up configuration endpoints...")
            
            # Test follow-up config creation
            follow_up_config = {
                "global_follow_up_hours": 24,
                "max_follow_ups": 2,
                "follow_up_interval_hours": 48,
                "auto_follow_up": True,
                "business_hours_only": False,
                "exclude_weekends": False
            }
            
            try:
                config_response = requests.post(f"{API_BASE}/follow-up/config", json=follow_up_config, timeout=15)
                config_created = config_response.status_code in [200, 201]
                config_details = f"Config creation status: {config_response.status_code}"
            except Exception as e:
                config_created = False
                config_details = f"Config creation error: {str(e)}"
            
            # Test follow-up email processing with test account
            if self.test_account_id:
                test_email_data = {
                    "subject": "Partnership Opportunity - Awaiting Response",
                    "body": "Hello, I reached out last week regarding a potential partnership between our companies. We're very interested in integrating your AI email assistant technology into our customer service platform. Could we schedule a call to discuss this opportunity further? I'd appreciate a response by the end of this week. Thank you!",
                    "sender": "partnerships@potentialclient.com",
                    "account_id": self.test_account_id
                }
                
                print("   Testing follow-up email creation...")
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    email_id = processed_email.get('id')
                    
                    # Check if follow-up was scheduled
                    if email_id:
                        # Look for follow-up entries in database
                        follow_ups = await self.db.follow_up_emails.find({"original_email_id": email_id}).to_list(10)
                        follow_up_created = len(follow_ups) > 0
                        
                        if follow_up_created:
                            follow_up = follow_ups[0]
                            follow_up_scheduled = follow_up.get('status') == 'pending'
                            follow_up_has_content = len(follow_up.get('draft_content', '')) > 50
                            follow_up_scheduled_time = follow_up.get('scheduled_time') is not None
                            
                            follow_up_system_working = follow_up_scheduled and follow_up_has_content and follow_up_scheduled_time
                        else:
                            follow_up_system_working = False
                    else:
                        follow_up_system_working = False
                        follow_up_created = False
                else:
                    follow_up_system_working = False
                    follow_up_created = False
            else:
                follow_up_system_working = False
                follow_up_created = False
            
            # Test follow-up listing endpoint
            try:
                follow_ups_response = requests.get(f"{API_BASE}/follow-ups", timeout=10)
                follow_ups_endpoint_working = follow_ups_response.status_code == 200
                follow_ups_endpoint_details = f"Follow-ups endpoint status: {follow_ups_response.status_code}"
            except Exception as e:
                follow_ups_endpoint_working = False
                follow_ups_endpoint_details = f"Follow-ups endpoint error: {str(e)}"
            
            # Overall follow-up system assessment
            follow_up_system_functional = (
                (config_created or follow_ups_endpoint_working) and  # At least one endpoint works
                (follow_up_created or follow_up_system_working)      # Follow-up creation works
            )
            
            details = f"Config creation: {config_created}, Follow-up created: {follow_up_created}, System working: {follow_up_system_working}, Endpoints: {follow_ups_endpoint_working}"
            
            self.log_test_result("Follow-up System", follow_up_system_functional, details)
            
            # Additional logging
            print(f"   {config_details}")
            print(f"   {follow_ups_endpoint_details}")
            if follow_up_created:
                print(f"   Follow-up successfully created and scheduled")
            
        except Exception as e:
            self.log_test_result("Follow-up System", False, f"Exception: {str(e)}")
    
    async def test_email_test_endpoint(self):
        """Test 5: Email Test Endpoint - /api/emails/test functionality"""
        print("\n🧪 Testing Email Test Endpoint...")
        
        if not self.test_account_id:
            self.log_test_result("Email Test Endpoint", False, "No test account available")
            return
        
        try:
            # Test various email scenarios
            test_scenarios = [
                {
                    "name": "Simple Inquiry",
                    "data": {
                        "subject": "Product Information Request",
                        "body": "Hello, I'd like to learn more about your AI email assistant. Can you send me some information?",
                        "sender": "simple@test.com",
                        "account_id": self.test_account_id
                    }
                },
                {
                    "name": "Complex Technical Query",
                    "data": {
                        "subject": "API Integration Documentation",
                        "body": "We need comprehensive API documentation for integrating your email assistant with our existing systems. Please include authentication methods, rate limits, webhook configurations, and error handling procedures.",
                        "sender": "developer@techcorp.com",
                        "account_id": self.test_account_id
                    }
                },
                {
                    "name": "Urgent Support Request",
                    "data": {
                        "subject": "URGENT: Production System Down",
                        "body": "Our production email system is experiencing critical failures. We need immediate support to restore service. This is affecting thousands of customers. Please escalate to your highest priority support team.",
                        "sender": "emergency@criticalclient.com",
                        "account_id": self.test_account_id
                    }
                }
            ]
            
            successful_tests = 0
            total_tests = len(test_scenarios)
            
            for scenario in test_scenarios:
                print(f"   Testing scenario: {scenario['name']}")
                
                try:
                    response = requests.post(f"{API_BASE}/emails/test", json=scenario['data'], timeout=30)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Check basic processing completion
                        has_id = 'id' in processed_email
                        has_status = 'status' in processed_email
                        has_draft = len(processed_email.get('draft', '')) > 20
                        status_valid = processed_email.get('status') not in ['error', 'failed']
                        
                        scenario_passed = has_id and has_status and has_draft and status_valid
                        
                        if scenario_passed:
                            successful_tests += 1
                            print(f"     ✅ {scenario['name']}: Success")
                        else:
                            print(f"     ❌ {scenario['name']}: Failed - ID:{has_id}, Status:{has_status}, Draft:{has_draft}, Valid:{status_valid}")
                    else:
                        print(f"     ❌ {scenario['name']}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"     ❌ {scenario['name']}: Exception - {str(e)}")
            
            # Test endpoint error handling
            print("   Testing error handling...")
            
            # Test with missing required fields
            invalid_data = {
                "subject": "Test",
                "body": "Test body"
                # Missing sender and account_id
            }
            
            try:
                error_response = requests.post(f"{API_BASE}/emails/test", json=invalid_data, timeout=10)
                error_handling_works = error_response.status_code in [400, 422]  # Should return validation error
            except Exception:
                error_handling_works = False
            
            # Test with invalid account ID
            invalid_account_data = {
                "subject": "Test",
                "body": "Test body",
                "sender": "test@test.com",
                "account_id": "invalid-account-id"
            }
            
            try:
                invalid_response = requests.post(f"{API_BASE}/emails/test", json=invalid_account_data, timeout=10)
                invalid_account_handling = invalid_response.status_code in [400, 404, 422]
            except Exception:
                invalid_account_handling = False
            
            endpoint_success_rate = successful_tests / total_tests
            endpoint_working = endpoint_success_rate >= 0.8 and error_handling_works  # At least 80% success rate
            
            details = f"Success rate: {successful_tests}/{total_tests} ({endpoint_success_rate:.1%}), Error handling: {error_handling_works}, Invalid account handling: {invalid_account_handling}"
            
            self.log_test_result("Email Test Endpoint", endpoint_working, details)
            
        except Exception as e:
            self.log_test_result("Email Test Endpoint", False, f"Exception: {str(e)}")
    
    async def test_email_account_creation_with_signature(self):
        """Test 6: Email Account Creation with Signature"""
        print("\n📧 Testing Email Account Creation with Signature...")
        
        try:
            # Test creating account with comprehensive signature
            account_data = {
                "name": "Signature Test Account",
                "email": "signature.test@company.com",
                "provider": "gmail",
                "username": "signature.test@company.com",
                "password": "test_password_123",
                "persona": "Professional customer service representative",
                "signature": "Best regards,\n\nMike Thompson\nCustomer Success Manager\nInnovative Solutions Inc.\n📧 mike.thompson@company.com\n📞 +1 (555) 987-6543\n🌐 www.innovativesolutions.com\n\n💡 Follow us on social media for updates and tips!",
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
                        
                        # Check signature field (should be masked in API response but we can verify structure)
                        has_signature_field = 'signature' in retrieved_account
                        has_persona_field = 'persona' in retrieved_account
                        has_follow_up_config = 'enable_follow_ups' in retrieved_account
                        
                        # Test signature in email processing
                        test_email_data = {
                            "subject": "Customer Service Test",
                            "body": "Hello, I need help with my account settings. Can you please assist me?",
                            "sender": "customer@example.com",
                            "account_id": account_id
                        }
                        
                        email_response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                        
                        if email_response.status_code in [200, 201]:
                            processed_email = email_response.json()
                            draft = processed_email.get('draft', '')
                            
                            # Check if signature is properly included
                            signature_included = "Mike Thompson" in draft and "Customer Success Manager" in draft
                            signature_formatted = "Innovative Solutions Inc." in draft
                            signature_has_contact = "mike.thompson@company.com" in draft or "555" in draft
                            
                            signature_processing_works = signature_included and signature_formatted and signature_has_contact
                        else:
                            signature_processing_works = False
                    else:
                        has_signature_field = False
                        has_persona_field = False
                        has_follow_up_config = False
                        signature_processing_works = False
                else:
                    has_signature_field = False
                    has_persona_field = False
                    has_follow_up_config = False
                    signature_processing_works = False
                
                # Cleanup - delete test account
                if account_id:
                    try:
                        requests.delete(f"{API_BASE}/email-accounts/{account_id}", timeout=10)
                    except:
                        pass  # Cleanup failure is not critical for test result
                
                account_creation_successful = (
                    account_created and password_masked and has_signature_field and 
                    has_persona_field and signature_processing_works
                )
                
                details = f"Account created: {account_created}, Password masked: {password_masked}, Signature field: {has_signature_field}, Signature processing: {signature_processing_works}, Follow-up config: {has_follow_up_config}"
                
                self.log_test_result("Email Account Creation with Signature", account_creation_successful, details)
                
            else:
                self.log_test_result("Email Account Creation with Signature", False, f"Account creation failed: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Email Account Creation with Signature", False, f"Exception: {str(e)}")
    
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
        print("CRITICAL FIXES TEST SUMMARY")
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
    print("🚀 Starting Critical Backend Fixes Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = CriticalFixesTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Setup test account
        if not await tester.setup_test_account_with_signature():
            print("❌ Test account setup failed, some tests will be skipped...")
        
        # Run critical fix tests
        await tester.test_signature_attachment_bug_fix()
        await tester.test_validation_agent_update()
        await tester.test_automatic_response_mechanism()
        await tester.test_follow_up_system()
        await tester.test_email_test_endpoint()
        await tester.test_email_account_creation_with_signature()
        
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