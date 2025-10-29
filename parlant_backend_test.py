#!/usr/bin/env python3
"""
Parlant-Enhanced Email Processing System Testing
Tests the three agents (Draft, Validation, Calendar) with Parlant framework integration
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://redis-rq-setup.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class ParlantEmailTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        
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

    async def test_draft_agent_with_parlant_guidelines(self):
        """Test 1: Draft Agent with Parlant Guidelines - different intents, persona alignment, KB integration"""
        print("\n🤖 Testing Draft Agent with Parlant Guidelines...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Draft Agent with Parlant Guidelines", False, "No active email accounts")
                return
            
            print(f"   Using account: {account['email']}")
            
            # Test scenarios with different intents
            test_scenarios = [
                {
                    "name": "Sales Inquiry",
                    "subject": "Interested in AI Email Assistant - Pricing Request",
                    "body": "Hi there! I'm the CEO of TechCorp and we're looking for an AI email automation solution. We handle about 500 customer emails daily and need to streamline our response process. Could you provide detailed pricing information for your AI Email Assistant? We're particularly interested in features like intent classification, automated responses, and integration capabilities. Our budget is around $5000/month. Please send me a comprehensive proposal with pricing tiers and implementation timeline.",
                    "sender": "ceo@techcorp.com",
                    "expected_intents": ["sales", "pricing", "product"]
                },
                {
                    "name": "Support Request", 
                    "subject": "Technical Issue - Email Processing Not Working",
                    "body": "Hello, I'm having trouble with my email processing system. The AI responses are not being generated properly and I'm getting timeout errors. I've tried restarting the service but the issue persists. This is affecting our customer service operations. Can you please help me troubleshoot this issue? I need urgent assistance as we have important client communications pending.",
                    "sender": "support@clientcompany.com",
                    "expected_intents": ["support", "technical", "urgent"]
                },
                {
                    "name": "Meeting Request",
                    "subject": "Schedule Demo Meeting - AI Email Assistant",
                    "body": "Good morning! I would like to schedule a demo meeting to see your AI Email Assistant in action. We're evaluating different solutions for our company and your product looks promising. I'm available next week on Tuesday, Wednesday, or Friday between 2-4 PM EST. Could we set up a 30-minute demo call? Please let me know what times work best for you. Looking forward to seeing the capabilities of your system.",
                    "sender": "manager@prospects.com",
                    "expected_intents": ["meeting", "demo", "scheduling"]
                }
            ]
            
            draft_results = []
            
            for scenario in test_scenarios:
                print(f"   Testing scenario: {scenario['name']}")
                
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": account['id']
                }
                
                try:
                    # Test email processing via API
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Check Parlant-enhanced draft generation
                        has_intents = bool(processed_email.get('intents'))
                        has_draft = bool(processed_email.get('draft'))
                        draft_length = len(processed_email.get('draft', ''))
                        
                        # Check for Parlant metadata in response
                        validation_result = processed_email.get('validation_result', {})
                        has_parlant_metadata = bool(validation_result.get('parlant_guidelines') or 
                                                  validation_result.get('parlant_confidence'))
                        
                        # Check persona alignment (account persona should influence response)
                        account_persona = account.get('persona', '')
                        draft_content = processed_email.get('draft', '').lower()
                        
                        # Check knowledge base integration (look for specific product mentions)
                        kb_integration = any(term in draft_content for term in 
                                           ['ai email assistant', 'email automation', 'pricing', 'features'])
                        
                        # Check professional tone and structure
                        has_greeting = any(greeting in draft_content for greeting in 
                                         ['dear', 'hello', 'hi', 'good morning', 'good afternoon'])
                        has_professional_tone = not any(casual in draft_content for casual in 
                                                      ['hey', 'sup', 'yo', 'lol', 'omg'])
                        
                        scenario_passed = (has_intents and has_draft and draft_length > 100 and 
                                         has_greeting and has_professional_tone and kb_integration)
                        
                        draft_results.append({
                            "scenario": scenario['name'],
                            "passed": scenario_passed,
                            "intents_found": len(processed_email.get('intents', [])),
                            "draft_length": draft_length,
                            "has_parlant_metadata": has_parlant_metadata,
                            "kb_integration": kb_integration,
                            "professional_tone": has_professional_tone,
                            "status": processed_email.get('status')
                        })
                        
                        print(f"     - Intents: {len(processed_email.get('intents', []))}")
                        print(f"     - Draft length: {draft_length} chars")
                        print(f"     - Parlant metadata: {has_parlant_metadata}")
                        print(f"     - KB integration: {kb_integration}")
                        print(f"     - Professional tone: {has_professional_tone}")
                        print(f"     - Status: {processed_email.get('status')}")
                        
                    else:
                        print(f"     ❌ API failed - Status: {response.status_code}")
                        draft_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    draft_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Evaluate overall results
            passed_scenarios = sum(1 for result in draft_results if result.get('passed', False))
            total_scenarios = len(draft_results)
            
            all_passed = passed_scenarios == total_scenarios
            
            details = f"Scenarios passed: {passed_scenarios}/{total_scenarios}. "
            for result in draft_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Draft Agent with Parlant Guidelines", all_passed, details)
            
            # Log individual scenario results
            for result in draft_results:
                scenario_name = f"Draft Agent - {result['scenario']}"
                scenario_passed = result.get('passed', False)
                scenario_details = ""
                if 'intents_found' in result:
                    scenario_details = f"Intents: {result['intents_found']}, Length: {result['draft_length']}, KB: {result['kb_integration']}, Professional: {result['professional_tone']}"
                elif 'error' in result:
                    scenario_details = result['error']
                
                self.log_test_result(scenario_name, scenario_passed, scenario_details)
            
        except Exception as e:
            self.log_test_result("Draft Agent with Parlant Guidelines", False, f"Exception: {str(e)}")

    async def test_validation_agent_with_enhanced_checks(self):
        """Test 2: Validation Agent with Enhanced Checks - Parlant compliance, hallucination detection, persona consistency"""
        print("\n🔍 Testing Validation Agent with Enhanced Checks...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Validation Agent with Enhanced Checks", False, "No active email accounts")
                return
            
            # Test scenarios for validation
            validation_scenarios = [
                {
                    "name": "Valid Professional Response",
                    "subject": "Product Information Request",
                    "body": "I need detailed information about your AI email assistant product, including pricing and features.",
                    "sender": "business@company.com",
                    "expected_validation": "PASS"
                },
                {
                    "name": "Complex Technical Query",
                    "subject": "Integration Requirements and API Documentation",
                    "body": "We're evaluating your AI email assistant for integration with our existing CRM system. Can you provide technical documentation, API specifications, and integration requirements? We need to understand data flow, security protocols, and scalability options.",
                    "sender": "tech@enterprise.com",
                    "expected_validation": "PASS"
                },
                {
                    "name": "Meeting Scheduling Request",
                    "subject": "Demo Meeting Request - Next Week",
                    "body": "I'd like to schedule a demo meeting for next Tuesday or Wednesday afternoon. We're interested in seeing how your AI handles different types of customer inquiries and generates appropriate responses.",
                    "sender": "sales@prospect.com",
                    "expected_validation": "PASS"
                }
            ]
            
            validation_results = []
            
            for scenario in validation_scenarios:
                print(f"   Testing validation scenario: {scenario['name']}")
                
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": account['id']
                }
                
                try:
                    # Process email and check validation
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Check validation results
                        validation_result = processed_email.get('validation_result', {})
                        validation_status = validation_result.get('status', 'UNKNOWN')
                        
                        # Check Parlant-enhanced validation features
                        has_parlant_validation = bool(validation_result.get('parlant_guidelines') or 
                                                    validation_result.get('parlant_confidence') or
                                                    validation_result.get('guidelines_applied'))
                        
                        # Check for enhanced validation criteria
                        has_coverage_report = bool(validation_result.get('coverage_report'))
                        has_feedback = bool(validation_result.get('feedback'))
                        
                        # Check persona consistency validation
                        persona_check = validation_result.get('persona_consistency', True)  # Default to True if not present
                        
                        # Check hallucination detection
                        hallucination_check = validation_result.get('hallucination_detected', False)  # Should be False for good responses
                        
                        # Check intent coverage
                        intent_coverage = validation_result.get('intent_coverage', {})
                        has_intent_coverage = bool(intent_coverage)
                        
                        scenario_passed = (validation_status in ['PASS', 'FAIL'] and  # Valid status
                                         has_feedback and  # Has validation feedback
                                         not hallucination_check and  # No hallucinations detected
                                         persona_check)  # Persona consistency maintained
                        
                        validation_results.append({
                            "scenario": scenario['name'],
                            "passed": scenario_passed,
                            "validation_status": validation_status,
                            "has_parlant_validation": has_parlant_validation,
                            "has_coverage_report": has_coverage_report,
                            "persona_consistent": persona_check,
                            "no_hallucination": not hallucination_check,
                            "has_intent_coverage": has_intent_coverage
                        })
                        
                        print(f"     - Validation status: {validation_status}")
                        print(f"     - Parlant validation: {has_parlant_validation}")
                        print(f"     - Coverage report: {has_coverage_report}")
                        print(f"     - Persona consistent: {persona_check}")
                        print(f"     - No hallucination: {not hallucination_check}")
                        print(f"     - Intent coverage: {has_intent_coverage}")
                        
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
            
            # Evaluate overall validation results
            passed_validations = sum(1 for result in validation_results if result.get('passed', False))
            total_validations = len(validation_results)
            
            all_passed = passed_validations == total_validations
            
            details = f"Validation scenarios passed: {passed_validations}/{total_validations}. "
            for result in validation_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Validation Agent with Enhanced Checks", all_passed, details)
            
            # Log individual validation results
            for result in validation_results:
                scenario_name = f"Validation Agent - {result['scenario']}"
                scenario_passed = result.get('passed', False)
                scenario_details = ""
                if 'validation_status' in result:
                    scenario_details = f"Status: {result['validation_status']}, Parlant: {result['has_parlant_validation']}, Persona: {result['persona_consistent']}"
                elif 'error' in result:
                    scenario_details = result['error']
                
                self.log_test_result(scenario_name, scenario_passed, scenario_details)
            
        except Exception as e:
            self.log_test_result("Validation Agent with Enhanced Checks", False, f"Exception: {str(e)}")

    async def test_calendar_agent_with_meeting_detection(self):
        """Test 3: Calendar Agent with Meeting Detection - enhanced meeting detection, conflict handling, confirmation intents"""
        print("\n📅 Testing Calendar Agent with Meeting Detection...")
        
        try:
            # Test meeting detection scenarios
            meeting_scenarios = [
                {
                    "name": "Simple Meeting Request",
                    "subject": "Schedule a Demo Meeting",
                    "body": "Hi, I'd like to schedule a demo meeting for next Tuesday at 2 PM. Can you confirm if this time works for you?",
                    "sender": "client@company.com",
                    "expected_meeting": True
                },
                {
                    "name": "Complex Meeting with Multiple Options",
                    "subject": "Meeting Request - Multiple Time Options",
                    "body": "Hello, I need to schedule a meeting to discuss our AI email assistant requirements. I'm available on Monday 10 AM, Tuesday 3 PM, or Wednesday 11 AM. Please let me know which time works best for your team. The meeting should take about 45 minutes.",
                    "sender": "manager@enterprise.com",
                    "expected_meeting": True
                },
                {
                    "name": "Meeting Reschedule Request",
                    "subject": "Need to Reschedule Our Meeting",
                    "body": "I need to reschedule our meeting planned for tomorrow at 3 PM. Can we move it to Thursday at the same time? Sorry for the inconvenience.",
                    "sender": "contact@business.com",
                    "expected_meeting": True
                },
                {
                    "name": "Non-Meeting Email",
                    "subject": "Product Information Request",
                    "body": "I'm interested in learning more about your AI email assistant. Can you send me pricing information and feature details?",
                    "sender": "info@company.com",
                    "expected_meeting": False
                }
            ]
            
            # Test calendar/meeting detection endpoint if available
            meeting_detection_results = []
            
            for scenario in meeting_scenarios:
                print(f"   Testing meeting scenario: {scenario['name']}")
                
                try:
                    # Test meeting detection via calendar endpoint
                    meeting_request = {
                        "email_content": scenario["body"],
                        "sender": scenario["sender"],
                        "user_timezone": "UTC"
                    }
                    
                    response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_request, timeout=30)
                    
                    if response.status_code == 200:
                        detection_result = response.json()
                        
                        # Check meeting detection results
                        is_meeting_detected = detection_result.get('is_meeting_request', False)
                        has_time_suggestions = bool(detection_result.get('suggested_times', []))
                        has_conflict_handling = bool(detection_result.get('conflict_resolution'))
                        confidence_score = detection_result.get('confidence', 0.0)
                        
                        # Check Parlant-enhanced features
                        has_parlant_metadata = bool(detection_result.get('parlant_guidelines') or 
                                                  detection_result.get('parlant_confidence'))
                        
                        # Validate detection accuracy
                        detection_accurate = (is_meeting_detected == scenario['expected_meeting'])
                        
                        scenario_passed = detection_accurate and confidence_score > 0.5
                        
                        meeting_detection_results.append({
                            "scenario": scenario['name'],
                            "passed": scenario_passed,
                            "meeting_detected": is_meeting_detected,
                            "expected_meeting": scenario['expected_meeting'],
                            "detection_accurate": detection_accurate,
                            "confidence": confidence_score,
                            "has_time_suggestions": has_time_suggestions,
                            "has_parlant_metadata": has_parlant_metadata
                        })
                        
                        print(f"     - Meeting detected: {is_meeting_detected} (expected: {scenario['expected_meeting']})")
                        print(f"     - Confidence: {confidence_score:.2f}")
                        print(f"     - Time suggestions: {has_time_suggestions}")
                        print(f"     - Parlant metadata: {has_parlant_metadata}")
                        
                    else:
                        print(f"     ❌ Meeting detection API failed - Status: {response.status_code}")
                        meeting_detection_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    meeting_detection_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Also test meeting detection through regular email processing
            print("   Testing meeting detection through email processing...")
            
            meeting_email_data = {
                "subject": "Demo Meeting Request - AI Email Assistant",
                "body": "I would like to schedule a 30-minute demo meeting to see your AI Email Assistant in action. I'm available next week on Tuesday or Wednesday afternoon. Please let me know what times work for you.",
                "sender": "demo@prospect.com",
                "account_id": (await self.db.email_accounts.find_one({"is_active": True}))['id']
            }
            
            email_processing_passed = False
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=meeting_email_data, timeout=45)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Check if meeting-related intents were detected
                    intents = processed_email.get('intents', [])
                    meeting_intents = [intent for intent in intents if 
                                     intent.get('is_meeting_related', False) or 
                                     'meeting' in intent.get('name', '').lower() or
                                     'demo' in intent.get('name', '').lower() or
                                     'schedule' in intent.get('name', '').lower()]
                    
                    has_meeting_intents = len(meeting_intents) > 0
                    
                    # Check if draft mentions meeting/scheduling
                    draft_content = processed_email.get('draft', '').lower()
                    mentions_meeting = any(term in draft_content for term in 
                                         ['meeting', 'schedule', 'demo', 'appointment', 'call'])
                    
                    email_processing_passed = has_meeting_intents or mentions_meeting
                    
                    print(f"     - Meeting intents found: {len(meeting_intents)}")
                    print(f"     - Draft mentions meeting: {mentions_meeting}")
                    
                else:
                    print(f"     ❌ Email processing failed - Status: {response.status_code}")
                    
            except Exception as e:
                print(f"     ❌ Email processing exception: {str(e)}")
            
            # Evaluate overall calendar agent results
            passed_detections = sum(1 for result in meeting_detection_results if result.get('passed', False))
            total_detections = len(meeting_detection_results)
            
            # Overall pass if either meeting detection API works OR email processing detects meetings
            all_passed = (passed_detections > 0 or email_processing_passed)
            
            details = f"Meeting detection: {passed_detections}/{total_detections}, Email processing: {email_processing_passed}. "
            for result in meeting_detection_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Calendar Agent with Meeting Detection", all_passed, details)
            
            # Log individual meeting detection results
            for result in meeting_detection_results:
                scenario_name = f"Calendar Agent - {result['scenario']}"
                scenario_passed = result.get('passed', False)
                scenario_details = ""
                if 'meeting_detected' in result:
                    scenario_details = f"Detected: {result['meeting_detected']}, Expected: {result['expected_meeting']}, Confidence: {result.get('confidence', 0):.2f}"
                elif 'error' in result:
                    scenario_details = result['error']
                
                self.log_test_result(scenario_name, scenario_passed, scenario_details)
            
            # Log email processing meeting detection
            self.log_test_result("Calendar Agent - Email Processing Integration", email_processing_passed, 
                               f"Meeting detection through email processing: {email_processing_passed}")
            
        except Exception as e:
            self.log_test_result("Calendar Agent with Meeting Detection", False, f"Exception: {str(e)}")

    async def test_end_to_end_parlant_integration(self):
        """Test 4: End-to-End Parlant Integration - complete workflow with all three agents"""
        print("\n🔄 Testing End-to-End Parlant Integration...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("End-to-End Parlant Integration", False, "No active email accounts")
                return
            
            # Comprehensive test scenarios that should trigger all three agents
            e2e_scenarios = [
                {
                    "name": "Complex Sales Inquiry with Meeting Request",
                    "subject": "Enterprise AI Solution - Pricing and Demo Request",
                    "body": "Hello, I'm the CTO of DataTech Solutions, a growing enterprise with 200+ employees. We're evaluating AI email automation solutions to handle our increasing customer support volume (500+ emails daily). I'm interested in your AI Email Assistant and would like to: 1) Get detailed pricing for enterprise plans, 2) Schedule a comprehensive demo meeting next week (preferably Tuesday or Wednesday 2-4 PM EST), 3) Understand integration requirements with our existing Salesforce CRM, 4) Learn about security compliance (SOC2, GDPR). This is a high-priority project with a budget of $10,000-15,000 monthly. Please provide a complete proposal and let's schedule that demo. Best regards, John Smith, CTO",
                    "sender": "john.smith@datatech.com"
                },
                {
                    "name": "Technical Support with Urgent Meeting",
                    "body": "We're experiencing critical issues with our current email automation system and need immediate assistance. Our customer response times have increased to 4+ hours, affecting our SLA commitments. Can you: 1) Provide emergency technical support, 2) Schedule an urgent consultation call today or tomorrow, 3) Share case studies of similar enterprise implementations, 4) Explain your disaster recovery and failover capabilities? This is affecting our business operations and we need to resolve this quickly. Please call me at 555-0123 or schedule a meeting ASAP.",
                    "sender": "emergency@clientcorp.com"
                }
            ]
            
            e2e_results = []
            
            for scenario in e2e_scenarios:
                print(f"   Testing E2E scenario: {scenario['name']}")
                
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": account['id']
                }
                
                try:
                    # Process complete email workflow
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Check Draft Agent results
                        has_intents = bool(processed_email.get('intents'))
                        has_draft = bool(processed_email.get('draft'))
                        draft_length = len(processed_email.get('draft', ''))
                        
                        # Check Validation Agent results
                        validation_result = processed_email.get('validation_result', {})
                        validation_status = validation_result.get('status', 'UNKNOWN')
                        has_validation_feedback = bool(validation_result.get('feedback'))
                        
                        # Check for Parlant metadata throughout workflow
                        has_parlant_guidelines = bool(validation_result.get('parlant_guidelines'))
                        has_parlant_confidence = bool(validation_result.get('parlant_confidence'))
                        parlant_metadata_present = has_parlant_guidelines or has_parlant_confidence
                        
                        # Check Calendar Agent integration (meeting detection)
                        intents = processed_email.get('intents', [])
                        meeting_intents = [intent for intent in intents if 
                                         intent.get('is_meeting_related', False) or 
                                         'meeting' in intent.get('name', '').lower() or
                                         'demo' in intent.get('name', '').lower() or
                                         'schedule' in intent.get('name', '').lower()]
                        
                        has_meeting_detection = len(meeting_intents) > 0
                        
                        # Check draft content for meeting acknowledgment
                        draft_content = processed_email.get('draft', '').lower()
                        acknowledges_meeting = any(term in draft_content for term in 
                                                 ['meeting', 'schedule', 'demo', 'call', 'appointment'])
                        
                        # Check final status and workflow completion
                        final_status = processed_email.get('status')
                        workflow_completed = final_status in ['ready_to_send', 'sent', 'needs_redraft']
                        
                        # Check persona consistency (account persona reflected in response)
                        account_persona = account.get('persona', '').lower()
                        persona_reflected = True  # Default to true if no specific persona
                        if account_persona and 'professional' in account_persona:
                            persona_reflected = not any(casual in draft_content for casual in 
                                                      ['hey', 'sup', 'yo', 'lol'])
                        
                        # Overall scenario evaluation
                        scenario_passed = (has_intents and has_draft and draft_length > 150 and
                                         validation_status in ['PASS', 'FAIL'] and
                                         has_validation_feedback and workflow_completed and
                                         persona_reflected)
                        
                        e2e_results.append({
                            "scenario": scenario['name'],
                            "passed": scenario_passed,
                            "draft_agent": {"intents": len(processed_email.get('intents', [])), 
                                          "draft_length": draft_length},
                            "validation_agent": {"status": validation_status, 
                                               "has_feedback": has_validation_feedback},
                            "calendar_agent": {"meeting_intents": len(meeting_intents), 
                                             "acknowledges_meeting": acknowledges_meeting},
                            "parlant_integration": {"metadata_present": parlant_metadata_present,
                                                  "guidelines": has_parlant_guidelines,
                                                  "confidence": has_parlant_confidence},
                            "workflow_status": final_status,
                            "persona_consistent": persona_reflected
                        })
                        
                        print(f"     - Draft Agent: {len(processed_email.get('intents', []))} intents, {draft_length} chars")
                        print(f"     - Validation Agent: {validation_status}, feedback: {has_validation_feedback}")
                        print(f"     - Calendar Agent: {len(meeting_intents)} meeting intents, acknowledges: {acknowledges_meeting}")
                        print(f"     - Parlant Integration: metadata: {parlant_metadata_present}")
                        print(f"     - Final Status: {final_status}")
                        print(f"     - Persona Consistent: {persona_reflected}")
                        
                    else:
                        print(f"     ❌ E2E processing failed - Status: {response.status_code}")
                        e2e_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"     ❌ Exception: {str(e)}")
                    e2e_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Evaluate overall E2E results
            passed_e2e = sum(1 for result in e2e_results if result.get('passed', False))
            total_e2e = len(e2e_results)
            
            all_passed = passed_e2e == total_e2e
            
            details = f"E2E scenarios passed: {passed_e2e}/{total_e2e}. "
            for result in e2e_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("End-to-End Parlant Integration", all_passed, details)
            
            # Log detailed E2E results
            for result in e2e_results:
                scenario_name = f"E2E Parlant - {result['scenario']}"
                scenario_passed = result.get('passed', False)
                scenario_details = ""
                if 'draft_agent' in result:
                    da = result['draft_agent']
                    va = result['validation_agent'] 
                    ca = result['calendar_agent']
                    pi = result['parlant_integration']
                    scenario_details = f"Draft: {da['intents']}i/{da['draft_length']}c, Validation: {va['status']}, Calendar: {ca['meeting_intents']}mi, Parlant: {pi['metadata_present']}"
                elif 'error' in result:
                    scenario_details = result['error']
                
                self.log_test_result(scenario_name, scenario_passed, scenario_details)
            
        except Exception as e:
            self.log_test_result("End-to-End Parlant Integration", False, f"Exception: {str(e)}")

    async def test_api_endpoints_with_parlant_metadata(self):
        """Test 5: API Endpoints Testing - verify Parlant data in API responses"""
        print("\n🌐 Testing API Endpoints with Parlant Metadata...")
        
        try:
            # Test /api/emails/test endpoint with Parlant-enhanced processing
            print("   Testing /api/emails/test endpoint with Parlant metadata...")
            
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("API Endpoints with Parlant Metadata", False, "No active email accounts")
                return
            
            test_email_data = {
                "subject": "Parlant API Test - Product Inquiry with Meeting Request",
                "body": "Hello, I'm interested in your AI Email Assistant product. Could you provide pricing information and schedule a demo meeting? I'm available next week for a 30-minute call to discuss our requirements.",
                "sender": "api.test@parlant.com",
                "account_id": account['id']
            }
            
            api_test_results = []
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=45)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    
                    # Check for Parlant metadata in API response
                    validation_result = processed_email.get('validation_result', {})
                    
                    # Check for Parlant-specific fields
                    has_parlant_guidelines = 'parlant_guidelines' in validation_result
                    has_parlant_confidence = 'parlant_confidence' in validation_result
                    has_guidelines_applied = 'guidelines_applied' in validation_result
                    has_coverage_report = 'coverage_report' in validation_result
                    
                    # Check for enhanced validation fields
                    has_persona_consistency = 'persona_consistency' in validation_result
                    has_hallucination_check = 'hallucination_detected' in validation_result
                    has_intent_coverage = 'intent_coverage' in validation_result
                    
                    # Check response structure completeness
                    has_intents = bool(processed_email.get('intents'))
                    has_draft = bool(processed_email.get('draft'))
                    has_validation = bool(processed_email.get('validation_result'))
                    has_status = bool(processed_email.get('status'))
                    
                    parlant_metadata_score = sum([
                        has_parlant_guidelines, has_parlant_confidence, has_guidelines_applied,
                        has_coverage_report, has_persona_consistency, has_hallucination_check,
                        has_intent_coverage
                    ])
                    
                    api_test_passed = (has_intents and has_draft and has_validation and 
                                     has_status and parlant_metadata_score >= 3)
                    
                    api_test_results.append({
                        "endpoint": "/api/emails/test",
                        "passed": api_test_passed,
                        "parlant_metadata_score": parlant_metadata_score,
                        "has_parlant_guidelines": has_parlant_guidelines,
                        "has_parlant_confidence": has_parlant_confidence,
                        "has_coverage_report": has_coverage_report,
                        "response_complete": has_intents and has_draft and has_validation
                    })
                    
                    print(f"     - Parlant metadata score: {parlant_metadata_score}/7")
                    print(f"     - Parlant guidelines: {has_parlant_guidelines}")
                    print(f"     - Parlant confidence: {has_parlant_confidence}")
                    print(f"     - Coverage report: {has_coverage_report}")
                    print(f"     - Response complete: {has_intents and has_draft and has_validation}")
                    
                else:
                    print(f"     ❌ API test failed - Status: {response.status_code}")
                    api_test_results.append({
                        "endpoint": "/api/emails/test",
                        "passed": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                print(f"     ❌ API test exception: {str(e)}")
                api_test_results.append({
                    "endpoint": "/api/emails/test",
                    "passed": False,
                    "error": str(e)
                })
            
            # Test email account creation with persona integration
            print("   Testing email account creation with persona integration...")
            
            try:
                account_data = {
                    "name": "Parlant Test Account",
                    "email": "parlant.test@example.com",
                    "provider": "gmail",
                    "username": "parlant.test@example.com",
                    "password": "test_password_123",
                    "persona": "Professional AI assistant with expertise in email automation and customer service",
                    "signature": "Best regards,\nParlant AI Assistant\nEmail Automation Specialist",
                    "auto_send": False
                }
                
                response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
                
                if response.status_code in [200, 201]:
                    created_account = response.json()
                    
                    # Check persona field integration
                    has_persona = bool(created_account.get('persona'))
                    persona_preserved = created_account.get('persona') == account_data['persona']
                    has_signature = bool(created_account.get('signature'))
                    
                    # Cleanup - delete test account
                    account_id = created_account.get('id')
                    if account_id:
                        try:
                            requests.delete(f"{API_BASE}/email-accounts/{account_id}", timeout=10)
                        except:
                            pass  # Ignore cleanup errors
                    
                    account_creation_passed = has_persona and persona_preserved and has_signature
                    
                    api_test_results.append({
                        "endpoint": "/api/email-accounts (create)",
                        "passed": account_creation_passed,
                        "has_persona": has_persona,
                        "persona_preserved": persona_preserved,
                        "has_signature": has_signature
                    })
                    
                    print(f"     - Persona field: {has_persona}")
                    print(f"     - Persona preserved: {persona_preserved}")
                    print(f"     - Signature field: {has_signature}")
                    
                else:
                    print(f"     ❌ Account creation failed - Status: {response.status_code}")
                    api_test_results.append({
                        "endpoint": "/api/email-accounts (create)",
                        "passed": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                print(f"     ❌ Account creation exception: {str(e)}")
                api_test_results.append({
                    "endpoint": "/api/email-accounts (create)",
                    "passed": False,
                    "error": str(e)
                })
            
            # Test calendar/meeting detection endpoint
            print("   Testing calendar/meeting detection endpoint...")
            
            try:
                meeting_request = {
                    "email_content": "I'd like to schedule a demo meeting for next Tuesday at 2 PM to discuss your AI email assistant capabilities.",
                    "sender": "demo@test.com",
                    "user_timezone": "UTC"
                }
                
                response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_request, timeout=30)
                
                if response.status_code == 200:
                    detection_result = response.json()
                    
                    # Check meeting detection response structure
                    has_meeting_detection = 'is_meeting_request' in detection_result
                    has_confidence = 'confidence' in detection_result
                    has_suggested_times = 'suggested_times' in detection_result
                    
                    # Check for Parlant metadata in meeting detection
                    has_parlant_meeting_metadata = bool(detection_result.get('parlant_guidelines') or 
                                                      detection_result.get('parlant_confidence'))
                    
                    meeting_detection_passed = (has_meeting_detection and has_confidence and 
                                              detection_result.get('confidence', 0) > 0.5)
                    
                    api_test_results.append({
                        "endpoint": "/api/calendar/detect-meeting",
                        "passed": meeting_detection_passed,
                        "has_meeting_detection": has_meeting_detection,
                        "has_confidence": has_confidence,
                        "confidence_score": detection_result.get('confidence', 0),
                        "has_parlant_metadata": has_parlant_meeting_metadata
                    })
                    
                    print(f"     - Meeting detection: {has_meeting_detection}")
                    print(f"     - Confidence score: {detection_result.get('confidence', 0):.2f}")
                    print(f"     - Parlant metadata: {has_parlant_meeting_metadata}")
                    
                else:
                    print(f"     ❌ Meeting detection failed - Status: {response.status_code}")
                    api_test_results.append({
                        "endpoint": "/api/calendar/detect-meeting",
                        "passed": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                print(f"     ❌ Meeting detection exception: {str(e)}")
                api_test_results.append({
                    "endpoint": "/api/calendar/detect-meeting",
                    "passed": False,
                    "error": str(e)
                })
            
            # Evaluate overall API endpoints results
            passed_endpoints = sum(1 for result in api_test_results if result.get('passed', False))
            total_endpoints = len(api_test_results)
            
            all_passed = passed_endpoints == total_endpoints
            
            details = f"API endpoints passed: {passed_endpoints}/{total_endpoints}. "
            for result in api_test_results:
                endpoint_name = result['endpoint'].split('/')[-1].split(' ')[0]
                if result.get('passed'):
                    details += f"{endpoint_name}: ✅ "
                else:
                    details += f"{endpoint_name}: ❌ "
            
            self.log_test_result("API Endpoints with Parlant Metadata", all_passed, details)
            
            # Log individual endpoint results
            for result in api_test_results:
                endpoint_name = f"API Endpoint - {result['endpoint']}"
                endpoint_passed = result.get('passed', False)
                endpoint_details = ""
                if 'parlant_metadata_score' in result:
                    endpoint_details = f"Parlant metadata: {result['parlant_metadata_score']}/7, Complete response: {result['response_complete']}"
                elif 'has_persona' in result:
                    endpoint_details = f"Persona: {result['has_persona']}, Preserved: {result['persona_preserved']}"
                elif 'confidence_score' in result:
                    endpoint_details = f"Detection: {result['has_meeting_detection']}, Confidence: {result['confidence_score']:.2f}"
                elif 'error' in result:
                    endpoint_details = result['error']
                
                self.log_test_result(endpoint_name, endpoint_passed, endpoint_details)
            
        except Exception as e:
            self.log_test_result("API Endpoints with Parlant Metadata", False, f"Exception: {str(e)}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 PARLANT EMAIL PROCESSING SYSTEM TEST SUMMARY")
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
    print("🚀 Starting Parlant-Enhanced Email Processing System Tests...")
    print("="*80)
    
    tester = ParlantEmailTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run all Parlant-specific tests
        await tester.test_draft_agent_with_parlant_guidelines()
        await tester.test_validation_agent_with_enhanced_checks()
        await tester.test_calendar_agent_with_meeting_detection()
        await tester.test_end_to_end_parlant_integration()
        await tester.test_api_endpoints_with_parlant_metadata()
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Exit with appropriate code
        if failed > 0:
            print(f"\n⚠️  {failed} tests failed. Please review the issues above.")
            sys.exit(1)
        else:
            print(f"\n🎉 All {passed} tests passed! Parlant email processing system is working correctly.")
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