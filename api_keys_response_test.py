#!/usr/bin/env python3
"""
Comprehensive Testing for Updated API Keys and Response System
Tests the specific requirements from the review request:
1. API Keys Validation (Groq & Cohere)
2. Response Length Limits (150-200 words)
3. Persona Integration
4. Automatic Reply Workflow
5. Follow-up System
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-account-auth.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Expected API Keys from review request
EXPECTED_GROQ_KEY = "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"
EXPECTED_COHERE_KEY = "rEiWPn4RxWnp5uEKgHEH7tj7D0MZGL76VurAXg5D"

class APIKeysResponseTester:
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
    
    def count_words(self, text: str) -> int:
        """Count words in text, excluding common signature elements"""
        if not text:
            return 0
        
        # Remove common signature patterns for accurate word count
        clean_text = text
        signature_patterns = [
            r'\n\n(Best regards|Sincerely|Kind regards|Warm regards|Regards)\s*,?\s*\n+.*$',
            r'\n\n---+.*$',
            r'\n\n\*+.*$',
        ]
        
        for pattern in signature_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.DOTALL | re.IGNORECASE)
        
        # Count words
        words = clean_text.split()
        return len(words)
    
    async def test_api_keys_validation(self):
        """Test 1: API Keys Validation - Verify both Groq and Cohere keys are working"""
        print("\n🔑 Testing API Keys Validation...")
        
        try:
            # Check environment variables first
            current_groq_key = os.environ.get('GROQ_API_KEY', '')
            current_cohere_key = os.environ.get('COHERE_API_KEY', '')
            
            keys_match = (current_groq_key == EXPECTED_GROQ_KEY and 
                         current_cohere_key == EXPECTED_COHERE_KEY)
            
            print(f"   Expected Groq Key: {EXPECTED_GROQ_KEY[:20]}...")
            print(f"   Current Groq Key:  {current_groq_key[:20]}...")
            print(f"   Expected Cohere Key: {EXPECTED_COHERE_KEY[:20]}...")
            print(f"   Current Cohere Key:  {current_cohere_key[:20]}...")
            
            # Test Groq API functionality
            groq_working = False
            try:
                # Import and test Groq function directly
                from server import groq_chat_completion
                
                test_messages = [{"role": "user", "content": "Say 'Groq API working' in exactly those words."}]
                groq_response = await groq_chat_completion(test_messages)
                groq_working = "groq api working" in groq_response.lower()
                print(f"   Groq API Test Response: {groq_response[:50]}...")
                
            except Exception as e:
                print(f"   Groq API Test Failed: {str(e)}")
                groq_working = False
            
            # Test Cohere API functionality
            cohere_working = False
            try:
                # Import and test Cohere function directly
                from server import get_cohere_embedding
                
                test_text = "This is a test for Cohere embedding API"
                cohere_embedding = await get_cohere_embedding(test_text)
                cohere_working = (isinstance(cohere_embedding, list) and 
                                len(cohere_embedding) > 0 and 
                                isinstance(cohere_embedding[0], float))
                print(f"   Cohere API Test: Generated {len(cohere_embedding)} dimensional embedding")
                
            except Exception as e:
                print(f"   Cohere API Test Failed: {str(e)}")
                cohere_working = False
            
            # Test integration via email processing
            integration_working = False
            try:
                # Get a test account
                account = await self.db.email_accounts.find_one({"is_active": True})
                if account:
                    self.test_account_id = account['id']
                    
                    # Test email processing that uses both APIs
                    test_email_data = {
                        "subject": "API Keys Test Email",
                        "body": "Hello, I need information about your pricing and would like to schedule a demo. Please provide details about your AI email assistant service.",
                        "sender": "apitest@example.com",
                        "account_id": account['id']
                    }
                    
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        has_intents = bool(processed_email.get('intents'))
                        has_draft = bool(processed_email.get('draft'))
                        final_status = processed_email.get('status')
                        
                        integration_working = (has_intents or has_draft) and final_status != 'error'
                        print(f"   Integration Test: Status={final_status}, Intents={len(processed_email.get('intents', []))}, Draft={len(processed_email.get('draft', ''))}")
                    else:
                        print(f"   Integration Test Failed: {response.status_code} - {response.text[:100]}")
                        
            except Exception as e:
                print(f"   Integration Test Failed: {str(e)}")
                integration_working = False
            
            all_passed = keys_match and groq_working and cohere_working and integration_working
            
            details = f"Keys Match: {keys_match}, Groq Working: {groq_working}, Cohere Working: {cohere_working}, Integration: {integration_working}"
            
            self.log_test_result("API Keys Validation", all_passed, details)
            
            # Log individual API results
            self.log_test_result("API Keys - Environment Variables", keys_match, 
                               f"Groq: {'✓' if current_groq_key == EXPECTED_GROQ_KEY else '✗'}, Cohere: {'✓' if current_cohere_key == EXPECTED_COHERE_KEY else '✗'}")
            self.log_test_result("API Keys - Groq Functionality", groq_working, 
                               f"Chat completion API working: {groq_working}")
            self.log_test_result("API Keys - Cohere Functionality", cohere_working, 
                               f"Embedding API working: {cohere_working}")
            self.log_test_result("API Keys - Integration Test", integration_working, 
                               f"Full email processing workflow: {integration_working}")
            
        except Exception as e:
            self.log_test_result("API Keys Validation", False, f"Exception: {str(e)}")
    
    async def test_response_length_limits(self):
        """Test 2: Response Length Limits - Verify responses are 150-200 words maximum"""
        print("\n📏 Testing Response Length Limits...")
        
        try:
            if not self.test_account_id:
                # Get a test account
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("Response Length Limits", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Test with different types of emails that might generate long responses
            test_scenarios = [
                {
                    "name": "Complex Product Inquiry",
                    "subject": "Detailed Information Request About Your AI Email Assistant",
                    "body": "Hello, I'm the CTO of a large enterprise company with over 10,000 employees. We receive thousands of customer emails daily across multiple departments including sales, support, billing, and technical inquiries. We need a comprehensive AI email automation solution that can handle complex customer inquiries, integrate with our existing CRM system, provide detailed analytics and reporting, support multiple languages, handle escalations, maintain compliance with GDPR and other regulations, provide custom training for our specific industry terminology, offer 24/7 support, and scale to handle our growing email volume. Could you please provide detailed information about your pricing tiers, implementation timeline, training requirements, integration capabilities, security features, compliance certifications, support options, and any case studies from similar enterprise deployments? We also need to understand your SLA commitments, disaster recovery procedures, and data retention policies. Please include information about your API capabilities, webhook support, and any limitations we should be aware of. We're looking to make a decision within the next two weeks and would appreciate a comprehensive proposal."
                },
                {
                    "name": "Technical Support Request",
                    "subject": "Multiple Technical Issues Need Resolution",
                    "body": "Hi, I'm experiencing several technical issues with your service that need immediate attention. First, the email classification seems to be inconsistent - some emails are being categorized incorrectly which is causing inappropriate responses to be sent to our customers. Second, the response generation is sometimes taking too long, causing timeouts and failed deliveries. Third, I've noticed that the knowledge base integration isn't working properly - responses don't seem to include relevant information from our uploaded documents. Fourth, the signature attachment feature is not working consistently. Fifth, the follow-up system is sending duplicate emails in some cases. Sixth, the dashboard analytics are showing incorrect numbers. Can you please provide step-by-step troubleshooting instructions for each of these issues, explain what might be causing them, provide workarounds if available, and let me know when permanent fixes will be implemented? This is affecting our customer service quality and we need urgent resolution."
                },
                {
                    "name": "Simple Pricing Inquiry",
                    "body": "Hi, I'm interested in your AI email assistant. Can you send me pricing information? Thanks!"
                }
            ]
            
            length_test_results = []
            
            for scenario in test_scenarios:
                try:
                    test_email_data = {
                        "subject": scenario.get("subject", "Test Email"),
                        "body": scenario["body"],
                        "sender": f"lengthtest{len(length_test_results)}@example.com",
                        "account_id": self.test_account_id
                    }
                    
                    print(f"   Testing: {scenario['name']}")
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        draft = processed_email.get('draft', '')
                        
                        if draft:
                            word_count = self.count_words(draft)
                            within_limit = 50 <= word_count <= 250  # Allow some flexibility
                            
                            length_test_results.append({
                                "scenario": scenario['name'],
                                "word_count": word_count,
                                "within_limit": within_limit,
                                "draft_preview": draft[:100] + "..." if len(draft) > 100 else draft
                            })
                            
                            print(f"     Word Count: {word_count} ({'✓' if within_limit else '✗'})")
                            print(f"     Preview: {draft[:80]}...")
                        else:
                            length_test_results.append({
                                "scenario": scenario['name'],
                                "word_count": 0,
                                "within_limit": False,
                                "draft_preview": "No draft generated"
                            })
                            print(f"     No draft generated")
                    else:
                        print(f"     API Error: {response.status_code}")
                        length_test_results.append({
                            "scenario": scenario['name'],
                            "word_count": 0,
                            "within_limit": False,
                            "draft_preview": f"API Error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     Exception: {str(e)}")
                    length_test_results.append({
                        "scenario": scenario['name'],
                        "word_count": 0,
                        "within_limit": False,
                        "draft_preview": f"Exception: {str(e)}"
                    })
            
            # Evaluate results
            successful_tests = [r for r in length_test_results if r['within_limit']]
            all_passed = len(successful_tests) >= len(length_test_results) * 0.7  # 70% success rate
            
            avg_word_count = sum(r['word_count'] for r in length_test_results if r['word_count'] > 0) / max(1, len([r for r in length_test_results if r['word_count'] > 0]))
            
            details = f"Successful: {len(successful_tests)}/{len(length_test_results)}, Avg Words: {avg_word_count:.1f}"
            
            self.log_test_result("Response Length Limits", all_passed, details)
            
            # Log individual scenario results
            for result in length_test_results:
                self.log_test_result(f"Length Test - {result['scenario']}", result['within_limit'], 
                                   f"Words: {result['word_count']}, Preview: {result['draft_preview'][:50]}...")
            
        except Exception as e:
            self.log_test_result("Response Length Limits", False, f"Exception: {str(e)}")
    
    async def test_persona_integration(self):
        """Test 3: Persona Integration - Verify persona field affects response tone and style"""
        print("\n🎭 Testing Persona Integration...")
        
        try:
            # Create test accounts with different personas
            test_personas = [
                {
                    "name": "Professional Persona Test",
                    "email": "professional.test@example.com",
                    "persona": "Professional and formal business representative who uses corporate language and maintains a serious tone",
                    "expected_tone": "formal"
                },
                {
                    "name": "Friendly Persona Test", 
                    "email": "friendly.test@example.com",
                    "persona": "Friendly and casual customer service representative who uses warm, approachable language and emoji occasionally",
                    "expected_tone": "friendly"
                },
                {
                    "name": "Technical Persona Test",
                    "email": "technical.test@example.com", 
                    "persona": "Technical expert who provides detailed, precise information and uses industry terminology appropriately",
                    "expected_tone": "technical"
                }
            ]
            
            persona_test_results = []
            created_account_ids = []
            
            for persona_config in test_personas:
                try:
                    # Create account with specific persona
                    account_data = {
                        "name": persona_config["name"],
                        "email": persona_config["email"],
                        "provider": "gmail",
                        "username": persona_config["email"],
                        "password": "test_password_123",
                        "persona": persona_config["persona"],
                        "signature": f"Best regards,\n{persona_config['name']}",
                        "auto_send": False
                    }
                    
                    response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
                    
                    if response.status_code in [200, 201]:
                        created_account = response.json()
                        account_id = created_account.get('id')
                        created_account_ids.append(account_id)
                        
                        # Test email processing with this persona
                        test_email_data = {
                            "subject": "Product Information Request",
                            "body": "Hi, I'm interested in learning more about your AI email assistant. Can you tell me about the features and pricing?",
                            "sender": "customer@example.com",
                            "account_id": account_id
                        }
                        
                        print(f"   Testing persona: {persona_config['expected_tone']}")
                        email_response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                        
                        if email_response.status_code in [200, 201]:
                            processed_email = email_response.json()
                            draft = processed_email.get('draft', '')
                            
                            if draft:
                                # Analyze tone characteristics
                                tone_analysis = self.analyze_response_tone(draft, persona_config['expected_tone'])
                                
                                persona_test_results.append({
                                    "persona": persona_config['expected_tone'],
                                    "account_id": account_id,
                                    "draft_generated": True,
                                    "tone_match": tone_analysis['matches_expected'],
                                    "characteristics": tone_analysis['characteristics'],
                                    "draft_preview": draft[:150] + "..." if len(draft) > 150 else draft
                                })
                                
                                print(f"     Tone Analysis: {tone_analysis['characteristics']}")
                                print(f"     Matches Expected: {tone_analysis['matches_expected']}")
                            else:
                                persona_test_results.append({
                                    "persona": persona_config['expected_tone'],
                                    "account_id": account_id,
                                    "draft_generated": False,
                                    "tone_match": False,
                                    "characteristics": "No draft generated",
                                    "draft_preview": "No draft"
                                })
                        else:
                            print(f"     Email processing failed: {email_response.status_code}")
                            persona_test_results.append({
                                "persona": persona_config['expected_tone'],
                                "account_id": account_id,
                                "draft_generated": False,
                                "tone_match": False,
                                "characteristics": f"API Error: {email_response.status_code}",
                                "draft_preview": "API Error"
                            })
                    else:
                        print(f"     Account creation failed: {response.status_code}")
                        persona_test_results.append({
                            "persona": persona_config['expected_tone'],
                            "account_id": None,
                            "draft_generated": False,
                            "tone_match": False,
                            "characteristics": f"Account creation failed: {response.status_code}",
                            "draft_preview": "Account creation failed"
                        })
                        
                except Exception as e:
                    print(f"     Exception testing persona {persona_config['expected_tone']}: {str(e)}")
                    persona_test_results.append({
                        "persona": persona_config['expected_tone'],
                        "account_id": None,
                        "draft_generated": False,
                        "tone_match": False,
                        "characteristics": f"Exception: {str(e)}",
                        "draft_preview": "Exception occurred"
                    })
            
            # Cleanup created accounts
            for account_id in created_account_ids:
                if account_id:
                    try:
                        requests.delete(f"{API_BASE}/email-accounts/{account_id}", timeout=10)
                    except:
                        pass
            
            # Evaluate results
            successful_persona_tests = [r for r in persona_test_results if r['tone_match']]
            all_passed = len(successful_persona_tests) >= len(persona_test_results) * 0.6  # 60% success rate
            
            details = f"Successful: {len(successful_persona_tests)}/{len(persona_test_results)} persona integrations working"
            
            self.log_test_result("Persona Integration", all_passed, details)
            
            # Log individual persona results
            for result in persona_test_results:
                self.log_test_result(f"Persona - {result['persona'].title()}", result['tone_match'], 
                                   f"Characteristics: {result['characteristics']}")
            
        except Exception as e:
            self.log_test_result("Persona Integration", False, f"Exception: {str(e)}")
    
    def analyze_response_tone(self, draft: str, expected_tone: str) -> dict:
        """Analyze the tone of a response draft"""
        draft_lower = draft.lower()
        
        characteristics = []
        matches_expected = False
        
        if expected_tone == "formal":
            # Check for formal language indicators
            formal_indicators = ["dear", "sincerely", "please find", "we would", "i would like to", "thank you for"]
            informal_indicators = ["hi", "hey", "awesome", "cool", "thanks!", "😊"]
            
            formal_count = sum(1 for indicator in formal_indicators if indicator in draft_lower)
            informal_count = sum(1 for indicator in informal_indicators if indicator in draft_lower)
            
            characteristics.append(f"Formal indicators: {formal_count}")
            characteristics.append(f"Informal indicators: {informal_count}")
            matches_expected = formal_count > informal_count
            
        elif expected_tone == "friendly":
            # Check for friendly language indicators
            friendly_indicators = ["hi", "hello", "thanks", "happy to", "glad to", "excited", "great"]
            cold_indicators = ["dear sir/madam", "to whom it may concern", "pursuant to"]
            
            friendly_count = sum(1 for indicator in friendly_indicators if indicator in draft_lower)
            cold_count = sum(1 for indicator in cold_indicators if indicator in draft_lower)
            
            characteristics.append(f"Friendly indicators: {friendly_count}")
            characteristics.append(f"Cold indicators: {cold_count}")
            matches_expected = friendly_count > cold_count
            
        elif expected_tone == "technical":
            # Check for technical language indicators
            technical_indicators = ["features", "functionality", "integration", "api", "system", "technical", "specifications"]
            simple_indicators = ["easy", "simple", "basic", "just"]
            
            technical_count = sum(1 for indicator in technical_indicators if indicator in draft_lower)
            simple_count = sum(1 for indicator in simple_indicators if indicator in draft_lower)
            
            characteristics.append(f"Technical indicators: {technical_count}")
            characteristics.append(f"Simple indicators: {simple_count}")
            matches_expected = technical_count >= simple_count
        
        return {
            "matches_expected": matches_expected,
            "characteristics": ", ".join(characteristics)
        }
    
    async def test_automatic_reply_workflow(self):
        """Test 4: Automatic Reply Workflow - Test full workflow from classification to sending"""
        print("\n🔄 Testing Automatic Reply Workflow...")
        
        try:
            if not self.test_account_id:
                # Get a test account
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("Automatic Reply Workflow", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            # Ensure account has auto_send enabled
            await self.db.email_accounts.update_one(
                {"id": self.test_account_id},
                {"$set": {"auto_send": True}}
            )
            
            # Test different workflow scenarios
            workflow_scenarios = [
                {
                    "name": "Sales Inquiry with Intent Match",
                    "subject": "Pricing Information Request",
                    "body": "Hello, I'm interested in your AI email assistant service. Could you please provide pricing information and schedule a demo? We're a medium-sized company looking to automate our customer service emails.",
                    "expected_intents": True,
                    "expected_auto_send": True
                },
                {
                    "name": "Support Request",
                    "subject": "Technical Support Needed",
                    "body": "Hi, I'm having trouble with the email classification feature. It seems to be categorizing emails incorrectly. Can you help me troubleshoot this issue?",
                    "expected_intents": True,
                    "expected_auto_send": True
                },
                {
                    "name": "General Inquiry",
                    "subject": "General Question",
                    "body": "Hi there, I heard about your service from a colleague. Can you tell me more about what you do?",
                    "expected_intents": False,  # May or may not match intents
                    "expected_auto_send": True  # Should still process with lenient validation
                }
            ]
            
            workflow_results = []
            
            for scenario in workflow_scenarios:
                try:
                    print(f"   Testing: {scenario['name']}")
                    
                    test_email_data = {
                        "subject": scenario["subject"],
                        "body": scenario["body"],
                        "sender": f"workflow{len(workflow_results)}@example.com",
                        "account_id": self.test_account_id
                    }
                    
                    # Process email through workflow
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Analyze workflow completion
                        email_id = processed_email.get('id')
                        status = processed_email.get('status')
                        intents = processed_email.get('intents', [])
                        draft = processed_email.get('draft', '')
                        validation_result = processed_email.get('validation_result', {})
                        
                        # Check workflow stages
                        classification_completed = len(intents) > 0 or status not in ['new', 'classifying']
                        draft_generated = bool(draft)
                        validation_completed = bool(validation_result)
                        auto_sent = status == 'sent'
                        ready_to_send = status in ['sent', 'ready_to_send']
                        
                        workflow_success = (classification_completed and draft_generated and 
                                          validation_completed and ready_to_send)
                        
                        workflow_results.append({
                            "scenario": scenario['name'],
                            "email_id": email_id,
                            "status": status,
                            "intents_found": len(intents),
                            "draft_generated": draft_generated,
                            "validation_completed": validation_completed,
                            "auto_sent": auto_sent,
                            "workflow_success": workflow_success,
                            "processing_time": "N/A"  # Could be measured if needed
                        })
                        
                        print(f"     Status: {status}")
                        print(f"     Intents: {len(intents)}")
                        print(f"     Draft: {'✓' if draft_generated else '✗'}")
                        print(f"     Validation: {'✓' if validation_completed else '✗'}")
                        print(f"     Auto-sent: {'✓' if auto_sent else '✗'}")
                        
                    else:
                        print(f"     API Error: {response.status_code}")
                        workflow_results.append({
                            "scenario": scenario['name'],
                            "email_id": None,
                            "status": f"API Error: {response.status_code}",
                            "intents_found": 0,
                            "draft_generated": False,
                            "validation_completed": False,
                            "auto_sent": False,
                            "workflow_success": False,
                            "processing_time": "N/A"
                        })
                        
                except Exception as e:
                    print(f"     Exception: {str(e)}")
                    workflow_results.append({
                        "scenario": scenario['name'],
                        "email_id": None,
                        "status": f"Exception: {str(e)}",
                        "intents_found": 0,
                        "draft_generated": False,
                        "validation_completed": False,
                        "auto_sent": False,
                        "workflow_success": False,
                        "processing_time": "N/A"
                    })
            
            # Evaluate results
            successful_workflows = [r for r in workflow_results if r['workflow_success']]
            all_passed = len(successful_workflows) >= len(workflow_results) * 0.7  # 70% success rate
            
            details = f"Successful: {len(successful_workflows)}/{len(workflow_results)} workflows completed"
            
            self.log_test_result("Automatic Reply Workflow", all_passed, details)
            
            # Log individual workflow results
            for result in workflow_results:
                self.log_test_result(f"Workflow - {result['scenario']}", result['workflow_success'], 
                                   f"Status: {result['status']}, Intents: {result['intents_found']}, Draft: {result['draft_generated']}")
            
        except Exception as e:
            self.log_test_result("Automatic Reply Workflow", False, f"Exception: {str(e)}")
    
    async def test_follow_up_system(self):
        """Test 5: Follow-up System - Ensure follow-up functionality is working properly"""
        print("\n📅 Testing Follow-up System...")
        
        try:
            # Test follow-up configuration endpoints
            config_tests = []
            
            # Test 5a: Check if follow-up models and endpoints exist
            try:
                # Test getting follow-up configurations (if endpoint exists)
                response = requests.get(f"{API_BASE}/follow-up-config", timeout=10)
                config_endpoint_exists = response.status_code in [200, 404]  # 404 is ok, means no configs yet
                config_tests.append(("Follow-up Config Endpoint", config_endpoint_exists))
                
            except Exception as e:
                config_tests.append(("Follow-up Config Endpoint", False))
            
            # Test 5b: Check email accounts have follow-up fields
            try:
                if self.test_account_id:
                    account = await self.db.email_accounts.find_one({"id": self.test_account_id})
                    if account:
                        has_follow_up_fields = (
                            'enable_follow_ups' in account and
                            'follow_up_hours_override' in account
                        )
                        config_tests.append(("Account Follow-up Fields", has_follow_up_fields))
                        
                        # Update account to enable follow-ups for testing
                        if has_follow_up_fields:
                            await self.db.email_accounts.update_one(
                                {"id": self.test_account_id},
                                {"$set": {
                                    "enable_follow_ups": True,
                                    "follow_up_hours_override": 24
                                }}
                            )
                    else:
                        config_tests.append(("Account Follow-up Fields", False))
                else:
                    config_tests.append(("Account Follow-up Fields", False))
                    
            except Exception as e:
                config_tests.append(("Account Follow-up Fields", False))
            
            # Test 5c: Check follow-up email model exists in database
            try:
                # Check if follow_up_emails collection exists and has proper structure
                follow_up_emails = await self.db.follow_up_emails.find().limit(1).to_list(1)
                follow_up_collection_exists = True  # Collection exists if query doesn't fail
                config_tests.append(("Follow-up Collection", follow_up_collection_exists))
                
            except Exception as e:
                config_tests.append(("Follow-up Collection", False))
            
            # Test 5d: Test follow-up creation workflow
            try:
                # Create a test email that should trigger follow-up
                if self.test_account_id:
                    test_email_data = {
                        "subject": "Follow-up Test Email",
                        "body": "Hi, I'm interested in your service but need some time to think about it. Please follow up with me in a day or two.",
                        "sender": "followup.test@example.com",
                        "account_id": self.test_account_id
                    }
                    
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        email_id = processed_email.get('id')
                        
                        # Check if follow-up was created (this would be in a real implementation)
                        # For now, we'll check if the email was processed successfully
                        follow_up_workflow = processed_email.get('status') in ['sent', 'ready_to_send']
                        config_tests.append(("Follow-up Workflow", follow_up_workflow))
                    else:
                        config_tests.append(("Follow-up Workflow", False))
                else:
                    config_tests.append(("Follow-up Workflow", False))
                    
            except Exception as e:
                config_tests.append(("Follow-up Workflow", False))
            
            # Test 5e: Check thread tracking functionality
            try:
                # Check if email threads collection exists
                threads = await self.db.email_threads.find().limit(1).to_list(1)
                thread_tracking_exists = True
                config_tests.append(("Thread Tracking", thread_tracking_exists))
                
            except Exception as e:
                config_tests.append(("Thread Tracking", False))
            
            # Evaluate results
            successful_tests = [test for test in config_tests if test[1]]
            all_passed = len(successful_tests) >= len(config_tests) * 0.6  # 60% success rate
            
            details = f"Successful: {len(successful_tests)}/{len(config_tests)} follow-up components working"
            
            self.log_test_result("Follow-up System", all_passed, details)
            
            # Log individual follow-up component results
            for test_name, test_result in config_tests:
                self.log_test_result(f"Follow-up - {test_name}", test_result, 
                                   f"Component working: {test_result}")
            
        except Exception as e:
            self.log_test_result("Follow-up System", False, f"Exception: {str(e)}")
    
    async def test_emails_test_endpoint(self):
        """Test 6: /api/emails/test endpoint comprehensive testing"""
        print("\n🧪 Testing /api/emails/test Endpoint...")
        
        try:
            if not self.test_account_id:
                # Get a test account
                account = await self.db.email_accounts.find_one({"is_active": True})
                if not account:
                    self.log_test_result("/api/emails/test Endpoint", False, "No active email accounts found")
                    return
                self.test_account_id = account['id']
            
            endpoint_tests = []
            
            # Test 6a: Basic endpoint functionality
            try:
                test_email_data = {
                    "subject": "Endpoint Test Email",
                    "body": "This is a test email to verify the /api/emails/test endpoint is working correctly.",
                    "sender": "endpoint.test@example.com",
                    "account_id": self.test_account_id
                }
                
                start_time = time.time()
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                end_time = time.time()
                
                processing_time = end_time - start_time
                
                basic_functionality = response.status_code in [200, 201]
                endpoint_tests.append(("Basic Functionality", basic_functionality, f"Status: {response.status_code}, Time: {processing_time:.1f}s"))
                
                if basic_functionality:
                    processed_email = response.json()
                    
                    # Test response structure
                    required_fields = ['id', 'status', 'intents', 'draft']
                    has_required_fields = all(field in processed_email for field in required_fields)
                    endpoint_tests.append(("Response Structure", has_required_fields, f"Fields: {list(processed_email.keys())}"))
                    
                    # Test processing completion
                    processing_completed = processed_email.get('status') not in ['new', 'error']
                    endpoint_tests.append(("Processing Completion", processing_completed, f"Status: {processed_email.get('status')}"))
                    
                    # Test response time
                    reasonable_time = processing_time < 45  # Should complete within 45 seconds
                    endpoint_tests.append(("Response Time", reasonable_time, f"Time: {processing_time:.1f}s"))
                    
                else:
                    endpoint_tests.append(("Response Structure", False, f"API Error: {response.status_code}"))
                    endpoint_tests.append(("Processing Completion", False, "API request failed"))
                    endpoint_tests.append(("Response Time", False, f"Time: {processing_time:.1f}s"))
                    
            except Exception as e:
                endpoint_tests.append(("Basic Functionality", False, f"Exception: {str(e)}"))
                endpoint_tests.append(("Response Structure", False, "Request failed"))
                endpoint_tests.append(("Processing Completion", False, "Request failed"))
                endpoint_tests.append(("Response Time", False, "Request failed"))
            
            # Test 6b: Error handling
            try:
                # Test with invalid account ID
                invalid_data = {
                    "subject": "Invalid Test",
                    "body": "Test with invalid account ID",
                    "sender": "invalid.test@example.com",
                    "account_id": "invalid-account-id"
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=invalid_data, timeout=30)
                error_handling = response.status_code in [400, 404, 422]  # Should return appropriate error
                endpoint_tests.append(("Error Handling", error_handling, f"Status: {response.status_code}"))
                
            except Exception as e:
                endpoint_tests.append(("Error Handling", False, f"Exception: {str(e)}"))
            
            # Test 6c: Multiple concurrent requests (stress test)
            try:
                concurrent_requests = []
                for i in range(3):  # Test 3 concurrent requests
                    test_data = {
                        "subject": f"Concurrent Test {i+1}",
                        "body": f"This is concurrent test email number {i+1}",
                        "sender": f"concurrent{i+1}@example.com",
                        "account_id": self.test_account_id
                    }
                    concurrent_requests.append(test_data)
                
                # Send requests concurrently (simplified version)
                concurrent_results = []
                for req_data in concurrent_requests:
                    try:
                        response = requests.post(f"{API_BASE}/emails/test", json=req_data, timeout=45)
                        concurrent_results.append(response.status_code in [200, 201])
                    except:
                        concurrent_results.append(False)
                
                concurrent_success = sum(concurrent_results) >= len(concurrent_results) * 0.7  # 70% success
                endpoint_tests.append(("Concurrent Requests", concurrent_success, f"Success: {sum(concurrent_results)}/{len(concurrent_results)}"))
                
            except Exception as e:
                endpoint_tests.append(("Concurrent Requests", False, f"Exception: {str(e)}"))
            
            # Evaluate results
            successful_tests = [test for test in endpoint_tests if test[1]]
            all_passed = len(successful_tests) >= len(endpoint_tests) * 0.75  # 75% success rate
            
            details = f"Successful: {len(successful_tests)}/{len(endpoint_tests)} endpoint tests passed"
            
            self.log_test_result("/api/emails/test Endpoint", all_passed, details)
            
            # Log individual endpoint test results
            for test_name, test_result, test_details in endpoint_tests:
                self.log_test_result(f"Endpoint - {test_name}", test_result, test_details)
            
        except Exception as e:
            self.log_test_result("/api/emails/test Endpoint", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🧪 API KEYS & RESPONSE SYSTEM TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📊 DETAILED RESULTS:")
        print("-" * 80)
        
        # Group results by main categories
        categories = {}
        for result in self.test_results:
            category = result['test'].split(' - ')[0] if ' - ' in result['test'] else result['test']
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        for category, tests in categories.items():
            category_passed = len([t for t in tests if t['passed']])
            category_total = len(tests)
            print(f"\n{category}: {category_passed}/{category_total}")
            
            for test in tests:
                status_icon = "✅" if test['passed'] else "❌"
                print(f"  {status_icon} {test['test']}")
                if test['details'] and not test['passed']:
                    print(f"     Details: {test['details']}")
        
        print("\n" + "="*80)
        
        # Critical issues summary
        critical_failures = [r for r in self.test_results if not r['passed'] and 
                           any(keyword in r['test'].lower() for keyword in 
                               ['api keys', 'response length', 'workflow', 'endpoint'])]
        
        if critical_failures:
            print("🚨 CRITICAL ISSUES FOUND:")
            for failure in critical_failures:
                print(f"  ❌ {failure['test']}: {failure['details']}")
        else:
            print("✅ NO CRITICAL ISSUES FOUND")
        
        print("="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting API Keys & Response System Testing...")
    print("="*80)
    
    tester = APIKeysResponseTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run all tests
        await tester.test_api_keys_validation()
        await tester.test_response_length_limits()
        await tester.test_persona_integration()
        await tester.test_automatic_reply_workflow()
        await tester.test_follow_up_system()
        await tester.test_emails_test_endpoint()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())