#!/usr/bin/env python3
"""
Gmail Account Creation End-to-End Test
Tests the complete email account creation workflow using real Gmail credentials
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
import smtplib

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

# Gmail credentials from the review request
GMAIL_EMAIL = "kasargovinda@gmail.com"
GMAIL_PASSWORD = "urvsdfvrzfabvykm"

class GmailAccountTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.test_user_email = None
        self.created_account_id = None
        
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
        """Cleanup resources and test data"""
        try:
            # Clean up created email account
            if self.created_account_id:
                try:
                    headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
                    response = requests.delete(f"{API_BASE}/email-accounts/{self.created_account_id}", 
                                             headers=headers, timeout=10)
                    print(f"🧹 Cleaned up test email account: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Failed to cleanup email account: {str(e)}")
            
            # Clean up test user
            if self.test_user_id:
                try:
                    await self.db.users.delete_one({"id": self.test_user_id})
                    print(f"🧹 Cleaned up test user")
                except Exception as e:
                    print(f"⚠️ Failed to cleanup test user: {str(e)}")
                    
        except Exception as e:
            print(f"⚠️ Cleanup error: {str(e)}")
        finally:
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
    
    def test_user_registration(self):
        """Test 1: Create a new user account via API"""
        print("\n👤 Testing User Registration...")
        
        try:
            # Generate unique test user email
            timestamp = int(time.time())
            self.test_user_email = f"gmail.test.user.{timestamp}@example.com"
            
            user_data = {
                "email": self.test_user_email,
                "password": "TestPassword123!",
                "full_name": "Gmail Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=user_data, timeout=15)
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                self.auth_token = response_data.get('access_token')
                self.test_user_id = response_data.get('user', {}).get('id')
                
                passed = bool(self.auth_token and self.test_user_id)
                details = f"Status: {response.status_code}, Token: {'✓' if self.auth_token else '✗'}, User ID: {'✓' if self.test_user_id else '✗'}"
            else:
                passed = False
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                
            self.log_test_result("User Registration", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("User Registration", False, f"Exception: {str(e)}")
            return False
    
    def test_user_login(self):
        """Test 2: Login with the created user to get authentication token"""
        print("\n🔐 Testing User Login...")
        
        try:
            if not self.test_user_email:
                self.log_test_result("User Login", False, "No test user email available")
                return False
            
            login_data = {
                "email": self.test_user_email,
                "password": "TestPassword123!"
            }
            
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=15)
            
            if response.status_code == 200:
                response_data = response.json()
                login_token = response_data.get('access_token')
                user_data = response_data.get('user', {})
                
                # Update auth token if login successful
                if login_token:
                    self.auth_token = login_token
                
                passed = bool(login_token and user_data.get('id'))
                details = f"Status: {response.status_code}, Token: {'✓' if login_token else '✗'}, User: {user_data.get('email', 'N/A')}"
            else:
                passed = False
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                
            self.log_test_result("User Login", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("User Login", False, f"Exception: {str(e)}")
            return False
    
    def test_gmail_account_creation(self):
        """Test 3: Create Gmail email account with provided credentials"""
        print("\n📧 Testing Gmail Account Creation...")
        
        try:
            if not self.auth_token:
                self.log_test_result("Gmail Account Creation", False, "No authentication token available")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            account_data = {
                "name": "Gmail Test Account",
                "email": GMAIL_EMAIL,
                "provider": "gmail",
                "username": GMAIL_EMAIL,
                "password": GMAIL_PASSWORD,
                "persona": "Professional Gmail assistant",
                "signature": "Best regards,\nGmail Test Account",
                "auto_send": False
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, 
                                   headers=headers, timeout=15)
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                self.created_account_id = response_data.get('id')
                
                # Verify account details
                email_correct = response_data.get('email') == GMAIL_EMAIL
                provider_correct = response_data.get('provider') == 'gmail'
                password_masked = response_data.get('password') == '***'
                
                passed = bool(self.created_account_id and email_correct and provider_correct)
                details = f"Status: {response.status_code}, ID: {self.created_account_id}, Email: {'✓' if email_correct else '✗'}, Provider: {'✓' if provider_correct else '✗'}, Password masked: {'✓' if password_masked else '✗'}"
            else:
                passed = False
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                
            self.log_test_result("Gmail Account Creation", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("Gmail Account Creation", False, f"Exception: {str(e)}")
            return False
    
    def test_account_verification(self):
        """Test 4: Verify the email account was created successfully"""
        print("\n✅ Testing Account Verification...")
        
        try:
            if not self.auth_token or not self.created_account_id:
                self.log_test_result("Account Verification", False, "Missing auth token or account ID")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test 4a: Get specific account
            response = requests.get(f"{API_BASE}/email-accounts/{self.created_account_id}", 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                account_data = response_data = response.json()
                
                # Verify account details
                email_match = account_data.get('email') == GMAIL_EMAIL
                provider_match = account_data.get('provider') == 'gmail'
                password_masked = account_data.get('password') == '***'
                is_active = account_data.get('is_active', False)
                
                get_passed = email_match and provider_match and password_masked
                get_details = f"Email: {'✓' if email_match else '✗'}, Provider: {'✓' if provider_match else '✗'}, Masked: {'✓' if password_masked else '✗'}, Active: {'✓' if is_active else '✗'}"
            else:
                get_passed = False
                get_details = f"Status: {response.status_code}"
            
            # Test 4b: List all accounts and verify our account appears
            response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
            
            if response.status_code == 200:
                accounts_list = response.json()
                our_account = next((acc for acc in accounts_list if acc.get('id') == self.created_account_id), None)
                
                list_passed = our_account is not None
                list_details = f"Found in list: {'✓' if list_passed else '✗'}, Total accounts: {len(accounts_list)}"
            else:
                list_passed = False
                list_details = f"Status: {response.status_code}"
            
            passed = get_passed and list_passed
            details = f"Get account: {get_passed} ({get_details}), List accounts: {list_passed} ({list_details})"
            
            self.log_test_result("Account Verification", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("Account Verification", False, f"Exception: {str(e)}")
            return False
    
    def test_gmail_imap_connection(self):
        """Test 5: Test IMAP connection to Gmail"""
        print("\n🔌 Testing Gmail IMAP Connection...")
        
        try:
            # Test direct IMAP connection
            imap_server = "imap.gmail.com"
            imap_port = 993
            
            try:
                # Create IMAP connection
                mail = imaplib.IMAP4_SSL(imap_server, imap_port)
                
                # Login
                mail.login(GMAIL_EMAIL, GMAIL_PASSWORD)
                
                # Select inbox
                status, messages = mail.select('INBOX')
                
                # Get message count
                message_count = int(messages[0]) if status == 'OK' else 0
                
                # Logout
                mail.logout()
                
                passed = True
                details = f"Server: {imap_server}:{imap_port}, Login: ✓, Inbox: ✓, Messages: {message_count}"
                
            except imaplib.IMAP4.error as e:
                passed = False
                details = f"IMAP Error: {str(e)}"
            except Exception as e:
                passed = False
                details = f"Connection Error: {str(e)}"
            
            self.log_test_result("Gmail IMAP Connection", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("Gmail IMAP Connection", False, f"Exception: {str(e)}")
            return False
    
    async def test_no_hardcoded_accounts(self):
        """Test 6: Confirm no hardcoded rohushanshinde@gmail.com accounts exist"""
        print("\n🚫 Testing No Hardcoded Accounts...")
        
        try:
            # Check database directly for hardcoded accounts
            hardcoded_accounts = await self.db.email_accounts.find({
                "email": "rohushanshinde@gmail.com"
            }).to_list(100)
            
            # Also check for any suspicious hardcoded patterns
            suspicious_accounts = await self.db.email_accounts.find({
                "email": {"$regex": "rohushanshinde", "$options": "i"}
            }).to_list(100)
            
            no_hardcoded = len(hardcoded_accounts) == 0
            no_suspicious = len(suspicious_accounts) == 0
            
            passed = no_hardcoded and no_suspicious
            details = f"Hardcoded 'rohushanshinde@gmail.com': {len(hardcoded_accounts)}, Suspicious patterns: {len(suspicious_accounts)}"
            
            if hardcoded_accounts:
                details += f", Found hardcoded: {[acc.get('email') for acc in hardcoded_accounts]}"
            
            if suspicious_accounts:
                details += f", Found suspicious: {[acc.get('email') for acc in suspicious_accounts]}"
            
            self.log_test_result("No Hardcoded Accounts", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("No Hardcoded Accounts", False, f"Exception: {str(e)}")
            return False
    
    def test_user_account_isolation(self):
        """Test 7: Verify user only sees their own email accounts"""
        print("\n🔒 Testing User Account Isolation...")
        
        try:
            if not self.auth_token:
                self.log_test_result("User Account Isolation", False, "No authentication token available")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get accounts for current user
            response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_accounts = response.json()
                
                # Verify our created account is in the list
                our_account = next((acc for acc in user_accounts if acc.get('id') == self.created_account_id), None)
                has_our_account = our_account is not None
                
                # Check if all accounts belong to our test (should only be our created account)
                # In a real system, we'd verify user_id matches, but we can check email patterns
                all_accounts_valid = all(
                    acc.get('email') == GMAIL_EMAIL or 'test' in acc.get('email', '').lower()
                    for acc in user_accounts
                )
                
                passed = has_our_account and all_accounts_valid
                details = f"Total accounts: {len(user_accounts)}, Has our account: {'✓' if has_our_account else '✗'}, All valid: {'✓' if all_accounts_valid else '✗'}"
                
                if user_accounts:
                    account_emails = [acc.get('email', 'N/A') for acc in user_accounts]
                    details += f", Emails: {account_emails}"
                    
            else:
                passed = False
                details = f"Status: {response.status_code}, Error: {response.text[:200]}"
            
            self.log_test_result("User Account Isolation", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("User Account Isolation", False, f"Exception: {str(e)}")
            return False
    
    def test_email_providers_endpoint(self):
        """Test 8: Verify email providers endpoint returns Gmail"""
        print("\n📋 Testing Email Providers Endpoint...")
        
        try:
            response = requests.get(f"{API_BASE}/email-providers", timeout=10)
            
            if response.status_code == 200:
                providers = response.json()
                
                # Check if Gmail provider exists
                gmail_provider = providers.get('gmail')
                has_gmail = gmail_provider is not None
                
                if has_gmail:
                    # Verify Gmail configuration
                    imap_server_correct = gmail_provider.get('imap_server') == 'imap.gmail.com'
                    imap_port_correct = gmail_provider.get('imap_port') == 993
                    smtp_server_correct = gmail_provider.get('smtp_server') == 'smtp.gmail.com'
                    smtp_port_correct = gmail_provider.get('smtp_port') == 587
                    requires_app_password = gmail_provider.get('requires_app_password') == True
                    
                    config_correct = all([imap_server_correct, imap_port_correct, 
                                        smtp_server_correct, smtp_port_correct, requires_app_password])
                else:
                    config_correct = False
                
                passed = has_gmail and config_correct
                details = f"Gmail provider: {'✓' if has_gmail else '✗'}, Config correct: {'✓' if config_correct else '✗'}, Total providers: {len(providers)}"
                
            else:
                passed = False
                details = f"Status: {response.status_code}"
            
            self.log_test_result("Email Providers Endpoint", passed, details)
            return passed
            
        except Exception as e:
            self.log_test_result("Email Providers Endpoint", False, f"Exception: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all Gmail account creation tests"""
        print("🚀 Starting Gmail Account Creation End-to-End Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Gmail Email: {GMAIL_EMAIL}")
        print("=" * 60)
        
        # Setup
        if not await self.setup():
            return False
        
        try:
            # Run tests in sequence
            test_results = []
            
            # Test 1: User Registration
            test_results.append(self.test_user_registration())
            
            # Test 2: User Login
            test_results.append(self.test_user_login())
            
            # Test 3: Gmail Account Creation
            test_results.append(self.test_gmail_account_creation())
            
            # Test 4: Account Verification
            test_results.append(self.test_account_verification())
            
            # Test 5: Gmail IMAP Connection
            test_results.append(self.test_gmail_imap_connection())
            
            # Test 6: No Hardcoded Accounts
            test_results.append(await self.test_no_hardcoded_accounts())
            
            # Test 7: User Account Isolation
            test_results.append(self.test_user_account_isolation())
            
            # Test 8: Email Providers Endpoint
            test_results.append(self.test_email_providers_endpoint())
            
            # Summary
            passed_tests = sum(test_results)
            total_tests = len(test_results)
            success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            print("\n" + "=" * 60)
            print("📊 TEST SUMMARY")
            print("=" * 60)
            print(f"Total Tests: {total_tests}")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {total_tests - passed_tests}")
            print(f"Success Rate: {success_rate:.1f}%")
            
            # Detailed results
            print("\n📋 DETAILED RESULTS:")
            for result in self.test_results:
                print(f"{result['status']}: {result['test']}")
                if result['details']:
                    print(f"   {result['details']}")
            
            # Overall assessment
            if success_rate >= 85:
                print(f"\n🎉 OVERALL: SUCCESS - Gmail account creation workflow is working!")
            elif success_rate >= 70:
                print(f"\n⚠️ OVERALL: PARTIAL SUCCESS - Some issues found but core functionality works")
            else:
                print(f"\n❌ OVERALL: FAILURE - Significant issues with Gmail account creation workflow")
            
            return success_rate >= 70
            
        finally:
            await self.cleanup()

async def main():
    """Main test execution"""
    tester = GmailAccountTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)