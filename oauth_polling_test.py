#!/usr/bin/env python3
"""
OAuth and Email Polling Investigation Test
Specifically tests the issues mentioned in the review request:
- User logged in as amits.joys@gmail.com
- Added Outlook OAuth account "amits.joys@outlook.com"  
- Email polling and processing flows not starting
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://redis-worker-setup.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test user credentials from review request
TEST_USER_EMAIL = "amits.joys@gmail.com"
TEST_USER_PASSWORD = "ij@123"
OAUTH_ACCOUNT_EMAIL = "amits.joys@outlook.com"

class OAuthPollingTester:
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
    
    async def authenticate_user(self):
        """Authenticate the test user and get auth token"""
        print(f"\n🔐 Authenticating user: {TEST_USER_EMAIL}")
        
        try:
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                auth_response = response.json()
                self.auth_token = auth_response.get('access_token')
                user_data = auth_response.get('user', {})
                self.test_user_id = user_data.get('id')
                
                self.log_test_result("User Authentication", True, 
                                   f"Successfully authenticated {TEST_USER_EMAIL}, User ID: {self.test_user_id}")
                return True
            else:
                self.log_test_result("User Authentication", False, 
                                   f"Login failed - Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("User Authentication", False, f"Authentication error: {str(e)}")
            return False
    
    def get_auth_headers(self):
        """Get authentication headers"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    async def test_polling_status(self):
        """Test 1: Check current email polling status via GET /api/polling/status"""
        print("\n📡 Testing Email Polling Status...")
        
        try:
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                polling_status = status_data.get('status')
                active_connections = status_data.get('active_connections', 0)
                
                is_running = polling_status == 'running'
                has_connections = active_connections > 0
                
                self.log_test_result("Polling Status Check", True, 
                                   f"Status: {polling_status}, Active connections: {active_connections}")
                
                # Additional check for polling service health
                if not is_running:
                    self.log_test_result("Polling Service Running", False, 
                                       "Polling service is not running - this may be why emails aren't being processed")
                else:
                    self.log_test_result("Polling Service Running", True, 
                                       f"Polling service is running with {active_connections} connections")
                
                return is_running
            else:
                self.log_test_result("Polling Status Check", False, 
                                   f"Failed to get polling status - Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Polling Status Check", False, f"Error: {str(e)}")
            return False
    
    async def test_oauth_microsoft_status(self):
        """Test 2: Check OAuth account status for Microsoft via GET /api/oauth/microsoft/status"""
        print("\n🔗 Testing Microsoft OAuth Status...")
        
        try:
            headers = self.get_auth_headers()
            response = requests.get(f"{API_BASE}/oauth/microsoft/status", headers=headers, timeout=10)
            
            if response.status_code == 200:
                oauth_data = response.json()
                self.log_test_result("Microsoft OAuth Status", True, 
                                   f"OAuth status retrieved: {json.dumps(oauth_data, indent=2)}")
                
                # Check if user has Microsoft OAuth configured
                has_oauth = oauth_data.get('connected', False) or oauth_data.get('authorized', False)
                if has_oauth:
                    self.log_test_result("Microsoft OAuth Connected", True, 
                                       "Microsoft OAuth account is connected")
                else:
                    self.log_test_result("Microsoft OAuth Connected", False, 
                                       "Microsoft OAuth account not connected - this may be the issue")
                
                return has_oauth
            elif response.status_code == 403:
                self.log_test_result("Microsoft OAuth Status", False, 
                                   "Access denied - user may not be properly authenticated")
                return False
            else:
                self.log_test_result("Microsoft OAuth Status", False, 
                                   f"Failed to get OAuth status - Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test_result("Microsoft OAuth Status", False, f"Error: {str(e)}")
            return False
    
    async def test_email_accounts_list(self):
        """Test 3: List all email accounts for the user via GET /api/email-accounts"""
        print("\n📧 Testing Email Accounts List...")
        
        try:
            headers = self.get_auth_headers()
            response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
            
            if response.status_code == 200:
                accounts = response.json()
                account_count = len(accounts)
                
                self.log_test_result("Email Accounts List", True, 
                                   f"Retrieved {account_count} email accounts")
                
                # Look for the specific OAuth account mentioned in review request
                oauth_account_found = False
                manual_accounts = []
                oauth_accounts = []
                active_accounts = []
                
                for account in accounts:
                    email = account.get('email', '')
                    auth_type = account.get('auth_type', 'manual')
                    is_active = account.get('is_active', False)
                    use_oauth = account.get('use_oauth', False)
                    
                    if email == OAUTH_ACCOUNT_EMAIL:
                        oauth_account_found = True
                        self.log_test_result("Outlook OAuth Account Found", True, 
                                           f"Found {OAUTH_ACCOUNT_EMAIL} - Auth type: {auth_type}, OAuth: {use_oauth}, Active: {is_active}")
                    
                    if auth_type == 'oauth' or use_oauth:
                        oauth_accounts.append(account)
                    else:
                        manual_accounts.append(account)
                    
                    if is_active:
                        active_accounts.append(account)
                
                if not oauth_account_found:
                    self.log_test_result("Outlook OAuth Account Found", False, 
                                       f"OAuth account {OAUTH_ACCOUNT_EMAIL} not found in user's accounts")
                
                self.log_test_result("Account Types Analysis", True, 
                                   f"Manual accounts: {len(manual_accounts)}, OAuth accounts: {len(oauth_accounts)}, Active accounts: {len(active_accounts)}")
                
                # Print detailed account information
                print("   📋 Account Details:")
                for i, account in enumerate(accounts):
                    print(f"      {i+1}. {account.get('email')} - {account.get('auth_type', 'manual')} - {'Active' if account.get('is_active') else 'Inactive'}")
                
                return accounts
            else:
                self.log_test_result("Email Accounts List", False, 
                                   f"Failed to get email accounts - Status: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_test_result("Email Accounts List", False, f"Error: {str(e)}")
            return []
    
    async def test_polling_configuration(self, accounts):
        """Test 4: Check if there are any email accounts configured for polling"""
        print("\n⚙️ Testing Email Account Polling Configuration...")
        
        try:
            if not accounts:
                self.log_test_result("Polling Configuration", False, "No email accounts to check")
                return False
            
            polling_configured_count = 0
            oauth_polling_count = 0
            
            for account in accounts:
                account_id = account.get('id')
                email = account.get('email')
                is_active = account.get('is_active', False)
                auth_type = account.get('auth_type', 'manual')
                use_oauth = account.get('use_oauth', False)
                
                # Check individual account polling status
                try:
                    headers = self.get_auth_headers()
                    polling_data = {"action": "status"}
                    response = requests.post(f"{API_BASE}/email-accounts/{account_id}/polling", 
                                           json=polling_data, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        polling_status = response.json()
                        polling_active = polling_status.get('polling_active', False)
                        has_connection = polling_status.get('has_connection', False)
                        last_polled = polling_status.get('last_polled')
                        
                        if polling_active:
                            polling_configured_count += 1
                        
                        if (auth_type == 'oauth' or use_oauth) and polling_active:
                            oauth_polling_count += 1
                        
                        status_msg = f"Email: {email}, Active: {is_active}, Polling: {polling_active}, Connection: {has_connection}"
                        if last_polled:
                            status_msg += f", Last polled: {last_polled}"
                        
                        self.log_test_result(f"Account Polling - {email}", polling_active, status_msg)
                        
                        # Special attention to the OAuth account from review request
                        if email == OAUTH_ACCOUNT_EMAIL:
                            if not polling_active:
                                self.log_test_result("OAuth Account Polling Issue", False, 
                                                   f"CRITICAL: {OAUTH_ACCOUNT_EMAIL} is not configured for polling - this is likely the root cause")
                            else:
                                self.log_test_result("OAuth Account Polling Issue", True, 
                                                   f"{OAUTH_ACCOUNT_EMAIL} is properly configured for polling")
                    else:
                        self.log_test_result(f"Account Polling - {email}", False, 
                                           f"Failed to get polling status - Status: {response.status_code}")
                        
                except Exception as e:
                    self.log_test_result(f"Account Polling - {email}", False, f"Error: {str(e)}")
            
            overall_success = polling_configured_count > 0
            self.log_test_result("Overall Polling Configuration", overall_success, 
                               f"Accounts with polling enabled: {polling_configured_count}/{len(accounts)}, OAuth accounts polling: {oauth_polling_count}")
            
            return overall_success
            
        except Exception as e:
            self.log_test_result("Polling Configuration", False, f"Error: {str(e)}")
            return False
    
    async def test_oauth_account_creation_process(self):
        """Test 5: Test email account creation/configuration process for OAuth"""
        print("\n🔧 Testing OAuth Account Creation Process...")
        
        try:
            # Check if OAuth endpoints are accessible
            headers = self.get_auth_headers()
            
            # Test Google OAuth endpoints
            try:
                response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
                google_oauth_accessible = response.status_code in [200, 403]  # 403 means endpoint exists but not authorized
                self.log_test_result("Google OAuth Endpoint", google_oauth_accessible, 
                                   f"Google OAuth status endpoint - Status: {response.status_code}")
            except Exception as e:
                google_oauth_accessible = False
                self.log_test_result("Google OAuth Endpoint", False, f"Error: {str(e)}")
            
            # Test Microsoft OAuth endpoints
            try:
                response = requests.get(f"{API_BASE}/oauth/microsoft/status", headers=headers, timeout=10)
                microsoft_oauth_accessible = response.status_code in [200, 403]
                self.log_test_result("Microsoft OAuth Endpoint", microsoft_oauth_accessible, 
                                   f"Microsoft OAuth status endpoint - Status: {response.status_code}")
            except Exception as e:
                microsoft_oauth_accessible = False
                self.log_test_result("Microsoft OAuth Endpoint", False, f"Error: {str(e)}")
            
            # Test OAuth account creation endpoint
            try:
                # This should fail with validation error, but endpoint should be accessible
                test_oauth_data = {
                    "provider": "microsoft",
                    "auth_type": "oauth"
                }
                response = requests.post(f"{API_BASE}/email-accounts/oauth", json=test_oauth_data, headers=headers, timeout=10)
                oauth_creation_accessible = response.status_code in [400, 422, 500]  # Endpoint exists but expects proper OAuth flow
                self.log_test_result("OAuth Account Creation Endpoint", oauth_creation_accessible, 
                                   f"OAuth account creation endpoint - Status: {response.status_code}")
            except Exception as e:
                oauth_creation_accessible = False
                self.log_test_result("OAuth Account Creation Endpoint", False, f"Error: {str(e)}")
            
            overall_success = google_oauth_accessible and microsoft_oauth_accessible
            self.log_test_result("OAuth Infrastructure", overall_success, 
                               f"OAuth endpoints accessible: Google={google_oauth_accessible}, Microsoft={microsoft_oauth_accessible}")
            
            return overall_success
            
        except Exception as e:
            self.log_test_result("OAuth Account Creation Process", False, f"Error: {str(e)}")
            return False
    
    async def test_background_services(self):
        """Test 6: Check any background services or workers that should be running"""
        print("\n🔄 Testing Background Services and Workers...")
        
        try:
            # Test RQ (Redis Queue) status if available
            rq_status = False
            try:
                # Check if we can import RQ components
                sys.path.append('/app/backend')
                from tasks import get_queue_stats, redis_conn
                
                # Try to get queue statistics
                queue_stats = get_queue_stats()
                if queue_stats:
                    rq_status = True
                    self.log_test_result("RQ Workers Status", True, 
                                       f"RQ queue stats: {json.dumps(queue_stats, indent=2)}")
                else:
                    self.log_test_result("RQ Workers Status", False, "RQ queue stats not available")
                    
            except ImportError:
                self.log_test_result("RQ Workers Status", False, "RQ not available - using fallback background tasks")
            except Exception as e:
                self.log_test_result("RQ Workers Status", False, f"RQ error: {str(e)}")
            
            # Check database for background task indicators
            try:
                # Check for recent email processing activity
                recent_emails = await self.db.emails.find().sort("created_at", -1).limit(10).to_list(10)
                recent_processing = len([e for e in recent_emails if e.get('status') in ['classifying', 'drafting', 'validating']])
                
                self.log_test_result("Recent Email Processing", recent_processing > 0, 
                                   f"Found {recent_processing} emails in processing states out of {len(recent_emails)} recent emails")
                
                # Check for follow-up emails (indicates background processing)
                follow_ups = await self.db.follow_up_emails.find().limit(5).to_list(5)
                follow_up_processing = len(follow_ups) > 0
                
                self.log_test_result("Follow-up Processing", follow_up_processing, 
                                   f"Found {len(follow_ups)} follow-up emails in database")
                
            except Exception as e:
                self.log_test_result("Database Background Activity", False, f"Error checking database: {str(e)}")
            
            # Test polling service control endpoints
            try:
                response = requests.post(f"{API_BASE}/polling/control", json={"action": "status"}, timeout=10)
                polling_control_accessible = response.status_code == 200
                
                if polling_control_accessible:
                    control_data = response.json()
                    self.log_test_result("Polling Control Service", True, 
                                       f"Polling control response: {json.dumps(control_data)}")
                else:
                    self.log_test_result("Polling Control Service", False, 
                                       f"Polling control not accessible - Status: {response.status_code}")
                    
            except Exception as e:
                self.log_test_result("Polling Control Service", False, f"Error: {str(e)}")
            
            return True
            
        except Exception as e:
            self.log_test_result("Background Services", False, f"Error: {str(e)}")
            return False
    
    async def test_email_processing_workflow(self):
        """Test 7: Test the complete email processing workflow from polling to AI response"""
        print("\n🤖 Testing Complete Email Processing Workflow...")
        
        try:
            # Get user's email accounts
            headers = self.get_auth_headers()
            accounts_response = requests.get(f"{API_BASE}/email-accounts", headers=headers, timeout=10)
            
            if accounts_response.status_code != 200 or not accounts_response.json():
                self.log_test_result("Email Processing Workflow", False, "No email accounts available for testing")
                return False
            
            accounts = accounts_response.json()
            test_account = accounts[0]  # Use first available account
            
            # Test email processing via test endpoint
            test_email_data = {
                "subject": "OAuth Polling Test - Urgent Business Inquiry",
                "body": f"Hello, I'm testing the email processing workflow for user {TEST_USER_EMAIL}. This email should trigger the complete AI processing pipeline including classification, draft generation, and validation. Please respond with pricing information for your services. This is specifically testing the OAuth account {OAUTH_ACCOUNT_EMAIL} integration and polling functionality.",
                "sender": "oauth.test@businessclient.com",
                "account_id": test_account['id']
            }
            
            print(f"   Testing with account: {test_account.get('email')} (ID: {test_account.get('id')})")
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, headers=headers, timeout=60)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    email_id = processed_email.get('email_id')
                    processing_status = processed_email.get('status', 'unknown')
                    processing_method = processed_email.get('processing_method', 'unknown')
                    
                    self.log_test_result("Email Processing API", True, 
                                       f"Email queued successfully - ID: {email_id}, Status: {processing_status}, Method: {processing_method}")
                    
                    # Wait a bit and check processing status
                    if email_id:
                        await asyncio.sleep(5)  # Give it time to process
                        
                        try:
                            status_response = requests.get(f"{API_BASE}/emails/{email_id}", headers=headers, timeout=10)
                            if status_response.status_code == 200:
                                email_status = status_response.json()
                                current_status = email_status.get('status', 'unknown')
                                has_intents = bool(email_status.get('intents'))
                                has_draft = bool(email_status.get('draft'))
                                has_validation = bool(email_status.get('validation_result'))
                                
                                workflow_progress = f"Status: {current_status}, Intents: {has_intents}, Draft: {has_draft}, Validation: {has_validation}"
                                
                                # Check if processing completed successfully
                                processing_successful = current_status in ['ready_to_send', 'sent', 'needs_redraft']
                                ai_components_working = has_intents or has_draft
                                
                                self.log_test_result("Email Processing Progress", processing_successful or ai_components_working, 
                                                   workflow_progress)
                                
                                if current_status == 'error':
                                    error_msg = email_status.get('error', 'Unknown error')
                                    self.log_test_result("Email Processing Error", False, 
                                                       f"Processing failed with error: {error_msg}")
                                elif current_status in ['classifying', 'drafting', 'validating']:
                                    self.log_test_result("Email Processing In Progress", True, 
                                                       f"Email is still processing: {current_status}")
                                
                            else:
                                self.log_test_result("Email Status Check", False, 
                                                   f"Failed to get email status - Status: {status_response.status_code}")
                        except Exception as e:
                            self.log_test_result("Email Status Check", False, f"Error checking status: {str(e)}")
                    
                    return True
                else:
                    error_details = f"Status: {response.status_code}, Response: {response.text[:500]}"
                    self.log_test_result("Email Processing API", False, error_details)
                    return False
                    
            except Exception as e:
                self.log_test_result("Email Processing API", False, f"Error: {str(e)}")
                return False
                
        except Exception as e:
            self.log_test_result("Email Processing Workflow", False, f"Error: {str(e)}")
            return False
    
    async def test_oauth_callback_errors(self):
        """Test 8: Investigate 400 Bad Request errors in Microsoft OAuth callback"""
        print("\n🔍 Testing OAuth Callback Error Investigation...")
        
        try:
            # Check OAuth callback endpoints
            callback_endpoints = [
                "/oauth/google/callback",
                "/oauth/microsoft/callback"
            ]
            
            for endpoint in callback_endpoints:
                try:
                    # Test with invalid parameters to see error handling
                    response = requests.get(f"{API_BASE}{endpoint}?code=invalid&state=test", timeout=10)
                    
                    # We expect this to fail, but we want to see how it fails
                    error_handling_ok = response.status_code in [400, 401, 403, 422]
                    
                    self.log_test_result(f"OAuth Callback Error Handling - {endpoint}", error_handling_ok, 
                                       f"Status: {response.status_code}, Response: {response.text[:200]}")
                    
                    if response.status_code == 400:
                        # This is the error mentioned in the review request
                        self.log_test_result("OAuth 400 Bad Request Investigation", True, 
                                           f"Found 400 Bad Request in {endpoint}: {response.text[:300]}")
                    
                except Exception as e:
                    self.log_test_result(f"OAuth Callback - {endpoint}", False, f"Error: {str(e)}")
            
            # Check OAuth configuration in environment
            oauth_config_complete = True
            required_oauth_vars = [
                'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI',
                'MICROSOFT_CLIENT_ID', 'MICROSOFT_CLIENT_SECRET', 'MICROSOFT_TENANT_ID', 'MICROSOFT_REDIRECT_URI'
            ]
            
            missing_vars = []
            for var in required_oauth_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)
                    oauth_config_complete = False
            
            if oauth_config_complete:
                self.log_test_result("OAuth Configuration", True, "All OAuth environment variables are configured")
            else:
                self.log_test_result("OAuth Configuration", False, f"Missing OAuth variables: {missing_vars}")
            
            return oauth_config_complete
            
        except Exception as e:
            self.log_test_result("OAuth Callback Error Investigation", False, f"Error: {str(e)}")
            return False
    
    async def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting OAuth and Email Polling Investigation")
        print(f"Target User: {TEST_USER_EMAIL}")
        print(f"OAuth Account: {OAUTH_ACCOUNT_EMAIL}")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 80)
        
        # Setup
        if not await self.setup():
            return
        
        # Authenticate user
        if not await self.authenticate_user():
            print("❌ Cannot proceed without authentication")
            return
        
        # Run all tests
        await self.test_polling_status()
        await self.test_oauth_microsoft_status()
        accounts = await self.test_email_accounts_list()
        await self.test_polling_configuration(accounts)
        await self.test_oauth_account_creation_process()
        await self.test_background_services()
        await self.test_email_processing_workflow()
        await self.test_oauth_callback_errors()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📈 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if failed_tests:
            print("\n🔍 CRITICAL ISSUES IDENTIFIED:")
            for test in failed_tests:
                print(f"   ❌ {test['test']}: {test['details']}")
        
        print("\n🎯 ROOT CAUSE ANALYSIS:")
        
        # Analyze results for root cause
        polling_issues = [r for r in self.test_results if 'polling' in r['test'].lower() and not r['passed']]
        oauth_issues = [r for r in self.test_results if 'oauth' in r['test'].lower() and not r['passed']]
        
        if polling_issues:
            print("   📡 POLLING ISSUES DETECTED:")
            for issue in polling_issues:
                print(f"      - {issue['test']}: {issue['details']}")
        
        if oauth_issues:
            print("   🔗 OAUTH ISSUES DETECTED:")
            for issue in oauth_issues:
                print(f"      - {issue['test']}: {issue['details']}")
        
        # Cleanup
        await self.cleanup()

async def main():
    tester = OAuthPollingTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())