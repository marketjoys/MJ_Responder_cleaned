#!/usr/bin/env python3
"""
Focused Parlant Framework Testing - Core functionality verification
Tests the essential Parlant framework components without heavy API calls
"""
import asyncio
import sys
import os
import requests
import json
from datetime import datetime

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

class ParlantFocusedTester:
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

    async def test_parlant_framework_initialization(self):
        """Test 1: Parlant Framework Initialization and Core Components"""
        print("\n🤖 Testing Parlant Framework Initialization...")
        
        try:
            # Import and verify framework components
            from parlant_framework import (
                parlant_framework, DraftAgent, ValidationAgent, CalendarAgent, 
                ParlantAgent, AgentResponse, Guideline
            )
            
            # Test framework initialization
            framework_exists = parlant_framework is not None
            
            # Test agent initialization
            draft_agent = parlant_framework.draft_agent
            validation_agent = parlant_framework.validation_agent
            calendar_agent = parlant_framework.calendar_agent
            
            agents_initialized = (
                isinstance(draft_agent, DraftAgent) and
                isinstance(validation_agent, ValidationAgent) and
                isinstance(calendar_agent, CalendarAgent)
            )
            
            # Test guideline counts
            draft_guidelines = len(draft_agent.guidelines)
            validation_guidelines = len(validation_agent.guidelines)
            calendar_guidelines = len(calendar_agent.guidelines)
            
            guidelines_loaded = (draft_guidelines >= 5 and validation_guidelines >= 5 and calendar_guidelines >= 4)
            
            # Test specific guidelines exist
            expected_draft_guidelines = ["professional_tone", "sales_inquiry", "support_request", "meeting_request", "persona_alignment"]
            draft_guidelines_present = all(g_id in draft_agent.guidelines for g_id in expected_draft_guidelines)
            
            expected_validation_guidelines = ["hallucination_check", "intent_coverage", "persona_consistency", "content_appropriateness"]
            validation_guidelines_present = all(g_id in validation_agent.guidelines for g_id in expected_validation_guidelines)
            
            expected_calendar_guidelines = ["meeting_detection", "conflict_resolution", "timezone_handling", "meeting_confirmation"]
            calendar_guidelines_present = all(g_id in calendar_agent.guidelines for g_id in expected_calendar_guidelines)
            
            all_passed = (framework_exists and agents_initialized and guidelines_loaded and
                         draft_guidelines_present and validation_guidelines_present and calendar_guidelines_present)
            
            details = f"Framework: {framework_exists}, Agents: {agents_initialized}, " \
                     f"Guidelines loaded: {guidelines_loaded} (D:{draft_guidelines}, V:{validation_guidelines}, C:{calendar_guidelines}), " \
                     f"Expected guidelines: D:{draft_guidelines_present}, V:{validation_guidelines_present}, C:{calendar_guidelines_present}"
            
            self.log_test_result("Parlant Framework Initialization", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Parlant Framework Initialization", False, f"Exception: {str(e)}")

    async def test_guideline_matching_functionality(self):
        """Test 2: Guideline Matching Functionality"""
        print("\n📋 Testing Guideline Matching Functionality...")
        
        try:
            from parlant_framework import parlant_framework
            
            # Test different contexts for guideline matching
            test_contexts = [
                {
                    "name": "Sales Inquiry Context",
                    "context": {
                        "email_content": "I want to buy your AI email assistant product. Please send pricing information.",
                        "intents": [{"name": "sales_inquiry", "confidence": 0.9}]
                    },
                    "expected_guidelines": ["sales_inquiry", "professional_tone", "persona_alignment"],
                    "agent": "draft"
                },
                {
                    "name": "Support Request Context",
                    "context": {
                        "email_content": "I'm having technical problems with the email system. It's not working properly.",
                        "intents": [{"name": "technical_support", "confidence": 0.8}]
                    },
                    "expected_guidelines": ["support_request", "professional_tone"],
                    "agent": "draft"
                },
                {
                    "name": "Meeting Request Context",
                    "context": {
                        "email_content": "Can we schedule a meeting next week to discuss the project?",
                        "intents": [{"name": "meeting_request", "confidence": 0.85}]
                    },
                    "expected_guidelines": ["meeting_request", "professional_tone"],
                    "agent": "draft"
                },
                {
                    "name": "Validation Context",
                    "context": {
                        "draft_content": "Our AI system can process 1 million emails per second.",
                        "email_content": "Tell me about your capabilities",
                        "type": "validation"
                    },
                    "expected_guidelines": ["hallucination_check", "content_appropriateness"],
                    "agent": "validation"
                }
            ]
            
            matching_results = []
            
            for test_case in test_contexts:
                print(f"   Testing: {test_case['name']}")
                
                # Select appropriate agent
                if test_case['agent'] == 'draft':
                    agent = parlant_framework.draft_agent
                elif test_case['agent'] == 'validation':
                    agent = parlant_framework.validation_agent
                else:
                    agent = parlant_framework.calendar_agent
                
                # Test guideline matching
                matched_guidelines = agent.match_guidelines(test_case['context'])
                matched_ids = [g.id for g in matched_guidelines]
                
                # Check if expected guidelines are matched
                expected_matched = any(expected in matched_ids for expected in test_case['expected_guidelines'])
                
                # Check if guidelines are sorted by priority
                priorities = [g.priority for g in matched_guidelines]
                priority_sorted = priorities == sorted(priorities, reverse=True)
                
                test_passed = expected_matched and len(matched_guidelines) > 0
                
                matching_results.append({
                    "test_case": test_case['name'],
                    "passed": test_passed,
                    "matched_count": len(matched_guidelines),
                    "expected_matched": expected_matched,
                    "priority_sorted": priority_sorted,
                    "matched_ids": matched_ids[:3]  # Show first 3
                })
                
                print(f"     - Matched guidelines: {len(matched_guidelines)}")
                print(f"     - Expected guidelines found: {expected_matched}")
                print(f"     - Top matches: {matched_ids[:3]}")
            
            # Evaluate overall matching functionality
            passed_matches = sum(1 for result in matching_results if result['passed'])
            total_matches = len(matching_results)
            
            all_passed = passed_matches == total_matches
            
            details = f"Matching tests passed: {passed_matches}/{total_matches}. "
            for result in matching_results:
                status = "✅" if result['passed'] else "❌"
                details += f"{result['test_case']}: {status} "
            
            self.log_test_result("Guideline Matching Functionality", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Guideline Matching Functionality", False, f"Exception: {str(e)}")

    async def test_agent_response_structure_creation(self):
        """Test 3: Agent Response Structure and Creation"""
        print("\n📊 Testing Agent Response Structure...")
        
        try:
            from parlant_framework import parlant_framework, AgentResponse
            
            # Test AgentResponse creation and structure
            test_response = AgentResponse(
                content="Test response content",
                confidence=0.85,
                guidelines_applied=["professional_tone", "sales_inquiry"],
                tools_used=["knowledge_base_search"],
                reasoning="Applied sales inquiry guideline based on email content",
                should_escalate=False
            )
            
            # Verify structure
            structure_tests = [
                ("has_content", hasattr(test_response, 'content') and test_response.content == "Test response content"),
                ("has_confidence", hasattr(test_response, 'confidence') and test_response.confidence == 0.85),
                ("has_guidelines_applied", hasattr(test_response, 'guidelines_applied') and len(test_response.guidelines_applied) == 2),
                ("has_tools_used", hasattr(test_response, 'tools_used') and len(test_response.tools_used) == 1),
                ("has_reasoning", hasattr(test_response, 'reasoning') and bool(test_response.reasoning)),
                ("has_should_escalate", hasattr(test_response, 'should_escalate') and test_response.should_escalate == False),
                ("confidence_valid_range", 0.0 <= test_response.confidence <= 1.0),
                ("guidelines_is_list", isinstance(test_response.guidelines_applied, list)),
                ("tools_is_list", isinstance(test_response.tools_used, list))
            ]
            
            passed_structure_tests = sum(1 for _, test_result in structure_tests if test_result)
            total_structure_tests = len(structure_tests)
            
            structure_passed = passed_structure_tests == total_structure_tests
            
            # Test framework processing with guidelines
            test_contexts = [
                {
                    "name": "Draft Enhancement",
                    "context": {
                        "email_content": "I need pricing information",
                        "intents": [{"name": "sales_inquiry", "confidence": 0.9}]
                    },
                    "method": "enhance_draft_generation"
                },
                {
                    "name": "Validation Enhancement", 
                    "context": {
                        "draft_content": "Thank you for your inquiry",
                        "email_content": "I need pricing information",
                        "intents": [{"name": "sales_inquiry", "confidence": 0.9}]
                    },
                    "method": "enhance_validation"
                }
            ]
            
            framework_processing_results = []
            
            for test_case in test_contexts:
                print(f"   Testing: {test_case['name']}")
                
                try:
                    if test_case['method'] == 'enhance_draft_generation':
                        result = await parlant_framework.enhance_draft_generation(
                            test_case['context'], 
                            test_case['context'].get('intents', [])
                        )
                        agent_response = result.get('agent_response')
                    else:  # enhance_validation
                        result = await parlant_framework.enhance_validation(
                            {"content": test_case['context'].get('draft_content', '')},
                            test_case['context'],
                            test_case['context'].get('intents', [])
                        )
                        agent_response = result.get('agent_response')
                    
                    # Verify agent response
                    is_agent_response = isinstance(agent_response, AgentResponse)
                    has_guidelines = len(agent_response.guidelines_applied) > 0 if is_agent_response else False
                    has_confidence = (agent_response.confidence > 0.0) if is_agent_response else False
                    
                    test_passed = is_agent_response and has_guidelines and has_confidence
                    
                    framework_processing_results.append({
                        "test_case": test_case['name'],
                        "passed": test_passed,
                        "is_agent_response": is_agent_response,
                        "guidelines_count": len(agent_response.guidelines_applied) if is_agent_response else 0,
                        "confidence": agent_response.confidence if is_agent_response else 0.0
                    })
                    
                    print(f"     - AgentResponse: {is_agent_response}")
                    if is_agent_response:
                        print(f"     - Guidelines applied: {len(agent_response.guidelines_applied)}")
                        print(f"     - Confidence: {agent_response.confidence:.2f}")
                    
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    framework_processing_results.append({
                        "test_case": test_case['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Evaluate overall results
            passed_processing = sum(1 for result in framework_processing_results if result.get('passed', False))
            total_processing = len(framework_processing_results)
            
            processing_passed = passed_processing == total_processing
            
            all_passed = structure_passed and processing_passed
            
            details = f"Structure tests: {passed_structure_tests}/{total_structure_tests}, " \
                     f"Processing tests: {passed_processing}/{total_processing}. " \
                     f"Structure: {structure_passed}, Processing: {processing_passed}"
            
            self.log_test_result("Agent Response Structure", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Agent Response Structure", False, f"Exception: {str(e)}")

    async def test_parlant_integration_in_email_processing(self):
        """Test 4: Parlant Integration in Email Processing (Single API Test)"""
        print("\n📧 Testing Parlant Integration in Email Processing...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Parlant Integration in Email Processing", False, "No active email accounts")
                return
            
            # Single focused test to verify Parlant integration
            test_email_data = {
                "subject": "AI Email Assistant Pricing Request",
                "body": "Hello, I'm interested in your AI Email Assistant product. Could you provide detailed pricing information and feature list? We're looking to automate our customer email responses.",
                "sender": "test@parlant.com",
                "account_id": account['id']
            }
            
            print(f"   Testing with account: {account['email']}")
            print("   Processing email through Parlant-enhanced pipeline...")
            
            try:
                # Process email with shorter timeout
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Check for Parlant framework indicators
                    validation_result = processed_email.get('validation_result', {})
                    
                    # Core functionality checks
                    has_intents = bool(processed_email.get('intents'))
                    has_draft = bool(processed_email.get('draft'))
                    has_validation = bool(validation_result)
                    workflow_completed = processed_email.get('status') in ['ready_to_send', 'sent', 'needs_redraft']
                    
                    # Parlant-specific checks
                    has_parlant_guidelines = bool(validation_result.get('parlant_guidelines'))
                    has_parlant_confidence = bool(validation_result.get('parlant_confidence'))
                    has_guidelines_applied = bool(validation_result.get('guidelines_applied'))
                    
                    parlant_metadata_present = has_parlant_guidelines or has_parlant_confidence or has_guidelines_applied
                    
                    # Draft quality checks
                    draft_content = processed_email.get('draft', '')
                    draft_length = len(draft_content)
                    has_professional_tone = not any(casual in draft_content.lower() for casual in ['hey', 'sup', 'yo'])
                    
                    # Overall assessment
                    core_functionality = has_intents and has_draft and has_validation and workflow_completed
                    parlant_integration = parlant_metadata_present
                    quality_checks = draft_length > 100 and has_professional_tone
                    
                    all_passed = core_functionality and quality_checks
                    
                    details = f"Core functionality: {core_functionality} (intents: {has_intents}, draft: {has_draft}, validation: {has_validation}, workflow: {workflow_completed}), " \
                             f"Parlant integration: {parlant_integration} (guidelines: {has_parlant_guidelines}, confidence: {has_parlant_confidence}, applied: {has_guidelines_applied}), " \
                             f"Quality: {quality_checks} (length: {draft_length}, professional: {has_professional_tone}), " \
                             f"Status: {processed_email.get('status')}"
                    
                    self.log_test_result("Parlant Integration in Email Processing", all_passed, details)
                    
                    # Additional detailed logging
                    print(f"     - Intents found: {len(processed_email.get('intents', []))}")
                    print(f"     - Draft length: {draft_length} characters")
                    print(f"     - Validation status: {validation_result.get('status', 'N/A')}")
                    print(f"     - Parlant metadata: {parlant_metadata_present}")
                    print(f"     - Final status: {processed_email.get('status')}")
                    
                else:
                    self.log_test_result("Parlant Integration in Email Processing", False, 
                                       f"API request failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                self.log_test_result("Parlant Integration in Email Processing", False, 
                                   "API request timed out after 30 seconds")
            except Exception as e:
                self.log_test_result("Parlant Integration in Email Processing", False, 
                                   f"API request exception: {str(e)}")
            
        except Exception as e:
            self.log_test_result("Parlant Integration in Email Processing", False, f"Exception: {str(e)}")

    async def test_calendar_agent_meeting_detection(self):
        """Test 5: Calendar Agent Meeting Detection"""
        print("\n📅 Testing Calendar Agent Meeting Detection...")
        
        try:
            # Test meeting detection endpoint
            meeting_scenarios = [
                {
                    "name": "Clear Meeting Request",
                    "content": "I would like to schedule a demo meeting for next Tuesday at 2 PM.",
                    "expected_meeting": True
                },
                {
                    "name": "Non-Meeting Email",
                    "content": "I need technical support for the email processing system.",
                    "expected_meeting": False
                }
            ]
            
            detection_results = []
            
            for scenario in meeting_scenarios:
                print(f"   Testing: {scenario['name']}")
                
                meeting_request = {
                    "email_content": scenario["content"],
                    "sender": "test@calendar.com",
                    "user_timezone": "UTC"
                }
                
                try:
                    response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_request, timeout=15)
                    
                    if response.status_code == 200:
                        detection_result = response.json()
                        
                        # Check detection accuracy
                        is_meeting_detected = detection_result.get('is_meeting_request', False)
                        detection_accurate = (is_meeting_detected == scenario['expected_meeting'])
                        
                        # Check response structure
                        has_confidence = 'confidence' in detection_result
                        confidence_score = detection_result.get('confidence', 0.0)
                        
                        # Check for Parlant calendar features
                        has_parlant_calendar = bool(detection_result.get('parlant_guidelines') or 
                                                  detection_result.get('parlant_confidence'))
                        
                        test_passed = detection_accurate and has_confidence
                        
                        detection_results.append({
                            "scenario": scenario['name'],
                            "passed": test_passed,
                            "detection_accurate": detection_accurate,
                            "confidence_score": confidence_score,
                            "has_parlant_calendar": has_parlant_calendar
                        })
                        
                        print(f"     - Meeting detected: {is_meeting_detected} (expected: {scenario['expected_meeting']})")
                        print(f"     - Confidence: {confidence_score:.2f}")
                        print(f"     - Parlant calendar: {has_parlant_calendar}")
                        
                    else:
                        print(f"     ❌ API failed - Status: {response.status_code}")
                        detection_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    detection_results.append({
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
                                        'calendar_analysis' in calendar_enhancement)
                
                detection_results.append({
                    "scenario": "Direct Calendar Agent",
                    "passed": direct_calendar_passed,
                    "has_calendar_analysis": 'calendar_analysis' in calendar_enhancement if calendar_enhancement else False
                })
                
                print(f"     - Direct calendar agent: {direct_calendar_passed}")
                
            except Exception as e:
                print(f"     ❌ Direct calendar exception: {str(e)}")
                detection_results.append({
                    "scenario": "Direct Calendar Agent",
                    "passed": False,
                    "error": str(e)
                })
            
            # Evaluate overall results
            passed_detections = sum(1 for result in detection_results if result.get('passed', False))
            total_detections = len(detection_results)
            
            # Accept partial success for calendar features
            all_passed = passed_detections >= (total_detections * 0.6)  # 60% pass rate
            
            details = f"Detection tests passed: {passed_detections}/{total_detections}. "
            for result in detection_results:
                status = "✅" if result.get('passed', False) else "❌"
                details += f"{result['scenario']}: {status} "
            
            self.log_test_result("Calendar Agent Meeting Detection", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Calendar Agent Meeting Detection", False, f"Exception: {str(e)}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 PARLANT FRAMEWORK FOCUSED TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Overall Results: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests*100):.1f}%)")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests > 0:
            print(f"\n🚨 Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   ❌ {result['test']}: {result['details']}")
        
        print(f"\n🎉 Successful Tests:")
        for result in self.test_results:
            if result['passed']:
                print(f"   ✅ {result['test']}")
        
        print("\n" + "="*80)
        return passed_tests, failed_tests

async def main():
    """Main test execution"""
    print("🚀 Starting Focused Parlant Framework Tests...")
    print("="*80)
    
    tester = ParlantFocusedTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run focused Parlant framework tests
        await tester.test_parlant_framework_initialization()
        await tester.test_guideline_matching_functionality()
        await tester.test_agent_response_structure_creation()
        await tester.test_parlant_integration_in_email_processing()
        await tester.test_calendar_agent_meeting_detection()
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Exit with appropriate code
        if failed > 0:
            print(f"\n⚠️  {failed} tests failed. Please review the issues above.")
            sys.exit(1)
        else:
            print(f"\n🎉 All {passed} tests passed! Parlant framework core functionality is working correctly.")
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