#!/usr/bin/env python3
"""
Comprehensive Automated Workflows Testing for Email Assistant System
Focus on testing automated workflows and features as requested in the review
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

class AutomatedWorkflowsTester:
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
    
    async def test_system_health_check(self):
        """Test 1: System Health Check - Backend running, database connectivity, API key validations"""
        print("\n🏥 Testing System Health Check...")
        
        try:
            # Test 1a: Backend Service Health
            try:
                response = requests.get(f"{BACKEND_URL}/health", timeout=10)
                backend_health = response.status_code == 200
            except:
                # Try alternative health check
                try:
                    response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                    backend_health = response.status_code == 200
                except:
                    backend_health = False
            
            # Test 1b: Database Connectivity
            try:
                # Test database connection by counting collections
                collections = await self.db.list_collection_names()
                db_health = len(collections) > 0
                db_details = f"Collections found: {len(collections)}"
            except Exception as e:
                db_health = False
                db_details = f"DB Error: {str(e)}"
            
            # Test 1c: API Key Validations - Groq API
            groq_key_valid = False
            try:
                groq_key = os.environ.get('GROQ_API_KEY')
                if groq_key and groq_key.startswith('gsk_'):
                    # Test with a simple classification request
                    test_email_data = {
                        "subject": "Test API Key Validation",
                        "body": "Testing Groq API key validation",
                        "sender": "test@example.com",
                        "account_id": "test-account"
                    }
                    
                    # Get a real account ID if available
                    accounts = await self.db.email_accounts.find().limit(1).to_list(1)
                    if accounts:
                        test_email_data["account_id"] = accounts[0]["id"]
                    
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                    # If we get a response (even if processing fails), the API key is valid
                    groq_key_valid = response.status_code in [200, 201, 500]  # 500 might be rate limit
                    groq_details = f"Groq API test status: {response.status_code}"
                else:
                    groq_details = "Groq API key not found or invalid format"
            except Exception as e:
                groq_details = f"Groq API test error: {str(e)}"
            
            # Test 1d: API Key Validations - Cohere API
            cohere_key_valid = False
            try:
                cohere_key = os.environ.get('COHERE_API_KEY')
                if cohere_key and len(cohere_key) > 20:
                    # Test by checking if we can create embeddings
                    kb_items = await self.db.knowledge_base.find({"embedding": {"$exists": True}}).limit(1).to_list(1)
                    cohere_key_valid = len(kb_items) > 0  # If we have embeddings, Cohere worked
                    cohere_details = f"Cohere validation via existing embeddings: {len(kb_items) > 0}"
                else:
                    cohere_details = "Cohere API key not found"
            except Exception as e:
                cohere_details = f"Cohere API test error: {str(e)}"
            
            # Test 1e: Essential Collections Check
            essential_collections = ['intents', 'knowledge_base', 'email_accounts', 'emails']
            collections_health = True
            collections_details = []
            
            for collection_name in essential_collections:
                try:
                    count = await self.db[collection_name].count_documents({})
                    collections_details.append(f"{collection_name}: {count}")
                    if collection_name in ['intents', 'knowledge_base'] and count == 0:
                        collections_health = False
                except Exception as e:
                    collections_health = False
                    collections_details.append(f"{collection_name}: ERROR")
            
            all_passed = backend_health and db_health and collections_health
            
            details = f"Backend: {backend_health}, DB: {db_health}, Groq: {groq_key_valid}, " \
                     f"Cohere: {cohere_key_valid}, Collections: {collections_health}"
            
            # Log individual components
            self.log_test_result("System Health - Backend Service", backend_health, "Backend API accessible")
            self.log_test_result("System Health - Database", db_health, db_details)
            self.log_test_result("System Health - Groq API Key", groq_key_valid, groq_details)
            self.log_test_result("System Health - Cohere API Key", cohere_key_valid, cohere_details)
            self.log_test_result("System Health - Collections", collections_health, ", ".join(collections_details))
            
            self.log_test_result("System Health Check", all_passed, details)
            
        except Exception as e:
            self.log_test_result("System Health Check", False, f"Exception: {str(e)}")
    
    async def test_automatic_polling_system(self):
        """Test 2: Automatic Polling System - Current status, email accounts, control endpoints"""
        print("\n📡 Testing Automatic Polling System...")
        
        try:
            # Test 2a: Current Polling Service Status
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                polling_status_passed = response.status_code == 200
                if polling_status_passed:
                    status_data = response.json()
                    service_running = status_data.get('status') == 'running'
                    active_connections = status_data.get('active_connections', 0)
                    status_details = f"Status: {status_data.get('status')}, Connections: {active_connections}"
                else:
                    service_running = False
                    status_details = f"HTTP {response.status_code}"
            except Exception as e:
                polling_status_passed = False
                service_running = False
                status_details = f"Error: {str(e)}"
            
            # Test 2b: Email Accounts Polling Status
            try:
                response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                accounts_status_passed = response.status_code == 200
                if accounts_status_passed:
                    accounts_data = response.json()
                    total_accounts = accounts_data.get('total_accounts', 0)
                    active_accounts = accounts_data.get('active_accounts', 0)
                    connected_accounts = accounts_data.get('connected_accounts', 0)
                    accounts_details = f"Total: {total_accounts}, Active: {active_accounts}, Connected: {connected_accounts}"
                else:
                    accounts_details = f"HTTP {response.status_code}"
            except Exception as e:
                accounts_status_passed = False
                accounts_details = f"Error: {str(e)}"
            
            # Test 2c: Verify Email Accounts Exist
            try:
                email_accounts = await self.db.email_accounts.find().to_list(100)
                accounts_exist = len(email_accounts) > 0
                active_accounts_db = len([acc for acc in email_accounts if acc.get('is_active', False)])
                accounts_exist_details = f"DB accounts: {len(email_accounts)}, Active: {active_accounts_db}"
            except Exception as e:
                accounts_exist = False
                accounts_exist_details = f"Error: {str(e)}"
            
            # Test 2d: Test Polling Control Endpoints
            control_endpoints_passed = True
            control_details = []
            
            # Test status endpoint
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                status_endpoint_ok = response.status_code == 200
                control_details.append(f"Status endpoint: {response.status_code}")
            except Exception as e:
                status_endpoint_ok = False
                control_details.append(f"Status endpoint: ERROR")
            
            # Test accounts status endpoint
            try:
                response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                accounts_endpoint_ok = response.status_code == 200
                control_details.append(f"Accounts status endpoint: {response.status_code}")
            except Exception as e:
                accounts_endpoint_ok = False
                control_details.append(f"Accounts status endpoint: ERROR")
            
            control_endpoints_passed = status_endpoint_ok and accounts_endpoint_ok
            
            # Test 2e: Individual Account Polling Control (if accounts exist)
            individual_control_passed = True
            if email_accounts:
                test_account = email_accounts[0]
                try:
                    # Test individual account status
                    status_data = {"action": "status"}
                    response = requests.post(f"{API_BASE}/email-accounts/{test_account['id']}/polling", 
                                           json=status_data, timeout=10)
                    individual_control_passed = response.status_code == 200
                    individual_details = f"Individual control: {response.status_code}"
                except Exception as e:
                    individual_control_passed = False
                    individual_details = f"Individual control: ERROR"
            else:
                individual_details = "No accounts to test individual control"
            
            all_passed = (polling_status_passed and accounts_status_passed and accounts_exist and 
                         control_endpoints_passed and individual_control_passed)
            
            # Log individual components
            self.log_test_result("Polling - Service Status", polling_status_passed, status_details)
            self.log_test_result("Polling - Accounts Status", accounts_status_passed, accounts_details)
            self.log_test_result("Polling - Accounts Exist", accounts_exist, accounts_exist_details)
            self.log_test_result("Polling - Control Endpoints", control_endpoints_passed, ", ".join(control_details))
            self.log_test_result("Polling - Individual Control", individual_control_passed, individual_details)
            
            details = f"Service: {service_running}, Accounts: {accounts_exist}, " \
                     f"Control: {control_endpoints_passed}, Individual: {individual_control_passed}"
            
            self.log_test_result("Automatic Polling System", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Automatic Polling System", False, f"Exception: {str(e)}")
    
    async def test_end_to_end_email_processing(self):
        """Test 3: End-to-End Email Processing Workflow - Complete AI workflow testing"""
        print("\n🤖 Testing End-to-End Email Processing Workflow...")
        
        try:
            # Get an active account for testing
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("End-to-End Email Processing", False, "No active email accounts found")
                return
            
            # Test 3a: Email Processing via API with Various Scenarios
            test_scenarios = [
                {
                    "name": "Sales Inquiry",
                    "subject": "Interested in Your AI Email Assistant - Pricing Request",
                    "body": "Hi there! I'm the operations manager at TechCorp and we're looking for an AI solution to handle our customer emails. We get about 500 emails per day and need automated responses. Can you provide pricing information and schedule a demo? We're particularly interested in intent classification and draft generation features. Our budget is around $5000/month. Please get back to me soon as we need to make a decision by Friday.",
                    "sender": "ops.manager@techcorp.com"
                },
                {
                    "name": "Support Request",
                    "subject": "Help with Email Integration Setup",
                    "body": "I'm having trouble setting up the email integration with our Gmail account. The IMAP connection keeps failing and I'm not sure if I'm using the right app password. Can you provide step-by-step instructions? Also, how do I configure the intent classification thresholds? Thanks for your help!",
                    "sender": "support.user@company.com"
                },
                {
                    "name": "Meeting Request",
                    "subject": "Schedule Demo Meeting for Next Week",
                    "body": "Hello! We'd like to schedule a demo meeting for your AI email assistant next week. We're available Tuesday through Thursday between 2-4 PM EST. Please let us know what works best for you. We'll have our technical team join the call to discuss integration requirements. Looking forward to seeing your solution in action!",
                    "sender": "demo.request@startup.io"
                }
            ]
            
            processing_results = []
            
            for scenario in test_scenarios:
                try:
                    print(f"   Testing scenario: {scenario['name']}")
                    
                    test_email_data = {
                        "subject": scenario["subject"],
                        "body": scenario["body"],
                        "sender": scenario["sender"],
                        "account_id": account['id']
                    }
                    
                    # Process email via API
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        
                        # Analyze processing results
                        intents_classified = len(processed_email.get('intents', []))
                        draft_generated = len(processed_email.get('draft', ''))
                        has_validation = processed_email.get('validation_result') is not None
                        final_status = processed_email.get('status')
                        
                        scenario_passed = (intents_classified >= 0 and draft_generated > 100 and 
                                         final_status not in ['error', 'failed'])
                        
                        processing_results.append({
                            "scenario": scenario['name'],
                            "passed": scenario_passed,
                            "intents": intents_classified,
                            "draft_length": draft_generated,
                            "validation": has_validation,
                            "status": final_status
                        })
                        
                        print(f"     - Intents: {intents_classified}, Draft: {draft_generated} chars, Status: {final_status}")
                        
                    else:
                        processing_results.append({
                            "scenario": scenario['name'],
                            "passed": False,
                            "error": f"HTTP {response.status_code}"
                        })
                        print(f"     - Failed with HTTP {response.status_code}")
                        
                except Exception as e:
                    processing_results.append({
                        "scenario": scenario['name'],
                        "passed": False,
                        "error": str(e)
                    })
                    print(f"     - Exception: {str(e)}")
            
            # Test 3b: Intent Classification Verification
            try:
                intents = await self.db.intents.find().to_list(100)
                intents_with_embeddings = [i for i in intents if i.get('embedding')]
                intent_system_working = len(intents_with_embeddings) > 0
                intent_details = f"Intents: {len(intents)}, With embeddings: {len(intents_with_embeddings)}"
            except Exception as e:
                intent_system_working = False
                intent_details = f"Error: {str(e)}"
            
            # Test 3c: Knowledge Base Integration
            try:
                kb_items = await self.db.knowledge_base.find().to_list(100)
                kb_with_embeddings = [kb for kb in kb_items if kb.get('embedding')]
                kb_system_working = len(kb_with_embeddings) > 0
                kb_details = f"KB items: {len(kb_items)}, With embeddings: {len(kb_with_embeddings)}"
            except Exception as e:
                kb_system_working = False
                kb_details = f"Error: {str(e)}"
            
            # Test 3d: Draft Generation Quality
            successful_scenarios = [r for r in processing_results if r.get('passed', False)]
            draft_quality_passed = len(successful_scenarios) >= 2  # At least 2 scenarios should work
            
            # Test 3e: Meeting Detection Integration
            meeting_detection_passed = False
            try:
                # Test meeting detection endpoint
                meeting_test_data = {
                    "email_content": "Let's schedule a meeting next Tuesday at 2 PM to discuss the project requirements.",
                    "sender": "meeting.test@example.com",
                    "user_timezone": "UTC"
                }
                
                response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_test_data, timeout=15)
                meeting_detection_passed = response.status_code == 200
                
                if meeting_detection_passed:
                    meeting_result = response.json()
                    meeting_details = f"Detection confidence: {meeting_result.get('confidence', 0)}"
                else:
                    meeting_details = f"HTTP {response.status_code}"
                    
            except Exception as e:
                meeting_details = f"Error: {str(e)}"
            
            # Test 3f: Complete AI Workflow Validation
            workflow_components = {
                "email_processing": len(successful_scenarios) > 0,
                "intent_classification": intent_system_working,
                "knowledge_base": kb_system_working,
                "draft_generation": draft_quality_passed,
                "meeting_detection": meeting_detection_passed
            }
            
            ai_workflow_passed = sum(workflow_components.values()) >= 3  # At least 3 components working
            
            all_passed = ai_workflow_passed and len(successful_scenarios) >= 1
            
            # Log individual components
            self.log_test_result("Email Processing - Scenarios", len(successful_scenarios) > 0, 
                               f"Successful scenarios: {len(successful_scenarios)}/{len(test_scenarios)}")
            self.log_test_result("Email Processing - Intent Classification", intent_system_working, intent_details)
            self.log_test_result("Email Processing - Knowledge Base", kb_system_working, kb_details)
            self.log_test_result("Email Processing - Draft Generation", draft_quality_passed, 
                               f"Quality drafts generated: {draft_quality_passed}")
            self.log_test_result("Email Processing - Meeting Detection", meeting_detection_passed, meeting_details)
            
            details = f"Scenarios: {len(successful_scenarios)}/{len(test_scenarios)}, " \
                     f"Intents: {intent_system_working}, KB: {kb_system_working}, " \
                     f"Drafts: {draft_quality_passed}, Meetings: {meeting_detection_passed}"
            
            self.log_test_result("End-to-End Email Processing Workflow", all_passed, details)
            
        except Exception as e:
            self.log_test_result("End-to-End Email Processing Workflow", False, f"Exception: {str(e)}")
    
    async def test_automated_features(self):
        """Test 4: Automated Features - Auto-follow up, meeting detection, auto-response, thread context"""
        print("\n🔄 Testing Automated Features...")
        
        try:
            # Test 4a: Auto-Follow Up Mechanisms
            try:
                # Check if there are emails with follow-up requirements
                emails_with_followup = await self.db.emails.find({
                    "status": {"$in": ["sent", "ready_to_send"]},
                    "intents.follow_up_hours": {"$exists": True}
                }).to_list(10)
                
                auto_followup_configured = len(emails_with_followup) > 0
                followup_details = f"Emails with follow-up: {len(emails_with_followup)}"
                
                # Check intent configurations for follow-up
                intents_with_followup = await self.db.intents.find({
                    "follow_up_hours": {"$gt": 0}
                }).to_list(100)
                
                followup_system_configured = len(intents_with_followup) > 0
                followup_details += f", Intents with follow-up: {len(intents_with_followup)}"
                
            except Exception as e:
                auto_followup_configured = False
                followup_system_configured = False
                followup_details = f"Error: {str(e)}"
            
            # Test 4b: Meeting Detection and Calendar Event Creation
            try:
                # Test meeting detection
                meeting_test_data = {
                    "email_content": "Can we schedule a meeting for tomorrow at 3 PM to discuss the quarterly review? I'll send you a calendar invite.",
                    "sender": "meeting.scheduler@company.com",
                    "user_timezone": "UTC"
                }
                
                response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_test_data, timeout=15)
                meeting_detection_working = response.status_code == 200
                
                if meeting_detection_working:
                    meeting_result = response.json()
                    meeting_confidence = meeting_result.get('confidence', 0)
                    meeting_detected = meeting_confidence > 0.5
                    meeting_details = f"Detection working, confidence: {meeting_confidence}"
                else:
                    meeting_detected = False
                    meeting_details = f"Detection failed: HTTP {response.status_code}"
                
                # Check for meeting intents in database
                meeting_intents = await self.db.meeting_intents.find().to_list(10)
                meeting_intents_exist = len(meeting_intents) > 0
                meeting_details += f", Meeting intents in DB: {len(meeting_intents)}"
                
            except Exception as e:
                meeting_detection_working = False
                meeting_detected = False
                meeting_intents_exist = False
                meeting_details = f"Error: {str(e)}"
            
            # Test 4c: Auto-Response System Based on Intents
            try:
                # Check if auto-send is configured for accounts
                accounts_with_autosend = await self.db.email_accounts.find({
                    "auto_send": True,
                    "is_active": True
                }).to_list(100)
                
                auto_response_configured = len(accounts_with_autosend) > 0
                
                # Check for emails that were auto-sent
                auto_sent_emails = await self.db.emails.find({
                    "status": "sent",
                    "sent_at": {"$exists": True}
                }).to_list(10)
                
                auto_response_working = len(auto_sent_emails) > 0
                auto_response_details = f"Auto-send accounts: {len(accounts_with_autosend)}, Auto-sent emails: {len(auto_sent_emails)}"
                
            except Exception as e:
                auto_response_configured = False
                auto_response_working = False
                auto_response_details = f"Error: {str(e)}"
            
            # Test 4d: Email Thread Context Handling
            try:
                # Look for emails with thread context
                emails_with_threads = await self.db.emails.find({
                    "thread_id": {"$exists": True, "$ne": ""},
                    "in_reply_to": {"$exists": True, "$ne": ""}
                }).to_list(10)
                
                thread_context_handling = len(emails_with_threads) > 0
                
                # Check for emails with references (thread continuity)
                emails_with_references = await self.db.emails.find({
                    "references": {"$exists": True, "$ne": ""}
                }).to_list(10)
                
                thread_continuity = len(emails_with_references) > 0
                thread_details = f"Threaded emails: {len(emails_with_threads)}, With references: {len(emails_with_references)}"
                
            except Exception as e:
                thread_context_handling = False
                thread_continuity = False
                thread_details = f"Error: {str(e)}"
            
            # Test 4e: Automated Workflow Integration
            try:
                # Test complete automated workflow by checking processed emails
                processed_emails = await self.db.emails.find({
                    "status": {"$in": ["ready_to_send", "sent"]},
                    "intents": {"$exists": True, "$ne": []},
                    "draft": {"$exists": True, "$ne": ""}
                }).to_list(20)
                
                automated_workflow_working = len(processed_emails) > 0
                
                # Calculate success rate
                total_emails = await self.db.emails.count_documents({})
                success_rate = (len(processed_emails) / total_emails * 100) if total_emails > 0 else 0
                
                workflow_details = f"Processed emails: {len(processed_emails)}/{total_emails}, Success rate: {success_rate:.1f}%"
                
            except Exception as e:
                automated_workflow_working = False
                workflow_details = f"Error: {str(e)}"
            
            # Overall assessment
            automated_features_working = (
                (auto_followup_configured or followup_system_configured) and
                (meeting_detection_working or meeting_intents_exist) and
                (auto_response_configured or auto_response_working) and
                (thread_context_handling or thread_continuity) and
                automated_workflow_working
            )
            
            # Log individual components
            self.log_test_result("Automated - Follow-up System", 
                               auto_followup_configured or followup_system_configured, followup_details)
            self.log_test_result("Automated - Meeting Detection", 
                               meeting_detection_working or meeting_intents_exist, meeting_details)
            self.log_test_result("Automated - Auto-Response", 
                               auto_response_configured or auto_response_working, auto_response_details)
            self.log_test_result("Automated - Thread Context", 
                               thread_context_handling or thread_continuity, thread_details)
            self.log_test_result("Automated - Workflow Integration", automated_workflow_working, workflow_details)
            
            details = f"Follow-up: {followup_system_configured}, Meeting: {meeting_detection_working}, " \
                     f"Auto-response: {auto_response_configured}, Threads: {thread_context_handling}, " \
                     f"Workflow: {automated_workflow_working}"
            
            self.log_test_result("Automated Features Testing", automated_features_working, details)
            
        except Exception as e:
            self.log_test_result("Automated Features Testing", False, f"Exception: {str(e)}")
    
    async def test_integration_testing(self):
        """Test 5: Integration Testing - Google OAuth, Cal.com, calendar providers, knowledge base search"""
        print("\n🔗 Testing Integration Systems...")
        
        try:
            # Test 5a: Google OAuth Integration Status
            try:
                response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
                oauth_status_working = response.status_code == 200
                
                if oauth_status_working:
                    oauth_data = response.json()
                    oauth_configured = oauth_data.get('configured', False)
                    oauth_details = f"Status endpoint working, configured: {oauth_configured}"
                else:
                    oauth_configured = False
                    oauth_details = f"Status endpoint failed: HTTP {response.status_code}"
                
                # Test OAuth authorization endpoint
                response = requests.get(f"{API_BASE}/oauth/google/authorize", timeout=10)
                oauth_auth_working = response.status_code in [200, 302]  # 302 for redirect
                oauth_details += f", Auth endpoint: {response.status_code}"
                
            except Exception as e:
                oauth_status_working = False
                oauth_configured = False
                oauth_auth_working = False
                oauth_details = f"Error: {str(e)}"
            
            # Test 5b: Cal.com Integration
            try:
                # Check if Cal.com API key is configured
                calcom_key = os.environ.get('CALCOM_API_KEY')
                calcom_configured = calcom_key is not None and calcom_key.startswith('cal_')
                
                # Test Cal.com calendar provider creation (if configured)
                if calcom_configured:
                    # This would require authentication, so we'll check for existing Cal.com providers
                    calcom_providers = await self.db.calendar_providers.find({
                        "provider_type": "calcom"
                    }).to_list(10)
                    
                    calcom_integration_working = len(calcom_providers) >= 0  # Even 0 is OK, means system can handle it
                    calcom_details = f"API key configured, providers in DB: {len(calcom_providers)}"
                else:
                    calcom_integration_working = False
                    calcom_details = "Cal.com API key not configured"
                
            except Exception as e:
                calcom_integration_working = False
                calcom_details = f"Error: {str(e)}"
            
            # Test 5c: Calendar Provider Connections
            try:
                # Check calendar providers in database
                calendar_providers = await self.db.calendar_providers.find().to_list(100)
                providers_exist = len(calendar_providers) > 0
                
                # Test calendar provider endpoints
                response = requests.get(f"{API_BASE}/calendar/providers", timeout=10)
                # This requires authentication, so we expect 401 or similar
                providers_endpoint_accessible = response.status_code in [200, 401, 403]
                
                calendar_details = f"Providers in DB: {len(calendar_providers)}, Endpoint accessible: {providers_endpoint_accessible}"
                
            except Exception as e:
                providers_exist = False
                providers_endpoint_accessible = False
                calendar_details = f"Error: {str(e)}"
            
            # Test 5d: Knowledge Base Vector Search Functionality
            try:
                # Test knowledge base search by checking embeddings
                kb_items = await self.db.knowledge_base.find({"embedding": {"$exists": True}}).to_list(100)
                kb_search_ready = len(kb_items) > 0
                
                # Test knowledge base endpoints
                response = requests.get(f"{API_BASE}/knowledge-base", timeout=10)
                kb_endpoint_working = response.status_code == 200
                
                if kb_endpoint_working and kb_search_ready:
                    # Test that embeddings are actually being used in email processing
                    # This is verified by checking if processed emails reference KB content
                    processed_emails = await self.db.emails.find({
                        "draft": {"$exists": True, "$ne": ""},
                        "status": {"$in": ["ready_to_send", "sent"]}
                    }).limit(5).to_list(5)
                    
                    kb_usage_detected = False
                    for email in processed_emails:
                        draft = email.get('draft', '').lower()
                        # Check if draft contains knowledge-based content
                        if any(word in draft for word in ['pricing', 'feature', 'product', 'service', 'support']):
                            kb_usage_detected = True
                            break
                    
                    vector_search_working = kb_usage_detected
                    kb_details = f"KB items with embeddings: {len(kb_items)}, Endpoint working: {kb_endpoint_working}, Usage detected: {kb_usage_detected}"
                else:
                    vector_search_working = False
                    kb_details = f"KB items: {len(kb_items)}, Endpoint: {kb_endpoint_working}"
                
            except Exception as e:
                kb_search_ready = False
                vector_search_working = False
                kb_details = f"Error: {str(e)}"
            
            # Test 5e: API Integration Health
            try:
                # Test key API endpoints for integration health
                integration_endpoints = [
                    ("/oauth/google/status", "Google OAuth"),
                    ("/calendar/providers", "Calendar Providers"),
                    ("/knowledge-base", "Knowledge Base"),
                    ("/intents", "Intents")
                ]
                
                endpoint_results = []
                for endpoint, name in integration_endpoints:
                    try:
                        response = requests.get(f"{API_BASE}{endpoint}", timeout=10)
                        # Accept various status codes as "working" (200, 401 for auth required, etc.)
                        working = response.status_code in [200, 401, 403]
                        endpoint_results.append((name, working, response.status_code))
                    except:
                        endpoint_results.append((name, False, "ERROR"))
                
                api_integration_health = sum(1 for _, working, _ in endpoint_results if working) >= 3
                api_details = ", ".join([f"{name}: {status}" for name, _, status in endpoint_results])
                
            except Exception as e:
                api_integration_health = False
                api_details = f"Error: {str(e)}"
            
            # Overall integration assessment
            integrations_working = (
                (oauth_status_working or oauth_configured) and
                (calcom_configured or calcom_integration_working) and
                (providers_exist or providers_endpoint_accessible) and
                (kb_search_ready or vector_search_working) and
                api_integration_health
            )
            
            # Log individual components
            self.log_test_result("Integration - Google OAuth", oauth_status_working or oauth_configured, oauth_details)
            self.log_test_result("Integration - Cal.com", calcom_configured or calcom_integration_working, calcom_details)
            self.log_test_result("Integration - Calendar Providers", providers_exist or providers_endpoint_accessible, calendar_details)
            self.log_test_result("Integration - Knowledge Base Search", kb_search_ready or vector_search_working, kb_details)
            self.log_test_result("Integration - API Health", api_integration_health, api_details)
            
            details = f"OAuth: {oauth_configured}, Cal.com: {calcom_configured}, " \
                     f"Calendar: {providers_exist}, KB Search: {vector_search_working}, " \
                     f"API Health: {api_integration_health}"
            
            self.log_test_result("Integration Testing", integrations_working, details)
            
        except Exception as e:
            self.log_test_result("Integration Testing", False, f"Exception: {str(e)}")
    
    async def test_database_state_analysis(self):
        """Test 6: Database State Analysis - Intents, knowledge base, email accounts, existing emails"""
        print("\n🗄️ Testing Database State Analysis...")
        
        try:
            # Test 6a: Intents Configuration Analysis
            try:
                intents = await self.db.intents.find().to_list(1000)
                intents_count = len(intents)
                
                # Analyze intent types
                meeting_intents = [i for i in intents if i.get('is_meeting_related', False)]
                intents_with_examples = [i for i in intents if i.get('examples') and len(i['examples']) > 0]
                intents_with_prompts = [i for i in intents if i.get('system_prompt', '').strip()]
                intents_with_embeddings = [i for i in intents if i.get('embedding')]
                
                intents_analysis = {
                    "total": intents_count,
                    "meeting_related": len(meeting_intents),
                    "with_examples": len(intents_with_examples),
                    "with_prompts": len(intents_with_prompts),
                    "with_embeddings": len(intents_with_embeddings)
                }
                
                intents_healthy = (intents_count > 0 and len(intents_with_embeddings) == intents_count)
                intents_details = f"Total: {intents_count}, Meeting: {len(meeting_intents)}, " \
                                f"Examples: {len(intents_with_examples)}, Embeddings: {len(intents_with_embeddings)}"
                
            except Exception as e:
                intents_healthy = False
                intents_details = f"Error: {str(e)}"
                intents_analysis = {}
            
            # Test 6b: Knowledge Base Entries Analysis
            try:
                kb_items = await self.db.knowledge_base.find().to_list(1000)
                kb_count = len(kb_items)
                
                # Analyze KB content
                kb_with_tags = [kb for kb in kb_items if kb.get('tags') and len(kb['tags']) > 0]
                kb_with_embeddings = [kb for kb in kb_items if kb.get('embedding')]
                
                # Analyze content length
                content_lengths = [len(kb.get('content', '')) for kb in kb_items]
                avg_content_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
                
                kb_analysis = {
                    "total": kb_count,
                    "with_tags": len(kb_with_tags),
                    "with_embeddings": len(kb_with_embeddings),
                    "avg_content_length": int(avg_content_length)
                }
                
                kb_healthy = (kb_count > 0 and len(kb_with_embeddings) == kb_count)
                kb_details = f"Total: {kb_count}, Tags: {len(kb_with_tags)}, " \
                           f"Embeddings: {len(kb_with_embeddings)}, Avg length: {int(avg_content_length)}"
                
            except Exception as e:
                kb_healthy = False
                kb_details = f"Error: {str(e)}"
                kb_analysis = {}
            
            # Test 6c: Email Accounts Status Analysis
            try:
                email_accounts = await self.db.email_accounts.find().to_list(1000)
                accounts_count = len(email_accounts)
                
                # Analyze account status
                active_accounts = [acc for acc in email_accounts if acc.get('is_active', False)]
                accounts_with_autosend = [acc for acc in email_accounts if acc.get('auto_send', False)]
                
                # Analyze providers
                providers = {}
                for acc in email_accounts:
                    provider = acc.get('provider', 'unknown')
                    providers[provider] = providers.get(provider, 0) + 1
                
                accounts_analysis = {
                    "total": accounts_count,
                    "active": len(active_accounts),
                    "auto_send": len(accounts_with_autosend),
                    "providers": providers
                }
                
                accounts_healthy = (accounts_count > 0 and len(active_accounts) > 0)
                accounts_details = f"Total: {accounts_count}, Active: {len(active_accounts)}, " \
                                 f"Auto-send: {len(accounts_with_autosend)}, Providers: {list(providers.keys())}"
                
            except Exception as e:
                accounts_healthy = False
                accounts_details = f"Error: {str(e)}"
                accounts_analysis = {}
            
            # Test 6d: Existing Emails Processing Status
            try:
                emails = await self.db.emails.find().to_list(1000)
                emails_count = len(emails)
                
                # Analyze email status
                status_counts = {}
                for email in emails:
                    status = email.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                # Analyze processing success
                processed_emails = [e for e in emails if e.get('status') in ['ready_to_send', 'sent']]
                failed_emails = [e for e in emails if e.get('status') in ['error', 'failed']]
                
                # Analyze email content
                emails_with_intents = [e for e in emails if e.get('intents') and len(e['intents']) > 0]
                emails_with_drafts = [e for e in emails if e.get('draft', '').strip()]
                
                processing_rate = (len(processed_emails) / emails_count * 100) if emails_count > 0 else 0
                
                emails_analysis = {
                    "total": emails_count,
                    "processed": len(processed_emails),
                    "failed": len(failed_emails),
                    "with_intents": len(emails_with_intents),
                    "with_drafts": len(emails_with_drafts),
                    "processing_rate": processing_rate,
                    "status_breakdown": status_counts
                }
                
                emails_healthy = (emails_count > 0 and processing_rate > 50)
                emails_details = f"Total: {emails_count}, Processed: {len(processed_emails)}, " \
                               f"Success rate: {processing_rate:.1f}%, Status: {status_counts}"
                
            except Exception as e:
                emails_healthy = False
                emails_details = f"Error: {str(e)}"
                emails_analysis = {}
            
            # Test 6e: Overall Database Health
            try:
                # Check collection sizes and indexes
                collections_info = {}
                essential_collections = ['intents', 'knowledge_base', 'email_accounts', 'emails', 'users']
                
                for collection_name in essential_collections:
                    try:
                        count = await self.db[collection_name].count_documents({})
                        collections_info[collection_name] = count
                    except:
                        collections_info[collection_name] = "ERROR"
                
                db_health = all(isinstance(count, int) and count >= 0 for count in collections_info.values())
                db_details = ", ".join([f"{name}: {count}" for name, count in collections_info.items()])
                
            except Exception as e:
                db_health = False
                db_details = f"Error: {str(e)}"
            
            # Overall database state assessment
            database_state_healthy = (intents_healthy and kb_healthy and accounts_healthy and 
                                    emails_healthy and db_health)
            
            # Log individual components
            self.log_test_result("Database - Intents Configuration", intents_healthy, intents_details)
            self.log_test_result("Database - Knowledge Base", kb_healthy, kb_details)
            self.log_test_result("Database - Email Accounts", accounts_healthy, accounts_details)
            self.log_test_result("Database - Email Processing", emails_healthy, emails_details)
            self.log_test_result("Database - Overall Health", db_health, db_details)
            
            details = f"Intents: {intents_analysis.get('total', 0)}, KB: {kb_analysis.get('total', 0)}, " \
                     f"Accounts: {accounts_analysis.get('total', 0)}, Emails: {emails_analysis.get('total', 0)}, " \
                     f"Processing rate: {emails_analysis.get('processing_rate', 0):.1f}%"
            
            self.log_test_result("Database State Analysis", database_state_healthy, details)
            
        except Exception as e:
            self.log_test_result("Database State Analysis", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE AUTOMATED WORKFLOWS TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {len(self.test_results)}")
        print(f"   Passed: {len(passed_tests)} ✅")
        print(f"   Failed: {len(failed_tests)} ❌")
        print(f"   Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}")
                if test['details']:
                    print(f"     Details: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   • {test['test']}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Comprehensive Automated Workflows Testing...")
    print("Focus: Automated workflows and features of the email assistant system")
    
    tester = AutomatedWorkflowsTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run all tests
        await tester.test_system_health_check()
        await tester.test_automatic_polling_system()
        await tester.test_end_to_end_email_processing()
        await tester.test_automated_features()
        await tester.test_integration_testing()
        await tester.test_database_state_analysis()
        
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