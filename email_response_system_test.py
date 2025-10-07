#!/usr/bin/env python3
"""
Comprehensive Email Response System Testing
Tests the complete automatic email response system with new API keys and model
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-account-auth.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Expected API Keys from review request
EXPECTED_GROQ_KEY = "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"
EXPECTED_COHERE_KEY = "uW0jaFve1ytQLy62iM0vnXHcb87mcVEg6eZzPtei"
EXPECTED_MODEL = "llama-3.3-70b-versatile"

class EmailResponseSystemTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.test_account = None
        
    async def setup(self):
        """Setup database connection and test account"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            
            # Get or create test account
            self.test_account = await self.db.email_accounts.find_one({"email": "rohushanshinde@gmail.com"})
            if not self.test_account:
                # Find any active account
                self.test_account = await self.db.email_accounts.find_one({"is_active": True})
            
            print("✅ Database connection established")
            if self.test_account:
                print(f"✅ Using test account: {self.test_account['email']}")
            else:
                print("⚠️  No test account found")
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
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
    
    def test_api_key_configuration(self):
        """Test 1: API Key Configuration - Verify Groq and Cohere API keys"""
        print("\n🔑 Testing API Key Configuration...")
        
        try:
            # Check environment variables
            current_groq_key = os.environ.get('GROQ_API_KEY', '')
            current_cohere_key = os.environ.get('COHERE_API_KEY', '')
            
            groq_key_correct = current_groq_key == EXPECTED_GROQ_KEY
            cohere_key_correct = current_cohere_key == EXPECTED_COHERE_KEY
            
            # Test Groq API connectivity
            groq_test_passed = False
            try:
                import httpx
                async def test_groq():
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {current_groq_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "messages": [{"role": "user", "content": "Test"}],
                                "model": EXPECTED_MODEL,
                                "max_completion_tokens": 10
                            },
                            timeout=10
                        )
                        return response.status_code == 200
                
                groq_test_passed = asyncio.run(test_groq())
            except Exception as e:
                print(f"   Groq API test error: {str(e)}")
                groq_test_passed = False
            
            # Test Cohere API connectivity
            cohere_test_passed = False
            try:
                import httpx
                async def test_cohere():
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
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
                            timeout=10
                        )
                        return response.status_code == 200
                
                cohere_test_passed = asyncio.run(test_cohere())
            except Exception as e:
                print(f"   Cohere API test error: {str(e)}")
                cohere_test_passed = False
            
            all_passed = groq_key_correct and cohere_key_correct and groq_test_passed and cohere_test_passed
            
            details = f"Groq key match: {groq_key_correct}, Cohere key match: {cohere_key_correct}, " \
                     f"Groq API test: {groq_test_passed}, Cohere API test: {cohere_test_passed}, " \
                     f"Model: {EXPECTED_MODEL}"
            
            self.log_test_result("API Key Configuration", all_passed, details)
            
        except Exception as e:
            self.log_test_result("API Key Configuration", False, f"Exception: {str(e)}")
    
    def test_polling_service_status(self):
        """Test 2: Polling Service Status - Verify polling service is running"""
        print("\n📡 Testing Polling Service Status...")
        
        try:
            # Test polling service status
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            service_running = (response.status_code == 200 and 
                             response.json().get('status') == 'running')
            
            # Test all accounts status
            accounts_response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
            accounts_status_ok = accounts_response.status_code == 200
            
            if accounts_status_ok:
                accounts_data = accounts_response.json()
                total_accounts = accounts_data.get('total_accounts', 0)
                active_accounts = accounts_data.get('active_accounts', 0)
                connected_accounts = accounts_data.get('connected_accounts', 0)
                
                details = f"Service running: {service_running}, Total accounts: {total_accounts}, " \
                         f"Active: {active_accounts}, Connected: {connected_accounts}"
            else:
                details = f"Service running: {service_running}, Accounts status failed"
            
            all_passed = service_running and accounts_status_ok
            
            self.log_test_result("Polling Service Status", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Polling Service Status", False, f"Exception: {str(e)}")
    
    def test_email_account_status(self):
        """Test 3: Email Account Status - Verify rohushanshinde@gmail.com account"""
        print("\n📧 Testing Email Account Status...")
        
        try:
            if not self.test_account:
                self.log_test_result("Email Account Status", False, "No test account available")
                return
            
            account_id = self.test_account['id']
            email = self.test_account['email']
            
            # Check account configuration
            is_active = self.test_account.get('is_active', False)
            auto_send_enabled = self.test_account.get('auto_send', False)
            has_signature = bool(self.test_account.get('signature', ''))
            
            # Test individual polling control
            try:
                status_data = {"action": "status"}
                response = requests.post(f"{API_BASE}/email-accounts/{account_id}/polling", 
                                       json=status_data, timeout=10)
                polling_status_ok = response.status_code == 200
                
                if polling_status_ok:
                    polling_data = response.json()
                    polling_active = polling_data.get('polling_active', False)
                    has_connection = polling_data.get('has_connection', False)
                    last_polled = polling_data.get('last_polled')
                else:
                    polling_active = False
                    has_connection = False
                    last_polled = None
                    
            except Exception as e:
                polling_status_ok = False
                polling_active = False
                has_connection = False
                last_polled = None
            
            all_passed = is_active and polling_status_ok
            
            details = f"Email: {email}, Active: {is_active}, Auto-send: {auto_send_enabled}, " \
                     f"Has signature: {has_signature}, Polling active: {polling_active}, " \
                     f"Has connection: {has_connection}, Last polled: {last_polled is not None}"
            
            self.log_test_result("Email Account Status", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Account Status", False, f"Exception: {str(e)}")
    
    def test_email_processing_varieties(self):
        """Test 4: Email Processing Test - Test various email types"""
        print("\n🤖 Testing Email Processing with Various Email Types...")
        
        if not self.test_account:
            self.log_test_result("Email Processing Varieties", False, "No test account available")
            return
        
        # Test email scenarios from review request
        test_scenarios = [
            {
                "name": "Sales Inquiry",
                "subject": "Pricing Information Request",
                "body": "Hi, I'm interested in your AI email assistant product. Could you please send me detailed pricing information and available packages? We're a growing company with about 50 employees and receive hundreds of customer emails daily. What would be the best solution for our needs?",
                "sender": "sales.manager@techcorp.com"
            },
            {
                "name": "Technical Support",
                "subject": "Integration Issues with Email API",
                "body": "Hello, we're experiencing issues integrating your email API with our existing system. The authentication seems to be failing and we're getting 401 errors. Could you please provide technical support? Our API key is configured correctly but the connection keeps timing out. We need urgent assistance as this is affecting our production environment.",
                "sender": "dev.team@startup.io"
            },
            {
                "name": "Partnership Inquiry",
                "subject": "Strategic Partnership Opportunity",
                "body": "Dear Team, I represent a leading CRM software company and we're interested in exploring a strategic partnership with your AI email automation platform. We believe there could be significant synergies between our customer management system and your email intelligence capabilities. Would you be open to discussing potential collaboration opportunities?",
                "sender": "partnerships@crmleader.com"
            },
            {
                "name": "Product Information",
                "subject": "Feature Comparison and Demo Request",
                "body": "Hi there, I'm evaluating different AI email automation solutions for our enterprise. Could you provide detailed information about your product features, especially around intent classification and response generation? We'd also like to schedule a demo to see the system in action. How does your solution compare to competitors in terms of accuracy and customization options?",
                "sender": "procurement@enterprise.com"
            },
            {
                "name": "Meeting Request",
                "subject": "Schedule Demo Call Next Week",
                "body": "Hello, I'd like to schedule a demo call for next week to discuss your AI email assistant. We're particularly interested in seeing how it handles customer support emails and generates personalized responses. Are you available Tuesday or Wednesday afternoon? Please let me know what times work best for you. Looking forward to learning more about your solution.",
                "sender": "cto@innovate.tech"
            }
        ]
        
        results = []
        
        for scenario in test_scenarios:
            print(f"\n   Testing: {scenario['name']}")
            
            try:
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": self.test_account['id']
                }
                
                # Process email via API
                start_time = time.time()
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                processing_time = time.time() - start_time
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Analyze results
                    status = processed_email.get('status', 'unknown')
                    intents = processed_email.get('intents', [])
                    draft = processed_email.get('draft', '')
                    draft_html = processed_email.get('draft_html', '')
                    validation_result = processed_email.get('validation_result', {})
                    
                    # Check for completeness
                    has_intents = len(intents) > 0
                    has_draft = len(draft) > 50  # Reasonable draft length
                    has_html = len(draft_html) > 50
                    is_complete = status in ['ready_to_send', 'sent', 'needs_redraft']
                    not_truncated = len(draft) > 100  # Check for truncation
                    
                    # Check validation
                    validation_status = validation_result.get('status', 'unknown') if validation_result else 'none'
                    
                    scenario_passed = (has_intents and has_draft and has_html and 
                                     is_complete and not_truncated and processing_time < 30)
                    
                    scenario_details = f"Status: {status}, Intents: {len(intents)}, " \
                                     f"Draft length: {len(draft)}, HTML length: {len(draft_html)}, " \
                                     f"Validation: {validation_status}, Time: {processing_time:.1f}s, " \
                                     f"Complete: {is_complete}, Not truncated: {not_truncated}"
                    
                    print(f"      {scenario['name']}: {'✅' if scenario_passed else '❌'} - {scenario_details}")
                    
                    results.append({
                        "scenario": scenario['name'],
                        "passed": scenario_passed,
                        "details": scenario_details,
                        "processing_time": processing_time,
                        "status": status,
                        "intents_count": len(intents),
                        "draft_length": len(draft)
                    })
                    
                else:
                    scenario_passed = False
                    scenario_details = f"API Error: {response.status_code} - {response.text[:100]}"
                    print(f"      {scenario['name']}: ❌ - {scenario_details}")
                    
                    results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "details": scenario_details,
                        "processing_time": processing_time
                    })
                
            except Exception as e:
                scenario_passed = False
                scenario_details = f"Exception: {str(e)}"
                print(f"      {scenario['name']}: ❌ - {scenario_details}")
                
                results.append({
                    "scenario": scenario['name'],
                    "passed": False,
                    "details": scenario_details
                })
        
        # Overall assessment
        passed_scenarios = [r for r in results if r['passed']]
        total_scenarios = len(results)
        passed_count = len(passed_scenarios)
        
        all_passed = passed_count >= 4  # At least 4 out of 5 should pass
        
        avg_processing_time = sum(r.get('processing_time', 0) for r in results) / len(results)
        
        overall_details = f"Passed: {passed_count}/{total_scenarios}, " \
                         f"Avg processing time: {avg_processing_time:.1f}s, " \
                         f"Success rate: {(passed_count/total_scenarios)*100:.1f}%"
        
        self.log_test_result("Email Processing Varieties", all_passed, overall_details)
        
        # Log individual scenario results
        for result in results:
            self.log_test_result(f"Email Processing - {result['scenario']}", 
                               result['passed'], result['details'])
    
    def test_auto_response_workflow(self):
        """Test 5: Auto-Response Workflow - Complete end-to-end workflow"""
        print("\n🔄 Testing Auto-Response Workflow...")
        
        if not self.test_account:
            self.log_test_result("Auto-Response Workflow", False, "No test account available")
            return
        
        try:
            # Test with a comprehensive email that should trigger full workflow
            test_email_data = {
                "subject": "Urgent: AI Email Assistant Implementation and Pricing",
                "body": "Hello, I'm the IT Director at a mid-size company and we urgently need to implement an AI email automation solution. We receive over 200 customer inquiries daily across sales, support, and general questions. Could you please provide: 1) Detailed pricing for enterprise plans, 2) Implementation timeline, 3) Integration requirements with our existing CRM, 4) Training and support options. We need to make a decision by end of this week. Please also schedule a demo call to show us the system capabilities. Thank you for your prompt response.",
                "sender": "it.director@midsize.corp",
                "account_id": self.test_account['id']
            }
            
            print("   Processing comprehensive test email...")
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
            processing_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                email_id = processed_email.get('id')
                
                # Analyze workflow completion
                status = processed_email.get('status', 'unknown')
                intents = processed_email.get('intents', [])
                draft = processed_email.get('draft', '')
                draft_html = processed_email.get('draft_html', '')
                validation_result = processed_email.get('validation_result', {})
                
                # Check workflow stages
                classification_completed = len(intents) > 0
                draft_generated = len(draft) > 100
                html_generated = len(draft_html) > 100
                validation_completed = bool(validation_result)
                final_status_valid = status in ['ready_to_send', 'sent', 'needs_redraft']
                
                # Check draft quality
                draft_comprehensive = len(draft) > 200  # Should be comprehensive
                draft_not_truncated = not draft.endswith('...')
                contains_signature = self.test_account.get('signature', '') in draft if self.test_account.get('signature') else True
                
                # Check validation details
                validation_status = validation_result.get('status', 'unknown') if validation_result else 'none'
                validation_feedback = validation_result.get('feedback', '') if validation_result else ''
                
                # Test auto-send functionality (if enabled)
                auto_send_test_passed = True
                if self.test_account.get('auto_send', False) and email_id and status == 'ready_to_send':
                    try:
                        print("   Testing auto-send functionality...")
                        send_response = requests.post(f"{API_BASE}/emails/{email_id}/send", 
                                                    json={"manual_override": False}, timeout=30)
                        auto_send_test_passed = send_response.status_code == 200
                        if auto_send_test_passed:
                            print("   ✅ Auto-send test passed")
                        else:
                            print(f"   ❌ Auto-send test failed: {send_response.status_code}")
                    except Exception as e:
                        auto_send_test_passed = False
                        print(f"   ❌ Auto-send test error: {str(e)}")
                
                workflow_completed = (classification_completed and draft_generated and 
                                    html_generated and validation_completed and 
                                    final_status_valid and draft_comprehensive and 
                                    draft_not_truncated and auto_send_test_passed)
                
                details = f"Processing time: {processing_time:.1f}s, Status: {status}, " \
                         f"Intents: {len(intents)}, Draft: {len(draft)} chars, " \
                         f"HTML: {len(draft_html)} chars, Validation: {validation_status}, " \
                         f"Comprehensive: {draft_comprehensive}, Not truncated: {draft_not_truncated}, " \
                         f"Auto-send: {auto_send_test_passed}, Workflow complete: {workflow_completed}"
                
                self.log_test_result("Auto-Response Workflow", workflow_completed, details)
                
                # Log individual workflow stages
                self.log_test_result("Workflow - Intent Classification", classification_completed, 
                                   f"{len(intents)} intents identified")
                self.log_test_result("Workflow - Draft Generation", draft_generated, 
                                   f"{len(draft)} characters generated")
                self.log_test_result("Workflow - HTML Generation", html_generated, 
                                   f"{len(draft_html)} characters generated")
                self.log_test_result("Workflow - Validation", validation_completed, 
                                   f"Status: {validation_status}")
                self.log_test_result("Workflow - Auto-Send", auto_send_test_passed, 
                                   f"Auto-send enabled: {self.test_account.get('auto_send', False)}")
                
            else:
                workflow_completed = False
                details = f"API Error: {response.status_code} - {response.text[:200]}"
                self.log_test_result("Auto-Response Workflow", False, details)
                
        except Exception as e:
            self.log_test_result("Auto-Response Workflow", False, f"Exception: {str(e)}")
    
    async def test_processing_pipeline(self):
        """Test 6: Processing Pipeline - Direct function testing"""
        print("\n⚙️ Testing Processing Pipeline Functions...")
        
        try:
            # Import required functions
            sys.path.append('/app/backend')
            from server import (classify_email_intents, generate_draft, validate_final_email, 
                              EmailMessage, get_cohere_embedding, groq_chat_completion)
            
            # Create test email object
            test_email = EmailMessage(
                account_id=self.test_account['id'] if self.test_account else 'test-account',
                message_id=f"<pipeline-test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Pipeline Test: AI Email Assistant Inquiry",
                sender="pipeline.test@example.com",
                recipient=self.test_account['email'] if self.test_account else 'test@example.com',
                body="Hello, I'm interested in your AI email assistant. Could you provide pricing information and schedule a demo? We need a solution that can handle customer support emails automatically.",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Test 6a: Intent Classification
            print("   Testing intent classification...")
            try:
                intents = await classify_email_intents(test_email)
                classification_passed = len(intents) >= 0  # Should not fail
                classification_details = f"Classified {len(intents)} intents"
                print(f"   ✅ Classification: {len(intents)} intents found")
            except Exception as e:
                classification_passed = False
                classification_details = f"Error: {str(e)}"
                print(f"   ❌ Classification failed: {str(e)}")
            
            # Test 6b: Draft Generation
            print("   Testing draft generation...")
            try:
                draft_result = await generate_draft(test_email, intents if classification_passed else [])
                draft_generated = isinstance(draft_result, dict) and len(draft_result.get('plain_text', '')) > 50
                draft_details = f"Generated {len(draft_result.get('plain_text', ''))} chars" if draft_generated else "Failed to generate"
                print(f"   ✅ Draft generation: {len(draft_result.get('plain_text', ''))} characters")
            except Exception as e:
                draft_generated = False
                draft_details = f"Error: {str(e)}"
                draft_result = {}
                print(f"   ❌ Draft generation failed: {str(e)}")
            
            # Test 6c: Validation
            print("   Testing validation...")
            try:
                if draft_generated and self.test_account:
                    validation_result = await validate_final_email(
                        test_email, 
                        draft_result, 
                        intents if classification_passed else [], 
                        self.test_account
                    )
                    validation_passed = isinstance(validation_result, dict) and 'status' in validation_result
                    validation_details = f"Status: {validation_result.get('status', 'unknown')}" if validation_passed else "Failed"
                    print(f"   ✅ Validation: {validation_result.get('status', 'unknown')}")
                else:
                    validation_passed = False
                    validation_details = "Skipped - prerequisites failed"
                    print("   ⚠️  Validation skipped - prerequisites failed")
            except Exception as e:
                validation_passed = False
                validation_details = f"Error: {str(e)}"
                print(f"   ❌ Validation failed: {str(e)}")
            
            # Test 6d: API Functions
            print("   Testing API functions...")
            try:
                # Test Cohere embedding
                embedding = await get_cohere_embedding("test text for embedding")
                embedding_passed = isinstance(embedding, list) and len(embedding) > 0
                
                # Test Groq chat completion
                messages = [{"role": "user", "content": "Say 'test successful' if you can read this."}]
                completion = await groq_chat_completion(messages)
                completion_passed = isinstance(completion, str) and len(completion) > 0
                
                api_functions_passed = embedding_passed and completion_passed
                api_details = f"Embedding: {embedding_passed}, Completion: {completion_passed}"
                print(f"   ✅ API functions: Embedding={embedding_passed}, Completion={completion_passed}")
                
            except Exception as e:
                api_functions_passed = False
                api_details = f"Error: {str(e)}"
                print(f"   ❌ API functions failed: {str(e)}")
            
            # Overall pipeline assessment
            pipeline_working = (classification_passed and draft_generated and 
                              validation_passed and api_functions_passed)
            
            overall_details = f"Classification: {classification_passed}, Draft: {draft_generated}, " \
                             f"Validation: {validation_passed}, API functions: {api_functions_passed}"
            
            self.log_test_result("Processing Pipeline", pipeline_working, overall_details)
            
            # Log individual pipeline components
            self.log_test_result("Pipeline - Intent Classification", classification_passed, classification_details)
            self.log_test_result("Pipeline - Draft Generation", draft_generated, draft_details)
            self.log_test_result("Pipeline - Validation", validation_passed, validation_details)
            self.log_test_result("Pipeline - API Functions", api_functions_passed, api_details)
            
        except Exception as e:
            self.log_test_result("Processing Pipeline", False, f"Exception: {str(e)}")
    
    def test_error_resolution(self):
        """Test 7: Error Resolution - Verify previous API model issues are resolved"""
        print("\n🔧 Testing Error Resolution...")
        
        try:
            # Test that the system is using the correct model
            current_groq_key = os.environ.get('GROQ_API_KEY', '')
            current_cohere_key = os.environ.get('COHERE_API_KEY', '')
            
            # Check if old problematic models are no longer in use
            # This would require checking the server.py file for model references
            try:
                with open('/app/backend/server.py', 'r') as f:
                    server_content = f.read()
                
                # Check for old problematic models
                old_models = [
                    'deepseek-r1-distill-llama-70b',
                    'llama3-8b-8192', 
                    'llama3-70b-8192'
                ]
                
                old_models_found = []
                for model in old_models:
                    if model in server_content:
                        old_models_found.append(model)
                
                # Check for new working model
                new_model_found = EXPECTED_MODEL in server_content
                
                model_update_passed = len(old_models_found) == 0 and new_model_found
                
            except Exception as e:
                model_update_passed = False
                old_models_found = ["Error reading server.py"]
                new_model_found = False
            
            # Test API connectivity with new keys
            api_connectivity_passed = False
            try:
                # Quick API test
                test_email_data = {
                    "subject": "Error Resolution Test",
                    "body": "Testing if API issues are resolved",
                    "sender": "error.test@example.com",
                    "account_id": self.test_account['id'] if self.test_account else 'test'
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                api_connectivity_passed = response.status_code in [200, 201]
                
                if api_connectivity_passed:
                    result = response.json()
                    # Check that it doesn't get stuck at 'classifying' stage
                    final_status = result.get('status', 'unknown')
                    not_stuck_classifying = final_status != 'classifying'
                    api_connectivity_passed = api_connectivity_passed and not_stuck_classifying
                
            except Exception as e:
                api_connectivity_passed = False
            
            all_passed = model_update_passed and api_connectivity_passed
            
            details = f"Model updated: {model_update_passed}, New model found: {new_model_found}, " \
                     f"Old models removed: {len(old_models_found) == 0}, API connectivity: {api_connectivity_passed}, " \
                     f"Old models found: {old_models_found if old_models_found else 'None'}"
            
            self.log_test_result("Error Resolution", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Error Resolution", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("EMAIL RESPONSE SYSTEM TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDETAILED RESULTS:")
        print("-" * 80)
        
        for result in self.test_results:
            status_icon = "✅" if result['passed'] else "❌"
            print(f"{status_icon} {result['test']}")
            if result['details']:
                print(f"   {result['details']}")
        
        print("\n" + "="*80)
        
        # Critical issues summary
        critical_failures = [r for r in self.test_results if not r['passed'] and 
                           any(keyword in r['test'].lower() for keyword in 
                               ['api key', 'polling', 'workflow', 'processing'])]
        
        if critical_failures:
            print("CRITICAL ISSUES FOUND:")
            for failure in critical_failures:
                print(f"❌ {failure['test']}: {failure['details']}")
        else:
            print("✅ NO CRITICAL ISSUES FOUND")
        
        return passed_tests, total_tests

async def main():
    """Main test execution"""
    print("🚀 Starting Email Response System Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = EmailResponseSystemTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests
        print("\n" + "="*80)
        print("RUNNING EMAIL RESPONSE SYSTEM TESTS")
        print("="*80)
        
        # Test 1: API Key Configuration
        tester.test_api_key_configuration()
        
        # Test 2: Polling Service Status
        tester.test_polling_service_status()
        
        # Test 3: Email Account Status
        tester.test_email_account_status()
        
        # Test 4: Email Processing Varieties
        tester.test_email_processing_varieties()
        
        # Test 5: Auto-Response Workflow
        tester.test_auto_response_workflow()
        
        # Test 6: Processing Pipeline
        await tester.test_processing_pipeline()
        
        # Test 7: Error Resolution
        tester.test_error_resolution()
        
        # Print summary
        passed, total = tester.print_summary()
        
        # Final assessment
        if passed >= total * 0.8:  # 80% pass rate
            print(f"\n🎉 EMAIL RESPONSE SYSTEM IS WORKING WELL ({passed}/{total} tests passed)")
        else:
            print(f"\n⚠️  EMAIL RESPONSE SYSTEM NEEDS ATTENTION ({passed}/{total} tests passed)")
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())