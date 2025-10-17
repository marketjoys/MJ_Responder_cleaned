#!/usr/bin/env python3
"""
Comprehensive Testing for Automatic Email Response System
Tests the updated API keys, validation improvements, and intent threshold changes
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-reply-checker.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test email account ID from user request
TEST_ACCOUNT_ID = "0cda0f06-6478-4eae-93da-4458a4728ab5"

class AutomaticResponseTester:
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
    
    async def test_api_keys_validation(self):
        """Test 1: Verify new API keys are working"""
        print("\n🔑 Testing API Keys Validation...")
        
        try:
            # Check environment variables
            groq_key = os.environ.get('GROQ_API_KEY')
            cohere_key = os.environ.get('COHERE_API_KEY')
            
            expected_groq = "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"
            expected_cohere = "rEiWPn4RxWnp5uEKgHEH7tj7D0MZGL76VurAXg5D"
            
            keys_updated = (groq_key == expected_groq and cohere_key == expected_cohere)
            
            # Test Groq API directly
            groq_working = False
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {groq_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "messages": [{"role": "user", "content": "Test message"}],
                            "model": "llama-3.3-70b-versatile",
                            "max_completion_tokens": 50
                        },
                        timeout=10
                    )
                    groq_working = response.status_code == 200
            except Exception as e:
                print(f"   Groq API test error: {str(e)}")
            
            # Test Cohere API directly
            cohere_working = False
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
                            "texts": ["test text"],
                            "input_type": "classification"
                        },
                        timeout=10
                    )
                    cohere_working = response.status_code == 200
            except Exception as e:
                print(f"   Cohere API test error: {str(e)}")
            
            all_passed = keys_updated and groq_working and cohere_working
            details = f"Keys updated: {keys_updated}, Groq working: {groq_working}, Cohere working: {cohere_working}"
            
            self.log_test_result("API Keys Validation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("API Keys Validation", False, f"Exception: {str(e)}")
    
    async def test_intent_threshold_changes(self):
        """Test 2: Verify intent confidence thresholds have been lowered"""
        print("\n🎯 Testing Intent Threshold Changes...")
        
        try:
            # Get all intents from database
            intents = await self.db.intents.find().to_list(100)
            
            if not intents:
                self.log_test_result("Intent Threshold Changes", False, "No intents found in database")
                return
            
            # Check if thresholds have been lowered to 0.7 or below
            lowered_thresholds = []
            high_thresholds = []
            
            for intent in intents:
                threshold = intent.get('confidence_threshold', 0.8)
                if threshold <= 0.7:
                    lowered_thresholds.append(intent['name'])
                else:
                    high_thresholds.append(f"{intent['name']}({threshold})")
            
            # Test with a borderline email that should now match with lower thresholds
            test_email_body = "I'm interested in your services and would like more information about pricing."
            
            # Import classification function
            sys.path.append('/app/backend')
            from server import classify_email_intents, EmailMessage
            
            test_email = EmailMessage(
                account_id=TEST_ACCOUNT_ID,
                message_id=f"threshold-test-{uuid.uuid4()}",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Service Inquiry",
                sender="test@example.com",
                recipient="support@company.com",
                body=test_email_body,
                received_at=datetime.utcnow(),
                status="new"
            )
            
            classified_intents = await classify_email_intents(test_email)
            
            # Check if we get more matches with lower thresholds
            intent_matches = len(classified_intents)
            threshold_improvement = intent_matches > 0
            
            all_passed = len(lowered_thresholds) > 0 and threshold_improvement
            details = f"Lowered thresholds: {len(lowered_thresholds)}, High thresholds: {len(high_thresholds)}, Intent matches: {intent_matches}"
            
            if high_thresholds:
                details += f", High threshold intents: {', '.join(high_thresholds[:3])}"
            
            self.log_test_result("Intent Threshold Changes", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Intent Threshold Changes", False, f"Exception: {str(e)}")
    
    async def test_email_with_intent_matches(self):
        """Test 3: Email WITH intent matches (should use strict validation)"""
        print("\n📧 Testing Email WITH Intent Matches...")
        
        try:
            # Create a clear sales inquiry that should match intents
            test_email_data = {
                "subject": "Urgent: Need Pricing for AI Email Assistant - Budget $50k",
                "body": "Hello! I'm the VP of Sales at TechCorp Inc. We're actively looking for an AI email automation solution to handle our customer inquiries. We receive over 500 emails daily and need automated responses. Please provide detailed pricing information for your AI Email Assistant platform. We have a budget of $50,000 and need to make a decision by end of this week. Can you also schedule a demo? We're particularly interested in intent classification and response generation capabilities. Please respond ASAP as this is urgent. Thank you!",
                "sender": "vp.sales@techcorp.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print(f"   Testing with clear sales inquiry...")
            start_time = time.time()
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                processing_time = time.time() - start_time
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Check if intents were identified
                    intents = processed_email.get('intents', [])
                    has_intents = len(intents) > 0
                    
                    # Check if draft was generated
                    draft = processed_email.get('draft', '')
                    has_draft = len(draft) > 50
                    
                    # Check validation result
                    validation = processed_email.get('validation_result', {})
                    validation_status = validation.get('status', 'UNKNOWN')
                    
                    # Check final status
                    final_status = processed_email.get('status', 'unknown')
                    
                    # For emails WITH intents, we expect strict validation
                    strict_validation_used = validation_status in ['PASS', 'FAIL'] and has_intents
                    
                    # Check if auto-send occurred (status should be "sent" not "needs_redraft")
                    auto_sent = final_status == 'sent'
                    
                    workflow_success = has_intents and has_draft and strict_validation_used
                    
                    details = f"Processing time: {processing_time:.1f}s, Intents: {len(intents)}, " \
                             f"Draft length: {len(draft)}, Validation: {validation_status}, " \
                             f"Final status: {final_status}, Auto-sent: {auto_sent}"
                    
                    print(f"   - Intents found: {[i.get('name', 'Unknown') for i in intents]}")
                    print(f"   - Validation mode: {'STRICT' if has_intents else 'LENIENT'}")
                    print(f"   - Final status: {final_status}")
                    
                    self.log_test_result("Email WITH Intent Matches", workflow_success, details)
                    
                else:
                    self.log_test_result("Email WITH Intent Matches", False, 
                                       f"API error: {response.status_code} - {response.text[:200]}")
                    
            except Exception as e:
                self.log_test_result("Email WITH Intent Matches", False, f"Request error: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Email WITH Intent Matches", False, f"Exception: {str(e)}")
    
    async def test_email_without_intent_matches(self):
        """Test 4: Email WITHOUT intent matches (should use lenient validation and still auto-send)"""
        print("\n📧 Testing Email WITHOUT Intent Matches...")
        
        try:
            # Create a general message that likely won't match specific intents
            test_email_data = {
                "subject": "General Question About Your Company",
                "body": "Hi there! I came across your website and was curious about your company culture and work environment. I'm a recent graduate looking for opportunities in the tech industry. Could you tell me more about what it's like to work at your company? I'm particularly interested in learning about your team dynamics and growth opportunities. Also, do you have any internship programs available? I'd appreciate any information you can share. Thanks for your time!",
                "sender": "student@university.edu",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print(f"   Testing with general inquiry (no specific intents)...")
            start_time = time.time()
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                processing_time = time.time() - start_time
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Check if intents were identified (should be few or none)
                    intents = processed_email.get('intents', [])
                    has_few_intents = len(intents) <= 1
                    
                    # Check if draft was generated despite no intents
                    draft = processed_email.get('draft', '')
                    has_draft = len(draft) > 50
                    
                    # Check validation result
                    validation = processed_email.get('validation_result', {})
                    validation_status = validation.get('status', 'UNKNOWN')
                    
                    # Check final status
                    final_status = processed_email.get('status', 'unknown')
                    
                    # For emails WITHOUT intents, we expect lenient validation and auto-send
                    lenient_validation_used = validation_status in ['PASS', 'LENIENT_PASS']
                    auto_sent = final_status == 'sent'
                    
                    # The key test: email should still be processed and sent even without intent matches
                    workflow_success = has_draft and (lenient_validation_used or auto_sent)
                    
                    details = f"Processing time: {processing_time:.1f}s, Intents: {len(intents)}, " \
                             f"Draft length: {len(draft)}, Validation: {validation_status}, " \
                             f"Final status: {final_status}, Auto-sent: {auto_sent}"
                    
                    print(f"   - Intents found: {len(intents)} ({'Few/None as expected' if has_few_intents else 'More than expected'})")
                    print(f"   - Validation mode: {'LENIENT' if has_few_intents else 'STRICT'}")
                    print(f"   - Final status: {final_status}")
                    print(f"   - Auto-send working: {auto_sent}")
                    
                    self.log_test_result("Email WITHOUT Intent Matches", workflow_success, details)
                    
                else:
                    self.log_test_result("Email WITHOUT Intent Matches", False, 
                                       f"API error: {response.status_code} - {response.text[:200]}")
                    
            except Exception as e:
                self.log_test_result("Email WITHOUT Intent Matches", False, f"Request error: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Email WITHOUT Intent Matches", False, f"Exception: {str(e)}")
    
    async def test_different_email_types(self):
        """Test 5: Different types of emails (sales, support, general)"""
        print("\n📨 Testing Different Email Types...")
        
        email_types = [
            {
                "type": "Sales Inquiry",
                "subject": "Product Demo Request - Enterprise Solution",
                "body": "We're evaluating email automation solutions for our 500-person company. Can you provide pricing for enterprise features and schedule a demo?",
                "sender": "procurement@enterprise.com"
            },
            {
                "type": "Support Request", 
                "subject": "Technical Issue - Email Not Processing",
                "body": "I'm having trouble with email processing in my account. Emails are stuck in 'classifying' status. Can you help troubleshoot this issue?",
                "sender": "user@customer.com"
            },
            {
                "type": "General Message",
                "subject": "Partnership Opportunity",
                "body": "Hello! I represent a marketing agency and we're interested in exploring potential partnership opportunities. Could we schedule a call to discuss?",
                "sender": "partnerships@agency.com"
            }
        ]
        
        results = []
        
        for email_type in email_types:
            try:
                test_data = {
                    "subject": email_type["subject"],
                    "body": email_type["body"],
                    "sender": email_type["sender"],
                    "account_id": TEST_ACCOUNT_ID
                }
                
                print(f"   Testing {email_type['type']}...")
                start_time = time.time()
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=45)
                processing_time = time.time() - start_time
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    intents_count = len(processed_email.get('intents', []))
                    draft_length = len(processed_email.get('draft', ''))
                    final_status = processed_email.get('status', 'unknown')
                    validation_status = processed_email.get('validation_result', {}).get('status', 'UNKNOWN')
                    
                    success = draft_length > 50 and final_status in ['sent', 'ready_to_send', 'needs_redraft']
                    
                    result = {
                        "type": email_type["type"],
                        "success": success,
                        "intents": intents_count,
                        "draft_length": draft_length,
                        "status": final_status,
                        "validation": validation_status,
                        "time": processing_time
                    }
                    results.append(result)
                    
                    print(f"     - Status: {final_status}, Intents: {intents_count}, Draft: {draft_length} chars")
                    
                else:
                    results.append({
                        "type": email_type["type"],
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                results.append({
                    "type": email_type["type"],
                    "success": False,
                    "error": str(e)
                })
        
        # Evaluate overall success
        successful_types = [r for r in results if r.get("success", False)]
        all_passed = len(successful_types) == len(email_types)
        
        details = f"Successful: {len(successful_types)}/{len(email_types)} types. "
        details += ", ".join([f"{r['type']}: {'✓' if r.get('success') else '✗'}" for r in results])
        
        self.log_test_result("Different Email Types", all_passed, details)
        
        # Log individual results
        for result in results:
            individual_success = result.get("success", False)
            individual_details = ""
            if individual_success:
                individual_details = f"Intents: {result.get('intents', 0)}, Status: {result.get('status', 'unknown')}, Time: {result.get('time', 0):.1f}s"
            else:
                individual_details = f"Error: {result.get('error', 'Unknown error')}"
            
            self.log_test_result(f"Email Type - {result['type']}", individual_success, individual_details)
    
    async def test_rate_limiting_and_timeouts(self):
        """Test 6: Check for API rate limiting or timeout issues"""
        print("\n⏱️ Testing Rate Limiting and Timeouts...")
        
        try:
            # Test multiple rapid requests to check rate limiting
            rapid_requests = []
            
            test_data = {
                "subject": "Rate Limit Test",
                "body": "This is a test email to check for rate limiting issues with the new API keys.",
                "sender": "ratelimit@test.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print("   Sending 3 rapid requests...")
            
            for i in range(3):
                try:
                    start_time = time.time()
                    response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=30)
                    processing_time = time.time() - start_time
                    
                    rapid_requests.append({
                        "request": i + 1,
                        "status_code": response.status_code,
                        "processing_time": processing_time,
                        "success": response.status_code in [200, 201]
                    })
                    
                    print(f"     Request {i+1}: {response.status_code} ({processing_time:.1f}s)")
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    rapid_requests.append({
                        "request": i + 1,
                        "error": str(e),
                        "success": False
                    })
            
            # Analyze results
            successful_requests = [r for r in rapid_requests if r.get("success", False)]
            rate_limited_requests = [r for r in rapid_requests if r.get("status_code") == 429]
            timeout_requests = [r for r in rapid_requests if "timeout" in str(r.get("error", "")).lower()]
            
            # Check processing times
            processing_times = [r.get("processing_time", 0) for r in successful_requests]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            max_processing_time = max(processing_times) if processing_times else 0
            
            # Test passes if most requests succeed and processing times are reasonable
            no_rate_limiting = len(rate_limited_requests) == 0
            no_timeouts = len(timeout_requests) == 0
            reasonable_times = max_processing_time < 60  # Under 1 minute
            most_successful = len(successful_requests) >= 2  # At least 2/3 succeed
            
            all_passed = no_rate_limiting and no_timeouts and reasonable_times and most_successful
            
            details = f"Successful: {len(successful_requests)}/3, Rate limited: {len(rate_limited_requests)}, " \
                     f"Timeouts: {len(timeout_requests)}, Avg time: {avg_processing_time:.1f}s, Max time: {max_processing_time:.1f}s"
            
            self.log_test_result("Rate Limiting and Timeouts", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Rate Limiting and Timeouts", False, f"Exception: {str(e)}")
    
    async def test_email_account_configuration(self):
        """Test 7: Verify email account configuration is working properly"""
        print("\n⚙️ Testing Email Account Configuration...")
        
        try:
            # Get the specific test account
            account = await self.db.email_accounts.find_one({"id": TEST_ACCOUNT_ID})
            
            if not account:
                self.log_test_result("Email Account Configuration", False, f"Test account {TEST_ACCOUNT_ID} not found")
                return
            
            # Check account configuration
            account_active = account.get('is_active', False)
            has_signature = bool(account.get('signature', ''))
            has_persona = bool(account.get('persona', ''))
            auto_send_enabled = account.get('auto_send', False)
            
            # Check via API
            try:
                response = requests.get(f"{API_BASE}/email-accounts/{TEST_ACCOUNT_ID}", timeout=10)
                api_accessible = response.status_code == 200
                
                if api_accessible:
                    api_account = response.json()
                    password_masked = api_account.get('password') == '***'
                else:
                    password_masked = False
                    
            except Exception as e:
                api_accessible = False
                password_masked = False
            
            # Test polling status for this account
            try:
                polling_data = {"action": "status"}
                response = requests.post(f"{API_BASE}/email-accounts/{TEST_ACCOUNT_ID}/polling", 
                                       json=polling_data, timeout=10)
                polling_accessible = response.status_code == 200
                
                if polling_accessible:
                    polling_status = response.json()
                    polling_active = polling_status.get('polling_active', False)
                    has_connection = polling_status.get('has_connection', False)
                else:
                    polling_active = False
                    has_connection = False
                    
            except Exception as e:
                polling_accessible = False
                polling_active = False
                has_connection = False
            
            # Overall assessment
            config_complete = account_active and has_signature and has_persona
            api_working = api_accessible and password_masked
            polling_working = polling_accessible
            
            all_passed = config_complete and api_working and polling_working
            
            details = f"Active: {account_active}, Signature: {has_signature}, Persona: {has_persona}, " \
                     f"Auto-send: {auto_send_enabled}, API access: {api_accessible}, " \
                     f"Polling: {polling_active}, Connection: {has_connection}"
            
            print(f"   Account: {account.get('email', 'Unknown')}")
            print(f"   Configuration complete: {config_complete}")
            print(f"   API accessible: {api_working}")
            print(f"   Polling status: {polling_working}")
            
            self.log_test_result("Email Account Configuration", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Account Configuration", False, f"Exception: {str(e)}")
    
    async def test_end_to_end_workflow(self):
        """Test 8: Complete end-to-end email processing workflow"""
        print("\n🔄 Testing End-to-End Workflow...")
        
        try:
            # Test with a comprehensive email that should trigger the full workflow
            test_email_data = {
                "subject": "URGENT: AI Email Assistant Implementation - Need Quote ASAP",
                "body": "Dear Team,\n\nI'm the IT Director at GlobalTech Solutions, and we urgently need to implement an AI email assistant for our customer service department. We're currently handling 1000+ customer emails daily and need automated responses to improve efficiency.\n\nSpecific requirements:\n- Intent classification for different inquiry types\n- Automated response generation\n- Integration with our existing email system\n- Support for multiple email accounts\n- Professional response quality\n\nCan you please provide:\n1. Detailed pricing information\n2. Implementation timeline\n3. Training and support options\n4. Demo scheduling\n\nWe have budget approval and need to make a decision by Friday. This is high priority for our Q1 objectives.\n\nPlease respond immediately.\n\nBest regards,\nJohn Smith\nIT Director\nGlobalTech Solutions",
                "sender": "john.smith@globaltech.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print("   Processing comprehensive business inquiry...")
            start_time = time.time()
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                total_processing_time = time.time() - start_time
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Analyze complete workflow
                    intents = processed_email.get('intents', [])
                    draft = processed_email.get('draft', '')
                    draft_html = processed_email.get('draft_html', '')
                    validation = processed_email.get('validation_result', {})
                    final_status = processed_email.get('status', 'unknown')
                    
                    # Workflow stages
                    stage_1_classification = len(intents) > 0
                    stage_2_draft_generation = len(draft) > 100  # Substantial draft
                    stage_3_validation = bool(validation)
                    stage_4_final_status = final_status in ['sent', 'ready_to_send', 'needs_redraft']
                    
                    # Quality checks
                    draft_has_greeting = any(word in draft.lower() for word in ['dear', 'hello', 'hi'])
                    draft_addresses_requirements = any(word in draft.lower() for word in ['pricing', 'demo', 'implementation'])
                    draft_professional = len(draft.split()) > 50  # Substantial response
                    
                    # HTML version check
                    has_html_version = len(draft_html) > 0
                    
                    # Complete workflow success
                    workflow_complete = (stage_1_classification and stage_2_draft_generation and 
                                       stage_3_validation and stage_4_final_status)
                    quality_adequate = draft_has_greeting and draft_addresses_requirements and draft_professional
                    
                    all_passed = workflow_complete and quality_adequate and has_html_version
                    
                    details = f"Time: {total_processing_time:.1f}s, Intents: {len(intents)}, " \
                             f"Draft: {len(draft)} chars, HTML: {len(draft_html)} chars, " \
                             f"Status: {final_status}, Quality: {quality_adequate}"
                    
                    print(f"   - Classification: {'✓' if stage_1_classification else '✗'} ({len(intents)} intents)")
                    print(f"   - Draft generation: {'✓' if stage_2_draft_generation else '✗'} ({len(draft)} chars)")
                    print(f"   - Validation: {'✓' if stage_3_validation else '✗'}")
                    print(f"   - Final status: {final_status}")
                    print(f"   - Quality checks: {'✓' if quality_adequate else '✗'}")
                    print(f"   - Total time: {total_processing_time:.1f} seconds")
                    
                    # Log the actual intents found for debugging
                    if intents:
                        intent_names = [intent.get('name', 'Unknown') for intent in intents]
                        print(f"   - Matched intents: {', '.join(intent_names)}")
                    
                    self.log_test_result("End-to-End Workflow", all_passed, details)
                    
                else:
                    self.log_test_result("End-to-End Workflow", False, 
                                       f"API error: {response.status_code} - {response.text[:200]}")
                    
            except Exception as e:
                self.log_test_result("End-to-End Workflow", False, f"Request error: {str(e)}")
                
        except Exception as e:
            self.log_test_result("End-to-End Workflow", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("AUTOMATIC EMAIL RESPONSE SYSTEM TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {len(self.test_results)}")
        print(f"   Passed: {len(passed_tests)} ✅")
        print(f"   Failed: {len(failed_tests)} ❌")
        print(f"   Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Automatic Email Response System Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Account ID: {TEST_ACCOUNT_ID}")
    
    tester = AutomaticResponseTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, exiting...")
        return
    
    try:
        # Run all tests
        await tester.test_api_keys_validation()
        await tester.test_intent_threshold_changes()
        await tester.test_email_with_intent_matches()
        await tester.test_email_without_intent_matches()
        await tester.test_different_email_types()
        await tester.test_rate_limiting_and_timeouts()
        await tester.test_email_account_configuration()
        await tester.test_end_to_end_workflow()
        
    finally:
        # Cleanup and summary
        await tester.cleanup()
        tester.print_summary()

if __name__ == "__main__":
    asyncio.run(main())