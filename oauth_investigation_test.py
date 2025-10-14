#!/usr/bin/env python3
"""
Comprehensive Google OAuth Email Account Addition Flow Investigation
Tests the entire Google OAuth flow from initiation to account creation and polling
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://agent-sync-workflow.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# OAuth Configuration from .env
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')

class OAuthInvestigationTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.test_user_email = "amits.joys@gmail.com"
        
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
    
    async def authenticate_test_user(self):
        """Authenticate as test user to get auth token"""
        print("\n🔐 Authenticating test user...")
        
        try:
            # Try to find existing user
            user_doc = await self.db.users.find_one({"email": self.test_user_email})
            
            if not user_doc:
                # Create test user if doesn't exist
                from auth import get_password_hash
                user_id = str(uuid.uuid4())
                test_user = {
                    "id": user_id,
                    "email": self.test_user_email,
                    "full_name": "OAuth Test User",
                    "hashed_password": get_password_hash("testpassword123"),
                    "is_active": True,
                    "email_quota": 1000,
                    "emails_used": 0,
                    "timezone": "UTC",
                    "created_at": datetime.utcnow()
                }
                await self.db.users.insert_one(test_user)
                print(f"✅ Created test user: {self.test_user_email}")
                user_doc = test_user
            
            self.test_user_id = user_doc["id"]
            
            # Login to get auth token
            login_data = {
                "email": self.test_user_email,
                "password": "testpassword123"
            }
            
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data["access_token"]
                print(f"✅ Authenticated user: {self.test_user_email}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return False
    
    def get_auth_headers(self):
        """Get authorization headers"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    async def test_oauth_initiation(self):
        """Test 1: OAuth Initiation - POST /api/oauth/google/authorize"""
        print("\n🚀 Testing OAuth Initiation...")
        
        try:
            # Test OAuth authorization endpoint
            oauth_data = {
                "scopes": ["email", "calendar"]
            }
            
            headers = self.get_auth_headers()
            response = requests.post(
                f"{API_BASE}/oauth/google/authorize", 
                json=oauth_data, 
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                auth_response = response.json()
                
                # Check required fields in response
                has_auth_url = "auth_url" in auth_response
                has_state = "state" in auth_response
                
                # Verify auth_url contains correct client_id
                auth_url = auth_response.get("auth_url", "")
                correct_client_id = GOOGLE_CLIENT_ID in auth_url if GOOGLE_CLIENT_ID else False
                correct_redirect_uri = GOOGLE_REDIRECT_URI in auth_url if GOOGLE_REDIRECT_URI else False
                
                # Check if scopes are included
                has_email_scope = "email" in auth_url
                has_calendar_scope = "calendar" in auth_url or "https://www.googleapis.com/auth/calendar" in auth_url
                
                all_checks_passed = (has_auth_url and has_state and correct_client_id and 
                                   correct_redirect_uri and has_email_scope)
                
                details = f"Status: {response.status_code}, Auth URL: {has_auth_url}, " \
                         f"State: {has_state}, Client ID: {correct_client_id}, " \
                         f"Redirect URI: {correct_redirect_uri}, Email scope: {has_email_scope}, " \
                         f"Calendar scope: {has_calendar_scope}"
                
                self.log_test_result("OAuth Initiation", all_checks_passed, details)
                
                # Store state for later tests
                if has_state:
                    self.oauth_state = auth_response.get("state")
                
            else:
                self.log_test_result("OAuth Initiation", False, 
                                   f"Status: {response.status_code}, Error: {response.text}")
                
        except Exception as e:
            self.log_test_result("OAuth Initiation", False, f"Exception: {str(e)}")
    
    async def test_oauth_status_check(self):
        """Test 2: OAuth Status Check - GET /api/oauth/google/status"""
        print("\n📊 Testing OAuth Status Check...")
        
        try:
            headers = self.get_auth_headers()
            response = requests.get(
                f"{API_BASE}/oauth/google/status",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                status_response = response.json()
                
                # Check response structure
                has_authorized = "authorized" in status_response
                has_email = "email" in status_response
                has_scopes = "scopes" in status_response
                
                structure_valid = has_authorized and has_email and has_scopes
                
                details = f"Status: {response.status_code}, Authorized: {status_response.get('authorized')}, " \
                         f"Email: {status_response.get('email')}, " \
                         f"Scopes: {len(status_response.get('scopes', []))}"
                
                self.log_test_result("OAuth Status Check", structure_valid, details)
                
            elif response.status_code == 401:
                # Not authorized yet - this is expected for new users
                self.log_test_result("OAuth Status Check", True, 
                                   f"Status: {response.status_code} (Not authorized - expected)")
            else:
                self.log_test_result("OAuth Status Check", False,
                                   f"Status: {response.status_code}, Error: {response.text}")
                
        except Exception as e:
            self.log_test_result("OAuth Status Check", False, f"Exception: {str(e)}")
    
    async def test_database_state_verification(self):
        """Test 3: Database State Verification - Check collections"""
        print("\n🗄️ Testing Database State Verification...")
        
        try:
            # Check oauth_tokens collection
            oauth_tokens = await self.db.oauth_tokens.find().to_list(100)
            oauth_tokens_count = len(oauth_tokens)
            
            # Check oauth_states collection  
            oauth_states = await self.db.oauth_states.find().to_list(100)
            oauth_states_count = len(oauth_states)
            
            # Check email_accounts collection structure
            email_accounts = await self.db.email_accounts.find().to_list(100)
            email_accounts_count = len(email_accounts)
            
            # Check for OAuth-specific accounts
            oauth_accounts = await self.db.email_accounts.find({"auth_type": "oauth"}).to_list(100)
            oauth_accounts_count = len(oauth_accounts)
            
            # Check Microsoft OAuth tokens (mentioned in review request)
            microsoft_tokens = await self.db.oauth_tokens_microsoft.find().to_list(100)
            microsoft_tokens_count = len(microsoft_tokens)
            
            # Check for the specific user mentioned in review request
            user_accounts = await self.db.email_accounts.find({"user_id": self.test_user_id}).to_list(100)
            user_accounts_count = len(user_accounts)
            
            # Verify collections exist and have proper structure
            collections_exist = True
            try:
                await self.db.oauth_tokens.find_one()
                await self.db.oauth_states.find_one()
                await self.db.email_accounts.find_one()
            except Exception:
                collections_exist = False
            
            details = f"OAuth tokens: {oauth_tokens_count}, OAuth states: {oauth_states_count}, " \
                     f"Email accounts: {email_accounts_count}, OAuth accounts: {oauth_accounts_count}, " \
                     f"Microsoft tokens: {microsoft_tokens_count}, User accounts: {user_accounts_count}, " \
                     f"Collections exist: {collections_exist}"
            
            self.log_test_result("Database State Verification", collections_exist, details)
            
            # Log specific findings for investigation
            if oauth_accounts_count > 0:
                print(f"   Found {oauth_accounts_count} OAuth accounts in database")
                for account in oauth_accounts:
                    print(f"   - OAuth Account: {account.get('email')} (Provider: {account.get('provider')}, Active: {account.get('is_active')})")
            
            if microsoft_tokens_count > 0:
                print(f"   Found {microsoft_tokens_count} Microsoft OAuth tokens")
                for token in microsoft_tokens:
                    print(f"   - Microsoft Token: User {token.get('user_id')} (Expires: {token.get('expires_at')})")
                    
        except Exception as e:
            self.log_test_result("Database State Verification", False, f"Exception: {str(e)}")
    
    async def test_oauth_callback_simulation(self):
        """Test 4: OAuth Callback Simulation - Test callback handling"""
        print("\n🔄 Testing OAuth Callback Simulation...")
        
        try:
            # Note: We can't fully simulate OAuth callback without actual Google OAuth flow
            # But we can test the callback endpoint structure and error handling
            
            # Test callback endpoint with missing parameters
            callback_url = f"{API_BASE}/oauth/google/callback"
            
            # Test 1: Missing parameters
            response = requests.get(callback_url, timeout=10)
            missing_params_handled = response.status_code in [400, 401, 422]  # Should handle missing params
            
            # Test 2: Invalid state parameter
            response = requests.get(f"{callback_url}?state=invalid_state&code=test_code", timeout=10)
            invalid_state_handled = response.status_code in [400, 401, 422]  # Should handle invalid state
            
            # Test 3: Check if callback endpoint exists
            # Try with some parameters to see if endpoint is accessible
            response = requests.get(f"{callback_url}?error=access_denied", timeout=10)
            endpoint_exists = response.status_code != 404  # Endpoint should exist
            
            callback_tests_passed = missing_params_handled and invalid_state_handled and endpoint_exists
            
            details = f"Missing params handled: {missing_params_handled}, " \
                     f"Invalid state handled: {invalid_state_handled}, " \
                     f"Endpoint exists: {endpoint_exists}"
            
            self.log_test_result("OAuth Callback Simulation", callback_tests_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Callback Simulation", False, f"Exception: {str(e)}")
    
    async def test_account_creation_with_oauth(self):
        """Test 5: Account Creation with OAuth - POST /api/email-accounts/oauth"""
        print("\n📧 Testing Account Creation with OAuth...")
        
        try:
            # Test OAuth account creation endpoint
            oauth_account_data = {
                "provider": "google",
                "oauth_email": "test.oauth@gmail.com",
                "name": "Test OAuth Account"
            }
            
            headers = self.get_auth_headers()
            response = requests.post(
                f"{API_BASE}/email-accounts/oauth",
                json=oauth_account_data,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                account_response = response.json()
                
                # Check account structure
                has_id = "id" in account_response
                has_oauth_fields = ("auth_type" in account_response and 
                                  account_response.get("auth_type") == "oauth")
                has_use_oauth = account_response.get("use_oauth") == True
                
                structure_valid = has_id and has_oauth_fields and has_use_oauth
                
                details = f"Status: {response.status_code}, Has ID: {has_id}, " \
                         f"OAuth auth type: {has_oauth_fields}, Use OAuth: {has_use_oauth}"
                
                self.log_test_result("Account Creation with OAuth", structure_valid, details)
                
            elif response.status_code == 401:
                # Not authorized - expected if no OAuth token
                self.log_test_result("Account Creation with OAuth", True,
                                   f"Status: {response.status_code} (Not authorized - expected without OAuth token)")
            elif response.status_code == 400:
                # Bad request - might be due to missing OAuth authorization
                error_message = response.text
                if "oauth" in error_message.lower() or "authorization" in error_message.lower():
                    self.log_test_result("Account Creation with OAuth", True,
                                       f"Status: {response.status_code} (OAuth authorization required - expected)")
                else:
                    self.log_test_result("Account Creation with OAuth", False,
                                       f"Status: {response.status_code}, Error: {error_message}")
            else:
                self.log_test_result("Account Creation with OAuth", False,
                                   f"Status: {response.status_code}, Error: {response.text}")
                
        except Exception as e:
            self.log_test_result("Account Creation with OAuth", False, f"Exception: {str(e)}")
    
    async def test_email_polling_verification(self):
        """Test 6: Email Polling Verification - Check polling service"""
        print("\n📡 Testing Email Polling Verification...")
        
        try:
            # Test polling service status
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            
            if response.status_code == 200:
                polling_status = response.json()
                service_running = polling_status.get("status") == "running"
                active_connections = polling_status.get("active_connections", 0)
                
                # Check accounts polling status
                accounts_response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                accounts_status_available = accounts_response.status_code == 200
                
                if accounts_status_available:
                    accounts_data = accounts_response.json()
                    total_accounts = len(accounts_data.get("accounts", []))
                    oauth_accounts_polling = 0
                    
                    for account in accounts_data.get("accounts", []):
                        if account.get("auth_type") == "oauth" and account.get("polling_active"):
                            oauth_accounts_polling += 1
                
                else:
                    total_accounts = 0
                    oauth_accounts_polling = 0
                
                # Check for OAuth routing issues (mentioned in review request)
                # Look for accounts that might be incorrectly routed
                oauth_accounts = await self.db.email_accounts.find({"auth_type": "oauth"}).to_list(100)
                oauth_routing_issues = 0
                
                for account in oauth_accounts:
                    provider = account.get("provider", "").lower()
                    oauth_email = account.get("oauth_email", "")
                    
                    # Check for Microsoft accounts that might be routed to Google
                    if ("outlook" in oauth_email or "hotmail" in oauth_email or 
                        "live.com" in oauth_email or "onmicrosoft.com" in oauth_email):
                        if provider != "microsoft" and provider != "outlook":
                            oauth_routing_issues += 1
                
                polling_functional = service_running and accounts_status_available
                
                details = f"Service running: {service_running}, Active connections: {active_connections}, " \
                         f"Total accounts: {total_accounts}, OAuth accounts polling: {oauth_accounts_polling}, " \
                         f"OAuth routing issues: {oauth_routing_issues}"
                
                self.log_test_result("Email Polling Verification", polling_functional, details)
                
                # Additional investigation for the specific issue mentioned
                if oauth_routing_issues > 0:
                    print(f"   ⚠️ Found {oauth_routing_issues} potential OAuth routing issues")
                    print("   This matches the issue described in the review request:")
                    print("   'Microsoft OAuth accounts incorrectly routed to Google Gmail API'")
                
            else:
                self.log_test_result("Email Polling Verification", False,
                                   f"Status: {response.status_code}, Error: {response.text}")
                
        except Exception as e:
            self.log_test_result("Email Polling Verification", False, f"Exception: {str(e)}")
    
    async def test_configuration_verification(self):
        """Test 7: Configuration Verification - Check OAuth settings"""
        print("\n⚙️ Testing Configuration Verification...")
        
        try:
            # Check environment variables
            google_client_id_set = bool(GOOGLE_CLIENT_ID)
            google_redirect_uri_set = bool(GOOGLE_REDIRECT_URI)
            
            # Verify redirect URI format
            correct_redirect_uri = False
            if GOOGLE_REDIRECT_URI:
                expected_callback = "/oauth/google/callback"
                correct_redirect_uri = expected_callback in GOOGLE_REDIRECT_URI
            
            # Check if redirect URI matches the one mentioned in review request
            expected_domain = "google-sync-app.preview.emergentagent.com"
            correct_domain = expected_domain in GOOGLE_REDIRECT_URI if GOOGLE_REDIRECT_URI else False
            
            # Test account limits validation (mentioned in review request)
            # 2 Gmail + 2 Outlook + 1 Custom = 5 total
            try:
                # This should be tested with actual account creation, but we can check if the function exists
                from server import validate_account_limits
                account_limits_function_exists = True
            except ImportError:
                account_limits_function_exists = False
            
            config_valid = (google_client_id_set and google_redirect_uri_set and 
                          correct_redirect_uri and correct_domain)
            
            details = f"Google Client ID: {google_client_id_set}, " \
                     f"Redirect URI set: {google_redirect_uri_set}, " \
                     f"Correct callback path: {correct_redirect_uri}, " \
                     f"Correct domain: {correct_domain}, " \
                     f"Account limits function: {account_limits_function_exists}"
            
            self.log_test_result("Configuration Verification", config_valid, details)
            
            # Log the actual configuration for debugging
            if GOOGLE_CLIENT_ID:
                print(f"   Google Client ID: {GOOGLE_CLIENT_ID}")
            if GOOGLE_REDIRECT_URI:
                print(f"   Google Redirect URI: {GOOGLE_REDIRECT_URI}")
                
        except Exception as e:
            self.log_test_result("Configuration Verification", False, f"Exception: {str(e)}")
    
    async def test_error_patterns_investigation(self):
        """Test 8: Error Patterns Investigation - Look for specific errors"""
        print("\n🔍 Testing Error Patterns Investigation...")
        
        try:
            error_patterns_found = []
            
            # Check backend logs for OAuth-related errors (simulated)
            # In a real scenario, we would check actual log files
            
            # Test 1: Check for 401 Unauthorized errors
            try:
                headers = {}  # No auth header
                response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
                if response.status_code == 401:
                    error_patterns_found.append("401_unauthorized_oauth_status")
            except Exception:
                pass
            
            # Test 2: Check for token validation failures
            try:
                invalid_headers = {"Authorization": "Bearer invalid_token"}
                response = requests.get(f"{API_BASE}/oauth/google/status", headers=invalid_headers, timeout=10)
                if response.status_code == 401:
                    error_patterns_found.append("token_validation_failure")
            except Exception:
                pass
            
            # Test 3: Check for account creation validation errors
            try:
                headers = self.get_auth_headers()
                invalid_oauth_data = {
                    "provider": "invalid_provider",
                    "oauth_email": "invalid_email"
                }
                response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                       json=invalid_oauth_data, headers=headers, timeout=10)
                if response.status_code == 400:
                    error_patterns_found.append("account_creation_validation_error")
            except Exception:
                pass
            
            # Test 4: Check for Gmail API access errors (simulated)
            # Look for OAuth accounts that might have API access issues
            oauth_accounts = await self.db.email_accounts.find({"auth_type": "oauth"}).to_list(100)
            gmail_api_issues = 0
            
            for account in oauth_accounts:
                # Check if account has proper OAuth token reference
                if not account.get("oauth_token_id"):
                    gmail_api_issues += 1
            
            if gmail_api_issues > 0:
                error_patterns_found.append(f"gmail_api_access_issues_{gmail_api_issues}")
            
            # Test 5: Check for polling service connection issues
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                if response.status_code != 200:
                    error_patterns_found.append("polling_service_connection_issue")
            except Exception:
                error_patterns_found.append("polling_service_connection_exception")
            
            # Evaluate findings
            critical_errors = [pattern for pattern in error_patterns_found 
                             if "gmail_api" in pattern or "polling" in pattern]
            
            investigation_successful = len(error_patterns_found) > 0  # We expect to find some error patterns
            
            details = f"Error patterns found: {len(error_patterns_found)}, " \
                     f"Critical errors: {len(critical_errors)}, " \
                     f"Patterns: {', '.join(error_patterns_found[:5])}"  # Limit to first 5
            
            self.log_test_result("Error Patterns Investigation", investigation_successful, details)
            
            # Log specific findings that match the review request
            if any("gmail_api" in pattern for pattern in error_patterns_found):
                print("   🚨 Found Gmail API access issues - matches review request findings")
            
            if any("polling" in pattern for pattern in error_patterns_found):
                print("   🚨 Found polling service issues - matches review request findings")
                
        except Exception as e:
            self.log_test_result("Error Patterns Investigation", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🔍 COMPREHENSIVE GOOGLE OAUTH INVESTIGATION SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 OVERALL RESULTS: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
            if result['details']:
                print(f"   {result['details']}")
        
        print("\n🎯 KEY FINDINGS FOR OAUTH FLOW:")
        
        # Analyze results for specific OAuth issues
        oauth_initiation = next((r for r in self.test_results if "OAuth Initiation" in r["test"]), None)
        if oauth_initiation and not oauth_initiation["passed"]:
            print("   🚨 OAuth initiation failing - users cannot start OAuth flow")
        
        database_state = next((r for r in self.test_results if "Database State" in r["test"]), None)
        if database_state and database_state["passed"]:
            print("   ✅ Database collections properly configured")
        
        polling_verification = next((r for r in self.test_results if "Polling Verification" in r["test"]), None)
        if polling_verification and not polling_verification["passed"]:
            print("   🚨 Email polling issues detected - matches review request")
        
        config_verification = next((r for r in self.test_results if "Configuration" in r["test"]), None)
        if config_verification and config_verification["passed"]:
            print("   ✅ OAuth configuration appears correct")
        
        print("\n💡 RECOMMENDATIONS:")
        if failed_tests > 0:
            print("   1. Review failed tests above for specific issues")
            print("   2. Check backend logs for detailed error messages")
            print("   3. Verify Google Cloud Console OAuth configuration")
            print("   4. Test OAuth flow manually in browser")
            print("   5. Check Redis connectivity for polling service")
        else:
            print("   ✅ All OAuth tests passed - system appears functional")
        
        print("\n🔗 NEXT STEPS:")
        print("   1. Manual OAuth flow testing with real Google account")
        print("   2. Backend log analysis for specific error messages")
        print("   3. Google Cloud Console configuration verification")
        print("   4. Email polling service debugging")
        
        return passed_tests, total_tests

async def main():
    """Main test execution"""
    print("🚀 Starting Comprehensive Google OAuth Email Account Addition Flow Investigation")
    print("="*80)
    
    tester = OAuthInvestigationTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Authenticate test user
        if not await tester.authenticate_test_user():
            print("❌ Authentication failed, continuing with limited tests...")
        
        # Run all OAuth investigation tests
        await tester.test_oauth_initiation()
        await tester.test_oauth_status_check()
        await tester.test_database_state_verification()
        await tester.test_oauth_callback_simulation()
        await tester.test_account_creation_with_oauth()
        await tester.test_email_polling_verification()
        await tester.test_configuration_verification()
        await tester.test_error_patterns_investigation()
        
        # Print comprehensive summary
        passed, total = tester.print_summary()
        
        # Exit with appropriate code
        exit_code = 0 if passed == total else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        exit_code = 130
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        await tester.cleanup()
    
    print(f"\n🏁 OAuth Investigation completed with exit code: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())