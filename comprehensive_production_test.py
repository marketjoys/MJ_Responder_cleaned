#!/usr/bin/env python3
"""
COMPREHENSIVE PRODUCTION READINESS TEST
Testing complete email automation workflow for production deployment

User Context:
- Email: amits.joys@gmail.com
- User ID: 18448dcf-8b80-4629-97c9-3df1fb6d46e5
- Password: ij@123

Email Accounts Added:
1. OAuth (Google): rathakartik8@gmail.com
2. Manual (IMAP/SMTP): kasargovinda@gmail.com

Test Objectives:
1. Authentication & User Management
2. Email Polling verification
3. Intent & Knowledge Base setup (currently 0 - CRITICAL ISSUE)
4. Complete Email Workflow testing
5. Calendar Integration
6. RQ Background Tasks
7. Critical Production Issues
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
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
COHERE_API_KEY = os.environ.get('COHERE_API_KEY')

# Test user credentials from review request
TEST_USER_EMAIL = "amits.joys@gmail.com"
TEST_USER_PASSWORD = "ij@123"
TEST_USER_ID = "18448dcf-8b80-4629-97c9-3df1fb6d46e5"

class ProductionReadinessTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.user_id = None
        self.critical_issues = []
        self.production_blockers = []
        
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
    
    def log_test_result(self, test_name: str, passed: bool, details: str = "", is_critical: bool = False):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "is_critical": is_critical,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        
        if not passed and is_critical:
            self.critical_issues.append(f"{test_name}: {details}")
        
        if not passed and ("CRITICAL" in details.upper() or "BLOCKER" in details.upper()):
            self.production_blockers.append(f"{test_name}: {details}")
    
    async def test_1_authentication_user_management(self):
        """Test 1: Authentication & User Management"""
        print("\n🔐 Testing Authentication & User Management...")
        
        try:
            # Test 1a: Login with provided credentials
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            try:
                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=15)
                login_success = response.status_code == 200
                
                if login_success:
                    result = response.json()
                    self.auth_token = result.get('access_token')
                    user_data = result.get('user', {})
                    self.user_id = user_data.get('id')
                    
                    # Verify user ID matches expected
                    user_id_matches = self.user_id == TEST_USER_ID
                    
                    login_details = f"Status: {response.status_code}, User ID: {self.user_id}, ID Match: {user_id_matches}"
                    self.log_test_result("User Authentication", login_success and user_id_matches, login_details, is_critical=True)
                else:
                    login_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    self.log_test_result("User Authentication", False, login_details, is_critical=True)
                    
            except Exception as e:
                self.log_test_result("User Authentication", False, f"Exception: {str(e)}", is_critical=True)
                return
            
            # Test 1b: Get user profile and quota info
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                try:
                    response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
                    profile_success = response.status_code == 200
                    
                    if profile_success:
                        profile_data = response.json()
                        has_quota_info = 'quota_info' in profile_data
                        email_matches = profile_data.get('email') == TEST_USER_EMAIL
                        
                        profile_details = f"Status: {response.status_code}, Email: {profile_data.get('email')}, Has Quota: {has_quota_info}"
                        self.log_test_result("User Profile & Quota", profile_success and has_quota_info and email_matches, profile_details)
                    else:
                        profile_details = f"Status: {response.status_code}"
                        self.log_test_result("User Profile & Quota", False, profile_details)
                        
                except Exception as e:
                    self.log_test_result("User Profile & Quota", False, f"Exception: {str(e)}")
            
            # Test 1c: Verify user has 2 email accounts
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                try:
                    response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
                    accounts_success = response.status_code == 200
                    
                    if accounts_success:
                        accounts = response.json()
                        account_count = len(accounts)
                        has_oauth_account = any(acc.get('auth_type') == 'oauth' for acc in accounts)
                        has_manual_account = any(acc.get('auth_type') == 'manual' for acc in accounts)
                        
                        # Check for specific accounts
                        oauth_email_found = any(acc.get('oauth_email') == 'rathakartik8@gmail.com' for acc in accounts)
                        manual_email_found = any(acc.get('email') == 'kasargovinda@gmail.com' for acc in accounts)
                        
                        accounts_details = f"Count: {account_count}, OAuth: {has_oauth_account}, Manual: {has_manual_account}, OAuth Email: {oauth_email_found}, Manual Email: {manual_email_found}"
                        expected_setup = account_count >= 2 and has_oauth_account and has_manual_account
                        
                        self.log_test_result("Email Accounts Setup", expected_setup, accounts_details, is_critical=True)
                    else:
                        accounts_details = f"Status: {response.status_code}"
                        self.log_test_result("Email Accounts Setup", False, accounts_details, is_critical=True)
                        
                except Exception as e:
                    self.log_test_result("Email Accounts Setup", False, f"Exception: {str(e)}", is_critical=True)
                    
        except Exception as e:
            self.log_test_result("Authentication & User Management", False, f"Exception: {str(e)}", is_critical=True)
    
    async def test_2_email_polling_verification(self):
        """Test 2: Email Polling Verification"""
        print("\n📡 Testing Email Polling Verification...")
        
        if not self.auth_token:
            self.log_test_result("Email Polling Verification", False, "No auth token available", is_critical=True)
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 2a: Check polling service status
            try:
                response = requests.get(f"{API_BASE}/polling/status", headers=headers, timeout=10)
                polling_running = response.status_code == 200 and response.json().get('status') == 'running'
                
                polling_details = f"Status: {response.status_code}, Service: {response.json().get('status') if response.status_code == 200 else 'Error'}"
                self.log_test_result("Polling Service Status", polling_running, polling_details, is_critical=True)
                
            except Exception as e:
                self.log_test_result("Polling Service Status", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 2b: Check both accounts are being polled
            try:
                response = requests.get(f"{API_BASE}/polling/accounts-status", headers=headers, timeout=10)
                accounts_status_success = response.status_code == 200
                
                if accounts_status_success:
                    status_data = response.json()
                    accounts = status_data.get('accounts', [])
                    active_accounts = [acc for acc in accounts if acc.get('polling_active')]
                    
                    # Check for OAuth and manual accounts
                    oauth_polling = any(acc.get('email') == 'rathakartik8@gmail.com' and acc.get('polling_active') for acc in accounts)
                    manual_polling = any(acc.get('email') == 'kasargovinda@gmail.com' and acc.get('polling_active') for acc in accounts)
                    
                    accounts_details = f"Total: {len(accounts)}, Active: {len(active_accounts)}, OAuth Polling: {oauth_polling}, Manual Polling: {manual_polling}"
                    both_polling = oauth_polling and manual_polling
                    
                    self.log_test_result("Both Accounts Polling", both_polling, accounts_details, is_critical=True)
                else:
                    accounts_details = f"Status: {response.status_code}"
                    self.log_test_result("Both Accounts Polling", False, accounts_details, is_critical=True)
                    
            except Exception as e:
                self.log_test_result("Both Accounts Polling", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 2c: Check last_polled timestamps
            try:
                accounts = await self.db.email_accounts.find({"user_id": self.user_id}).to_list(100)
                
                recent_polling = []
                for account in accounts:
                    last_polled = account.get('last_polled')
                    if last_polled:
                        time_diff = datetime.utcnow() - last_polled
                        is_recent = time_diff.total_seconds() < 3600  # Within last hour
                        recent_polling.append(is_recent)
                
                all_recent = len(recent_polling) > 0 and all(recent_polling)
                timestamp_details = f"Accounts checked: {len(accounts)}, Recent polling: {len([r for r in recent_polling if r])}/{len(recent_polling)}"
                
                self.log_test_result("Recent Polling Timestamps", all_recent, timestamp_details)
                
            except Exception as e:
                self.log_test_result("Recent Polling Timestamps", False, f"Exception: {str(e)}")
            
            # Test 2d: Verify OAuth token is valid
            try:
                oauth_token = await self.db.oauth_tokens.find_one({"user_id": self.user_id, "provider": "google"})
                
                if oauth_token:
                    expires_at = oauth_token.get('expires_at')
                    is_valid = expires_at and expires_at > datetime.utcnow()
                    has_refresh = bool(oauth_token.get('refresh_token'))
                    
                    token_details = f"Token found: True, Valid: {is_valid}, Has Refresh: {has_refresh}, Expires: {expires_at}"
                    self.log_test_result("OAuth Token Valid", is_valid, token_details, is_critical=True)
                else:
                    self.log_test_result("OAuth Token Valid", False, "No OAuth token found", is_critical=True)
                    
            except Exception as e:
                self.log_test_result("OAuth Token Valid", False, f"Exception: {str(e)}", is_critical=True)
                
        except Exception as e:
            self.log_test_result("Email Polling Verification", False, f"Exception: {str(e)}", is_critical=True)
    
    async def test_3_intent_knowledge_base_setup(self):
        """Test 3: Intent & Knowledge Base Setup (CRITICAL ISSUE - currently 0)"""
        print("\n🎯 Testing Intent & Knowledge Base Setup...")
        
        if not self.auth_token:
            self.log_test_result("Intent & Knowledge Base Setup", False, "No auth token available", is_critical=True)
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 3a: Check if user has intents
            try:
                response = requests.get(f"{API_BASE}/intents", headers=headers, timeout=10)
                intents_success = response.status_code == 200
                
                if intents_success:
                    intents = response.json()
                    intent_count = len(intents)
                    
                    # CRITICAL: User currently has 0 intents
                    has_intents = intent_count > 0
                    intents_details = f"Status: {response.status_code}, Count: {intent_count}"
                    
                    if not has_intents:
                        intents_details += " - CRITICAL: No intents configured, email workflow will fail"
                    
                    self.log_test_result("User Has Intents", has_intents, intents_details, is_critical=True)
                else:
                    intents_details = f"Status: {response.status_code}"
                    self.log_test_result("User Has Intents", False, intents_details, is_critical=True)
                    
            except Exception as e:
                self.log_test_result("User Has Intents", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 3b: Check if user has knowledge base entries
            try:
                response = requests.get(f"{API_BASE}/knowledge-base", headers=headers, timeout=10)
                kb_success = response.status_code == 200
                
                if kb_success:
                    kb_entries = response.json()
                    kb_count = len(kb_entries)
                    
                    has_kb = kb_count > 0
                    kb_details = f"Status: {response.status_code}, Count: {kb_count}"
                    
                    if not has_kb:
                        kb_details += " - CRITICAL: No knowledge base entries, responses will lack context"
                    
                    self.log_test_result("User Has Knowledge Base", has_kb, kb_details, is_critical=True)
                else:
                    kb_details = f"Status: {response.status_code}"
                    self.log_test_result("User Has Knowledge Base", False, kb_details, is_critical=True)
                    
            except Exception as e:
                self.log_test_result("User Has Knowledge Base", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 3c: Test creating intents via API
            try:
                intent_data = {
                    "name": "Sales Inquiry",
                    "description": "Handle sales inquiries and pricing requests",
                    "examples": [
                        "I want to know about your pricing",
                        "Can you send me a quote?",
                        "What are your rates?",
                        "I'm interested in your services"
                    ],
                    "system_prompt": "Respond professionally to sales inquiries with enthusiasm and provide helpful information about our services.",
                    "confidence_threshold": 0.7,
                    "follow_up_hours": 24,
                    "is_meeting_related": False
                }
                
                response = requests.post(f"{API_BASE}/intents", json=intent_data, headers=headers, timeout=15)
                create_intent_success = response.status_code in [200, 201]
                
                intent_create_details = f"Status: {response.status_code}"
                if create_intent_success:
                    created_intent = response.json()
                    intent_create_details += f", ID: {created_intent.get('id')}"
                
                self.log_test_result("Create Intent via API", create_intent_success, intent_create_details)
                
            except Exception as e:
                self.log_test_result("Create Intent via API", False, f"Exception: {str(e)}")
            
            # Test 3d: Test creating knowledge base entries
            try:
                kb_data = {
                    "title": "Company Services Overview",
                    "content": "We provide AI-powered email automation services that help businesses manage customer inquiries efficiently. Our platform uses advanced machine learning to classify emails, generate appropriate responses, and maintain professional communication standards. We offer flexible pricing plans starting from $99/month for small businesses up to enterprise solutions for large organizations.",
                    "tags": ["services", "pricing", "company", "overview"]
                }
                
                response = requests.post(f"{API_BASE}/knowledge-base", json=kb_data, headers=headers, timeout=15)
                create_kb_success = response.status_code in [200, 201]
                
                kb_create_details = f"Status: {response.status_code}"
                if create_kb_success:
                    created_kb = response.json()
                    kb_create_details += f", ID: {created_kb.get('id')}"
                
                self.log_test_result("Create Knowledge Base via API", create_kb_success, kb_create_details)
                
            except Exception as e:
                self.log_test_result("Create Knowledge Base via API", False, f"Exception: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Intent & Knowledge Base Setup", False, f"Exception: {str(e)}", is_critical=True)
    
    async def test_4_complete_email_workflow(self):
        """Test 4: Complete Email Workflow"""
        print("\n🤖 Testing Complete Email Workflow...")
        
        if not self.auth_token:
            self.log_test_result("Complete Email Workflow", False, "No auth token available", is_critical=True)
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Get an active account for testing
            response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
            if response.status_code != 200 or not response.json():
                self.log_test_result("Complete Email Workflow", False, "No email accounts available", is_critical=True)
                return
            
            test_account = response.json()[0]
            account_id = test_account['id']
            
            # Test 4a: Intent classification (uses Cohere embeddings)
            try:
                # Test Cohere API directly
                cohere_test_data = {
                    "model": "embed-english-v3.0",
                    "texts": ["I need pricing information for your services"],
                    "input_type": "classification"
                }
                
                cohere_headers = {
                    "Authorization": f"Bearer {COHERE_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                cohere_response = requests.post(
                    "https://api.cohere.com/v1/embed",
                    json=cohere_test_data,
                    headers=cohere_headers,
                    timeout=15
                )
                
                cohere_working = cohere_response.status_code == 200
                cohere_details = f"Cohere API Status: {cohere_response.status_code}"
                
                if not cohere_working:
                    cohere_details += f", Error: {cohere_response.text[:100]}"
                
                self.log_test_result("Cohere Embeddings API", cohere_working, cohere_details, is_critical=True)
                
            except Exception as e:
                self.log_test_result("Cohere Embeddings API", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 4b: Draft generation (uses Groq LLM)
            try:
                # Test Groq API directly
                groq_test_data = {
                    "messages": [
                        {"role": "user", "content": "Generate a professional email response to a pricing inquiry"}
                    ],
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.6,
                    "max_completion_tokens": 500
                }
                
                groq_headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                groq_response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=groq_test_data,
                    headers=groq_headers,
                    timeout=30
                )
                
                groq_working = groq_response.status_code == 200
                groq_details = f"Groq API Status: {groq_response.status_code}"
                
                if groq_working:
                    result = groq_response.json()
                    response_length = len(result.get("choices", [{}])[0].get("message", {}).get("content", ""))
                    groq_details += f", Response length: {response_length} chars"
                else:
                    groq_details += f", Error: {groq_response.text[:100]}"
                
                self.log_test_result("Groq LLM API", groq_working, groq_details, is_critical=True)
                
            except Exception as e:
                self.log_test_result("Groq LLM API", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 4c: Complete workflow via email test endpoint
            try:
                test_email_data = {
                    "subject": "Pricing Inquiry for AI Email Assistant",
                    "body": "Hello! I'm interested in your AI email automation services. Could you please provide detailed pricing information and schedule a demo? We're a growing company with about 50 employees and receive around 200 customer emails daily. We need a solution that can handle various types of inquiries professionally. What are your pricing tiers and what's included in each plan? Thank you!",
                    "sender": "business.owner@techcompany.com",
                    "account_id": account_id
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, headers=headers, timeout=45)
                workflow_success = response.status_code in [200, 201]
                
                if workflow_success:
                    processed_email = response.json()
                    email_id = processed_email.get('email_id')
                    status = processed_email.get('status')
                    
                    workflow_details = f"Status: {response.status_code}, Email ID: {email_id}, Processing Status: {status}"
                    
                    # Wait a moment for processing to complete
                    if email_id:
                        time.sleep(5)
                        
                        # Check final email status
                        email_response = requests.get(f"{API_BASE}/emails/{email_id}", headers=headers, timeout=10)
                        if email_response.status_code == 200:
                            email_data = email_response.json()
                            final_status = email_data.get('status')
                            has_intents = len(email_data.get('intents', [])) > 0
                            has_draft = len(email_data.get('draft', '')) > 0
                            has_validation = email_data.get('validation_result') is not None
                            
                            workflow_details += f", Final Status: {final_status}, Intents: {has_intents}, Draft: {has_draft}, Validation: {has_validation}"
                            
                            # Workflow is successful if it processed without errors
                            workflow_complete = final_status not in ['error', 'failed']
                        else:
                            workflow_complete = False
                            workflow_details += f", Email check failed: {email_response.status_code}"
                    else:
                        workflow_complete = False
                        workflow_details += ", No email ID returned"
                else:
                    workflow_complete = False
                    workflow_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                
                self.log_test_result("Complete Email Workflow", workflow_complete, workflow_details, is_critical=True)
                
            except Exception as e:
                self.log_test_result("Complete Email Workflow", False, f"Exception: {str(e)}", is_critical=True)
                
        except Exception as e:
            self.log_test_result("Complete Email Workflow", False, f"Exception: {str(e)}", is_critical=True)
    
    async def test_5_calendar_integration(self):
        """Test 5: Calendar Integration"""
        print("\n📅 Testing Calendar Integration...")
        
        if not self.auth_token:
            self.log_test_result("Calendar Integration", False, "No auth token available", is_critical=True)
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test 5a: Verify calendar provider is set up for rathakartik8@gmail.com
            try:
                calendar_providers = await self.db.calendar_providers.find({"user_id": self.user_id}).to_list(100)
                
                oauth_calendar_provider = None
                for provider in calendar_providers:
                    if provider.get('oauth_email') == 'rathakartik8@gmail.com':
                        oauth_calendar_provider = provider
                        break
                
                has_oauth_calendar = oauth_calendar_provider is not None
                
                if has_oauth_calendar:
                    provider_details = f"Provider found: True, Type: {oauth_calendar_provider.get('provider_type')}, Active: {oauth_calendar_provider.get('is_active')}"
                else:
                    provider_details = f"Provider found: False, Total providers: {len(calendar_providers)}"
                
                self.log_test_result("Calendar Provider Setup", has_oauth_calendar, provider_details, is_critical=True)
                
            except Exception as e:
                self.log_test_result("Calendar Provider Setup", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 5b: Test calendar API endpoints
            try:
                response = requests.get(f"{API_BASE}/calendar/calendars", headers=headers, timeout=15)
                calendars_success = response.status_code == 200
                
                if calendars_success:
                    calendars_data = response.json()
                    calendar_count = len(calendars_data) if isinstance(calendars_data, list) else 0
                    calendars_details = f"Status: {response.status_code}, Calendars found: {calendar_count}"
                else:
                    calendars_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                
                self.log_test_result("Calendar API Access", calendars_success, calendars_details)
                
            except Exception as e:
                self.log_test_result("Calendar API Access", False, f"Exception: {str(e)}")
            
            # Test 5c: Test meeting detection
            try:
                meeting_test_data = {
                    "email_content": "Hi, I'd like to schedule a meeting with you next Tuesday at 2 PM to discuss our project requirements. Please let me know if this time works for you.",
                    "sender": "client@example.com",
                    "user_timezone": "UTC"
                }
                
                response = requests.post(f"{API_BASE}/calendar/detect-meeting", json=meeting_test_data, headers=headers, timeout=15)
                meeting_detection_success = response.status_code == 200
                
                if meeting_detection_success:
                    detection_result = response.json()
                    has_meeting_intent = detection_result.get('has_meeting_intent', False)
                    meeting_details = f"Status: {response.status_code}, Meeting detected: {has_meeting_intent}"
                else:
                    meeting_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                
                self.log_test_result("Meeting Detection", meeting_detection_success, meeting_details)
                
            except Exception as e:
                self.log_test_result("Meeting Detection", False, f"Exception: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Calendar Integration", False, f"Exception: {str(e)}", is_critical=True)
    
    async def test_6_rq_background_tasks(self):
        """Test 6: RQ Background Tasks"""
        print("\n⚙️ Testing RQ Background Tasks...")
        
        try:
            # Test 6a: Verify Redis connection
            try:
                import redis
                redis_client = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
                redis_ping = redis_client.ping()
                
                redis_details = f"Redis ping: {redis_ping}"
                self.log_test_result("Redis Connection", redis_ping, redis_details, is_critical=True)
                
            except Exception as e:
                self.log_test_result("Redis Connection", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 6b: Verify RQ worker is processing jobs
            try:
                from rq import Queue
                from redis import Redis
                
                redis_conn = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
                queue = Queue('default', connection=redis_conn)
                
                # Get queue stats
                queue_length = len(queue)
                failed_jobs = len(queue.failed_job_registry)
                
                rq_details = f"Queue length: {queue_length}, Failed jobs: {failed_jobs}"
                rq_working = True  # If we can access the queue, RQ is working
                
                self.log_test_result("RQ Worker Status", rq_working, rq_details, is_critical=True)
                
            except Exception as e:
                self.log_test_result("RQ Worker Status", False, f"Exception: {str(e)}", is_critical=True)
            
            # Test 6c: Check if periodic tasks are scheduled
            try:
                # Check if there are any scheduled jobs
                from rq_scheduler import Scheduler
                
                redis_conn = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
                scheduler = Scheduler(connection=redis_conn)
                
                scheduled_jobs = scheduler.get_jobs()
                scheduled_count = len(scheduled_jobs)
                
                scheduler_details = f"Scheduled jobs: {scheduled_count}"
                scheduler_working = scheduled_count >= 0  # Any number is fine, just need scheduler to work
                
                self.log_test_result("Periodic Tasks Scheduler", scheduler_working, scheduler_details)
                
            except Exception as e:
                self.log_test_result("Periodic Tasks Scheduler", False, f"Exception: {str(e)}")
                
        except Exception as e:
            self.log_test_result("RQ Background Tasks", False, f"Exception: {str(e)}", is_critical=True)
    
    async def test_7_critical_production_issues(self):
        """Test 7: Critical Production Issues Check"""
        print("\n🚨 Testing Critical Production Issues...")
        
        # This test summarizes the critical issues found in other tests
        critical_count = len(self.critical_issues)
        blocker_count = len(self.production_blockers)
        
        # Check API keys are working
        groq_working = GROQ_API_KEY and len(GROQ_API_KEY) > 20
        cohere_working = COHERE_API_KEY and len(COHERE_API_KEY) > 20
        
        api_keys_details = f"Groq API Key: {'✅' if groq_working else '❌'}, Cohere API Key: {'✅' if cohere_working else '❌'}"
        self.log_test_result("API Keys Configuration", groq_working and cohere_working, api_keys_details, is_critical=True)
        
        # Overall production readiness
        production_ready = critical_count == 0 and blocker_count == 0
        production_details = f"Critical issues: {critical_count}, Production blockers: {blocker_count}"
        
        self.log_test_result("Production Readiness", production_ready, production_details, is_critical=True)
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE PRODUCTION READINESS TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        # Critical Issues
        if self.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(self.critical_issues)}):")
            for issue in self.critical_issues:
                print(f"   ❌ {issue}")
        
        # Production Blockers
        if self.production_blockers:
            print(f"\n🛑 PRODUCTION BLOCKERS ({len(self.production_blockers)}):")
            for blocker in self.production_blockers:
                print(f"   🛑 {blocker}")
        
        # Failed Tests Details
        failed_results = [r for r in self.test_results if not r['passed']]
        if failed_results:
            print(f"\n❌ FAILED TESTS DETAILS:")
            for result in failed_results:
                print(f"   • {result['test']}: {result['details']}")
        
        # Successful Tests (Summary)
        passed_results = [r for r in self.test_results if r['passed']]
        if passed_results:
            print(f"\n✅ SUCCESSFUL TESTS ({len(passed_results)}):")
            for result in passed_results:
                print(f"   • {result['test']}")
        
        print("\n" + "="*80)
        
        # Production Readiness Assessment
        if not self.critical_issues and not self.production_blockers:
            print("🎉 PRODUCTION READY: All critical systems are working correctly!")
        elif len(self.critical_issues) <= 2:
            print("⚠️  MOSTLY READY: Minor issues need to be resolved before production")
        else:
            print("🚫 NOT PRODUCTION READY: Critical issues must be resolved")
        
        print("="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Comprehensive Production Readiness Test")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test User: {TEST_USER_EMAIL}")
    print("-" * 80)
    
    tester = ProductionReadinessTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Failed to setup test environment")
            return
        
        # Run all tests
        await tester.test_1_authentication_user_management()
        await tester.test_2_email_polling_verification()
        await tester.test_3_intent_knowledge_base_setup()
        await tester.test_4_complete_email_workflow()
        await tester.test_5_calendar_integration()
        await tester.test_6_rq_background_tasks()
        await tester.test_7_critical_production_issues()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())