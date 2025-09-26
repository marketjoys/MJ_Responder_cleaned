#!/usr/bin/env python3
"""
Gmail Account Setup and Automatic Response System Testing
Tests the specific requirements from the review request:
1. Add Gmail account (kasargovinda@gmail.com)
2. Verify system setup (API keys, polling, intents, knowledge base)
3. Test email processing with different scenarios
4. Debug auto-response issues
5. Check account status
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
from email_services import EmailPollingService, EmailConnection
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://followup-debugger.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Gmail account details from review request
GMAIL_ACCOUNT = {
    "name": "Govinda Kasar Gmail Account",
    "email": "kasargovinda@gmail.com",
    "provider": "gmail",
    "username": "kasargovinda@gmail.com",
    "password": "urvsdfvrzfabvykm",  # App password from request
    "persona": "Professional AI assistant specializing in email automation and customer support",
    "signature": "Best regards,\\nAI Email Assistant\\nPowered by Reply Genius",
    "auto_send": True,  # Enable auto-send as requested
    "is_active": True
}

class GmailAutoResponseTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.gmail_account_id = None
        self.auth_token = None
        
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
    
    async def test_1_add_gmail_account(self):
        """Test 1: Add Gmail Account with specified credentials"""
        print("\n📧 Test 1: Adding Gmail Account (kasargovinda@gmail.com)...")
        
        try:
            # Check if account already exists
            existing_accounts = await self.db.email_accounts.find({"email": GMAIL_ACCOUNT["email"]}).to_list(10)
            if existing_accounts:
                print(f"   Account already exists, using existing account ID: {existing_accounts[0]['id']}")
                self.gmail_account_id = existing_accounts[0]['id']
                
                # Update existing account with correct settings
                update_data = GMAIL_ACCOUNT.copy()
                response = requests.put(f"{API_BASE}/email-accounts/{self.gmail_account_id}", json=update_data, timeout=15)
                account_updated = response.status_code == 200
                
                self.log_test_result("Gmail Account - Update Existing", account_updated, 
                                   f"Status: {response.status_code}, Updated existing account")
                return account_updated
            
            # Create new Gmail account
            response = requests.post(f"{API_BASE}/email-accounts", json=GMAIL_ACCOUNT, timeout=15)
            account_created = response.status_code in [200, 201]
            
            if account_created:
                created_account = response.json()
                self.gmail_account_id = created_account.get('id')
                
                # Verify account settings
                provider_correct = created_account.get('provider') == 'gmail'
                imap_correct = created_account.get('imap_server') == 'imap.gmail.com'
                smtp_correct = created_account.get('smtp_server') == 'smtp.gmail.com'
                auto_send_enabled = created_account.get('auto_send') == True
                is_active = created_account.get('is_active') == True
                
                details = f"Status: {response.status_code}, ID: {self.gmail_account_id}, " \
                         f"Provider: {provider_correct}, IMAP: {imap_correct}, SMTP: {smtp_correct}, " \
                         f"Auto-send: {auto_send_enabled}, Active: {is_active}"
                
                all_settings_correct = (provider_correct and imap_correct and smtp_correct and 
                                      auto_send_enabled and is_active)
                
                self.log_test_result("Gmail Account - Create New", all_settings_correct, details)
                return all_settings_correct
            else:
                self.log_test_result("Gmail Account - Create New", False, 
                                   f"Status: {response.status_code}, Error: {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("Gmail Account - Add", False, f"Exception: {str(e)}")
            return False
    
    async def test_2_verify_system_setup(self):
        """Test 2: Verify System Setup - API keys, polling service, intents, knowledge base"""
        print("\n🔧 Test 2: Verifying System Setup...")
        
        try:
            # Test 2a: Verify Groq API Key
            groq_key = os.environ.get('GROQ_API_KEY')
            groq_valid = groq_key and groq_key.startswith('gsk_')
            print(f"   Groq API Key: {'✅ Valid' if groq_valid else '❌ Invalid'}")
            
            # Test 2b: Verify Cohere API Key  
            cohere_key = os.environ.get('COHERE_API_KEY')
            cohere_valid = cohere_key and len(cohere_key) > 20
            print(f"   Cohere API Key: {'✅ Valid' if cohere_valid else '❌ Invalid'}")
            
            # Test 2c: Test Groq API functionality
            groq_working = False
            try:
                # Test with a simple classification request
                test_email_data = {
                    "subject": "Test API Functionality",
                    "body": "This is a test to verify the Groq API is working correctly.",
                    "sender": "test@example.com",
                    "account_id": self.gmail_account_id or "test-id"
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                groq_working = response.status_code in [200, 201]
                
                if groq_working:
                    processed_email = response.json()
                    has_processing = processed_email.get('status') not in ['new', 'error']
                    print(f"   Groq API Test: {'✅ Working' if has_processing else '⚠️ Limited'}")
                else:
                    print(f"   Groq API Test: ❌ Failed - Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   Groq API Test: ❌ Exception: {str(e)}")
            
            # Test 2d: Test Cohere API functionality (via embeddings)
            cohere_working = False
            try:
                # Check if existing intents have embeddings (indicates Cohere is working)
                intents = await self.db.intents.find().to_list(10)
                intents_with_embeddings = [i for i in intents if i.get('embedding')]
                cohere_working = len(intents_with_embeddings) > 0
                print(f"   Cohere API Test: {'✅ Working' if cohere_working else '❌ No embeddings found'}")
                
            except Exception as e:
                print(f"   Cohere API Test: ❌ Exception: {str(e)}")
            
            # Test 2e: Verify Polling Service
            polling_running = False
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                if response.status_code == 200:
                    status_data = response.json()
                    polling_running = status_data.get('status') == 'running'
                    active_connections = status_data.get('active_connections', 0)
                    print(f"   Polling Service: {'✅ Running' if polling_running else '❌ Stopped'} ({active_connections} connections)")
                else:
                    print(f"   Polling Service: ❌ Status check failed: {response.status_code}")
                    
            except Exception as e:
                print(f"   Polling Service: ❌ Exception: {str(e)}")
            
            # Test 2f: Check Intents
            intents_count = 0
            try:
                intents = await self.db.intents.find().to_list(100)
                intents_count = len(intents)
                meeting_intents = len([i for i in intents if i.get('is_meeting_related')])
                print(f"   Intents: ✅ {intents_count} total ({meeting_intents} meeting-related)")
                
            except Exception as e:
                print(f"   Intents: ❌ Exception: {str(e)}")
            
            # Test 2g: Check Knowledge Base
            kb_count = 0
            try:
                kb_items = await self.db.knowledge_base.find().to_list(100)
                kb_count = len(kb_items)
                kb_with_embeddings = len([kb for kb in kb_items if kb.get('embedding')])
                print(f"   Knowledge Base: ✅ {kb_count} entries ({kb_with_embeddings} with embeddings)")
                
            except Exception as e:
                print(f"   Knowledge Base: ❌ Exception: {str(e)}")
            
            # Overall system health
            system_healthy = (groq_valid and cohere_valid and groq_working and 
                            cohere_working and polling_running and 
                            intents_count >= 5 and kb_count >= 5)
            
            details = f"Groq: {groq_working}, Cohere: {cohere_working}, Polling: {polling_running}, " \
                     f"Intents: {intents_count}, KB: {kb_count}"
            
            self.log_test_result("System Setup Verification", system_healthy, details)
            return system_healthy
            
        except Exception as e:
            self.log_test_result("System Setup Verification", False, f"Exception: {str(e)}")
            return False
    
    async def test_3_email_processing_scenarios(self):
        """Test 3: Test Email Processing with Different Scenarios"""
        print("\n🤖 Test 3: Testing Email Processing Scenarios...")
        
        if not self.gmail_account_id:
            self.log_test_result("Email Processing Scenarios", False, "No Gmail account ID available")
            return False
        
        scenarios = [
            {
                "name": "Simple Inquiry",
                "subject": "Question about your AI email assistant",
                "body": "Hi, I'm interested in learning more about your AI email assistant. Can you provide some basic information about how it works and pricing? Thanks!",
                "sender": "curious.customer@example.com",
                "expected_intents": ["inquiry", "pricing", "information"]
            },
            {
                "name": "Meeting Request", 
                "subject": "Schedule a demo meeting",
                "body": "Hello, I would like to schedule a demo meeting to see your AI email assistant in action. I'm available next week Tuesday or Wednesday afternoon. Could we set up a 30-minute call? Please let me know what times work for you.",
                "sender": "business.lead@company.com",
                "expected_intents": ["meeting", "demo", "scheduling"]
            },
            {
                "name": "Customer Support",
                "subject": "Need help with email automation setup",
                "body": "I'm having trouble setting up the email automation for my business. The system doesn't seem to be processing emails correctly. Can you help me troubleshoot this issue? I need to get this working as soon as possible for my customer service team.",
                "sender": "support.needed@business.com",
                "expected_intents": ["support", "troubleshooting", "technical"]
            }
        ]
        
        scenario_results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n   Scenario {i}: {scenario['name']}")
            
            try:
                # Test email processing
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": self.gmail_account_id
                }
                
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                processing_successful = response.status_code in [200, 201]
                
                if processing_successful:
                    processed_email = response.json()
                    
                    # Check processing results
                    email_id = processed_email.get('id')
                    status = processed_email.get('status', 'unknown')
                    intents = processed_email.get('intents', [])
                    draft = processed_email.get('draft', '')
                    validation = processed_email.get('validation_result', {})
                    
                    # Analyze results
                    has_intents = len(intents) > 0
                    has_draft = len(draft) > 50  # Reasonable draft length
                    has_validation = bool(validation)
                    ready_to_send = status == 'ready_to_send'
                    
                    intent_names = [intent.get('name', '') for intent in intents]
                    
                    scenario_passed = processing_successful and has_draft
                    
                    details = f"Status: {status}, Intents: {len(intents)} ({', '.join(intent_names[:3])}), " \
                             f"Draft: {len(draft)} chars, Ready: {ready_to_send}"
                    
                    print(f"      {scenario['name']}: {'✅ PASS' if scenario_passed else '❌ FAIL'}")
                    print(f"      Details: {details}")
                    
                    scenario_results.append({
                        "name": scenario["name"],
                        "passed": scenario_passed,
                        "email_id": email_id,
                        "status": status,
                        "intents_count": len(intents),
                        "draft_length": len(draft),
                        "ready_to_send": ready_to_send
                    })
                    
                else:
                    print(f"      {scenario['name']}: ❌ FAIL - Status: {response.status_code}")
                    scenario_results.append({
                        "name": scenario["name"],
                        "passed": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                print(f"      {scenario['name']}: ❌ FAIL - Exception: {str(e)}")
                scenario_results.append({
                    "name": scenario["name"],
                    "passed": False,
                    "error": str(e)
                })
        
        # Overall assessment
        passed_scenarios = len([r for r in scenario_results if r.get('passed', False)])
        total_scenarios = len(scenarios)
        
        all_scenarios_passed = passed_scenarios == total_scenarios
        
        # Create results summary without backslashes in f-string
        result_items = []
        for r in scenario_results:
            name = r["name"]
            status_icon = "✅" if r.get("passed") else "❌"
            result_items.append(f"{name}: {status_icon}")
        
        details = f"Passed: {passed_scenarios}/{total_scenarios} scenarios. Results: {', '.join(result_items)}"
        
        self.log_test_result("Email Processing Scenarios", all_scenarios_passed, details)
        
        # Store scenario results for debugging
        self.scenario_results = scenario_results
        return all_scenarios_passed
    
    async def test_4_debug_auto_response_issues(self):
        """Test 4: Debug Auto-Response Issues"""
        print("\n🔍 Test 4: Debugging Auto-Response Issues...")
        
        if not self.gmail_account_id:
            self.log_test_result("Auto-Response Debug", False, "No Gmail account ID available")
            return False
        
        try:
            # Test 4a: Verify account auto-send setting
            response = requests.get(f"{API_BASE}/email-accounts/{self.gmail_account_id}", timeout=10)
            if response.status_code == 200:
                account_data = response.json()
                auto_send_enabled = account_data.get('auto_send', False)
                is_active = account_data.get('is_active', False)
                print(f"   Account Settings: Auto-send: {auto_send_enabled}, Active: {is_active}")
            else:
                auto_send_enabled = False
                is_active = False
                print(f"   Account Settings: ❌ Failed to retrieve - Status: {response.status_code}")
            
            # Test 4b: Check email processing workflow
            print("   Testing complete workflow: receive → classify → draft → validate → auto-send")
            
            # Create a test email that should trigger auto-response
            test_email_data = {
                "subject": "Auto-Response Test - Please Reply Automatically",
                "body": "This is a test email to verify the automatic response system is working. The system should classify this email, generate a draft response, validate it, and automatically send it back to me since auto-send is enabled.",
                "sender": "autoresponse.test@example.com",
                "account_id": self.gmail_account_id
            }
            
            # Process the email
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            workflow_successful = response.status_code in [200, 201]
            
            if workflow_successful:
                processed_email = response.json()
                email_id = processed_email.get('id')
                
                # Check workflow progression
                status = processed_email.get('status', 'unknown')
                intents = processed_email.get('intents', [])
                draft = processed_email.get('draft', '')
                validation = processed_email.get('validation_result', {})
                
                # Workflow steps analysis
                step_1_classify = len(intents) > 0
                step_2_draft = len(draft) > 50
                step_3_validate = bool(validation)
                step_4_ready = status == 'ready_to_send'
                step_5_auto_send = status == 'sent'  # Would be 'sent' if auto-send worked
                
                print(f"      Step 1 - Classify: {'✅' if step_1_classify else '❌'} ({len(intents)} intents)")
                print(f"      Step 2 - Draft: {'✅' if step_2_draft else '❌'} ({len(draft)} chars)")
                print(f"      Step 3 - Validate: {'✅' if step_3_validate else '❌'} ({validation.get('status', 'None')})")
                print(f"      Step 4 - Ready: {'✅' if step_4_ready else '❌'} (Status: {status})")
                print(f"      Step 5 - Auto-send: {'✅' if step_5_auto_send else '❌'} (Status: {status})")
                
                # Test 4c: Manual send test if auto-send didn't work
                manual_send_test = False
                if step_4_ready and not step_5_auto_send and email_id:
                    print("   Testing manual send functionality...")
                    try:
                        send_request = {"email_id": email_id, "manual_override": False}
                        send_response = requests.post(f"{API_BASE}/emails/{email_id}/send", json=send_request, timeout=15)
                        manual_send_test = send_response.status_code == 200
                        print(f"      Manual Send: {'✅' if manual_send_test else '❌'} (Status: {send_response.status_code})")
                    except Exception as e:
                        print(f"      Manual Send: ❌ Exception: {str(e)}")
                
                # Overall workflow assessment
                workflow_complete = step_1_classify and step_2_draft and step_3_validate and step_4_ready
                auto_response_working = step_5_auto_send or manual_send_test
                
                details = f"Workflow: {workflow_complete}, Auto-send: {auto_send_enabled}, " \
                         f"Status: {status}, Manual send: {manual_send_test}"
                
                self.log_test_result("Auto-Response Workflow", workflow_complete, details)
                
                # Identify issues
                if not auto_response_working:
                    issues = []
                    if not auto_send_enabled:
                        issues.append("Auto-send disabled in account settings")
                    if not is_active:
                        issues.append("Account not active")
                    if not step_4_ready:
                        issues.append("Email not reaching 'ready_to_send' status")
                    if step_4_ready and not step_5_auto_send:
                        issues.append("Auto-send mechanism not triggering")
                    
                    print(f"   🚨 Auto-Response Issues Identified: {'; '.join(issues)}")
                
                return workflow_complete
                
            else:
                print(f"   ❌ Workflow test failed - Status: {response.status_code}")
                self.log_test_result("Auto-Response Workflow", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Auto-Response Debug", False, f"Exception: {str(e)}")
            return False
    
    async def test_5_account_status_check(self):
        """Test 5: Account Status Check - IMAP/SMTP connectivity, polling status"""
        print("\n📊 Test 5: Account Status Check...")
        
        if not self.gmail_account_id:
            self.log_test_result("Account Status Check", False, "No Gmail account ID available")
            return False
        
        try:
            # Test 5a: Account polling status
            polling_status_data = {"action": "status"}
            response = requests.post(f"{API_BASE}/email-accounts/{self.gmail_account_id}/polling", 
                                   json=polling_status_data, timeout=10)
            
            polling_status_ok = response.status_code == 200
            if polling_status_ok:
                status_data = response.json()
                polling_active = status_data.get('polling_active', False)
                has_connection = status_data.get('has_connection', False)
                last_polled = status_data.get('last_polled')
                last_uid = status_data.get('last_uid', 0)
                
                print(f"   Polling Status: Active: {polling_active}, Connected: {has_connection}")
                print(f"   Last Polled: {last_polled}, Last UID: {last_uid}")
            else:
                print(f"   Polling Status: ❌ Failed to get status - {response.status_code}")
            
            # Test 5b: Test IMAP connectivity
            imap_test_passed = False
            try:
                # Get account details from database
                account_doc = await self.db.email_accounts.find_one({"id": self.gmail_account_id})
                if account_doc:
                    # Test IMAP connection
                    connection = EmailConnection(account_doc)
                    imap_connected = connection.connect_imap()
                    
                    if imap_connected:
                        # Test basic IMAP operations
                        try:
                            connection.imap.select('INBOX')
                            imap_test_passed = True
                            print("   IMAP Connection: ✅ Connected and can access INBOX")
                        except Exception as e:
                            print(f"   IMAP Connection: ⚠️ Connected but INBOX access failed: {str(e)}")
                        finally:
                            connection.disconnect_imap()
                    else:
                        print("   IMAP Connection: ❌ Failed to connect")
                else:
                    print("   IMAP Connection: ❌ Account not found in database")
                    
            except Exception as e:
                print(f"   IMAP Connection: ❌ Exception: {str(e)}")
            
            # Test 5c: Test SMTP connectivity (basic connection test)
            smtp_test_passed = False
            try:
                if account_doc:
                    connection = EmailConnection(account_doc)
                    # Test SMTP connection (without sending)
                    import smtplib
                    smtp_server = smtplib.SMTP(account_doc['smtp_server'], account_doc['smtp_port'])
                    smtp_server.starttls()
                    smtp_server.login(account_doc['username'], account_doc['password'])
                    smtp_server.quit()
                    smtp_test_passed = True
                    print("   SMTP Connection: ✅ Connected and authenticated")
                    
            except Exception as e:
                print(f"   SMTP Connection: ❌ Failed: {str(e)}")
            
            # Test 5d: Overall account health
            account_healthy = polling_status_ok and imap_test_passed and smtp_test_passed
            
            # Test 5e: Start polling if not active
            if polling_status_ok and not status_data.get('polling_active', False):
                print("   Starting polling for account...")
                start_data = {"action": "start"}
                start_response = requests.post(f"{API_BASE}/email-accounts/{self.gmail_account_id}/polling", 
                                             json=start_data, timeout=10)
                polling_started = start_response.status_code == 200
                print(f"   Polling Start: {'✅' if polling_started else '❌'} Status: {start_response.status_code}")
            
            details = f"Polling: {polling_status_ok}, IMAP: {imap_test_passed}, SMTP: {smtp_test_passed}"
            
            self.log_test_result("Account Status Check", account_healthy, details)
            return account_healthy
            
        except Exception as e:
            self.log_test_result("Account Status Check", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📋 GMAIL AUTO-RESPONSE SYSTEM TEST SUMMARY")
        print("="*80)
        
        passed_tests = len([r for r in self.test_results if r['passed']])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
        print()
        
        # Group results by category
        categories = {
            "Gmail Account Setup": [],
            "System Verification": [],
            "Email Processing": [],
            "Auto-Response Debug": [],
            "Account Status": []
        }
        
        for result in self.test_results:
            test_name = result['test']
            if 'Gmail Account' in test_name:
                categories["Gmail Account Setup"].append(result)
            elif 'System Setup' in test_name:
                categories["System Verification"].append(result)
            elif 'Email Processing' in test_name:
                categories["Email Processing"].append(result)
            elif 'Auto-Response' in test_name:
                categories["Auto-Response Debug"].append(result)
            elif 'Account Status' in test_name:
                categories["Account Status"].append(result)
        
        for category, results in categories.items():
            if results:
                print(f"📂 {category}:")
                for result in results:
                    print(f"   {result['status']}: {result['test']}")
                    if result['details']:
                        print(f"      {result['details']}")
                print()
        
        # Key findings
        print("🔍 KEY FINDINGS:")
        
        # Gmail account status
        if self.gmail_account_id:
            print(f"✅ Gmail account (kasargovinda@gmail.com) configured with ID: {self.gmail_account_id}")
        else:
            print("❌ Gmail account setup failed")
        
        # Auto-response capability
        auto_response_tests = [r for r in self.test_results if 'Auto-Response' in r['test']]
        if auto_response_tests and auto_response_tests[0]['passed']:
            print("✅ Auto-response workflow functional")
        else:
            print("❌ Auto-response workflow has issues")
        
        # System health
        system_tests = [r for r in self.test_results if 'System Setup' in r['test']]
        if system_tests and system_tests[0]['passed']:
            print("✅ System setup (API keys, polling, intents, KB) verified")
        else:
            print("❌ System setup issues detected")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Gmail Auto-Response System Testing...")
    print("="*80)
    
    tester = GmailAutoResponseTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Failed to setup test environment")
            return
        
        # Run tests in sequence
        await tester.test_1_add_gmail_account()
        await tester.test_2_verify_system_setup()
        await tester.test_3_email_processing_scenarios()
        await tester.test_4_debug_auto_response_issues()
        await tester.test_5_account_status_check()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())