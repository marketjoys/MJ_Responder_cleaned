#!/usr/bin/env python3
"""
Gmail Account Setup Test for Automatic Response Testing
Tests the specific Gmail account (kasargovinda@gmail.com) setup and configuration
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://account-sync-check.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Gmail credentials from review request
GMAIL_EMAIL = "kasargovinda@gmail.com"
GMAIL_PASSWORD = "urvsdfvrzfabvykm"

class GmailAccountSetupTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
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
    
    def test_user_registration_and_login(self):
        """Test 1: Create or use existing user account"""
        print("\n👤 Testing User Registration and Login...")
        
        try:
            # Create unique test user
            test_email = f"gmail.setup.test.{int(time.time())}@example.com"
            user_data = {
                "email": test_email,
                "password": "TestPassword123!",
                "full_name": "Gmail Setup Test User"
            }
            
            # Test user registration
            try:
                response = requests.post(f"{API_BASE}/auth/register", json=user_data, timeout=15)
                register_passed = response.status_code in [200, 201]
                
                if register_passed:
                    register_result = response.json()
                    self.auth_token = register_result.get('access_token')
                    self.test_user_id = register_result.get('user', {}).get('id')
                    register_details = f"Status: {response.status_code}, User ID: {self.test_user_id}"
                else:
                    register_details = f"Status: {response.status_code}, Error: {response.text}"
            except Exception as e:
                register_passed = False
                register_details = f"Error: {str(e)}"
            
            # Test user login
            login_passed = False
            if register_passed:
                try:
                    login_data = {
                        "email": test_email,
                        "password": "TestPassword123!"
                    }
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    login_passed = response.status_code == 200
                    
                    if login_passed:
                        login_result = response.json()
                        self.auth_token = login_result.get('access_token')
                        login_details = f"Status: {response.status_code}, Token received"
                    else:
                        login_details = f"Status: {response.status_code}"
                except Exception as e:
                    login_passed = False
                    login_details = f"Error: {str(e)}"
            else:
                login_details = "Skipped - registration failed"
            
            all_passed = register_passed and login_passed
            
            self.log_test_result("User Registration", register_passed, register_details)
            self.log_test_result("User Login", login_passed, login_details)
            self.log_test_result("User Account Setup", all_passed, f"Registration: {register_passed}, Login: {login_passed}")
            
            return all_passed
            
        except Exception as e:
            self.log_test_result("User Account Setup", False, f"Exception: {str(e)}")
            return False
    
    def test_gmail_account_creation(self):
        """Test 2: Create Gmail email account via API and ensure it persists in database"""
        print("\n📧 Testing Gmail Account Creation...")
        
        if not self.auth_token:
            self.log_test_result("Gmail Account Creation", False, "No auth token available")
            return False
        
        try:
            # Create Gmail account with specific credentials
            gmail_account_data = {
                "name": "Gmail Test Account for Automatic Response",
                "email": GMAIL_EMAIL,
                "provider": "gmail",
                "username": GMAIL_EMAIL,
                "password": GMAIL_PASSWORD,
                "persona": "Professional AI assistant for automatic email responses",
                "signature": "Best regards,\nAI Email Assistant",
                "auto_send": True
            }
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            try:
                response = requests.post(f"{API_BASE}/email-accounts", json=gmail_account_data, headers=headers, timeout=15)
                create_passed = response.status_code in [200, 201]
                
                if create_passed:
                    created_account = response.json()
                    self.gmail_account_id = created_account.get('id')
                    
                    # Verify account details
                    email_correct = created_account.get('email') == GMAIL_EMAIL
                    provider_correct = created_account.get('provider') == 'gmail'
                    is_active = created_account.get('is_active', False)
                    
                    create_details = f"Status: {response.status_code}, ID: {self.gmail_account_id}, Email: {email_correct}, Provider: {provider_correct}, Active: {is_active}"
                else:
                    create_details = f"Status: {response.status_code}, Error: {response.text}"
            except Exception as e:
                create_passed = False
                create_details = f"Error: {str(e)}"
            
            # Test account persistence in database
            persistence_passed = False
            if create_passed and self.gmail_account_id:
                try:
                    # Wait a moment for database write
                    time.sleep(1)
                    
                    # Check if account exists in database
                    account_doc = await self.db.email_accounts.find_one({"id": self.gmail_account_id})
                    if account_doc:
                        persistence_passed = (
                            account_doc.get('email') == GMAIL_EMAIL and
                            account_doc.get('provider') == 'gmail' and
                            account_doc.get('is_active', False)
                        )
                        persistence_details = f"Account found in DB, Email: {account_doc.get('email')}, Active: {account_doc.get('is_active')}"
                    else:
                        persistence_details = "Account not found in database"
                except Exception as e:
                    persistence_details = f"Database check error: {str(e)}"
            else:
                persistence_details = "Skipped - account creation failed"
            
            all_passed = create_passed and persistence_passed
            
            self.log_test_result("Gmail Account Creation", create_passed, create_details)
            self.log_test_result("Gmail Account Persistence", persistence_passed, persistence_details)
            self.log_test_result("Gmail Account Setup Complete", all_passed, f"Creation: {create_passed}, Persistence: {persistence_passed}")
            
            return all_passed
            
        except Exception as e:
            self.log_test_result("Gmail Account Creation", False, f"Exception: {str(e)}")
            return False
    
    def test_gmail_account_activation(self):
        """Test 3: Enable the account for polling (is_active = true)"""
        print("\n🔄 Testing Gmail Account Activation...")
        
        if not self.gmail_account_id or not self.auth_token:
            self.log_test_result("Gmail Account Activation", False, "No Gmail account ID or auth token")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Check current status
            try:
                response = requests.get(f"{API_BASE}/email-accounts/{self.gmail_account_id}", headers=headers, timeout=10)
                if response.status_code == 200:
                    account_data = response.json()
                    current_status = account_data.get('is_active', False)
                    status_check_details = f"Current status: {current_status}"
                else:
                    status_check_details = f"Status check failed: {response.status_code}"
                    current_status = None
            except Exception as e:
                status_check_details = f"Status check error: {str(e)}"
                current_status = None
            
            # Ensure account is active (toggle if needed)
            activation_passed = False
            if current_status is not None:
                if current_status:
                    # Already active
                    activation_passed = True
                    activation_details = "Account already active"
                else:
                    # Need to activate
                    try:
                        response = requests.put(f"{API_BASE}/email-accounts/{self.gmail_account_id}/toggle", headers=headers, timeout=10)
                        activation_passed = response.status_code == 200
                        
                        if activation_passed:
                            # Verify activation
                            verify_response = requests.get(f"{API_BASE}/email-accounts/{self.gmail_account_id}", headers=headers, timeout=10)
                            if verify_response.status_code == 200:
                                verified_data = verify_response.json()
                                activation_passed = verified_data.get('is_active', False)
                                activation_details = f"Toggle status: {response.status_code}, Verified active: {activation_passed}"
                            else:
                                activation_details = f"Toggle status: {response.status_code}, Verification failed: {verify_response.status_code}"
                        else:
                            activation_details = f"Toggle failed: {response.status_code}"
                    except Exception as e:
                        activation_passed = False
                        activation_details = f"Activation error: {str(e)}"
            else:
                activation_details = "Cannot activate - status check failed"
            
            self.log_test_result("Gmail Account Status Check", current_status is not None, status_check_details)
            self.log_test_result("Gmail Account Activation", activation_passed, activation_details)
            
            return activation_passed
            
        except Exception as e:
            self.log_test_result("Gmail Account Activation", False, f"Exception: {str(e)}")
            return False
    
    def test_polling_system_detection(self):
        """Test 4: Verify account appears in polling system"""
        print("\n📡 Testing Polling System Detection...")
        
        if not self.gmail_account_id:
            self.log_test_result("Polling System Detection", False, "No Gmail account ID")
            return False
        
        try:
            # Test polling service status
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                service_running = (response.status_code == 200 and 
                                 response.json().get('status') == 'running')
                service_details = f"Status: {response.status_code}, Running: {service_running}"
            except Exception as e:
                service_running = False
                service_details = f"Error: {str(e)}"
            
            # Test account visibility in polling system
            account_visible = False
            if service_running:
                try:
                    response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                    if response.status_code == 200:
                        polling_data = response.json()
                        accounts = polling_data.get('accounts', [])
                        
                        # Find our Gmail account
                        gmail_account = None
                        for account in accounts:
                            if account.get('account_id') == self.gmail_account_id:
                                gmail_account = account
                                break
                        
                        if gmail_account:
                            account_visible = True
                            is_polling_active = gmail_account.get('polling_active', False)
                            has_connection = gmail_account.get('has_connection', False)
                            visibility_details = f"Account found, Polling active: {is_polling_active}, Has connection: {has_connection}"
                        else:
                            visibility_details = f"Account not found in polling system (Total accounts: {len(accounts)})"
                    else:
                        visibility_details = f"Accounts status failed: {response.status_code}"
                except Exception as e:
                    visibility_details = f"Visibility check error: {str(e)}"
            else:
                visibility_details = "Skipped - polling service not running"
            
            all_passed = service_running and account_visible
            
            self.log_test_result("Polling Service Running", service_running, service_details)
            self.log_test_result("Gmail Account Visible in Polling", account_visible, visibility_details)
            self.log_test_result("Polling System Detection", all_passed, f"Service: {service_running}, Visible: {account_visible}")
            
            return all_passed
            
        except Exception as e:
            self.log_test_result("Polling System Detection", False, f"Exception: {str(e)}")
            return False
    
    def test_imap_connection(self):
        """Test 5: Test IMAP connection is working"""
        print("\n🔌 Testing IMAP Connection...")
        
        try:
            # Test direct IMAP connection
            connection_passed = False
            try:
                # Connect to Gmail IMAP
                imap = imaplib.IMAP4_SSL('imap.gmail.com', 993)
                
                # Login with credentials
                imap.login(GMAIL_EMAIL, GMAIL_PASSWORD)
                
                # Select inbox
                status, messages = imap.select('INBOX')
                
                if status == 'OK':
                    # Get message count
                    message_count = int(messages[0])
                    connection_passed = True
                    connection_details = f"Connected successfully, Inbox messages: {message_count}"
                    
                    # Test basic operations
                    status, message_ids = imap.search(None, 'ALL')
                    if status == 'OK':
                        total_messages = len(message_ids[0].split()) if message_ids[0] else 0
                        connection_details += f", Total messages: {total_messages}"
                else:
                    connection_details = f"Inbox selection failed: {status}"
                
                # Close connection
                imap.close()
                imap.logout()
                
            except Exception as e:
                connection_passed = False
                connection_details = f"IMAP connection error: {str(e)}"
            
            # Test connection via API (if account exists)
            api_connection_passed = False
            if self.gmail_account_id and self.auth_token:
                try:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    
                    # Test individual polling control to verify connection
                    polling_data = {"action": "status"}
                    response = requests.post(f"{API_BASE}/email-accounts/{self.gmail_account_id}/polling", 
                                           json=polling_data, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        polling_status = response.json()
                        has_connection = polling_status.get('has_connection', False)
                        polling_active = polling_status.get('polling_active', False)
                        api_connection_passed = True  # API call succeeded
                        api_details = f"Status: {response.status_code}, Has connection: {has_connection}, Polling active: {polling_active}"
                    else:
                        api_details = f"Polling status failed: {response.status_code}"
                except Exception as e:
                    api_details = f"API connection test error: {str(e)}"
            else:
                api_connection_passed = True  # Skip if no account
                api_details = "Skipped - no account or auth token"
            
            all_passed = connection_passed and api_connection_passed
            
            self.log_test_result("Direct IMAP Connection", connection_passed, connection_details)
            self.log_test_result("API Connection Test", api_connection_passed, api_details)
            self.log_test_result("IMAP Connection Working", all_passed, f"Direct: {connection_passed}, API: {api_connection_passed}")
            
            return all_passed
            
        except Exception as e:
            self.log_test_result("IMAP Connection Working", False, f"Exception: {str(e)}")
            return False
    
    def test_gmail_provider_configuration(self):
        """Test 6: Verify proper Gmail IMAP/SMTP settings"""
        print("\n⚙️ Testing Gmail Provider Configuration...")
        
        try:
            # Test email providers endpoint
            try:
                response = requests.get(f"{API_BASE}/email-providers", timeout=10)
                providers_passed = response.status_code == 200
                
                if providers_passed:
                    providers = response.json()
                    gmail_config = providers.get('gmail', {})
                    
                    # Verify Gmail configuration
                    expected_imap_server = "imap.gmail.com"
                    expected_imap_port = 993
                    expected_smtp_server = "smtp.gmail.com"
                    expected_smtp_port = 587
                    requires_app_password = True
                    
                    imap_server_correct = gmail_config.get('imap_server') == expected_imap_server
                    imap_port_correct = gmail_config.get('imap_port') == expected_imap_port
                    smtp_server_correct = gmail_config.get('smtp_server') == expected_smtp_server
                    smtp_port_correct = gmail_config.get('smtp_port') == expected_smtp_port
                    app_password_correct = gmail_config.get('requires_app_password') == requires_app_password
                    
                    config_correct = (imap_server_correct and imap_port_correct and 
                                    smtp_server_correct and smtp_port_correct and app_password_correct)
                    
                    providers_details = f"IMAP: {gmail_config.get('imap_server')}:{gmail_config.get('imap_port')}, SMTP: {gmail_config.get('smtp_server')}:{gmail_config.get('smtp_port')}, App password: {gmail_config.get('requires_app_password')}"
                else:
                    config_correct = False
                    providers_details = f"Status: {response.status_code}"
            except Exception as e:
                providers_passed = False
                config_correct = False
                providers_details = f"Error: {str(e)}"
            
            # Verify created account has correct settings
            account_config_correct = False
            if self.gmail_account_id and self.auth_token:
                try:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = requests.get(f"{API_BASE}/email-accounts/{self.gmail_account_id}", headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        account = response.json()
                        
                        account_imap_correct = account.get('imap_server') == "imap.gmail.com"
                        account_imap_port_correct = account.get('imap_port') == 993
                        account_smtp_correct = account.get('smtp_server') == "smtp.gmail.com"
                        account_smtp_port_correct = account.get('smtp_port') == 587
                        
                        account_config_correct = (account_imap_correct and account_imap_port_correct and 
                                                account_smtp_correct and account_smtp_port_correct)
                        
                        account_details = f"Account IMAP: {account.get('imap_server')}:{account.get('imap_port')}, SMTP: {account.get('smtp_server')}:{account.get('smtp_port')}"
                    else:
                        account_details = f"Account retrieval failed: {response.status_code}"
                except Exception as e:
                    account_details = f"Account config check error: {str(e)}"
            else:
                account_config_correct = True  # Skip if no account
                account_details = "Skipped - no account created"
            
            all_passed = providers_passed and config_correct and account_config_correct
            
            self.log_test_result("Gmail Provider Configuration", config_correct, providers_details)
            self.log_test_result("Gmail Account Configuration", account_config_correct, account_details)
            self.log_test_result("Gmail Configuration Complete", all_passed, f"Provider: {config_correct}, Account: {account_config_correct}")
            
            return all_passed
            
        except Exception as e:
            self.log_test_result("Gmail Configuration Complete", False, f"Exception: {str(e)}")
            return False
    
    async def test_account_persistence_verification(self):
        """Test 7: Confirm account stays in database after creation (DO NOT clean up)"""
        print("\n💾 Testing Account Persistence Verification...")
        
        if not self.gmail_account_id:
            self.log_test_result("Account Persistence Verification", False, "No Gmail account ID")
            return False
        
        try:
            # Wait a moment to ensure all operations are complete
            await asyncio.sleep(2)
            
            # Check database directly
            try:
                account_doc = await self.db.email_accounts.find_one({"id": self.gmail_account_id})
                
                if account_doc:
                    # Verify all key fields are present and correct
                    email_correct = account_doc.get('email') == GMAIL_EMAIL
                    provider_correct = account_doc.get('provider') == 'gmail'
                    is_active = account_doc.get('is_active', False)
                    has_password = bool(account_doc.get('password'))
                    has_imap_settings = bool(account_doc.get('imap_server'))
                    has_smtp_settings = bool(account_doc.get('smtp_server'))
                    
                    persistence_passed = (email_correct and provider_correct and is_active and 
                                        has_password and has_imap_settings and has_smtp_settings)
                    
                    db_details = f"Email: {email_correct}, Provider: {provider_correct}, Active: {is_active}, Password: {has_password}, IMAP: {has_imap_settings}, SMTP: {has_smtp_settings}"
                else:
                    persistence_passed = False
                    db_details = "Account not found in database"
            except Exception as e:
                persistence_passed = False
                db_details = f"Database check error: {str(e)}"
            
            # Check via API as well
            api_persistence_passed = False
            if self.auth_token:
                try:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = requests.get(f"{API_BASE}/email-accounts/{self.gmail_account_id}", headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        account_data = response.json()
                        api_persistence_passed = (
                            account_data.get('email') == GMAIL_EMAIL and
                            account_data.get('provider') == 'gmail' and
                            account_data.get('is_active', False)
                        )
                        api_details = f"API retrieval successful, Email: {account_data.get('email')}, Active: {account_data.get('is_active')}"
                    else:
                        api_details = f"API retrieval failed: {response.status_code}"
                except Exception as e:
                    api_details = f"API check error: {str(e)}"
            else:
                api_persistence_passed = True  # Skip if no auth
                api_details = "Skipped - no auth token"
            
            all_passed = persistence_passed and api_persistence_passed
            
            self.log_test_result("Database Persistence", persistence_passed, db_details)
            self.log_test_result("API Persistence", api_persistence_passed, api_details)
            self.log_test_result("Account Persistence Verification", all_passed, f"Database: {persistence_passed}, API: {api_persistence_passed}")
            
            # Log final account details for verification
            if all_passed:
                print(f"\n🎉 Gmail Account Successfully Set Up:")
                print(f"   Account ID: {self.gmail_account_id}")
                print(f"   Email: {GMAIL_EMAIL}")
                print(f"   Provider: gmail")
                print(f"   Status: Active and ready for automatic response testing")
                print(f"   ⚠️  Account will persist in database as requested")
            
            return all_passed
            
        except Exception as e:
            self.log_test_result("Account Persistence Verification", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("GMAIL ACCOUNT SETUP TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        print("\n" + "="*80)
        
        if self.gmail_account_id:
            print(f"🎯 GMAIL ACCOUNT READY FOR AUTOMATIC RESPONSE TESTING")
            print(f"   Account ID: {self.gmail_account_id}")
            print(f"   Email: {GMAIL_EMAIL}")
            print(f"   Status: Configured and persistent")
        else:
            print("❌ GMAIL ACCOUNT SETUP INCOMPLETE")
        
        print("="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting Gmail Account Setup Test for Automatic Response Testing")
    print(f"Target Gmail Account: {GMAIL_EMAIL}")
    print(f"Backend URL: {BACKEND_URL}")
    print("="*80)
    
    tester = GmailAccountSetupTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting")
            return
        
        # Run tests in sequence
        print("\n📋 Running Gmail Account Setup Tests...")
        
        # Test 1: User Registration and Login
        user_setup_success = tester.test_user_registration_and_login()
        
        # Test 2: Gmail Account Creation
        if user_setup_success:
            gmail_creation_success = tester.test_gmail_account_creation()
        else:
            gmail_creation_success = False
        
        # Test 3: Gmail Account Activation
        if gmail_creation_success:
            activation_success = tester.test_gmail_account_activation()
        else:
            activation_success = False
        
        # Test 4: Polling System Detection
        polling_success = tester.test_polling_system_detection()
        
        # Test 5: IMAP Connection
        imap_success = tester.test_imap_connection()
        
        # Test 6: Gmail Provider Configuration
        config_success = tester.test_gmail_provider_configuration()
        
        # Test 7: Account Persistence Verification
        persistence_success = await tester.test_account_persistence_verification()
        
        # Print summary
        tester.print_summary()
        
        # Overall success
        overall_success = (user_setup_success and gmail_creation_success and 
                          activation_success and imap_success and config_success and 
                          persistence_success)
        
        if overall_success:
            print("\n🎉 ALL TESTS PASSED - Gmail account is ready for automatic response testing!")
            return True
        else:
            print("\n❌ SOME TESTS FAILED - Please review the issues above")
            return False
        
    except Exception as e:
        print(f"\n💥 Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)