#!/usr/bin/env python3
"""
CRITICAL OAUTH DEBUGGING - Microsoft Outlook Authentication Issues
Focused testing for OAuth token storage, Microsoft OAuth configuration, and email polling integration
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-restart-all.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthDebugTester:
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
    
    async def test_oauth_token_storage(self):
        """Test 1: Check OAuth Token Storage - Look in oauth_tokens_microsoft collection for user amits.joys@gmail.com"""
        print("\n🔍 Testing OAuth Token Storage...")
        
        try:
            # Check oauth_tokens_microsoft collection
            microsoft_tokens = await self.db.oauth_tokens_microsoft.find().to_list(100)
            print(f"   Found {len(microsoft_tokens)} Microsoft OAuth tokens in database")
            
            # Look for specific user amits.joys@gmail.com
            user_tokens = []
            target_user_email = "amits.joys@gmail.com"
            target_outlook_email = "amits.joys@outlook.com"
            
            for token in microsoft_tokens:
                print(f"   Token ID: {token.get('id', 'N/A')}")
                print(f"   User ID: {token.get('user_id', 'N/A')}")
                print(f"   Email: {token.get('email', 'N/A')}")
                print(f"   Expires: {token.get('expires_at', 'N/A')}")
                print(f"   Created: {token.get('created_at', 'N/A')}")
                print(f"   ---")
                
                # Check if this token belongs to our target user
                if (token.get('email') == target_outlook_email or 
                    target_user_email in str(token.get('user_id', '')) or
                    target_outlook_email in str(token.get('email', ''))):
                    user_tokens.append(token)
            
            # Check oauth_tokens_google collection for comparison
            google_tokens = await self.db.oauth_tokens_google.find().to_list(100)
            print(f"   Found {len(google_tokens)} Google OAuth tokens in database")
            
            # Check if user has Google OAuth token
            google_user_tokens = []
            for token in google_tokens:
                if (token.get('email') == target_user_email or 
                    target_user_email in str(token.get('email', ''))):
                    google_user_tokens.append(token)
            
            # Check email accounts collection for OAuth accounts
            oauth_accounts = await self.db.email_accounts.find({
                "auth_type": "oauth",
                "use_oauth": True
            }).to_list(100)
            
            print(f"   Found {len(oauth_accounts)} OAuth email accounts")
            
            target_oauth_accounts = []
            for account in oauth_accounts:
                print(f"   OAuth Account - Email: {account.get('email')}, Provider: {account.get('provider')}")
                print(f"   OAuth Token ID: {account.get('oauth_token_id')}")
                print(f"   OAuth Email: {account.get('oauth_email')}")
                print(f"   Active: {account.get('is_active')}")
                print(f"   ---")
                
                if (account.get('email') == target_outlook_email or 
                    account.get('oauth_email') == target_outlook_email):
                    target_oauth_accounts.append(account)
            
            # Evaluate results
            tokens_exist = len(microsoft_tokens) > 0
            user_has_microsoft_token = len(user_tokens) > 0
            user_has_google_token = len(google_user_tokens) > 0
            oauth_accounts_exist = len(oauth_accounts) > 0
            target_account_exists = len(target_oauth_accounts) > 0
            
            all_passed = tokens_exist and oauth_accounts_exist
            
            details = f"Microsoft tokens: {len(microsoft_tokens)}, Google tokens: {len(google_tokens)}, " \
                     f"OAuth accounts: {len(oauth_accounts)}, Target user Microsoft tokens: {len(user_tokens)}, " \
                     f"Target user Google tokens: {len(google_user_tokens)}, Target OAuth accounts: {len(target_oauth_accounts)}"
            
            self.log_test_result("OAuth Token Storage", all_passed, details)
            
            # Log specific findings for the target user
            if user_tokens:
                print(f"🎯 FOUND TARGET USER MICROSOFT TOKENS:")
                for token in user_tokens:
                    print(f"   - Token ID: {token.get('id')}")
                    print(f"   - Email: {token.get('email')}")
                    print(f"   - Expires: {token.get('expires_at')}")
                    print(f"   - Access Token Present: {'access_token' in token}")
                    print(f"   - Refresh Token Present: {'refresh_token' in token}")
            
            if target_oauth_accounts:
                print(f"🎯 FOUND TARGET OAUTH ACCOUNTS:")
                for account in target_oauth_accounts:
                    print(f"   - Account ID: {account.get('id')}")
                    print(f"   - Email: {account.get('email')}")
                    print(f"   - Provider: {account.get('provider')}")
                    print(f"   - OAuth Token ID: {account.get('oauth_token_id')}")
                    print(f"   - Active: {account.get('is_active')}")
            
            return user_tokens, target_oauth_accounts
            
        except Exception as e:
            self.log_test_result("OAuth Token Storage", False, f"Exception: {str(e)}")
            return [], []
    
    async def test_microsoft_oauth_configuration(self):
        """Test 2: Test Microsoft OAuth Configuration - Check if Azure AD app supports personal Microsoft accounts"""
        print("\n🔧 Testing Microsoft OAuth Configuration...")
        
        try:
            # Check environment variables
            microsoft_client_id = os.environ.get('MICROSOFT_CLIENT_ID')
            microsoft_client_secret = os.environ.get('MICROSOFT_CLIENT_SECRET')
            microsoft_tenant_id = os.environ.get('MICROSOFT_TENANT_ID')
            microsoft_redirect_uri = os.environ.get('MICROSOFT_REDIRECT_URI')
            
            config_complete = all([
                microsoft_client_id,
                microsoft_client_secret,
                microsoft_tenant_id,
                microsoft_redirect_uri
            ])
            
            print(f"   Microsoft Client ID: {microsoft_client_id}")
            print(f"   Microsoft Tenant ID: {microsoft_tenant_id}")
            print(f"   Microsoft Redirect URI: {microsoft_redirect_uri}")
            print(f"   Client Secret Present: {'Yes' if microsoft_client_secret else 'No'}")
            
            # Check if tenant is configured for personal accounts
            # Common tenant ID indicates multi-tenant app that supports personal accounts
            supports_personal_accounts = (
                microsoft_tenant_id == "common" or 
                microsoft_tenant_id == "consumers" or
                len(microsoft_tenant_id) > 30  # Specific tenant ID (may not support personal accounts)
            )
            
            print(f"   Tenant Configuration: {microsoft_tenant_id}")
            print(f"   Likely supports personal accounts: {supports_personal_accounts}")
            
            # Test OAuth endpoints availability
            try:
                # Test Microsoft OAuth authorization endpoint
                auth_url = f"https://login.microsoftonline.com/{microsoft_tenant_id}/oauth2/v2.0/authorize"
                response = requests.get(auth_url, timeout=10, allow_redirects=False)
                auth_endpoint_accessible = response.status_code in [200, 302, 400]  # 400 is expected without params
                print(f"   Auth endpoint accessible: {auth_endpoint_accessible} (Status: {response.status_code})")
            except Exception as e:
                auth_endpoint_accessible = False
                print(f"   Auth endpoint test failed: {str(e)}")
            
            # Test token endpoint
            try:
                token_url = f"https://login.microsoftonline.com/{microsoft_tenant_id}/oauth2/v2.0/token"
                response = requests.post(token_url, data={}, timeout=10)
                token_endpoint_accessible = response.status_code in [400, 401]  # Expected without proper auth
                print(f"   Token endpoint accessible: {token_endpoint_accessible} (Status: {response.status_code})")
            except Exception as e:
                token_endpoint_accessible = False
                print(f"   Token endpoint test failed: {str(e)}")
            
            # Check backend OAuth service availability
            try:
                from oauth_microsoft import microsoft_oauth_service
                oauth_service_available = microsoft_oauth_service is not None
                print(f"   OAuth service imported: {oauth_service_available}")
            except Exception as e:
                oauth_service_available = False
                print(f"   OAuth service import failed: {str(e)}")
            
            # Check Microsoft services availability
            try:
                from microsoft_services import MicrosoftMailService, MicrosoftCalendarService
                microsoft_services_available = True
                print(f"   Microsoft services imported: {microsoft_services_available}")
            except Exception as e:
                microsoft_services_available = False
                print(f"   Microsoft services import failed: {str(e)}")
            
            all_passed = (config_complete and auth_endpoint_accessible and 
                         token_endpoint_accessible and oauth_service_available and
                         microsoft_services_available)
            
            details = f"Config complete: {config_complete}, Auth endpoint: {auth_endpoint_accessible}, " \
                     f"Token endpoint: {token_endpoint_accessible}, OAuth service: {oauth_service_available}, " \
                     f"Microsoft services: {microsoft_services_available}, Supports personal: {supports_personal_accounts}"
            
            self.log_test_result("Microsoft OAuth Configuration", all_passed, details)
            
            # Log potential issues
            if not supports_personal_accounts:
                print("⚠️  WARNING: Tenant configuration may not support personal Microsoft accounts")
                print("   Consider using 'common' or 'consumers' tenant for personal account support")
            
            return config_complete, supports_personal_accounts
            
        except Exception as e:
            self.log_test_result("Microsoft OAuth Configuration", False, f"Exception: {str(e)}")
            return False, False
    
    async def test_email_polling_service(self):
        """Test 3: Check Email Polling Service - Verify if Microsoft OAuth accounts are being polled correctly"""
        print("\n📡 Testing Email Polling Service for OAuth Accounts...")
        
        try:
            # Check polling service status
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                polling_running = (response.status_code == 200 and 
                                 response.json().get('status') == 'running')
                print(f"   Polling service status: {response.json().get('status') if response.status_code == 200 else 'Error'}")
            except Exception as e:
                polling_running = False
                print(f"   Polling service check failed: {str(e)}")
            
            # Check accounts polling status
            try:
                response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                if response.status_code == 200:
                    accounts_status = response.json()
                    all_accounts = accounts_status.get('accounts', [])
                    oauth_accounts = [acc for acc in all_accounts if acc.get('auth_type') == 'oauth']
                    microsoft_oauth_accounts = [acc for acc in oauth_accounts if acc.get('provider') == 'microsoft']
                    
                    print(f"   Total accounts: {len(all_accounts)}")
                    print(f"   OAuth accounts: {len(oauth_accounts)}")
                    print(f"   Microsoft OAuth accounts: {len(microsoft_oauth_accounts)}")
                    
                    for acc in microsoft_oauth_accounts:
                        print(f"   Microsoft OAuth Account:")
                        print(f"     - Email: {acc.get('email')}")
                        print(f"     - Polling Active: {acc.get('polling_active')}")
                        print(f"     - Has Connection: {acc.get('has_connection')}")
                        print(f"     - Last Polled: {acc.get('last_polled')}")
                        print(f"     - Last UID: {acc.get('last_uid')}")
                    
                    accounts_status_available = True
                else:
                    accounts_status_available = False
                    microsoft_oauth_accounts = []
                    print(f"   Accounts status check failed: {response.status_code}")
            except Exception as e:
                accounts_status_available = False
                microsoft_oauth_accounts = []
                print(f"   Accounts status check failed: {str(e)}")
            
            # Check email_services.py for OAuth routing logic
            try:
                from email_services import EmailPollingService
                polling_service = EmailPollingService(MONGO_URL, DB_NAME)
                
                # Check if polling service has OAuth account handling
                has_oauth_handling = hasattr(polling_service, '_poll_oauth_account')
                print(f"   Polling service has OAuth handling: {has_oauth_handling}")
                
                # Check for Microsoft-specific handling
                try:
                    import inspect
                    source = inspect.getsource(polling_service._poll_account)
                    has_microsoft_routing = 'microsoft' in source.lower() or 'outlook' in source.lower()
                    print(f"   Has Microsoft routing logic: {has_microsoft_routing}")
                except:
                    has_microsoft_routing = False
                    print(f"   Could not check Microsoft routing logic")
                
            except Exception as e:
                has_oauth_handling = False
                has_microsoft_routing = False
                print(f"   Polling service check failed: {str(e)}")
            
            # Check backend logs for OAuth polling errors
            try:
                import subprocess
                result = subprocess.run(['tail', '-n', '50', '/var/log/supervisor/backend.err.log'], 
                                      capture_output=True, text=True, timeout=10)
                backend_logs = result.stdout
                
                oauth_errors = []
                if 'oauth' in backend_logs.lower():
                    lines = backend_logs.split('\n')
                    for line in lines:
                        if 'oauth' in line.lower() and ('error' in line.lower() or 'fail' in line.lower()):
                            oauth_errors.append(line.strip())
                
                print(f"   OAuth-related errors in logs: {len(oauth_errors)}")
                for error in oauth_errors[-3:]:  # Show last 3 errors
                    print(f"     - {error}")
                
                logs_accessible = True
            except Exception as e:
                logs_accessible = False
                oauth_errors = []
                print(f"   Could not access backend logs: {str(e)}")
            
            all_passed = (polling_running and accounts_status_available and 
                         has_oauth_handling and logs_accessible)
            
            details = f"Polling running: {polling_running}, Accounts status: {accounts_status_available}, " \
                     f"OAuth handling: {has_oauth_handling}, Microsoft routing: {has_microsoft_routing}, " \
                     f"Microsoft OAuth accounts: {len(microsoft_oauth_accounts)}, OAuth errors: {len(oauth_errors)}"
            
            self.log_test_result("Email Polling Service", all_passed, details)
            
            return microsoft_oauth_accounts, oauth_errors
            
        except Exception as e:
            self.log_test_result("Email Polling Service", False, f"Exception: {str(e)}")
            return [], []
    
    async def test_oauth_flow(self):
        """Test 4: Test OAuth Flow - Try Microsoft OAuth authentication process and check for token validation issues"""
        print("\n🔐 Testing OAuth Flow...")
        
        try:
            # Test OAuth authorize endpoint (POST with authentication required)
            try:
                # This should require authentication, so expect 401/403
                oauth_data = ["email", "calendar"]
                response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", 
                                       json=oauth_data, timeout=10)
                oauth_authorize_available = response.status_code in [401, 403, 422]  # Should require auth
                print(f"   OAuth authorize endpoint: {oauth_authorize_available} (Status: {response.status_code})")
                
                if response.status_code == 401:
                    print(f"   OAuth authorize requires authentication (expected)")
                elif response.status_code == 403:
                    print(f"   OAuth authorize forbidden (may need proper auth)")
                elif response.status_code == 422:
                    print(f"   OAuth authorize validation error (endpoint exists)")
                
            except Exception as e:
                oauth_authorize_available = False
                print(f"   OAuth authorize endpoint test failed: {str(e)}")
            
            # Test OAuth callback endpoint
            try:
                # Test with dummy parameters (should fail gracefully)
                callback_params = {
                    'code': 'dummy_code',
                    'state': 'dummy_state'
                }
                response = requests.get(f"{API_BASE}/oauth/microsoft/callback", 
                                      params=callback_params, timeout=10)
                callback_accessible = response.status_code in [400, 401, 500]  # Should fail but be accessible
                print(f"   OAuth callback endpoint: {callback_accessible} (Status: {response.status_code})")
                
                if response.status_code == 400:
                    print(f"   OAuth callback returned 400 - likely invalid state/code (expected)")
                
            except Exception as e:
                callback_accessible = False
                print(f"   OAuth callback endpoint test failed: {str(e)}")
            
            # Test token validation
            try:
                # Get existing Microsoft tokens to test validation
                microsoft_tokens = await self.db.oauth_tokens_microsoft.find().to_list(10)
                
                if microsoft_tokens:
                    test_token = microsoft_tokens[0]
                    print(f"   Testing token validation with token ID: {test_token.get('id')}")
                    
                    # Check token expiry
                    expires_at = test_token.get('expires_at')
                    if expires_at:
                        if isinstance(expires_at, str):
                            from datetime import datetime
                            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        
                        is_expired = expires_at < datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
                        print(f"   Token expired: {is_expired}")
                        print(f"   Token expires at: {expires_at}")
                    else:
                        is_expired = True
                        print(f"   Token has no expiry date")
                    
                    # Check token structure
                    has_access_token = 'access_token' in test_token
                    has_refresh_token = 'refresh_token' in test_token
                    has_email = 'email' in test_token
                    
                    print(f"   Token has access_token: {has_access_token}")
                    print(f"   Token has refresh_token: {has_refresh_token}")
                    print(f"   Token has email: {has_email}")
                    
                    token_structure_valid = has_access_token and has_email
                else:
                    print(f"   No Microsoft tokens found for validation testing")
                    token_structure_valid = False
                    is_expired = True
                    
            except Exception as e:
                token_structure_valid = False
                is_expired = True
                print(f"   Token validation test failed: {str(e)}")
            
            # Test Microsoft Graph API connectivity (if we have a valid token)
            graph_api_accessible = False
            if microsoft_tokens and not is_expired:
                try:
                    test_token = microsoft_tokens[0]
                    access_token = test_token.get('access_token')
                    
                    if access_token:
                        headers = {
                            'Authorization': f'Bearer {access_token}',
                            'Content-Type': 'application/json'
                        }
                        
                        # Test basic Graph API call
                        response = requests.get('https://graph.microsoft.com/v1.0/me', 
                                              headers=headers, timeout=10)
                        graph_api_accessible = response.status_code in [200, 401]  # 401 means accessible but token invalid
                        print(f"   Microsoft Graph API test: {graph_api_accessible} (Status: {response.status_code})")
                        
                        if response.status_code == 401:
                            print(f"   Graph API returned 401 - token may be invalid or expired")
                        elif response.status_code == 200:
                            user_info = response.json()
                            print(f"   Graph API user: {user_info.get('mail', user_info.get('userPrincipalName', 'Unknown'))}")
                    else:
                        print(f"   No access token available for Graph API test")
                        
                except Exception as e:
                    print(f"   Microsoft Graph API test failed: {str(e)}")
            
            all_passed = (oauth_authorize_available and callback_accessible and 
                         token_structure_valid and not is_expired)
            
            details = f"Authorize endpoint: {oauth_authorize_available}, Callback: {callback_accessible}, " \
                     f"Token structure: {token_structure_valid}, Token expired: {is_expired}, " \
                     f"Graph API: {graph_api_accessible}"
            
            self.log_test_result("OAuth Flow", all_passed, details)
            
            return oauth_authorize_available, token_structure_valid, is_expired
            
        except Exception as e:
            self.log_test_result("OAuth Flow", False, f"Exception: {str(e)}")
            return False, False, True
    
    async def test_account_creation(self):
        """Test 5: Check Account Creation - Verify if email account gets created properly after OAuth success"""
        print("\n📧 Testing OAuth Account Creation...")
        
        try:
            # Test OAuth account creation endpoint
            try:
                # Test the endpoint structure (should require authentication)
                response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                       json={}, timeout=10)
                oauth_endpoint_exists = response.status_code in [400, 401, 422]  # Should fail but exist
                print(f"   OAuth account creation endpoint exists: {oauth_endpoint_exists} (Status: {response.status_code})")
            except Exception as e:
                oauth_endpoint_exists = False
                print(f"   OAuth account creation endpoint test failed: {str(e)}")
            
            # Check existing OAuth accounts in database
            oauth_accounts = await self.db.email_accounts.find({
                "auth_type": "oauth",
                "use_oauth": True
            }).to_list(100)
            
            print(f"   Found {len(oauth_accounts)} OAuth accounts in database")
            
            microsoft_oauth_accounts = [acc for acc in oauth_accounts if acc.get('provider') == 'microsoft']
            print(f"   Microsoft OAuth accounts: {len(microsoft_oauth_accounts)}")
            
            # Check account structure for OAuth accounts
            properly_structured_accounts = 0
            for account in microsoft_oauth_accounts:
                has_oauth_token_id = bool(account.get('oauth_token_id'))
                has_oauth_email = bool(account.get('oauth_email'))
                has_provider = account.get('provider') == 'microsoft'
                is_oauth_type = account.get('auth_type') == 'oauth' and account.get('use_oauth') == True
                
                if has_oauth_token_id and has_oauth_email and has_provider and is_oauth_type:
                    properly_structured_accounts += 1
                
                print(f"   Account {account.get('email')}:")
                print(f"     - OAuth Token ID: {has_oauth_token_id}")
                print(f"     - OAuth Email: {has_oauth_email}")
                print(f"     - Provider: {account.get('provider')}")
                print(f"     - Auth Type: {account.get('auth_type')}")
                print(f"     - Use OAuth: {account.get('use_oauth')}")
                print(f"     - Active: {account.get('is_active')}")
            
            # Check for orphaned tokens (tokens without corresponding accounts)
            microsoft_tokens = await self.db.oauth_tokens_microsoft.find().to_list(100)
            orphaned_tokens = 0
            
            for token in microsoft_tokens:
                token_id = token.get('id')
                # Find if any account references this token
                account_with_token = await self.db.email_accounts.find_one({
                    "oauth_token_id": token_id
                })
                
                if not account_with_token:
                    orphaned_tokens += 1
                    print(f"   Orphaned token found: {token_id} (Email: {token.get('email')})")
            
            # Check account limits validation
            try:
                from server import validate_account_limits
                account_limits_available = True
                print(f"   Account limits validation available: {account_limits_available}")
            except Exception as e:
                account_limits_available = False
                print(f"   Account limits validation not available: {str(e)}")
            
            # Test account creation workflow components
            try:
                # Check if OAuth services are properly integrated
                from oauth_microsoft import microsoft_oauth_service
                from microsoft_services import MicrosoftMailService
                
                oauth_integration_complete = True
                print(f"   OAuth integration components available: {oauth_integration_complete}")
            except Exception as e:
                oauth_integration_complete = False
                print(f"   OAuth integration components missing: {str(e)}")
            
            all_passed = (oauth_endpoint_exists and 
                         properly_structured_accounts == len(microsoft_oauth_accounts) and
                         orphaned_tokens == 0 and
                         account_limits_available and
                         oauth_integration_complete)
            
            details = f"Endpoint exists: {oauth_endpoint_exists}, Properly structured: {properly_structured_accounts}/{len(microsoft_oauth_accounts)}, " \
                     f"Orphaned tokens: {orphaned_tokens}, Account limits: {account_limits_available}, " \
                     f"OAuth integration: {oauth_integration_complete}"
            
            self.log_test_result("OAuth Account Creation", all_passed, details)
            
            return oauth_accounts, microsoft_oauth_accounts, orphaned_tokens
            
        except Exception as e:
            self.log_test_result("OAuth Account Creation", False, f"Exception: {str(e)}")
            return [], [], 0
    
    async def test_azure_ad_error_investigation(self):
        """Test 6: Investigate Azure AD Error AADSTS50020 - User account from identity provider 'live.com' does not exist in tenant"""
        print("\n🔍 Investigating Azure AD Error AADSTS50020...")
        
        try:
            # Check tenant configuration
            microsoft_tenant_id = os.environ.get('MICROSOFT_TENANT_ID')
            print(f"   Current tenant ID: {microsoft_tenant_id}")
            
            # Analyze tenant type
            if microsoft_tenant_id == "common":
                tenant_type = "Multi-tenant (supports personal and work accounts)"
                supports_personal = True
            elif microsoft_tenant_id == "consumers":
                tenant_type = "Consumer tenant (personal accounts only)"
                supports_personal = True
            elif microsoft_tenant_id == "organizations":
                tenant_type = "Organizational tenant (work accounts only)"
                supports_personal = False
            else:
                tenant_type = "Specific tenant (may not support personal accounts)"
                supports_personal = False
            
            print(f"   Tenant type: {tenant_type}")
            print(f"   Supports personal accounts: {supports_personal}")
            
            # Check OAuth scopes
            try:
                from oauth_microsoft import microsoft_oauth_service
                # Try to get OAuth configuration
                oauth_scopes = getattr(microsoft_oauth_service, 'scopes', [])
                print(f"   OAuth scopes: {oauth_scopes}")
                
                # Check if scopes are appropriate for personal accounts
                has_mail_scope = any('mail' in scope.lower() for scope in oauth_scopes)
                has_user_scope = any('user' in scope.lower() for scope in oauth_scopes)
                
                print(f"   Has mail scope: {has_mail_scope}")
                print(f"   Has user scope: {has_user_scope}")
                
                scopes_appropriate = has_mail_scope and has_user_scope
            except Exception as e:
                print(f"   Could not check OAuth scopes: {str(e)}")
                scopes_appropriate = False
            
            # Check for specific error patterns in logs
            try:
                import subprocess
                result = subprocess.run(['grep', '-i', 'AADSTS50020', '/var/log/supervisor/backend.err.log'], 
                                      capture_output=True, text=True, timeout=10)
                aadsts_errors = result.stdout.strip().split('\n') if result.stdout.strip() else []
                
                print(f"   AADSTS50020 errors found in logs: {len(aadsts_errors)}")
                for error in aadsts_errors[-2:]:  # Show last 2 errors
                    if error.strip():
                        print(f"     - {error.strip()}")
                
                # Check for live.com identity provider errors
                result = subprocess.run(['grep', '-i', 'live.com', '/var/log/supervisor/backend.err.log'], 
                                      capture_output=True, text=True, timeout=10)
                live_com_errors = result.stdout.strip().split('\n') if result.stdout.strip() else []
                
                print(f"   live.com related errors: {len(live_com_errors)}")
                for error in live_com_errors[-2:]:  # Show last 2 errors
                    if error.strip():
                        print(f"     - {error.strip()}")
                
                error_logs_accessible = True
            except Exception as e:
                aadsts_errors = []
                live_com_errors = []
                error_logs_accessible = False
                print(f"   Could not access error logs: {str(e)}")
            
            # Check Microsoft OAuth configuration for personal account support
            microsoft_redirect_uri = os.environ.get('MICROSOFT_REDIRECT_URI')
            redirect_uri_valid = microsoft_redirect_uri and 'https://' in microsoft_redirect_uri
            
            print(f"   Redirect URI valid: {redirect_uri_valid}")
            print(f"   Redirect URI: {microsoft_redirect_uri}")
            
            # Recommendations based on findings
            recommendations = []
            
            if not supports_personal:
                recommendations.append("Change MICROSOFT_TENANT_ID to 'common' to support personal Microsoft accounts")
            
            if len(aadsts_errors) > 0:
                recommendations.append("AADSTS50020 errors indicate tenant configuration issue with personal accounts")
            
            if len(live_com_errors) > 0:
                recommendations.append("live.com identity provider errors suggest personal account authentication issues")
            
            if not scopes_appropriate:
                recommendations.append("Review OAuth scopes to ensure they support personal account access")
            
            print(f"   Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"     {i}. {rec}")
            
            all_passed = (supports_personal and scopes_appropriate and 
                         len(aadsts_errors) == 0 and redirect_uri_valid)
            
            details = f"Supports personal: {supports_personal}, Scopes OK: {scopes_appropriate}, " \
                     f"AADSTS errors: {len(aadsts_errors)}, live.com errors: {len(live_com_errors)}, " \
                     f"Redirect URI valid: {redirect_uri_valid}, Recommendations: {len(recommendations)}"
            
            self.log_test_result("Azure AD Error Investigation", all_passed, details)
            
            return supports_personal, recommendations
            
        except Exception as e:
            self.log_test_result("Azure AD Error Investigation", False, f"Exception: {str(e)}")
            return False, []
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🔍 CRITICAL OAUTH DEBUGGING - TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL: {len(self.test_results)}")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        print("\n" + "="*80)
        
        # Calculate overall success rate
        success_rate = (len(passed_tests) / len(self.test_results)) * 100 if self.test_results else 0
        print(f"📈 SUCCESS RATE: {success_rate:.1f}%")
        
        return success_rate >= 70  # Consider 70% or higher as acceptable

async def main():
    """Main test execution"""
    print("🚀 Starting CRITICAL OAUTH DEBUGGING Tests...")
    print("Focus: Microsoft Outlook Authentication Issues")
    print("User: amits.joys@gmail.com trying to add amits.joys@outlook.com")
    print("="*80)
    
    tester = OAuthDebugTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return False
        
        # Run all tests
        user_tokens, target_accounts = await tester.test_oauth_token_storage()
        config_complete, supports_personal = await tester.test_microsoft_oauth_configuration()
        microsoft_accounts, oauth_errors = await tester.test_email_polling_service()
        oauth_working, token_valid, token_expired = await tester.test_oauth_flow()
        all_accounts, ms_accounts, orphaned = await tester.test_account_creation()
        personal_support, recommendations = await tester.test_azure_ad_error_investigation()
        
        # Print summary
        success = tester.print_summary()
        
        # Print specific findings for the review request
        print("\n🎯 SPECIFIC FINDINGS FOR REVIEW REQUEST:")
        print("="*50)
        print(f"1. OAuth Token Storage: {len(user_tokens)} tokens found for target user")
        print(f"2. Microsoft OAuth Config: {'✅ Complete' if config_complete else '❌ Incomplete'}")
        print(f"3. Personal Account Support: {'✅ Supported' if supports_personal else '❌ Not Supported'}")
        print(f"4. Email Polling: {len(microsoft_accounts)} Microsoft OAuth accounts")
        print(f"5. OAuth Flow: {'✅ Working' if oauth_working else '❌ Issues Found'}")
        print(f"6. Token Validation: {'❌ Expired' if token_expired else '✅ Valid'}")
        print(f"7. Account Creation: {len(ms_accounts)} Microsoft accounts, {orphaned} orphaned tokens")
        print(f"8. OAuth Errors in Logs: {len(oauth_errors)} errors found")
        
        if recommendations:
            print(f"\n💡 CRITICAL RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        return success
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return False
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)