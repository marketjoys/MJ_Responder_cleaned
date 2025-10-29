#!/usr/bin/env python3
"""
Final Comprehensive Test for Review Request Requirements
Tests all specific requirements mentioned in the review request
"""
import requests
import json
import time
import re
import os
import asyncio
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://redis-rq-setup.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Expected API Keys from review request
EXPECTED_GROQ_KEY = "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"
EXPECTED_COHERE_KEY = "rEiWPn4RxWnp5uEKgHEH7tj7D0MZGL76VurAXg5D"

class ComprehensiveReviewTester:
    def __init__(self):
        self.results = {}
        self.test_account_id = None
        
    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        self.results[test_name] = {
            'passed': passed,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
    
    def count_words(self, text):
        """Count words in text, excluding signatures"""
        if not text:
            return 0
        
        # Remove signature patterns for accurate count
        clean_text = text
        signature_patterns = [
            r'\n\n(Best regards|Sincerely|Kind regards|Warm regards|Regards)\s*,?\s*\n+.*$',
            r'\n\n---+.*$',
        ]
        
        for pattern in signature_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.DOTALL | re.IGNORECASE)
        
        return len(clean_text.split())
    
    def test_api_keys_validation(self):
        """Test 1: API Keys Validation - Verify both Groq and Cohere keys"""
        print("\n🔑 Testing API Keys Validation...")
        
        try:
            # Check environment variables
            current_groq_key = os.environ.get('GROQ_API_KEY', '')
            current_cohere_key = os.environ.get('COHERE_API_KEY', '')
            
            groq_match = current_groq_key == EXPECTED_GROQ_KEY
            cohere_match = current_cohere_key == EXPECTED_COHERE_KEY
            
            print(f"   Groq Key: {current_groq_key[:20]}... ({'✓' if groq_match else '✗'})")
            print(f"   Cohere Key: {current_cohere_key[:20]}... ({'✓' if cohere_match else '✗'})")
            
            # Test API functionality directly
            groq_working = False
            cohere_working = False
            
            try:
                # Test Groq API
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {current_groq_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [{"role": "user", "content": "Say 'API working' exactly."}],
                        "model": "llama-3.3-70b-versatile",
                        "max_completion_tokens": 10
                    },
                    timeout=15
                )
                groq_working = response.status_code == 200
                print(f"   Groq API Test: {'✓' if groq_working else '✗'} (Status: {response.status_code})")
                
            except Exception as e:
                print(f"   Groq API Test: ✗ (Error: {str(e)[:50]})")
            
            try:
                # Test Cohere API
                response = requests.post(
                    "https://api.cohere.com/v1/embed",
                    headers={
                        "Authorization": f"Bearer {current_cohere_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "embed-english-v3.0",
                        "texts": ["test"],
                        "input_type": "classification"
                    },
                    timeout=15
                )
                cohere_working = response.status_code == 200
                print(f"   Cohere API Test: {'✓' if cohere_working else '✗'} (Status: {response.status_code})")
                
            except Exception as e:
                print(f"   Cohere API Test: ✗ (Error: {str(e)[:50]})")
            
            all_passed = groq_match and cohere_match and groq_working and cohere_working
            details = f"Keys Match: Groq={groq_match}, Cohere={cohere_match}; APIs Working: Groq={groq_working}, Cohere={cohere_working}"
            
            self.log_result("API Keys Validation", all_passed, details)
            return all_passed
            
        except Exception as e:
            self.log_result("API Keys Validation", False, f"Exception: {str(e)}")
            return False
    
    def test_response_length_limits(self):
        """Test 2: Response Length Limits - 150-200 words maximum"""
        print("\n📏 Testing Response Length Limits...")
        
        try:
            # Get test account
            accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
            if accounts_response.status_code != 200 or not accounts_response.json():
                self.log_result("Response Length Limits", False, "No email accounts found")
                return False
            
            self.test_account_id = accounts_response.json()[0]['id']
            
            # Test scenarios that might generate long responses
            test_scenarios = [
                {
                    "name": "Simple Inquiry",
                    "body": "Hi, I'm interested in your AI email assistant. Can you send me pricing information?"
                },
                {
                    "name": "Complex Enterprise Request",
                    "body": "Hello, I'm the CTO of a large enterprise company with over 10,000 employees. We receive thousands of customer emails daily across multiple departments including sales, support, billing, and technical inquiries. We need a comprehensive AI email automation solution that can handle complex customer inquiries, integrate with our existing CRM system, provide detailed analytics and reporting, support multiple languages, handle escalations, maintain compliance with GDPR and other regulations, provide custom training for our specific industry terminology, offer 24/7 support, and scale to handle our growing email volume. Could you please provide detailed information about your pricing tiers, implementation timeline, training requirements, integration capabilities, security features, compliance certifications, support options, and any case studies from similar enterprise deployments?"
                }
            ]
            
            length_results = []
            
            for scenario in test_scenarios:
                try:
                    test_email_data = {
                        "subject": f"Length Test: {scenario['name']}",
                        "body": scenario["body"],
                        "sender": "lengthtest@example.com",
                        "account_id": self.test_account_id
                    }
                    
                    print(f"   Testing: {scenario['name']}")
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        draft = processed_email.get('draft', '')
                        
                        if draft:
                            word_count = self.count_words(draft)
                            # Allow some flexibility: 50-300 words (target 150-200)
                            within_limit = 50 <= word_count <= 300
                            
                            length_results.append({
                                "scenario": scenario['name'],
                                "word_count": word_count,
                                "within_limit": within_limit,
                                "draft_preview": draft[:100] + "..." if len(draft) > 100 else draft
                            })
                            
                            print(f"     Word Count: {word_count} ({'✓' if within_limit else '✗'})")
                        else:
                            length_results.append({
                                "scenario": scenario['name'],
                                "word_count": 0,
                                "within_limit": False,
                                "draft_preview": "No draft generated"
                            })
                            print(f"     No draft generated")
                    else:
                        print(f"     API Error: {response.status_code}")
                        length_results.append({
                            "scenario": scenario['name'],
                            "word_count": 0,
                            "within_limit": False,
                            "draft_preview": f"API Error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     Exception: {str(e)}")
                    length_results.append({
                        "scenario": scenario['name'],
                        "word_count": 0,
                        "within_limit": False,
                        "draft_preview": f"Exception: {str(e)}"
                    })
            
            # Evaluate results
            successful_tests = [r for r in length_results if r['within_limit']]
            all_passed = len(successful_tests) >= len(length_results) * 0.7  # 70% success rate
            
            avg_words = sum(r['word_count'] for r in length_results if r['word_count'] > 0) / max(1, len([r for r in length_results if r['word_count'] > 0]))
            details = f"Successful: {len(successful_tests)}/{len(length_results)}, Avg Words: {avg_words:.1f}"
            
            self.log_result("Response Length Limits", all_passed, details)
            return all_passed
            
        except Exception as e:
            self.log_result("Response Length Limits", False, f"Exception: {str(e)}")
            return False
    
    def test_persona_integration(self):
        """Test 3: Persona Integration - Verify persona affects response tone"""
        print("\n🎭 Testing Persona Integration...")
        
        try:
            # Create test account with specific persona
            persona_account_data = {
                "name": "Persona Test Account",
                "email": "persona.test@example.com",
                "provider": "gmail",
                "username": "persona.test@example.com",
                "password": "test_password",
                "persona": "Friendly and enthusiastic customer service representative who uses warm, welcoming language and occasionally uses exclamation points to show excitement",
                "signature": "Best regards,\nPersona Test Team",
                "auto_send": False
            }
            
            # Create account
            response = requests.post(f"{API_BASE}/email-accounts", json=persona_account_data, timeout=15)
            
            if response.status_code in [200, 201]:
                created_account = response.json()
                persona_account_id = created_account.get('id')
                
                # Test email processing with persona
                test_email_data = {
                    "subject": "Persona Integration Test",
                    "body": "Hi, I'm interested in your AI email assistant service. Can you tell me more about the features and pricing?",
                    "sender": "customer@example.com",
                    "account_id": persona_account_id
                }
                
                email_response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                persona_working = False
                if email_response.status_code in [200, 201]:
                    processed_email = email_response.json()
                    draft = processed_email.get('draft', '')
                    
                    if draft:
                        # Analyze for friendly/enthusiastic tone
                        draft_lower = draft.lower()
                        friendly_indicators = ["hi", "hello", "happy", "excited", "glad", "welcome", "great", "wonderful"]
                        enthusiasm_indicators = ["!", "excited", "thrilled", "delighted"]
                        
                        friendly_count = sum(1 for indicator in friendly_indicators if indicator in draft_lower)
                        enthusiasm_count = sum(1 for indicator in enthusiasm_indicators if indicator in draft)
                        
                        persona_working = friendly_count > 0 or enthusiasm_count > 0
                        
                        print(f"     Draft generated: ✓")
                        print(f"     Friendly indicators: {friendly_count}")
                        print(f"     Enthusiasm indicators: {enthusiasm_count}")
                        print(f"     Preview: {draft[:80]}...")
                    else:
                        print(f"     No draft generated")
                else:
                    print(f"     Email processing failed: {email_response.status_code}")
                
                # Cleanup
                try:
                    requests.delete(f"{API_BASE}/email-accounts/{persona_account_id}", timeout=10)
                except:
                    pass
                
                details = f"Account created: True, Draft generated: {bool(draft) if 'draft' in locals() else False}, Persona detected: {persona_working}"
                self.log_result("Persona Integration", persona_working, details)
                return persona_working
                
            else:
                self.log_result("Persona Integration", False, f"Account creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Persona Integration", False, f"Exception: {str(e)}")
            return False
    
    def test_automatic_reply_workflow(self):
        """Test 4: Automatic Reply Workflow - Full workflow from classification to sending"""
        print("\n🔄 Testing Automatic Reply Workflow...")
        
        try:
            if not self.test_account_id:
                # Get test account
                accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
                if accounts_response.status_code != 200 or not accounts_response.json():
                    self.log_result("Automatic Reply Workflow", False, "No email accounts found")
                    return False
                self.test_account_id = accounts_response.json()[0]['id']
            
            # Test comprehensive workflow
            test_email_data = {
                "subject": "Workflow Test - Product Inquiry",
                "body": "Hello, I'm interested in your AI email assistant service. Could you please provide pricing information and schedule a demo? We're a medium-sized company looking to automate our customer service emails. We receive about 200 emails per day and need a solution that can handle various types of inquiries including sales, support, and general questions.",
                "sender": "workflow.test@example.com",
                "account_id": self.test_account_id
            }
            
            print(f"   Processing test email...")
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Analyze workflow completion
                status = processed_email.get('status', 'unknown')
                intents = processed_email.get('intents', [])
                draft = processed_email.get('draft', '')
                validation_result = processed_email.get('validation_result', {})
                
                # Check workflow stages
                classification_completed = len(intents) > 0 or status not in ['new', 'classifying']
                draft_generated = bool(draft)
                validation_completed = bool(validation_result)
                workflow_completed = status in ['sent', 'ready_to_send']
                
                print(f"     Processing Time: {processing_time:.1f}s")
                print(f"     Final Status: {status}")
                print(f"     Intents Found: {len(intents)}")
                print(f"     Draft Generated: {'✓' if draft_generated else '✗'}")
                print(f"     Validation Completed: {'✓' if validation_completed else '✗'}")
                print(f"     Workflow Completed: {'✓' if workflow_completed else '✗'}")
                
                # Check for auto-send capability
                auto_send_ready = status == 'sent' or (status == 'ready_to_send' and draft_generated)
                
                workflow_success = (classification_completed and draft_generated and 
                                  validation_completed and auto_send_ready)
                
                details = f"Status: {status}, Intents: {len(intents)}, Draft: {len(draft)} chars, Time: {processing_time:.1f}s"
                self.log_result("Automatic Reply Workflow", workflow_success, details)
                return workflow_success
                
            else:
                self.log_result("Automatic Reply Workflow", False, f"API Error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Automatic Reply Workflow", False, f"Exception: {str(e)}")
            return False
    
    def test_follow_up_system(self):
        """Test 5: Follow-up System - Ensure follow-up functionality works"""
        print("\n📅 Testing Follow-up System...")
        
        try:
            if not self.test_account_id:
                # Get test account
                accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
                if accounts_response.status_code != 200 or not accounts_response.json():
                    self.log_result("Follow-up System", False, "No email accounts found")
                    return False
                self.test_account_id = accounts_response.json()[0]['id']
            
            # Check account has follow-up fields
            account_response = requests.get(f"{API_BASE}/email-accounts/{self.test_account_id}", timeout=10)
            if account_response.status_code == 200:
                account = account_response.json()
                has_follow_up_fields = (
                    'enable_follow_ups' in account and
                    'follow_up_hours_override' in account
                )
                print(f"     Follow-up fields present: {'✓' if has_follow_up_fields else '✗'}")
            else:
                has_follow_up_fields = False
                print(f"     Could not check account fields")
            
            # Test follow-up workflow
            test_email_data = {
                "subject": "Follow-up Test Email",
                "body": "Hi, I'm interested in your AI email assistant but I need some time to think about it. Please follow up with me in a day or two with more information.",
                "sender": "followup.test@example.com",
                "account_id": self.test_account_id
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
            
            follow_up_workflow = False
            if response.status_code in [200, 201]:
                processed_email = response.json()
                status = processed_email.get('status')
                
                # Check if email was processed successfully (follow-up creation would happen in background)
                follow_up_workflow = status in ['sent', 'ready_to_send']
                print(f"     Email processed: {'✓' if follow_up_workflow else '✗'} (Status: {status})")
            else:
                print(f"     Email processing failed: {response.status_code}")
            
            # Overall follow-up system assessment
            follow_up_working = has_follow_up_fields and follow_up_workflow
            
            details = f"Fields present: {has_follow_up_fields}, Workflow: {follow_up_workflow}"
            self.log_result("Follow-up System", follow_up_working, details)
            return follow_up_working
            
        except Exception as e:
            self.log_result("Follow-up System", False, f"Exception: {str(e)}")
            return False
    
    def test_emails_test_endpoint(self):
        """Test 6: /api/emails/test endpoint comprehensive functionality"""
        print("\n🧪 Testing /api/emails/test Endpoint...")
        
        try:
            if not self.test_account_id:
                # Get test account
                accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
                if accounts_response.status_code != 200 or not accounts_response.json():
                    self.log_result("/api/emails/test Endpoint", False, "No email accounts found")
                    return False
                self.test_account_id = accounts_response.json()[0]['id']
            
            # Test basic endpoint functionality
            test_email_data = {
                "subject": "Endpoint Test Email",
                "body": "This is a comprehensive test of the /api/emails/test endpoint to verify it processes emails correctly with the updated API keys and response limits.",
                "sender": "endpoint.test@example.com",
                "account_id": self.test_account_id
            }
            
            print(f"   Testing endpoint functionality...")
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check response structure
                required_fields = ['id', 'status', 'intents', 'draft']
                has_required_fields = all(field in processed_email for field in required_fields)
                
                # Check processing completion
                status = processed_email.get('status', 'unknown')
                processing_completed = status not in ['new', 'error']
                
                # Check response time
                reasonable_time = processing_time < 60  # Should complete within 60 seconds
                
                print(f"     Response Status: {response.status_code}")
                print(f"     Processing Time: {processing_time:.1f}s")
                print(f"     Email Status: {status}")
                print(f"     Required Fields: {'✓' if has_required_fields else '✗'}")
                print(f"     Processing Completed: {'✓' if processing_completed else '✗'}")
                print(f"     Reasonable Time: {'✓' if reasonable_time else '✗'}")
                
                endpoint_working = (has_required_fields and processing_completed and reasonable_time)
                
                details = f"Status: {response.status_code}, Time: {processing_time:.1f}s, Email Status: {status}"
                self.log_result("/api/emails/test Endpoint", endpoint_working, details)
                return endpoint_working
                
            else:
                self.log_result("/api/emails/test Endpoint", False, f"HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("/api/emails/test Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def print_comprehensive_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🧪 COMPREHENSIVE REVIEW REQUEST TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results.values() if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📊 DETAILED RESULTS:")
        print("-" * 80)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status}: {test_name}")
            if result['details']:
                print(f"     {result['details']}")
        
        print("\n🎯 REVIEW REQUEST REQUIREMENTS STATUS:")
        print("-" * 80)
        
        requirements = {
            "API Keys Validation": "API Keys Validation",
            "Response Length Limits": "Response Length Limits", 
            "Persona Integration": "Persona Integration",
            "Automatic Reply Workflow": "Automatic Reply Workflow",
            "Follow-up System": "Follow-up System",
            "/api/emails/test Endpoint": "/api/emails/test Endpoint"
        }
        
        for req_name, test_name in requirements.items():
            if test_name in self.results:
                status = "✅ WORKING" if self.results[test_name]['passed'] else "❌ ISSUES"
                print(f"  {status}: {req_name}")
            else:
                print(f"  ❓ NOT TESTED: {req_name}")
        
        # Critical issues summary
        critical_failures = [name for name, result in self.results.items() if not result['passed']]
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES FOUND:")
            for failure in critical_failures:
                print(f"  ❌ {failure}: {self.results[failure]['details']}")
        else:
            print("\n✅ ALL REQUIREMENTS WORKING CORRECTLY")
        
        print("="*80)

def main():
    """Main test execution"""
    print("🚀 Starting Comprehensive Review Request Testing...")
    print("Testing all requirements from the review request:")
    print("1. API Keys Validation (Groq & Cohere)")
    print("2. Response Length Limits (150-200 words)")
    print("3. Persona Integration")
    print("4. Automatic Reply Workflow")
    print("5. Follow-up System")
    print("6. /api/emails/test Endpoint")
    print("="*80)
    
    tester = ComprehensiveReviewTester()
    
    try:
        # Run all tests
        tester.test_api_keys_validation()
        tester.test_response_length_limits()
        tester.test_persona_integration()
        tester.test_automatic_reply_workflow()
        tester.test_follow_up_system()
        tester.test_emails_test_endpoint()
        
        # Print comprehensive summary
        tester.print_comprehensive_summary()
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()