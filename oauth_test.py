#!/usr/bin/env python3
"""
OAuth Integration Testing for Microsoft and Google OAuth Endpoints
Tests Microsoft OAuth endpoints, Google OAuth endpoints, and OAuth-based account creation
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

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-sync-fix-2.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class OAuthTester:
    def __init__(self):
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        
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
    
    async def setup_test_user(self):
        """Create or login test user for OAuth testing"""
        print("\n🔐 Setting up test user for OAuth testing...")
        
        # Try to register a test user
        test_user_data = {
            "email": f"oauth.test.{int(time.time())}@example.com",
            "password": "OAuthTest123!",
            "full_name": "OAuth Test User"
        }
        
        try:
            # Try to register
            response = requests.post(f"{API_BASE}/auth/register", json=test_user_data, timeout=10)
            if response.status_code in [200, 201]:
                auth_data = response.json()
                self.auth_token = auth_data.get('access_token')
                self.test_user_id = auth_data.get('user', {}).get('id')
                print(f"✅ Test user registered: {test_user_data['email']}")
                return True
            else:
                # Try to login instead
                login_data = {
                    "email": test_user_data['email'],
                    "password": test_user_data['password']
                }
                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                if response.status_code == 200:
                    auth_data = response.json()
                    self.auth_token = auth_data.get('access_token')
                    self.test_user_id = auth_data.get('user', {}).get('id')
                    print(f"✅ Test user logged in: {test_user_data['email']}")
                    return True
                else:
                    print(f"❌ Failed to setup test user: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Error setting up test user: {str(e)}")
            return False
    
    def get_auth_headers(self):
        """Get authorization headers for API requests"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    def test_microsoft_oauth_endpoints(self):
        """Test Microsoft OAuth endpoints"""
        print("\n🔵 Testing Microsoft OAuth Endpoints...")
        
        headers = self.get_auth_headers()
        
        # Test 1: POST /api/oauth/microsoft/authorize with email scope
        try:
            email_auth_data = ["email"]
            response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", 
                                   json=email_auth_data, headers=headers, timeout=10)
            
            email_auth_passed = response.status_code == 200
            if email_auth_passed:
                auth_response = response.json()
                has_auth_url = 'auth_url' in auth_response
                has_state = 'state' in auth_response
                email_auth_passed = has_auth_url and has_state
                email_auth_details = f"Status: {response.status_code}, Has auth_url: {has_auth_url}, Has state: {has_state}"
            else:
                email_auth_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            email_auth_passed = False
            email_auth_details = f"Error: {str(e)}"
        
        # Test 2: POST /api/oauth/microsoft/authorize with calendar scope
        try:
            calendar_auth_data = ["calendar"]
            response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", 
                                   json=calendar_auth_data, headers=headers, timeout=10)
            
            calendar_auth_passed = response.status_code == 200
            if calendar_auth_passed:
                auth_response = response.json()
                has_auth_url = 'auth_url' in auth_response
                has_state = 'state' in auth_response
                calendar_auth_passed = has_auth_url and has_state
                calendar_auth_details = f"Status: {response.status_code}, Has auth_url: {has_auth_url}, Has state: {has_state}"
            else:
                calendar_auth_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            calendar_auth_passed = False
            calendar_auth_details = f"Error: {str(e)}"
        
        # Test 3: GET /api/oauth/microsoft/status
        try:
            response = requests.get(f"{API_BASE}/oauth/microsoft/status", 
                                  headers=headers, timeout=10)
            
            status_passed = response.status_code == 200
            if status_passed:
                status_response = response.json()
                has_status_structure = 'authorized' in status_response
                status_details = f"Status: {response.status_code}, Has status structure: {has_status_structure}"
            else:
                status_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            status_passed = False
            status_details = f"Error: {str(e)}"
        
        # Test 4: POST /api/oauth/microsoft/revoke
        try:
            response = requests.post(f"{API_BASE}/oauth/microsoft/revoke", 
                                   headers=headers, timeout=10)
            
            revoke_passed = response.status_code == 200
            if revoke_passed:
                revoke_response = response.json()
                has_message = 'message' in revoke_response
                revoke_details = f"Status: {response.status_code}, Has message: {has_message}"
            else:
                revoke_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            revoke_passed = False
            revoke_details = f"Error: {str(e)}"
        
        # Log individual results
        self.log_test_result("Microsoft OAuth - Email Authorization", email_auth_passed, email_auth_details)
        self.log_test_result("Microsoft OAuth - Calendar Authorization", calendar_auth_passed, calendar_auth_details)
        self.log_test_result("Microsoft OAuth - Status Check", status_passed, status_details)
        self.log_test_result("Microsoft OAuth - Revoke Tokens", revoke_passed, revoke_details)
        
        # Overall Microsoft OAuth test
        all_passed = email_auth_passed and calendar_auth_passed and status_passed and revoke_passed
        overall_details = f"Email auth: {email_auth_passed}, Calendar auth: {calendar_auth_passed}, Status: {status_passed}, Revoke: {revoke_passed}"
        self.log_test_result("Microsoft OAuth Endpoints", all_passed, overall_details)
        
        return all_passed
    
    def test_google_oauth_endpoints(self):
        """Test Google OAuth endpoints"""
        print("\n🟢 Testing Google OAuth Endpoints...")
        
        headers = self.get_auth_headers()
        
        # Test 1: POST /api/oauth/google/authorize
        try:
            auth_data = ["email", "calendar"]
            response = requests.post(f"{API_BASE}/oauth/google/authorize", 
                                   json=auth_data, headers=headers, timeout=10)
            
            auth_passed = response.status_code == 200
            if auth_passed:
                auth_response = response.json()
                has_auth_url = 'auth_url' in auth_response
                has_state = 'state' in auth_response
                auth_passed = has_auth_url and has_state
                auth_details = f"Status: {response.status_code}, Has auth_url: {has_auth_url}, Has state: {has_state}"
            else:
                auth_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            auth_passed = False
            auth_details = f"Error: {str(e)}"
        
        # Test 2: GET /api/oauth/google/status
        try:
            response = requests.get(f"{API_BASE}/oauth/google/status", 
                                  headers=headers, timeout=10)
            
            status_passed = response.status_code == 200
            if status_passed:
                status_response = response.json()
                has_status_structure = 'authorized' in status_response
                status_details = f"Status: {response.status_code}, Has status structure: {has_status_structure}"
            else:
                status_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            status_passed = False
            status_details = f"Error: {str(e)}"
        
        # Test 3: POST /api/oauth/google/revoke
        try:
            response = requests.post(f"{API_BASE}/oauth/google/revoke", 
                                   headers=headers, timeout=10)
            
            revoke_passed = response.status_code == 200
            if revoke_passed:
                revoke_response = response.json()
                has_message = 'message' in revoke_response
                revoke_details = f"Status: {response.status_code}, Has message: {has_message}"
            else:
                revoke_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            revoke_passed = False
            revoke_details = f"Error: {str(e)}"
        
        # Log individual results
        self.log_test_result("Google OAuth - Authorization", auth_passed, auth_details)
        self.log_test_result("Google OAuth - Status Check", status_passed, status_details)
        self.log_test_result("Google OAuth - Revoke Tokens", revoke_passed, revoke_details)
        
        # Overall Google OAuth test
        all_passed = auth_passed and status_passed and revoke_passed
        overall_details = f"Auth: {auth_passed}, Status: {status_passed}, Revoke: {revoke_passed}"
        self.log_test_result("Google OAuth Endpoints", all_passed, overall_details)
        
        return all_passed
    
    def test_email_accounts_oauth_creation(self):
        """Test email account creation using OAuth for both providers"""
        print("\n📧 Testing Email Account OAuth Creation...")
        
        headers = self.get_auth_headers()
        
        # Test 1: POST /api/email-accounts/oauth with provider='gmail'
        try:
            gmail_data = {
                "name": "Test Gmail OAuth Account",
                "email": "test.oauth@gmail.com",
                "provider": "gmail",
                "auth_type": "oauth",
                "use_oauth": True,
                "signature": "Test OAuth Signature"
            }
            response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                   json=gmail_data, headers=headers, timeout=10)
            
            gmail_passed = response.status_code in [200, 201, 400]  # 400 is expected if OAuth not completed
            if response.status_code in [200, 201]:
                gmail_details = f"Status: {response.status_code}, Account created successfully"
            elif response.status_code == 400:
                # Check if it's the expected OAuth error
                error_text = response.text.lower()
                if 'oauth' in error_text or 'authorized' in error_text:
                    gmail_passed = True
                    gmail_details = f"Status: {response.status_code}, Expected OAuth error: {response.text[:100]}"
                else:
                    gmail_passed = False
                    gmail_details = f"Status: {response.status_code}, Unexpected error: {response.text[:100]}"
            else:
                gmail_passed = False
                gmail_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            gmail_passed = False
            gmail_details = f"Error: {str(e)}"
        
        # Test 2: POST /api/email-accounts/oauth with provider='outlook'
        try:
            outlook_data = {
                "name": "Test Outlook OAuth Account",
                "email": "test.oauth@outlook.com",
                "provider": "outlook",
                "auth_type": "oauth",
                "use_oauth": True,
                "signature": "Test OAuth Signature"
            }
            response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                   json=outlook_data, headers=headers, timeout=10)
            
            outlook_passed = response.status_code in [200, 201, 400]  # 400 is expected if OAuth not completed
            if response.status_code in [200, 201]:
                outlook_details = f"Status: {response.status_code}, Account created successfully"
            elif response.status_code == 400:
                # Check if it's the expected OAuth error
                error_text = response.text.lower()
                if 'oauth' in error_text or 'authorized' in error_text:
                    outlook_passed = True
                    outlook_details = f"Status: {response.status_code}, Expected OAuth error: {response.text[:100]}"
                else:
                    outlook_passed = False
                    outlook_details = f"Status: {response.status_code}, Unexpected error: {response.text[:100]}"
            else:
                outlook_passed = False
                outlook_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            outlook_passed = False
            outlook_details = f"Error: {str(e)}"
        
        # Test 3: Test with invalid provider
        try:
            invalid_data = {
                "provider": "invalid_provider",
                "name": "Test Invalid Provider"
            }
            response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                   json=invalid_data, headers=headers, timeout=10)
            
            invalid_provider_passed = response.status_code == 400
            invalid_provider_details = f"Status: {response.status_code}, Expected 400 for invalid provider"
        except Exception as e:
            invalid_provider_passed = False
            invalid_provider_details = f"Error: {str(e)}"
        
        # Log individual results
        self.log_test_result("Email OAuth - Gmail Provider", gmail_passed, gmail_details)
        self.log_test_result("Email OAuth - Outlook Provider", outlook_passed, outlook_details)
        self.log_test_result("Email OAuth - Invalid Provider Error", invalid_provider_passed, invalid_provider_details)
        
        # Overall email OAuth test
        all_passed = gmail_passed and outlook_passed and invalid_provider_passed
        overall_details = f"Gmail: {gmail_passed}, Outlook: {outlook_passed}, Error handling: {invalid_provider_passed}"
        self.log_test_result("Email Accounts OAuth Creation", all_passed, overall_details)
        
        return all_passed
    
    def test_calendar_providers_oauth_creation(self):
        """Test calendar provider creation using OAuth for both providers"""
        print("\n📅 Testing Calendar Provider OAuth Creation...")
        
        headers = self.get_auth_headers()
        
        # Test 1: POST /api/calendar/providers/oauth with provider_type='google'
        try:
            google_data = {
                "provider_type": "google",
                "provider_name": "Test Google Calendar OAuth",
                "timezone": "UTC"
            }
            response = requests.post(f"{API_BASE}/calendar/providers/oauth", 
                                   json=google_data, headers=headers, timeout=10)
            
            google_passed = response.status_code in [200, 201, 400]  # 400 is expected if OAuth not completed
            if response.status_code in [200, 201]:
                google_details = f"Status: {response.status_code}, Provider created successfully"
            elif response.status_code == 400:
                # Check if it's the expected OAuth error
                error_text = response.text.lower()
                if 'oauth' in error_text or 'authorized' in error_text:
                    google_passed = True
                    google_details = f"Status: {response.status_code}, Expected OAuth error: {response.text[:100]}"
                else:
                    google_passed = False
                    google_details = f"Status: {response.status_code}, Unexpected error: {response.text[:100]}"
            else:
                google_passed = False
                google_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            google_passed = False
            google_details = f"Error: {str(e)}"
        
        # Test 2: POST /api/calendar/providers/oauth with provider_type='microsoft'
        try:
            microsoft_data = {
                "provider_type": "microsoft",
                "provider_name": "Test Microsoft Calendar OAuth",
                "timezone": "UTC"
            }
            response = requests.post(f"{API_BASE}/calendar/providers/oauth", 
                                   json=microsoft_data, headers=headers, timeout=10)
            
            microsoft_passed = response.status_code in [200, 201, 400]  # 400 is expected if OAuth not completed
            if response.status_code in [200, 201]:
                microsoft_details = f"Status: {response.status_code}, Provider created successfully"
            elif response.status_code == 400:
                # Check if it's the expected OAuth error
                error_text = response.text.lower()
                if 'oauth' in error_text or 'authorized' in error_text:
                    microsoft_passed = True
                    microsoft_details = f"Status: {response.status_code}, Expected OAuth error: {response.text[:100]}"
                else:
                    microsoft_passed = False
                    microsoft_details = f"Status: {response.status_code}, Unexpected error: {response.text[:100]}"
            else:
                microsoft_passed = False
                microsoft_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
        except Exception as e:
            microsoft_passed = False
            microsoft_details = f"Error: {str(e)}"
        
        # Test 3: Test with invalid provider type
        try:
            invalid_data = {
                "provider_type": "invalid_provider",
                "provider_name": "Test Invalid Provider",
                "timezone": "UTC"
            }
            response = requests.post(f"{API_BASE}/calendar/providers/oauth", 
                                   json=invalid_data, headers=headers, timeout=10)
            
            invalid_provider_passed = response.status_code == 400
            invalid_provider_details = f"Status: {response.status_code}, Expected 400 for invalid provider"
        except Exception as e:
            invalid_provider_passed = False
            invalid_provider_details = f"Error: {str(e)}"
        
        # Log individual results
        self.log_test_result("Calendar OAuth - Google Provider", google_passed, google_details)
        self.log_test_result("Calendar OAuth - Microsoft Provider", microsoft_passed, microsoft_details)
        self.log_test_result("Calendar OAuth - Invalid Provider Error", invalid_provider_passed, invalid_provider_details)
        
        # Overall calendar OAuth test
        all_passed = google_passed and microsoft_passed and invalid_provider_passed
        overall_details = f"Google: {google_passed}, Microsoft: {microsoft_passed}, Error handling: {invalid_provider_passed}"
        self.log_test_result("Calendar Providers OAuth Creation", all_passed, overall_details)
        
        return all_passed
    
    def test_oauth_configuration_validation(self):
        """Test OAuth configuration and environment variables"""
        print("\n⚙️ Testing OAuth Configuration...")
        
        # Test Microsoft OAuth configuration
        microsoft_client_id = os.environ.get('MICROSOFT_CLIENT_ID')
        microsoft_client_secret = os.environ.get('MICROSOFT_CLIENT_SECRET')
        microsoft_tenant_id = os.environ.get('MICROSOFT_TENANT_ID')
        microsoft_redirect_uri = os.environ.get('MICROSOFT_REDIRECT_URI')
        
        microsoft_config_passed = all([
            microsoft_client_id,
            microsoft_client_secret,
            microsoft_tenant_id,
            microsoft_redirect_uri
        ])
        
        microsoft_config_details = f"Client ID: {'✓' if microsoft_client_id else '✗'}, " \
                                 f"Client Secret: {'✓' if microsoft_client_secret else '✗'}, " \
                                 f"Tenant ID: {'✓' if microsoft_tenant_id else '✗'}, " \
                                 f"Redirect URI: {'✓' if microsoft_redirect_uri else '✗'}"
        
        # Test Google OAuth configuration
        google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
        google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        google_redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')
        
        google_config_passed = all([
            google_client_id,
            google_client_secret,
            google_redirect_uri
        ])
        
        google_config_details = f"Client ID: {'✓' if google_client_id else '✗'}, " \
                              f"Client Secret: {'✓' if google_client_secret else '✗'}, " \
                              f"Redirect URI: {'✓' if google_redirect_uri else '✗'}"
        
        # Log results
        self.log_test_result("Microsoft OAuth Configuration", microsoft_config_passed, microsoft_config_details)
        self.log_test_result("Google OAuth Configuration", google_config_passed, google_config_details)
        
        # Overall configuration test
        all_passed = microsoft_config_passed and google_config_passed
        overall_details = f"Microsoft config: {microsoft_config_passed}, Google config: {google_config_passed}"
        self.log_test_result("OAuth Configuration Validation", all_passed, overall_details)
        
        return all_passed
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🧪 OAUTH TESTING SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result['passed']:
                print(f"  - {result['test']}")
        
        return passed_tests, failed_tests

async def main():
    """Main test execution"""
    print("🚀 Starting OAuth Integration Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = OAuthTester()
    
    # Setup test user
    if not await tester.setup_test_user():
        print("❌ Failed to setup test user. Exiting.")
        return
    
    # Run OAuth tests
    print("\n" + "="*80)
    print("🧪 RUNNING OAUTH TESTS")
    print("="*80)
    
    # Test OAuth configuration
    tester.test_oauth_configuration_validation()
    
    # Test Microsoft OAuth endpoints
    tester.test_microsoft_oauth_endpoints()
    
    # Test Google OAuth endpoints
    tester.test_google_oauth_endpoints()
    
    # Test OAuth-based account creation
    tester.test_email_accounts_oauth_creation()
    tester.test_calendar_providers_oauth_creation()
    
    # Print summary
    passed, failed = tester.print_summary()
    
    # Exit with appropriate code
    if failed > 0:
        print(f"\n❌ Testing completed with {failed} failures")
        sys.exit(1)
    else:
        print(f"\n✅ All {passed} tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())