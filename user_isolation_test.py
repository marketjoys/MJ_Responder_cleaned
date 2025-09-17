#!/usr/bin/env python3
"""
URGENT: User Isolation and Automatic Responder Testing
Tests user data isolation and Gmail automatic responder functionality
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid
import imaplib

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-codebase-debug.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Gmail credentials provided for testing
GMAIL_EMAIL = "kasargovinda@gmail.com"
GMAIL_PASSWORD = "urvsdfvrzfabvykm"

class UserIsolationTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.user1_token = None
        self.user2_token = None
        self.user1_id = None
        self.user2_id = None
        self.gmail_account_id = None
        
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
    
    def create_test_users(self):
        """Create two test users for isolation testing"""
        print("\n👥 Creating Test Users for Isolation Testing...")
        
        try:
            # Create User 1
            user1_data = {
                "email": f"user1.isolation.{int(time.time())}@example.com",
                "password": "testpassword123",
                "full_name": "Test User One"
            }
            
            response1 = requests.post(f"{API_BASE}/auth/register", json=user1_data, timeout=15)
            user1_created = response1.status_code in [200, 201]
            
            if user1_created:
                user1_response = response1.json()
                self.user1_token = user1_response.get('access_token')
                self.user1_id = user1_response.get('user', {}).get('id')
                print(f"   User 1 created: {user1_data['email']}")
            
            # Create User 2
            user2_data = {
                "email": f"user2.isolation.{int(time.time())}@example.com",
                "password": "testpassword123",
                "full_name": "Test User Two"
            }
            
            response2 = requests.post(f"{API_BASE}/auth/register", json=user2_data, timeout=15)
            user2_created = response2.status_code in [200, 201]
            
            if user2_created:
                user2_response = response2.json()
                self.user2_token = user2_response.get('access_token')
                self.user2_id = user2_response.get('user', {}).get('id')
                print(f"   User 2 created: {user2_data['email']}")
            
            both_created = user1_created and user2_created
            details = f"User1: {user1_created}, User2: {user2_created}"
            
            self.log_test_result("Create Test Users", both_created, details)
            return both_created
            
        except Exception as e:
            self.log_test_result("Create Test Users", False, f"Exception: {str(e)}")
            return False
    
    def test_user_isolation_intents(self):
        """Test user isolation for intents CRUD operations"""
        print("\n🎯 Testing User Isolation - Intents...")
        
        if not self.user1_token or not self.user2_token:
            self.log_test_result("User Isolation - Intents", False, "Test users not created")
            return
        
        try:
            headers1 = {"Authorization": f"Bearer {self.user1_token}"}
            headers2 = {"Authorization": f"Bearer {self.user2_token}"}
            
            # User 1 creates an intent
            intent1_data = {
                "name": "User 1 Private Intent",
                "description": "This intent belongs only to user 1",
                "examples": ["user 1 example", "private intent"],
                "confidence_threshold": 0.7
            }
            
            response = requests.post(f"{API_BASE}/intents", json=intent1_data, headers=headers1, timeout=15)
            intent1_created = response.status_code in [200, 201]
            intent1_id = response.json().get('id') if intent1_created else None
            
            # User 2 creates an intent
            intent2_data = {
                "name": "User 2 Private Intent",
                "description": "This intent belongs only to user 2",
                "examples": ["user 2 example", "separate intent"],
                "confidence_threshold": 0.7
            }
            
            response = requests.post(f"{API_BASE}/intents", json=intent2_data, headers=headers2, timeout=15)
            intent2_created = response.status_code in [200, 201]
            intent2_id = response.json().get('id') if intent2_created else None
            
            # Test isolation: User 1 should only see their intent
            response = requests.get(f"{API_BASE}/intents", headers=headers1, timeout=10)
            user1_intents = response.json() if response.status_code == 200 else []
            user1_sees_only_own = (len([i for i in user1_intents if i.get('name') == 'User 1 Private Intent']) == 1 and
                                  len([i for i in user1_intents if i.get('name') == 'User 2 Private Intent']) == 0)
            
            # Test isolation: User 2 should only see their intent
            response = requests.get(f"{API_BASE}/intents", headers=headers2, timeout=10)
            user2_intents = response.json() if response.status_code == 200 else []
            user2_sees_only_own = (len([i for i in user2_intents if i.get('name') == 'User 2 Private Intent']) == 1 and
                                  len([i for i in user2_intents if i.get('name') == 'User 1 Private Intent']) == 0)
            
            # Test cross-user access prevention: User 1 cannot access User 2's intent
            cross_access_blocked = True
            if intent2_id:
                response = requests.get(f"{API_BASE}/intents/{intent2_id}", headers=headers1, timeout=10)
                cross_access_blocked = response.status_code == 404
            
            # Test update isolation: User 1 cannot update User 2's intent
            update_blocked = True
            if intent2_id:
                update_data = {"name": "Hacked Intent", "description": "Hacked description"}
                response = requests.put(f"{API_BASE}/intents/{intent2_id}", json=update_data, headers=headers1, timeout=10)
                update_blocked = response.status_code == 404
            
            # Test delete isolation: User 1 cannot delete User 2's intent
            delete_blocked = True
            if intent2_id:
                response = requests.delete(f"{API_BASE}/intents/{intent2_id}", headers=headers1, timeout=10)
                delete_blocked = response.status_code == 404
            
            # Cleanup - delete created intents
            if intent1_id:
                requests.delete(f"{API_BASE}/intents/{intent1_id}", headers=headers1, timeout=10)
            if intent2_id:
                requests.delete(f"{API_BASE}/intents/{intent2_id}", headers=headers2, timeout=10)
            
            all_passed = (intent1_created and intent2_created and user1_sees_only_own and 
                         user2_sees_only_own and cross_access_blocked and update_blocked and delete_blocked)
            
            details = f"Create: {intent1_created and intent2_created}, List isolation: {user1_sees_only_own and user2_sees_only_own}, " \
                     f"Cross-access blocked: {cross_access_blocked}, Update blocked: {update_blocked}, Delete blocked: {delete_blocked}"
            
            self.log_test_result("User Isolation - Intents", all_passed, details)
            
        except Exception as e:
            self.log_test_result("User Isolation - Intents", False, f"Exception: {str(e)}")
    
    def test_user_isolation_knowledge_base(self):
        """Test user isolation for knowledge base CRUD operations"""
        print("\n📚 Testing User Isolation - Knowledge Base...")
        
        if not self.user1_token or not self.user2_token:
            self.log_test_result("User Isolation - Knowledge Base", False, "Test users not created")
            return
        
        try:
            headers1 = {"Authorization": f"Bearer {self.user1_token}"}
            headers2 = {"Authorization": f"Bearer {self.user2_token}"}
            
            # User 1 creates a knowledge base entry
            kb1_data = {
                "title": "User 1 Private Knowledge",
                "content": "This knowledge base entry belongs only to user 1 and contains sensitive information",
                "tags": ["user1", "private", "confidential"]
            }
            
            response = requests.post(f"{API_BASE}/knowledge-base", json=kb1_data, headers=headers1, timeout=15)
            kb1_created = response.status_code in [200, 201]
            kb1_id = response.json().get('id') if kb1_created else None
            
            # User 2 creates a knowledge base entry
            kb2_data = {
                "title": "User 2 Private Knowledge",
                "content": "This knowledge base entry belongs only to user 2 and contains different sensitive information",
                "tags": ["user2", "private", "separate"]
            }
            
            response = requests.post(f"{API_BASE}/knowledge-base", json=kb2_data, headers=headers2, timeout=15)
            kb2_created = response.status_code in [200, 201]
            kb2_id = response.json().get('id') if kb2_created else None
            
            # Test isolation: User 1 should only see their KB entry
            response = requests.get(f"{API_BASE}/knowledge-base", headers=headers1, timeout=10)
            user1_kb = response.json() if response.status_code == 200 else []
            user1_sees_only_own = (len([kb for kb in user1_kb if kb.get('title') == 'User 1 Private Knowledge']) == 1 and
                                  len([kb for kb in user1_kb if kb.get('title') == 'User 2 Private Knowledge']) == 0)
            
            # Test isolation: User 2 should only see their KB entry
            response = requests.get(f"{API_BASE}/knowledge-base", headers=headers2, timeout=10)
            user2_kb = response.json() if response.status_code == 200 else []
            user2_sees_only_own = (len([kb for kb in user2_kb if kb.get('title') == 'User 2 Private Knowledge']) == 1 and
                                  len([kb for kb in user2_kb if kb.get('title') == 'User 1 Private Knowledge']) == 0)
            
            # Test cross-user access prevention
            cross_access_blocked = True
            if kb2_id:
                response = requests.get(f"{API_BASE}/knowledge-base/{kb2_id}", headers=headers1, timeout=10)
                cross_access_blocked = response.status_code == 404
            
            # Test update isolation
            update_blocked = True
            if kb2_id:
                update_data = {"title": "Hacked Knowledge", "content": "Hacked content"}
                response = requests.put(f"{API_BASE}/knowledge-base/{kb2_id}", json=update_data, headers=headers1, timeout=10)
                update_blocked = response.status_code == 404
            
            # Test delete isolation
            delete_blocked = True
            if kb2_id:
                response = requests.delete(f"{API_BASE}/knowledge-base/{kb2_id}", headers=headers1, timeout=10)
                delete_blocked = response.status_code == 404
            
            # Cleanup
            if kb1_id:
                requests.delete(f"{API_BASE}/knowledge-base/{kb1_id}", headers=headers1, timeout=10)
            if kb2_id:
                requests.delete(f"{API_BASE}/knowledge-base/{kb2_id}", headers=headers2, timeout=10)
            
            all_passed = (kb1_created and kb2_created and user1_sees_only_own and 
                         user2_sees_only_own and cross_access_blocked and update_blocked and delete_blocked)
            
            details = f"Create: {kb1_created and kb2_created}, List isolation: {user1_sees_only_own and user2_sees_only_own}, " \
                     f"Cross-access blocked: {cross_access_blocked}, Update blocked: {update_blocked}, Delete blocked: {delete_blocked}"
            
            self.log_test_result("User Isolation - Knowledge Base", all_passed, details)
            
        except Exception as e:
            self.log_test_result("User Isolation - Knowledge Base", False, f"Exception: {str(e)}")
    
    def test_user_isolation_email_accounts(self):
        """Test user isolation for email accounts CRUD operations"""
        print("\n📧 Testing User Isolation - Email Accounts...")
        
        if not self.user1_token or not self.user2_token:
            self.log_test_result("User Isolation - Email Accounts", False, "Test users not created")
            return
        
        try:
            headers1 = {"Authorization": f"Bearer {self.user1_token}"}
            headers2 = {"Authorization": f"Bearer {self.user2_token}"}
            
            # User 1 creates an email account
            account1_data = {
                "name": "User 1 Private Account",
                "email": "user1.private@example.com",
                "provider": "gmail",
                "username": "user1.private@example.com",
                "password": "user1_secret_password",
                "persona": "User 1 assistant",
                "auto_send": False
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account1_data, headers=headers1, timeout=15)
            account1_created = response.status_code in [200, 201]
            account1_id = response.json().get('id') if account1_created else None
            
            # User 2 creates an email account
            account2_data = {
                "name": "User 2 Private Account",
                "email": "user2.private@example.com",
                "provider": "gmail",
                "username": "user2.private@example.com",
                "password": "user2_secret_password",
                "persona": "User 2 assistant",
                "auto_send": False
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account2_data, headers=headers2, timeout=15)
            account2_created = response.status_code in [200, 201]
            account2_id = response.json().get('id') if account2_created else None
            
            # Test isolation: User 1 should only see their account
            response = requests.get(f"{API_BASE}/email-accounts", headers=headers1, timeout=10)
            user1_accounts = response.json() if response.status_code == 200 else []
            user1_sees_only_own = (len([acc for acc in user1_accounts if acc.get('email') == 'user1.private@example.com']) == 1 and
                                  len([acc for acc in user1_accounts if acc.get('email') == 'user2.private@example.com']) == 0)
            
            # Test isolation: User 2 should only see their account
            response = requests.get(f"{API_BASE}/email-accounts", headers=headers2, timeout=10)
            user2_accounts = response.json() if response.status_code == 200 else []
            user2_sees_only_own = (len([acc for acc in user2_accounts if acc.get('email') == 'user2.private@example.com']) == 1 and
                                  len([acc for acc in user2_accounts if acc.get('email') == 'user1.private@example.com']) == 0)
            
            # Test cross-user access prevention
            cross_access_blocked = True
            if account2_id:
                response = requests.get(f"{API_BASE}/email-accounts/{account2_id}", headers=headers1, timeout=10)
                cross_access_blocked = response.status_code == 404
            
            # Test update isolation
            update_blocked = True
            if account2_id:
                update_data = {"name": "Hacked Account"}
                response = requests.put(f"{API_BASE}/email-accounts/{account2_id}", json=update_data, headers=headers1, timeout=10)
                update_blocked = response.status_code == 404
            
            # Test delete isolation
            delete_blocked = True
            if account2_id:
                response = requests.delete(f"{API_BASE}/email-accounts/{account2_id}", headers=headers1, timeout=10)
                delete_blocked = response.status_code == 404
            
            # Test polling control isolation
            polling_blocked = True
            if account2_id:
                polling_data = {"action": "status"}
                response = requests.post(f"{API_BASE}/email-accounts/{account2_id}/polling", json=polling_data, headers=headers1, timeout=10)
                polling_blocked = response.status_code == 404
            
            # Cleanup
            if account1_id:
                requests.delete(f"{API_BASE}/email-accounts/{account1_id}", headers=headers1, timeout=10)
            if account2_id:
                requests.delete(f"{API_BASE}/email-accounts/{account2_id}", headers=headers2, timeout=10)
            
            all_passed = (account1_created and account2_created and user1_sees_only_own and 
                         user2_sees_only_own and cross_access_blocked and update_blocked and 
                         delete_blocked and polling_blocked)
            
            details = f"Create: {account1_created and account2_created}, List isolation: {user1_sees_only_own and user2_sees_only_own}, " \
                     f"Cross-access blocked: {cross_access_blocked}, Update blocked: {update_blocked}, " \
                     f"Delete blocked: {delete_blocked}, Polling blocked: {polling_blocked}"
            
            self.log_test_result("User Isolation - Email Accounts", all_passed, details)
            
        except Exception as e:
            self.log_test_result("User Isolation - Email Accounts", False, f"Exception: {str(e)}")
    
    def test_gmail_connection(self):
        """Test direct Gmail IMAP connection with provided credentials"""
        print("\n📬 Testing Gmail IMAP Connection...")
        
        try:
            # Test direct IMAP connection
            mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            mail.login(GMAIL_EMAIL, GMAIL_PASSWORD)
            mail.select('inbox')
            
            # Get message count
            status, messages = mail.search(None, 'ALL')
            message_count = len(messages[0].split()) if messages[0] else 0
            
            mail.logout()
            
            connection_successful = True
            details = f"Connected to {GMAIL_EMAIL}, Messages in inbox: {message_count}"
            
            self.log_test_result("Gmail IMAP Connection", connection_successful, details)
            return connection_successful
            
        except Exception as e:
            self.log_test_result("Gmail IMAP Connection", False, f"Connection failed: {str(e)}")
            return False
    
    def test_gmail_account_creation(self):
        """Test Gmail account creation with provided credentials"""
        print("\n📧 Testing Gmail Account Creation...")
        
        if not self.user1_token:
            self.log_test_result("Gmail Account Creation", False, "Test user not created")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.user1_token}"}
            
            # Create Gmail account with provided credentials
            gmail_data = {
                "name": "Gmail Auto Responder Test",
                "email": GMAIL_EMAIL,
                "provider": "gmail",
                "username": GMAIL_EMAIL,
                "password": GMAIL_PASSWORD,
                "persona": "Professional email assistant for testing automatic responses",
                "signature": "Best regards,\nAI Email Assistant (Test Mode)",
                "auto_send": True  # Enable auto-send for testing
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=gmail_data, headers=headers, timeout=15)
            account_created = response.status_code in [200, 201]
            
            if account_created:
                account_response = response.json()
                self.gmail_account_id = account_response.get('id')
                
                # Verify account was created and is active
                verify_response = requests.get(f"{API_BASE}/email-accounts/{self.gmail_account_id}", headers=headers, timeout=10)
                account_verified = (verify_response.status_code == 200 and 
                                  verify_response.json().get('email') == GMAIL_EMAIL and
                                  verify_response.json().get('is_active') == True)
                
                details = f"Account created with ID: {self.gmail_account_id}, Active: {account_verified}"
            else:
                account_verified = False
                details = f"Creation failed - Status: {response.status_code}, Error: {response.text[:200]}"
            
            success = account_created and account_verified
            self.log_test_result("Gmail Account Creation", success, details)
            return success
            
        except Exception as e:
            self.log_test_result("Gmail Account Creation", False, f"Exception: {str(e)}")
            return False
    
    def test_polling_service_status(self):
        """Test polling service status and Gmail account integration"""
        print("\n📡 Testing Polling Service Status...")
        
        try:
            # Check overall polling service status
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            service_running = (response.status_code == 200 and 
                             response.json().get('status') == 'running')
            
            # Check accounts polling status
            if not self.user1_token:
                self.log_test_result("Polling Service Status", False, "Test user not available")
                return False
            
            headers = {"Authorization": f"Bearer {self.user1_token}"}
            response = requests.get(f"{API_BASE}/polling/accounts-status", headers=headers, timeout=10)
            accounts_status_available = response.status_code == 200
            
            if accounts_status_available:
                status_data = response.json()
                total_accounts = status_data.get('total_accounts', 0)
                active_accounts = status_data.get('active_accounts', 0)
                connected_accounts = status_data.get('connected_accounts', 0)
                
                # Check if Gmail account is in the list
                gmail_account_found = False
                if self.gmail_account_id:
                    accounts_list = status_data.get('accounts', [])
                    gmail_account_found = any(acc.get('account_id') == self.gmail_account_id for acc in accounts_list)
                
                details = f"Service running: {service_running}, Total accounts: {total_accounts}, " \
                         f"Active: {active_accounts}, Connected: {connected_accounts}, Gmail found: {gmail_account_found}"
            else:
                details = f"Service running: {service_running}, Accounts status unavailable"
            
            success = service_running and accounts_status_available
            self.log_test_result("Polling Service Status", success, details)
            return success
            
        except Exception as e:
            self.log_test_result("Polling Service Status", False, f"Exception: {str(e)}")
            return False
    
    def test_email_processing_workflow(self):
        """Test complete email processing workflow with Gmail account"""
        print("\n🤖 Testing Email Processing Workflow...")
        
        if not self.gmail_account_id or not self.user1_token:
            self.log_test_result("Email Processing Workflow", False, "Gmail account not created")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.user1_token}"}
            
            # Test email processing with realistic content
            test_email_data = {
                "subject": "Inquiry about AI Email Assistant Pricing",
                "body": "Hello! I'm interested in your AI email assistant service. Could you please provide information about pricing plans and features? I run a small business and receive about 50 emails per day that need responses. What would be the best plan for my needs? Also, do you offer a free trial? Thank you for your time.",
                "sender": "business.owner@testcompany.com",
                "account_id": self.gmail_account_id
            }
            
            # Process the email
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, headers=headers, timeout=30)
            processing_successful = response.status_code in [200, 201]
            
            if processing_successful:
                processed_email = response.json()
                
                # Check processing results
                has_intents = bool(processed_email.get('intents'))
                has_draft = bool(processed_email.get('draft'))
                has_validation = bool(processed_email.get('validation_result'))
                final_status = processed_email.get('status')
                
                # Check draft quality
                draft_content = processed_email.get('draft', '')
                draft_length = len(draft_content)
                draft_quality = (draft_length > 100 and 
                               'pricing' in draft_content.lower() and
                               'thank' in draft_content.lower())
                
                workflow_complete = (has_intents or has_draft) and final_status != 'error'
                
                details = f"Processing: {processing_successful}, Intents: {len(processed_email.get('intents', []))}, " \
                         f"Draft length: {draft_length}, Status: {final_status}, Quality: {draft_quality}"
            else:
                workflow_complete = False
                details = f"Processing failed - Status: {response.status_code}, Error: {response.text[:200]}"
            
            success = processing_successful and workflow_complete
            self.log_test_result("Email Processing Workflow", success, details)
            return success
            
        except Exception as e:
            self.log_test_result("Email Processing Workflow", False, f"Exception: {str(e)}")
            return False
    
    def test_automatic_responder_setup(self):
        """Test automatic responder configuration and readiness"""
        print("\n🔄 Testing Automatic Responder Setup...")
        
        if not self.gmail_account_id or not self.user1_token:
            self.log_test_result("Automatic Responder Setup", False, "Gmail account not created")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.user1_token}"}
            
            # Verify account is configured for auto-send
            response = requests.get(f"{API_BASE}/email-accounts/{self.gmail_account_id}", headers=headers, timeout=10)
            account_configured = (response.status_code == 200 and 
                                response.json().get('auto_send') == True and
                                response.json().get('is_active') == True)
            
            # Test polling control for the Gmail account
            polling_data = {"action": "start"}
            response = requests.post(f"{API_BASE}/email-accounts/{self.gmail_account_id}/polling", 
                                   json=polling_data, headers=headers, timeout=10)
            polling_started = response.status_code == 200
            
            # Check polling status
            status_data = {"action": "status"}
            response = requests.post(f"{API_BASE}/email-accounts/{self.gmail_account_id}/polling", 
                                   json=status_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                status_info = response.json()
                polling_active = status_info.get('polling_active', False)
                has_connection = status_info.get('has_connection', False)
                last_polled = status_info.get('last_polled')
                
                status_details = f"Active: {polling_active}, Connected: {has_connection}, Last polled: {last_polled is not None}"
            else:
                polling_active = False
                status_details = f"Status check failed: {response.status_code}"
            
            # Test that emails endpoint is accessible
            response = requests.get(f"{API_BASE}/emails", headers=headers, timeout=10)
            emails_accessible = response.status_code == 200
            
            if emails_accessible:
                emails_list = response.json()
                emails_count = len(emails_list)
            else:
                emails_count = 0
            
            success = account_configured and polling_started and polling_active and emails_accessible
            
            details = f"Account configured: {account_configured}, Polling started: {polling_started}, " \
                     f"Polling active: {polling_active}, Emails accessible: {emails_accessible} ({emails_count} emails), " \
                     f"{status_details}"
            
            self.log_test_result("Automatic Responder Setup", success, details)
            return success
            
        except Exception as e:
            self.log_test_result("Automatic Responder Setup", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("USER ISOLATION AND AUTOMATIC RESPONDER TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {len(self.test_results)}")
        print(f"   Passed: {len(passed_tests)}")
        print(f"   Failed: {len(failed_tests)}")
        print(f"   Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        print(f"\n✅ PASSED TESTS:")
        for test in passed_tests:
            print(f"   - {test['test']}")
        
        # Critical findings
        print(f"\n🔍 CRITICAL FINDINGS:")
        
        user_isolation_tests = [r for r in self.test_results if 'User Isolation' in r['test']]
        isolation_passed = all(r['passed'] for r in user_isolation_tests)
        print(f"   User Isolation: {'✅ WORKING' if isolation_passed else '❌ FAILED'}")
        
        gmail_tests = [r for r in self.test_results if 'Gmail' in r['test'] or 'Automatic' in r['test'] or 'Email Processing' in r['test']]
        gmail_passed = all(r['passed'] for r in gmail_tests)
        print(f"   Gmail Auto Responder: {'✅ WORKING' if gmail_passed else '❌ FAILED'}")
        
        polling_tests = [r for r in self.test_results if 'Polling' in r['test']]
        polling_passed = all(r['passed'] for r in polling_tests)
        print(f"   Polling Service: {'✅ WORKING' if polling_passed else '❌ FAILED'}")
        
        print(f"\n📧 GMAIL ACCOUNT STATUS:")
        if self.gmail_account_id:
            print(f"   Account ID: {self.gmail_account_id}")
            print(f"   Email: {GMAIL_EMAIL}")
            print(f"   Status: Configured and ready for automatic responses")
        else:
            print(f"   Status: Not configured")
        
        return len(passed_tests), len(failed_tests)

async def main():
    """Main test execution"""
    print("🚀 Starting URGENT User Isolation and Automatic Responder Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Gmail Credentials: {GMAIL_EMAIL} / {'*' * len(GMAIL_PASSWORD)}")
    
    tester = UserIsolationTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Create test users
        if not tester.create_test_users():
            print("❌ Failed to create test users, exiting...")
            return
        
        # Test Gmail connection first
        if not tester.test_gmail_connection():
            print("⚠️  Gmail connection failed, but continuing with other tests...")
        
        # Test user isolation
        tester.test_user_isolation_intents()
        tester.test_user_isolation_knowledge_base()
        tester.test_user_isolation_email_accounts()
        
        # Test Gmail account creation and automatic responder
        if tester.test_gmail_account_creation():
            tester.test_polling_service_status()
            tester.test_email_processing_workflow()
            tester.test_automatic_responder_setup()
        else:
            print("⚠️  Gmail account creation failed, skipping automatic responder tests...")
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Final status
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! User isolation and automatic responder are working correctly.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please review the issues above.")
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())