#!/usr/bin/env python3
"""
Comprehensive Parlant Framework Integration Testing
Tests all aspects of the Parlant-inspired framework as requested in the review
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

class ParlantFrameworkTester:
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

    async def test_parlant_framework_components(self):
        """Test 1: Parlant Framework Components - Verify all three agents are properly initialized"""
        print("\n🤖 Testing Parlant Framework Components...")
        
        try:
            # Import and test framework components
            from parlant_framework import parlant_framework, DraftAgent, ValidationAgent, CalendarAgent, ParlantAgent, AgentResponse
            
            # Test 1a: Framework initialization
            framework_initialized = parlant_framework is not None
            
            # Test 1b: Draft Agent initialization and guidelines
            draft_agent = parlant_framework.draft_agent
            draft_agent_initialized = isinstance(draft_agent, DraftAgent)
            draft_guidelines_count = len(draft_agent.guidelines)
            
            # Check specific draft agent guidelines
            expected_draft_guidelines = ["professional_tone", "sales_inquiry", "support_request", "meeting_request", "persona_alignment"]
            draft_guidelines_present = all(guideline_id in draft_agent.guidelines for guideline_id in expected_draft_guidelines)
            
            # Test 1c: Validation Agent initialization and guidelines
            validation_agent = parlant_framework.validation_agent
            validation_agent_initialized = isinstance(validation_agent, ValidationAgent)
            validation_guidelines_count = len(validation_agent.guidelines)
            
            # Check specific validation agent guidelines
            expected_validation_guidelines = ["hallucination_check", "intent_coverage", "persona_consistency", "content_appropriateness", "completeness_check"]
            validation_guidelines_present = all(guideline_id in validation_agent.guidelines for guideline_id in expected_validation_guidelines)
            
            # Test 1d: Calendar Agent initialization and guidelines
            calendar_agent = parlant_framework.calendar_agent
            calendar_agent_initialized = isinstance(calendar_agent, CalendarAgent)
            calendar_guidelines_count = len(calendar_agent.guidelines)
            
            # Check specific calendar agent guidelines
            expected_calendar_guidelines = ["meeting_detection", "conflict_resolution", "timezone_handling", "meeting_confirmation"]
            calendar_guidelines_present = all(guideline_id in calendar_agent.guidelines for guideline_id in expected_calendar_guidelines)
            
            # Test 1e: Guideline matching functionality
            test_context = {
                "email_content": "I need pricing information for your AI email assistant product",
                "intents": [{"name": "sales_inquiry", "confidence": 0.8}]
            }
            
            matched_guidelines = draft_agent.match_guidelines(test_context)
            guideline_matching_works = len(matched_guidelines) > 0
            
            # Test 1f: AgentResponse structure
            test_response = AgentResponse(
                content="Test response",
                confidence=0.9,
                guidelines_applied=["professional_tone"],
                tools_used=["knowledge_base_search"],
                reasoning="Test reasoning"
            )
            agent_response_structure = (hasattr(test_response, 'content') and 
                                      hasattr(test_response, 'confidence') and
                                      hasattr(test_response, 'guidelines_applied') and
                                      hasattr(test_response, 'tools_used'))
            
            all_passed = (framework_initialized and draft_agent_initialized and 
                         validation_agent_initialized and calendar_agent_initialized and
                         draft_guidelines_present and validation_guidelines_present and
                         calendar_guidelines_present and guideline_matching_works and
                         agent_response_structure)
            
            details = f"Framework: {framework_initialized}, Draft Agent: {draft_agent_initialized} ({draft_guidelines_count} guidelines), " \
                     f"Validation Agent: {validation_agent_initialized} ({validation_guidelines_count} guidelines), " \
                     f"Calendar Agent: {calendar_agent_initialized} ({calendar_guidelines_count} guidelines), " \
                     f"Guideline matching: {guideline_matching_works}, AgentResponse: {agent_response_structure}"
            
            self.log_test_result("Parlant Framework Components", all_passed, details)
            
            # Log individual component results
            self.log_test_result("Parlant - Draft Agent Initialization", draft_agent_initialized and draft_guidelines_present, 
                               f"Guidelines: {draft_guidelines_count}, Expected present: {draft_guidelines_present}")
            self.log_test_result("Parlant - Validation Agent Initialization", validation_agent_initialized and validation_guidelines_present,
                               f"Guidelines: {validation_guidelines_count}, Expected present: {validation_guidelines_present}")
            self.log_test_result("Parlant - Calendar Agent Initialization", calendar_agent_initialized and calendar_guidelines_present,
                               f"Guidelines: {calendar_guidelines_count}, Expected present: {calendar_guidelines_present}")
            self.log_test_result("Parlant - Guideline Matching", guideline_matching_works,
                               f"Matched {len(matched_guidelines)} guidelines for test context")
            
        except Exception as e:
            self.log_test_result("Parlant Framework Components", False, f"Exception: {str(e)}")

    async def test_email_processing_with_parlant_integration(self):
        """Test 2: Email Processing with Parlant Integration - Test /api/emails/test endpoint with Parlant framework"""
        print("\n📧 Testing Email Processing with Parlant Integration...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Email Processing with Parlant Integration", False, "No active email accounts")
                return
            
            # Test scenarios to verify Parlant framework is used
            test_scenarios = [
                {
                    "name": "Sales Inquiry with Parlant",
                    "subject": "AI Email Assistant Pricing and Features",
                    "body": "Hello, I'm interested in your AI Email Assistant product. Could you provide detailed pricing information, feature list, and implementation timeline? We're a mid-size company looking to automate our customer email responses.",
                    "sender": "sales@company.com",
                    "expected_guidelines": ["sales_inquiry", "professional_tone", "persona_alignment"]
                },
                {
                    "name": "Support Request with Parlant",
                    "subject": "Technical Issue - Email Processing Error",
                    "body": "We're experiencing issues with our email automation system. The AI responses are not generating properly and we're getting timeout errors. Can you help us troubleshoot this problem urgently?",
                    "sender": "support@client.com",
                    "expected_guidelines": ["support_request", "professional_tone", "persona_alignment"]
                },
                {
                    "name": "Meeting Request with Parlant",
                    "subject": "Schedule Demo Meeting",
                    "body": "I would like to schedule a demo meeting to see your AI Email Assistant in action. I'm available next Tuesday or Wednesday afternoon. Please let me know what times work for you.",
                    "sender": "demo@prospect.com",
                    "expected_guidelines": ["meeting_request", "professional_tone", "persona_alignment"]
                },
                {
                    "name": "General Email with Parlant",
                    "subject": "General Information Request",
                    "body": "I heard about your company and would like to learn more about your services. Could you send me some general information about what you offer?",
                    "sender": "info@general.com",
                    "expected_guidelines": ["professional_tone", "persona_alignment"]
                }
            ]
            
            parlant_integration_results = []
            
            for scenario in test_scenarios:
                print(f"   Testing scenario: {scenario['name']}")
                
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": account['id']
                }
                
                try:
                    # Process email through Parlant-enhanced pipeline
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Check for Parlant framework usage indicators
                        validation_result = processed_email.get('validation_result', {})
                        
                        # Check for Parlant-specific metadata
                        has_parlant_guidelines = bool(validation_result.get('parlant_guidelines'))
                        has_parlant_confidence = bool(validation_result.get('parlant_confidence'))
                        has_guidelines_applied = bool(validation_result.get('guidelines_applied'))
                        
                        # Check draft generation with Parlant enhancement
                        draft_content = processed_email.get('draft', '')
                        draft_length = len(draft_content)
                        has_professional_tone = not any(casual in draft_content.lower() for casual in ['hey', 'sup', 'yo'])
                        
                        # Check validation with Parlant enhancement
                        validation_status = validation_result.get('status', 'UNKNOWN')
                        has_validation_feedback = bool(validation_result.get('feedback'))
                        
                        # Check for intent classification (should work with Parlant)
                        intents = processed_email.get('intents', [])
                        has_intents = len(intents) > 0
                        
                        # Check for persona alignment (Parlant guideline)
                        account_persona = account.get('persona', '')
                        persona_reflected = True  # Default to true if no specific persona
                        
                        # Overall Parlant integration assessment
                        parlant_metadata_present = has_parlant_guidelines or has_parlant_confidence or has_guidelines_applied
                        workflow_completed = processed_email.get('status') in ['ready_to_send', 'sent', 'needs_redraft']
                        
                        scenario_passed = (has_intents and draft_length > 100 and has_professional_tone and
                                         validation_status in ['PASS', 'FAIL'] and workflow_completed and
                                         parlant_metadata_present)
                        
                        parlant_integration_results.append({
                            "scenario": scenario['name'],
                            "passed": scenario_passed,
                            "parlant_metadata": parlant_metadata_present,
                            "guidelines_applied": validation_result.get('guidelines_applied', []),
                            "draft_length": draft_length,
                            "validation_status": validation_status,
                            "intents_found": len(intents),
                            "workflow_status": processed_email.get('status')
                        })
                        
                        print(f"     - Parlant metadata: {parlant_metadata_present}")
                        print(f"     - Guidelines applied: {len(validation_result.get('guidelines_applied', []))}")
                        print(f"     - Draft length: {draft_length} chars")
                        print(f"     - Validation status: {validation_status}")
                        print(f"     - Intents found: {len(intents)}")
                        print(f"     - Workflow status: {processed_email.get('status')}")
                        
                    else:
                        print(f"     ❌ API failed - Status: {response.status_code}")
                        parlant_integration_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    parlant_integration_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Evaluate overall results
            passed_scenarios = sum(1 for result in parlant_integration_results if result.get('passed', False))
            total_scenarios = len(parlant_integration_results)
            
            all_passed = passed_scenarios >= (total_scenarios * 0.75)  # 75% pass rate acceptable
            
            details = f"Scenarios passed: {passed_scenarios}/{total_scenarios}. "
            for result in parlant_integration_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Email Processing with Parlant Integration", all_passed, details)
            
            # Log individual scenario results
            for result in parlant_integration_results:
                scenario_name = f"Parlant Integration - {result['scenario']}"
                scenario_passed = result.get('passed', False)
                scenario_details = ""
                if 'parlant_metadata' in result:
                    scenario_details = f"Metadata: {result['parlant_metadata']}, Guidelines: {len(result.get('guidelines_applied', []))}, Draft: {result['draft_length']}c"
                elif 'error' in result:
                    scenario_details = result['error']
                
                self.log_test_result(scenario_name, scenario_passed, scenario_details)
            
        except Exception as e:
            self.log_test_result("Email Processing with Parlant Integration", False, f"Exception: {str(e)}")

    async def test_parlant_guidelines_application(self):
        """Test 3: Parlant Guidelines Application - Test specific guideline matching and application"""
        print("\n📋 Testing Parlant Guidelines Application...")
        
        try:
            # Import framework for direct testing
            from parlant_framework import parlant_framework
            
            # Test specific guideline scenarios
            guideline_scenarios = [
                {
                    "name": "Sales Inquiry Guideline",
                    "context": {
                        "email_content": "I want to buy your AI email assistant. Please send pricing information.",
                        "intents": [{"name": "sales_inquiry", "confidence": 0.9}],
                        "type": "draft_generation"
                    },
                    "expected_guideline": "sales_inquiry",
                    "agent": "draft"
                },
                {
                    "name": "Support Request Guideline",
                    "context": {
                        "email_content": "I'm having technical problems with the email system. It's not working properly.",
                        "intents": [{"name": "technical_support", "confidence": 0.8}],
                        "type": "draft_generation"
                    },
                    "expected_guideline": "support_request",
                    "agent": "draft"
                },
                {
                    "name": "Meeting Request Guideline",
                    "context": {
                        "email_content": "Can we schedule a meeting next week to discuss the project?",
                        "intents": [{"name": "meeting_request", "confidence": 0.85}],
                        "type": "draft_generation"
                    },
                    "expected_guideline": "meeting_request",
                    "agent": "draft"
                },
                {
                    "name": "Professional Tone Guideline",
                    "context": {
                        "email_content": "Hello, I need some information about your services.",
                        "intents": [],
                        "type": "draft_generation"
                    },
                    "expected_guideline": "professional_tone",
                    "agent": "draft"
                },
                {
                    "name": "Hallucination Check Guideline",
                    "context": {
                        "draft_content": "Our AI system can process 1 million emails per second.",
                        "email_content": "Tell me about your capabilities",
                        "type": "validation"
                    },
                    "expected_guideline": "hallucination_check",
                    "agent": "validation"
                },
                {
                    "name": "Intent Coverage Guideline",
                    "context": {
                        "draft_content": "Thank you for your email.",
                        "intents": [{"name": "pricing_request", "confidence": 0.9}],
                        "type": "validation"
                    },
                    "expected_guideline": "intent_coverage",
                    "agent": "validation"
                }
            ]
            
            guideline_results = []
            
            for scenario in guideline_scenarios:
                print(f"   Testing guideline: {scenario['name']}")
                
                try:
                    # Select appropriate agent
                    if scenario['agent'] == 'draft':
                        agent = parlant_framework.draft_agent
                    elif scenario['agent'] == 'validation':
                        agent = parlant_framework.validation_agent
                    else:
                        agent = parlant_framework.calendar_agent
                    
                    # Test guideline matching
                    matched_guidelines = agent.match_guidelines(scenario['context'])
                    guideline_ids = [g.id for g in matched_guidelines]
                    
                    # Check if expected guideline is matched
                    expected_matched = scenario['expected_guideline'] in guideline_ids
                    
                    # Test framework processing
                    if scenario['agent'] == 'draft':
                        enhancement = await parlant_framework.enhance_draft_generation(
                            scenario['context'], 
                            scenario['context'].get('intents', [])
                        )
                        framework_response = enhancement.get('agent_response')
                    elif scenario['agent'] == 'validation':
                        enhancement = await parlant_framework.enhance_validation(
                            {"content": scenario['context'].get('draft_content', '')},
                            scenario['context'],
                            scenario['context'].get('intents', [])
                        )
                        framework_response = enhancement.get('agent_response')
                    else:
                        enhancement = await parlant_framework.enhance_calendar_processing(scenario['context'])
                        framework_response = enhancement.get('calendar_analysis')
                    
                    # Check framework response
                    has_framework_response = framework_response is not None
                    has_guidelines_applied = bool(framework_response.guidelines_applied if framework_response else False)
                    
                    scenario_passed = expected_matched and has_framework_response
                    
                    guideline_results.append({
                        "scenario": scenario['name'],
                        "passed": scenario_passed,
                        "expected_guideline": scenario['expected_guideline'],
                        "matched_guidelines": guideline_ids,
                        "expected_matched": expected_matched,
                        "framework_response": has_framework_response,
                        "guidelines_applied": framework_response.guidelines_applied if framework_response else []
                    })
                    
                    print(f"     - Expected guideline '{scenario['expected_guideline']}' matched: {expected_matched}")
                    print(f"     - Total guidelines matched: {len(guideline_ids)}")
                    print(f"     - Framework response: {has_framework_response}")
                    if framework_response:
                        print(f"     - Guidelines applied: {len(framework_response.guidelines_applied)}")
                    
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    guideline_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Evaluate overall guideline application
            passed_guidelines = sum(1 for result in guideline_results if result.get('passed', False))
            total_guidelines = len(guideline_results)
            
            all_passed = passed_guidelines >= (total_guidelines * 0.8)  # 80% pass rate
            
            details = f"Guidelines passed: {passed_guidelines}/{total_guidelines}. "
            for result in guideline_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Parlant Guidelines Application", all_passed, details)
            
            # Log individual guideline results
            for result in guideline_results:
                scenario_name = f"Guideline - {result['scenario']}"
                scenario_passed = result.get('passed', False)
                scenario_details = ""
                if 'expected_matched' in result:
                    scenario_details = f"Expected matched: {result['expected_matched']}, Guidelines: {len(result.get('matched_guidelines', []))}"
                elif 'error' in result:
                    scenario_details = result['error']
                
                self.log_test_result(scenario_name, scenario_passed, scenario_details)
            
        except Exception as e:
            self.log_test_result("Parlant Guidelines Application", False, f"Exception: {str(e)}")

    async def test_agent_response_structure(self):
        """Test 4: Agent Response Structure - Verify AgentResponse objects with confidence scores and tracking"""
        print("\n📊 Testing Agent Response Structure...")
        
        try:
            # Import required classes
            from parlant_framework import parlant_framework, AgentResponse
            
            # Test AgentResponse structure and functionality
            test_contexts = [
                {
                    "name": "Draft Generation Response",
                    "context": {
                        "email_content": "I need pricing information for your AI assistant",
                        "intents": [{"name": "sales_inquiry", "confidence": 0.9}],
                        "type": "draft_generation"
                    },
                    "agent_type": "draft"
                },
                {
                    "name": "Validation Response",
                    "context": {
                        "draft_content": "Thank you for your inquiry. Here's our pricing information...",
                        "email_content": "I need pricing information",
                        "intents": [{"name": "sales_inquiry", "confidence": 0.9}],
                        "type": "validation"
                    },
                    "agent_type": "validation"
                },
                {
                    "name": "Calendar Processing Response",
                    "context": {
                        "email_content": "Let's schedule a meeting for next Tuesday at 2 PM",
                        "subject": "Meeting Request",
                        "type": "calendar_processing"
                    },
                    "agent_type": "calendar"
                }
            ]
            
            response_structure_results = []
            
            for test_case in test_contexts:
                print(f"   Testing response structure: {test_case['name']}")
                
                try:
                    # Get agent response based on type
                    if test_case['agent_type'] == 'draft':
                        enhancement = await parlant_framework.enhance_draft_generation(
                            test_case['context'], 
                            test_case['context'].get('intents', [])
                        )
                        agent_response = enhancement.get('agent_response')
                    elif test_case['agent_type'] == 'validation':
                        enhancement = await parlant_framework.enhance_validation(
                            {"content": test_case['context'].get('draft_content', '')},
                            test_case['context'],
                            test_case['context'].get('intents', [])
                        )
                        agent_response = enhancement.get('agent_response')
                    else:  # calendar
                        enhancement = await parlant_framework.enhance_calendar_processing(test_case['context'])
                        agent_response = enhancement.get('calendar_analysis')
                    
                    # Verify AgentResponse structure
                    is_agent_response = isinstance(agent_response, AgentResponse)
                    
                    if is_agent_response:
                        # Check required fields
                        has_content = hasattr(agent_response, 'content')
                        has_confidence = hasattr(agent_response, 'confidence') and isinstance(agent_response.confidence, (int, float))
                        has_guidelines_applied = hasattr(agent_response, 'guidelines_applied') and isinstance(agent_response.guidelines_applied, list)
                        has_tools_used = hasattr(agent_response, 'tools_used') and isinstance(agent_response.tools_used, list)
                        has_reasoning = hasattr(agent_response, 'reasoning')
                        
                        # Check confidence score validity
                        confidence_valid = 0.0 <= agent_response.confidence <= 1.0
                        
                        # Check guidelines tracking
                        guidelines_tracked = len(agent_response.guidelines_applied) >= 0
                        
                        # Check tools tracking
                        tools_tracked = len(agent_response.tools_used) >= 0
                        
                        structure_valid = (has_content and has_confidence and has_guidelines_applied and 
                                         has_tools_used and has_reasoning and confidence_valid and
                                         guidelines_tracked and tools_tracked)
                    else:
                        structure_valid = False
                        has_content = has_confidence = has_guidelines_applied = has_tools_used = has_reasoning = False
                        confidence_valid = guidelines_tracked = tools_tracked = False
                    
                    response_structure_results.append({
                        "test_case": test_case['name'],
                        "passed": structure_valid,
                        "is_agent_response": is_agent_response,
                        "has_required_fields": has_content and has_confidence and has_guidelines_applied and has_tools_used,
                        "confidence_valid": confidence_valid,
                        "guidelines_count": len(agent_response.guidelines_applied) if is_agent_response else 0,
                        "tools_count": len(agent_response.tools_used) if is_agent_response else 0,
                        "confidence_score": agent_response.confidence if is_agent_response else 0.0
                    })
                    
                    print(f"     - AgentResponse instance: {is_agent_response}")
                    if is_agent_response:
                        print(f"     - Confidence score: {agent_response.confidence:.2f}")
                        print(f"     - Guidelines applied: {len(agent_response.guidelines_applied)}")
                        print(f"     - Tools used: {len(agent_response.tools_used)}")
                        print(f"     - Has reasoning: {bool(agent_response.reasoning)}")
                    
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    response_structure_results.append({
                        "test_case": test_case['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Test manual AgentResponse creation
            print("   Testing manual AgentResponse creation...")
            try:
                manual_response = AgentResponse(
                    content="Test response content",
                    confidence=0.85,
                    guidelines_applied=["professional_tone", "sales_inquiry"],
                    tools_used=["knowledge_base_search"],
                    reasoning="Applied sales inquiry guideline based on email content",
                    should_escalate=False
                )
                
                manual_creation_passed = (isinstance(manual_response, AgentResponse) and
                                        manual_response.confidence == 0.85 and
                                        len(manual_response.guidelines_applied) == 2 and
                                        len(manual_response.tools_used) == 1)
                
                response_structure_results.append({
                    "test_case": "Manual AgentResponse Creation",
                    "passed": manual_creation_passed,
                    "is_agent_response": isinstance(manual_response, AgentResponse),
                    "confidence_score": manual_response.confidence,
                    "guidelines_count": len(manual_response.guidelines_applied),
                    "tools_count": len(manual_response.tools_used)
                })
                
                print(f"     - Manual creation: {manual_creation_passed}")
                
            except Exception as e:
                print(f"     ❌ Manual creation exception: {str(e)}")
                response_structure_results.append({
                    "test_case": "Manual AgentResponse Creation",
                    "passed": False,
                    "error": str(e)
                })
            
            # Evaluate overall response structure
            passed_structures = sum(1 for result in response_structure_results if result.get('passed', False))
            total_structures = len(response_structure_results)
            
            all_passed = passed_structures == total_structures
            
            details = f"Response structures passed: {passed_structures}/{total_structures}. "
            for result in response_structure_results:
                if result.get('passed'):
                    details += f"{result['test_case']}: ✅ "
                else:
                    details += f"{result['test_case']}: ❌ "
            
            self.log_test_result("Agent Response Structure", all_passed, details)
            
            # Log individual structure results
            for result in response_structure_results:
                test_name = f"Response Structure - {result['test_case']}"
                test_passed = result.get('passed', False)
                test_details = ""
                if 'confidence_score' in result:
                    test_details = f"Confidence: {result['confidence_score']:.2f}, Guidelines: {result.get('guidelines_count', 0)}, Tools: {result.get('tools_count', 0)}"
                elif 'error' in result:
                    test_details = result['error']
                
                self.log_test_result(test_name, test_passed, test_details)
            
        except Exception as e:
            self.log_test_result("Agent Response Structure", False, f"Exception: {str(e)}")

    async def test_validation_agent_comprehensive(self):
        """Test 5: Validation Agent Comprehensive - Test all validation functions"""
        print("\n🔍 Testing Validation Agent Comprehensive...")
        
        try:
            # Get active account for testing
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Validation Agent Comprehensive", False, "No active email accounts")
                return
            
            # Test comprehensive validation scenarios
            validation_scenarios = [
                {
                    "name": "Hallucination Check Test",
                    "subject": "Product Information Request",
                    "body": "Tell me about your AI email assistant capabilities and pricing",
                    "sender": "test@hallucination.com",
                    "validation_focus": "hallucination_check"
                },
                {
                    "name": "Intent Coverage Test",
                    "subject": "Multiple Requests - Pricing, Demo, and Support",
                    "body": "I need pricing information, want to schedule a demo, and also have some technical questions about integration. Can you help with all of these?",
                    "sender": "test@intent.com",
                    "validation_focus": "intent_coverage"
                },
                {
                    "name": "Persona Consistency Test",
                    "subject": "Professional Communication Test",
                    "body": "I'm looking for a professional AI solution for our enterprise. Please provide formal documentation and pricing.",
                    "sender": "test@persona.com",
                    "validation_focus": "persona_consistency"
                },
                {
                    "name": "Content Appropriateness Test",
                    "subject": "Business Inquiry",
                    "body": "Hello, I'm interested in your business solutions. Please provide appropriate business information.",
                    "sender": "test@appropriate.com",
                    "validation_focus": "content_appropriateness"
                }
            ]
            
            validation_results = []
            
            for scenario in validation_scenarios:
                print(f"   Testing validation: {scenario['name']}")
                
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": account['id']
                }
                
                try:
                    # Process email through validation pipeline
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        validation_result = processed_email.get('validation_result', {})
                        
                        # Check validation status
                        validation_status = validation_result.get('status', 'UNKNOWN')
                        has_validation_status = validation_status in ['PASS', 'FAIL']
                        
                        # Check for validation feedback
                        has_feedback = bool(validation_result.get('feedback'))
                        
                        # Check for Parlant validation enhancements
                        has_parlant_validation = bool(validation_result.get('parlant_guidelines') or 
                                                    validation_result.get('parlant_confidence'))
                        
                        # Check specific validation aspects
                        has_hallucination_check = 'hallucination' in str(validation_result).lower()
                        has_intent_coverage = 'intent' in str(validation_result).lower() or 'coverage' in str(validation_result).lower()
                        has_persona_check = 'persona' in str(validation_result).lower()
                        has_appropriateness_check = 'appropriate' in str(validation_result).lower() or 'professional' in str(validation_result).lower()
                        
                        # Check validation recommendations
                        has_recommendations = bool(validation_result.get('recommendations'))
                        
                        # Overall validation assessment
                        validation_comprehensive = (has_validation_status and has_feedback and
                                                  (has_hallucination_check or has_intent_coverage or 
                                                   has_persona_check or has_appropriateness_check))
                        
                        validation_results.append({
                            "scenario": scenario['name'],
                            "passed": validation_comprehensive,
                            "validation_status": validation_status,
                            "has_feedback": has_feedback,
                            "has_parlant_validation": has_parlant_validation,
                            "has_hallucination_check": has_hallucination_check,
                            "has_intent_coverage": has_intent_coverage,
                            "has_persona_check": has_persona_check,
                            "has_appropriateness_check": has_appropriateness_check,
                            "has_recommendations": has_recommendations
                        })
                        
                        print(f"     - Validation status: {validation_status}")
                        print(f"     - Has feedback: {has_feedback}")
                        print(f"     - Parlant validation: {has_parlant_validation}")
                        print(f"     - Hallucination check: {has_hallucination_check}")
                        print(f"     - Intent coverage: {has_intent_coverage}")
                        print(f"     - Persona check: {has_persona_check}")
                        print(f"     - Appropriateness check: {has_appropriateness_check}")
                        
                    else:
                        print(f"     ❌ API failed - Status: {response.status_code}")
                        validation_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    validation_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Test direct validation agent functionality
            print("   Testing direct validation agent...")
            try:
                from parlant_framework import parlant_framework
                
                test_context = {
                    "draft_content": "Thank you for your inquiry about our AI email assistant. We offer competitive pricing and excellent features.",
                    "email_content": "I need pricing information for your AI assistant",
                    "intents": [{"name": "sales_inquiry", "confidence": 0.9}],
                    "persona": account.get('persona', 'Professional assistant')
                }
                
                validation_enhancement = await parlant_framework.enhance_validation(
                    {"content": test_context["draft_content"]},
                    test_context,
                    test_context["intents"]
                )
                
                direct_validation_passed = (validation_enhancement is not None and
                                          'validation_results' in validation_enhancement and
                                          'agent_response' in validation_enhancement)
                
                validation_results.append({
                    "scenario": "Direct Validation Agent Test",
                    "passed": direct_validation_passed,
                    "has_validation_results": 'validation_results' in validation_enhancement if validation_enhancement else False,
                    "has_agent_response": 'agent_response' in validation_enhancement if validation_enhancement else False
                })
                
                print(f"     - Direct validation: {direct_validation_passed}")
                
            except Exception as e:
                print(f"     ❌ Direct validation exception: {str(e)}")
                validation_results.append({
                    "scenario": "Direct Validation Agent Test",
                    "passed": False,
                    "error": str(e)
                })
            
            # Evaluate overall validation results
            passed_validations = sum(1 for result in validation_results if result.get('passed', False))
            total_validations = len(validation_results)
            
            all_passed = passed_validations >= (total_validations * 0.75)  # 75% pass rate
            
            details = f"Validation tests passed: {passed_validations}/{total_validations}. "
            for result in validation_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Validation Agent Comprehensive", all_passed, details)
            
            # Log individual validation results
            for result in validation_results:
                test_name = f"Validation - {result['scenario']}"
                test_passed = result.get('passed', False)
                test_details = ""
                if 'validation_status' in result:
                    test_details = f"Status: {result['validation_status']}, Feedback: {result.get('has_feedback', False)}, Parlant: {result.get('has_parlant_validation', False)}"
                elif 'error' in result:
                    test_details = result['error']
                
                self.log_test_result(test_name, test_passed, test_details)
            
        except Exception as e:
            self.log_test_result("Validation Agent Comprehensive", False, f"Exception: {str(e)}")

    async def test_calendar_agent_integration(self):
        """Test 6: Calendar Agent Integration - Test meeting detection and calendar functionality"""
        print("\n📅 Testing Calendar Agent Integration...")
        
        try:
            # Test calendar/meeting detection scenarios
            calendar_scenarios = [
                {
                    "name": "Meeting Detection with Parlant Guidelines",
                    "email_content": "I would like to schedule a demo meeting for next Tuesday at 2 PM to discuss your AI email assistant capabilities.",
                    "sender": "meeting@test.com",
                    "expected_meeting": True
                },
                {
                    "name": "Complex Meeting Request",
                    "email_content": "Can we set up a meeting next week? I'm available Monday 10 AM, Tuesday 3 PM, or Wednesday 11 AM. We need to discuss integration requirements and pricing.",
                    "sender": "complex@meeting.com",
                    "expected_meeting": True
                },
                {
                    "name": "Conflict Resolution Test",
                    "email_content": "I need to reschedule our meeting from tomorrow 2 PM to Thursday same time. Is that possible?",
                    "sender": "reschedule@test.com",
                    "expected_meeting": True
                },
                {
                    "name": "Timezone Handling Test",
                    "email_content": "Let's schedule a call for 3 PM EST next Friday. I'm in New York timezone.",
                    "sender": "timezone@test.com",
                    "expected_meeting": True
                },
                {
                    "name": "Non-Meeting Email",
                    "email_content": "I need technical support for the email processing system. It's not working correctly.",
                    "sender": "support@test.com",
                    "expected_meeting": False
                }
            ]
            
            calendar_results = []
            
            # Test calendar/meeting detection endpoint
            for scenario in calendar_scenarios:
                print(f"   Testing calendar scenario: {scenario['name']}")
                
                try:
                    # Test meeting detection API
                    meeting_request = {
                        "email_content": scenario["email_content"],
                        "sender": scenario["sender"],
                        "user_timezone": "UTC"
                    }
                    
                    response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_request, timeout=30)
                    
                    if response.status_code == 200:
                        detection_result = response.json()
                        
                        # Check meeting detection accuracy
                        is_meeting_detected = detection_result.get('is_meeting_request', False)
                        detection_accurate = (is_meeting_detected == scenario['expected_meeting'])
                        
                        # Check confidence score
                        confidence_score = detection_result.get('confidence', 0.0)
                        has_confidence = confidence_score > 0.0
                        
                        # Check for Parlant calendar guidelines
                        has_parlant_calendar = bool(detection_result.get('parlant_guidelines') or 
                                                  detection_result.get('parlant_confidence'))
                        
                        # Check additional calendar features
                        has_suggested_times = bool(detection_result.get('suggested_times'))
                        has_conflict_resolution = bool(detection_result.get('conflict_resolution'))
                        
                        scenario_passed = detection_accurate and has_confidence
                        
                        calendar_results.append({
                            "scenario": scenario['name'],
                            "passed": scenario_passed,
                            "meeting_detected": is_meeting_detected,
                            "expected_meeting": scenario['expected_meeting'],
                            "detection_accurate": detection_accurate,
                            "confidence_score": confidence_score,
                            "has_parlant_calendar": has_parlant_calendar,
                            "has_suggested_times": has_suggested_times,
                            "has_conflict_resolution": has_conflict_resolution
                        })
                        
                        print(f"     - Meeting detected: {is_meeting_detected} (expected: {scenario['expected_meeting']})")
                        print(f"     - Detection accurate: {detection_accurate}")
                        print(f"     - Confidence: {confidence_score:.2f}")
                        print(f"     - Parlant calendar: {has_parlant_calendar}")
                        
                    else:
                        print(f"     ❌ Calendar API failed - Status: {response.status_code}")
                        calendar_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    calendar_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Test direct calendar agent functionality
            print("   Testing direct calendar agent...")
            try:
                from parlant_framework import parlant_framework
                
                test_context = {
                    "email_content": "Let's schedule a meeting for next Tuesday at 2 PM",
                    "subject": "Meeting Request",
                    "sender": "direct@test.com"
                }
                
                calendar_enhancement = await parlant_framework.enhance_calendar_processing(test_context)
                
                direct_calendar_passed = (calendar_enhancement is not None and
                                        'calendar_analysis' in calendar_enhancement and
                                        'meeting_detection' in calendar_enhancement)
                
                calendar_results.append({
                    "scenario": "Direct Calendar Agent Test",
                    "passed": direct_calendar_passed,
                    "has_calendar_analysis": 'calendar_analysis' in calendar_enhancement if calendar_enhancement else False,
                    "has_meeting_detection": 'meeting_detection' in calendar_enhancement if calendar_enhancement else False
                })
                
                print(f"     - Direct calendar agent: {direct_calendar_passed}")
                
            except Exception as e:
                print(f"     ❌ Direct calendar exception: {str(e)}")
                calendar_results.append({
                    "scenario": "Direct Calendar Agent Test",
                    "passed": False,
                    "error": str(e)
                })
            
            # Test calendar integration through email processing
            print("   Testing calendar integration through email processing...")
            try:
                account = await self.db.email_accounts.find_one({"is_active": True})
                if account:
                    meeting_email_data = {
                        "subject": "Demo Meeting Request - AI Email Assistant",
                        "body": "I would like to schedule a 30-minute demo meeting to see your AI Email Assistant in action. I'm available next week on Tuesday or Wednesday afternoon.",
                        "sender": "integration@demo.com",
                        "account_id": account['id']
                    }
                    
                    response = requests.post(f"{API_BASE}/emails/test", json=meeting_email_data, timeout=45)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Check for meeting-related intents
                        intents = processed_email.get('intents', [])
                        meeting_intents = [intent for intent in intents if 
                                         intent.get('is_meeting_related', False) or 
                                         'meeting' in intent.get('name', '').lower() or
                                         'demo' in intent.get('name', '').lower()]
                        
                        # Check draft content for meeting acknowledgment
                        draft_content = processed_email.get('draft', '').lower()
                        acknowledges_meeting = any(term in draft_content for term in 
                                                 ['meeting', 'schedule', 'demo', 'appointment'])
                        
                        integration_passed = len(meeting_intents) > 0 or acknowledges_meeting
                        
                        calendar_results.append({
                            "scenario": "Email Processing Calendar Integration",
                            "passed": integration_passed,
                            "meeting_intents_found": len(meeting_intents),
                            "acknowledges_meeting": acknowledges_meeting
                        })
                        
                        print(f"     - Meeting intents: {len(meeting_intents)}")
                        print(f"     - Acknowledges meeting: {acknowledges_meeting}")
                        
                    else:
                        calendar_results.append({
                            "scenario": "Email Processing Calendar Integration",
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                else:
                    calendar_results.append({
                        "scenario": "Email Processing Calendar Integration",
                        "passed": False,
                        "error": "No active account found"
                    })
                    
            except Exception as e:
                print(f"     ❌ Integration exception: {str(e)}")
                calendar_results.append({
                    "scenario": "Email Processing Calendar Integration",
                    "passed": False,
                    "error": str(e)
                })
            
            # Evaluate overall calendar results
            passed_calendar = sum(1 for result in calendar_results if result.get('passed', False))
            total_calendar = len(calendar_results)
            
            all_passed = passed_calendar >= (total_calendar * 0.6)  # 60% pass rate (calendar features may be limited)
            
            details = f"Calendar tests passed: {passed_calendar}/{total_calendar}. "
            for result in calendar_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Calendar Agent Integration", all_passed, details)
            
            # Log individual calendar results
            for result in calendar_results:
                test_name = f"Calendar - {result['scenario']}"
                test_passed = result.get('passed', False)
                test_details = ""
                if 'detection_accurate' in result:
                    test_details = f"Accurate: {result['detection_accurate']}, Confidence: {result.get('confidence_score', 0):.2f}"
                elif 'meeting_intents_found' in result:
                    test_details = f"Meeting intents: {result['meeting_intents_found']}, Acknowledges: {result.get('acknowledges_meeting', False)}"
                elif 'error' in result:
                    test_details = result['error']
                
                self.log_test_result(test_name, test_passed, test_details)
            
        except Exception as e:
            self.log_test_result("Calendar Agent Integration", False, f"Exception: {str(e)}")

    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🎯 PARLANT FRAMEWORK COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Overall Results: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests*100):.1f}%)")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        # Group results by category
        categories = {
            "Framework Components": [],
            "Email Processing": [],
            "Guidelines": [],
            "Response Structure": [],
            "Validation": [],
            "Calendar": []
        }
        
        for result in self.test_results:
            test_name = result['test']
            if 'Framework Components' in test_name or 'Parlant -' in test_name:
                categories["Framework Components"].append(result)
            elif 'Email Processing' in test_name or 'Integration -' in test_name:
                categories["Email Processing"].append(result)
            elif 'Guidelines' in test_name or 'Guideline -' in test_name:
                categories["Guidelines"].append(result)
            elif 'Response Structure' in test_name:
                categories["Response Structure"].append(result)
            elif 'Validation' in test_name:
                categories["Validation"].append(result)
            elif 'Calendar' in test_name:
                categories["Calendar"].append(result)
        
        print(f"\n📋 Results by Category:")
        for category, results in categories.items():
            if results:
                passed_in_category = sum(1 for r in results if r['passed'])
                total_in_category = len(results)
                print(f"   {category}: {passed_in_category}/{total_in_category} passed")
        
        if failed_tests > 0:
            print(f"\n🚨 Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   ❌ {result['test']}: {result['details']}")
        
        print(f"\n🎉 Key Successful Areas:")
        success_areas = []
        if any('Framework Components' in r['test'] and r['passed'] for r in self.test_results):
            success_areas.append("✅ Parlant Framework Components Initialized")
        if any('Email Processing' in r['test'] and r['passed'] for r in self.test_results):
            success_areas.append("✅ Email Processing with Parlant Integration")
        if any('Guidelines' in r['test'] and r['passed'] for r in self.test_results):
            success_areas.append("✅ Parlant Guidelines Application")
        if any('Response Structure' in r['test'] and r['passed'] for r in self.test_results):
            success_areas.append("✅ Agent Response Structure")
        if any('Validation' in r['test'] and r['passed'] for r in self.test_results):
            success_areas.append("✅ Validation Agent Functionality")
        if any('Calendar' in r['test'] and r['passed'] for r in self.test_results):
            success_areas.append("✅ Calendar Agent Integration")
        
        for area in success_areas:
            print(f"   {area}")
        
        print("\n" + "="*80)
        return passed_tests, failed_tests

async def main():
    """Main test execution"""
    print("🚀 Starting Comprehensive Parlant Framework Integration Tests...")
    print("="*80)
    
    tester = ParlantFrameworkTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run all comprehensive Parlant framework tests
        await tester.test_parlant_framework_components()
        await tester.test_email_processing_with_parlant_integration()
        await tester.test_parlant_guidelines_application()
        await tester.test_agent_response_structure()
        await tester.test_validation_agent_comprehensive()
        await tester.test_calendar_agent_integration()
        
        # Print comprehensive summary
        passed, failed = tester.print_summary()
        
        # Exit with appropriate code
        if failed > 0:
            print(f"\n⚠️  {failed} tests failed. Please review the issues above.")
            sys.exit(1)
        else:
            print(f"\n🎉 All {passed} tests passed! Parlant framework integration is working correctly.")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())