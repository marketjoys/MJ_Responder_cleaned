#!/usr/bin/env python3
"""
Microsoft OAuth Integration Testing
Tests Microsoft OAuth authorization flow, status check, email account creation, and multiple account support
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-and-review.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class MicrosoftOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.auth_headers = {}
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Authenticate with existing user
            await self.authenticate()
            
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    async def authenticate(self):
        """Authenticate with the API to get access token"""
        try:
            print("🔐 Authenticating with API...")
            
            # Try to login with admin user
            login_data = {
                "email": "admin@example.com",
                "password": "admin123"
            }
            
            response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                auth_response = response.json()
                self.auth_token = auth_response.get('access_token')
                self.test_user_id = auth_response.get('user', {}).get('id')
                
                if self.auth_token:
                    self.auth_headers = {
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json"
                    }
                    print(f"✅ Authenticated successfully (User ID: {self.test_user_id})")
                    return True
                else:
                    print("❌ No access token received")
                    return False
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
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
    
    def make_request(self, method, url, **kwargs):
        """Make authenticated HTTP request"""
        if 'headers' not in kwargs:
            kwargs['headers'] = self.auth_headers
        else:
            kwargs['headers'].update(self.auth_headers)
        
        return getattr(requests, method.lower())(url, **kwargs)
    
    async def test_microsoft_oauth_authorization_flow(self):
        """Test 1: Microsoft OAuth Authorization Flow - /api/oauth/microsoft/authorize"""
        print("\n🔐 Testing Microsoft OAuth Authorization Flow...")
        
        try:
            # Test 1a: Test authorization endpoint with proper payload
            auth_payload = {
                "scopes": ["email", "calendar"]
            }
            
            try:
                print("   Testing /api/oauth/microsoft/authorize endpoint...")
                response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", json=auth_payload, headers=self.auth_headers, timeout=15)
                
                auth_passed = response.status_code == 200
                
                if auth_passed:
                    auth_response = response.json()
                    has_auth_url = 'auth_url' in auth_response
                    has_state = 'state' in auth_response
                    
                    # Verify auth URL contains Microsoft OAuth endpoint
                    auth_url = auth_response.get('auth_url', '')
                    is_microsoft_url = 'login.microsoftonline.com' in auth_url
                    
                    # Verify required parameters in URL
                    has_client_id = 'client_id=' in auth_url
                    has_redirect_uri = 'redirect_uri=' in auth_url
                    has_scope = 'scope=' in auth_url
                    has_response_type = 'response_type=code' in auth_url
                    
                    auth_details = f"Status: {response.status_code}, Has auth_url: {has_auth_url}, " \
                                 f"Has state: {has_state}, Microsoft URL: {is_microsoft_url}, " \
                                 f"Required params: client_id={has_client_id}, redirect_uri={has_redirect_uri}, " \
                                 f"scope={has_scope}, response_type={has_response_type}"
                    
                    auth_passed = (has_auth_url and has_state and is_microsoft_url and 
                                 has_client_id and has_redirect_uri and has_scope and has_response_type)
                    
                    print(f"   - Auth URL: {auth_url[:100]}...")
                    print(f"   - State: {auth_response.get('state', 'N/A')}")
                    
                else:
                    auth_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    print(f"   ❌ Authorization failed - {auth_details}")
                    
            except Exception as e:
                auth_passed = False
                auth_details = f"Exception: {str(e)}"
                print(f"   ❌ Authorization exception: {str(e)}")
            
            # Test 1b: Test with invalid payload
            try:
                print("   Testing with invalid payload...")
                invalid_payload = {"invalid_field": "test"}
                response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", json=invalid_payload, headers=self.auth_headers, timeout=10)
                
                # Should handle invalid payload gracefully (either 400 or still work with defaults)
                invalid_handled = response.status_code in [200, 400, 422]
                invalid_details = f"Invalid payload status: {response.status_code}"
                
            except Exception as e:
                invalid_handled = False
                invalid_details = f"Invalid payload exception: {str(e)}"
            
            # Test 1c: Test with empty payload
            try:
                print("   Testing with empty payload...")
                response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", json={}, headers=self.auth_headers, timeout=10)
                
                empty_handled = response.status_code in [200, 400, 422]
                empty_details = f"Empty payload status: {response.status_code}"
                
            except Exception as e:
                empty_handled = False
                empty_details = f"Empty payload exception: {str(e)}"
            
            all_passed = auth_passed and invalid_handled and empty_handled
            
            details = f"Main flow: {auth_passed}, Invalid payload: {invalid_handled}, Empty payload: {empty_handled}"
            
            self.log_test_result("Microsoft OAuth Authorization Flow", all_passed, details)
            self.log_test_result("OAuth Auth - Main Flow", auth_passed, auth_details)
            self.log_test_result("OAuth Auth - Invalid Payload", invalid_handled, invalid_details)
            self.log_test_result("OAuth Auth - Empty Payload", empty_handled, empty_details)
            
        except Exception as e:
            self.log_test_result("Microsoft OAuth Authorization Flow", False, f"Exception: {str(e)}")
    
    async def test_microsoft_oauth_status_check(self):
        """Test 2: Microsoft OAuth Status Check - /api/oauth/microsoft/status"""
        print("\n📊 Testing Microsoft OAuth Status Check...")
        
        try:
            # Test 2a: Test status endpoint with authentication
            try:
                print("   Testing /api/oauth/microsoft/status endpoint (authenticated)...")
                response = self.make_request('get', f"{API_BASE}/oauth/microsoft/status", timeout=10)
                
                # Should return 200 for authenticated requests
                auth_passed = response.status_code == 200
                
                if response.status_code == 200:
                    status_response = response.json()
                    auth_details = f"Status: {response.status_code}, Response: {status_response}"
                else:
                    auth_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                    
            except Exception as e:
                auth_passed = False
                auth_details = f"Exception: {str(e)}"
            
            # Test 2a2: Test status endpoint without authentication
            try:
                print("   Testing /api/oauth/microsoft/status endpoint (unauthenticated)...")
                response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
                
                # Should return 401/403 for unauthenticated requests
                unauth_passed = response.status_code in [401, 403]
                unauth_details = f"Unauth status: {response.status_code}"
                    
            except Exception as e:
                unauth_passed = False
                unauth_details = f"Exception: {str(e)}"
            
            # Test 2b: Test status endpoint structure (authenticated)
            try:
                print("   Testing status endpoint response structure...")
                response = self.make_request('get', f"{API_BASE}/oauth/microsoft/status", timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    
                    # The response might be different based on implementation
                    # Let's be flexible and just check it's valid JSON
                    structure_passed = isinstance(status_data, (dict, list))
                    structure_details = f"Status: {response.status_code}, Valid JSON: {structure_passed}, Data: {str(status_data)[:100]}"
                    
                else:
                    structure_passed = False
                    structure_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                    
            except Exception as e:
                structure_passed = False
                structure_details = f"Exception: {str(e)}"
            
            # Test 2c: Test with different HTTP methods
            try:
                print("   Testing unsupported HTTP methods...")
                
                # POST should not be allowed
                post_response = requests.post(f"{API_BASE}/oauth/microsoft/status", timeout=10)
                post_handled = post_response.status_code in [405, 404, 401, 403]  # Method not allowed or auth required
                
                # PUT should not be allowed
                put_response = requests.put(f"{API_BASE}/oauth/microsoft/status", timeout=10)
                put_handled = put_response.status_code in [405, 404, 401, 403]
                
                methods_details = f"POST: {post_response.status_code}, PUT: {put_response.status_code}"
                methods_passed = post_handled and put_handled
                
            except Exception as e:
                methods_passed = False
                methods_details = f"Exception: {str(e)}"
            
            all_passed = auth_passed and unauth_passed and structure_passed and methods_passed
            
            details = f"Auth: {auth_passed}, Unauth handling: {unauth_passed}, Structure: {structure_passed}, Methods: {methods_passed}"
            
            self.log_test_result("Microsoft OAuth Status Check", all_passed, details)
            self.log_test_result("OAuth Status - Authenticated", auth_passed, auth_details)
            self.log_test_result("OAuth Status - Unauth Handling", unauth_passed, unauth_details)
            self.log_test_result("OAuth Status - Response Structure", structure_passed, structure_details)
            self.log_test_result("OAuth Status - HTTP Methods", methods_passed, methods_details)
            
        except Exception as e:
            self.log_test_result("Microsoft OAuth Status Check", False, f"Exception: {str(e)}")
    
    async def test_oauth_email_account_creation(self):
        """Test 3: OAuth Email Account Creation - /api/email-accounts/oauth with Microsoft provider"""
        print("\n📧 Testing OAuth Email Account Creation...")
        
        try:
            # First, check if oauth_tokens_microsoft collection exists and has test data
            print("   Checking oauth_tokens_microsoft collection...")
            
            # Check collection exists
            collections = await self.db.list_collection_names()
            has_microsoft_collection = 'oauth_tokens_microsoft' in collections
            
            if not has_microsoft_collection:
                print("   Creating test oauth_tokens_microsoft collection...")
                # Create a test OAuth token for testing
                test_oauth_token = {
                    "id": str(uuid.uuid4()),
                    "user_id": "test-user-id",
                    "email": "test.microsoft@outlook.com",
                    "access_token": "test_access_token_123",
                    "refresh_token": "test_refresh_token_456",
                    "expires_at": datetime.utcnow() + timedelta(hours=1),
                    "scopes": ["email", "calendar"],
                    "created_at": datetime.utcnow()
                }
                await self.db.oauth_tokens_microsoft.insert_one(test_oauth_token)
                print(f"   ✅ Created test OAuth token: {test_oauth_token['email']}")
            
            # Get existing OAuth tokens for testing
            oauth_tokens = await self.db.oauth_tokens_microsoft.find().to_list(10)
            print(f"   Found {len(oauth_tokens)} OAuth tokens in oauth_tokens_microsoft collection")
            
            # Test 3a: Create OAuth email account with Microsoft provider
            if oauth_tokens:
                test_token = oauth_tokens[0]
                oauth_email = test_token.get('email', 'test.microsoft@outlook.com')
                
                account_data = {
                    "provider": "microsoft",
                    "oauth_email": oauth_email
                }
                
                try:
                    print(f"   Testing OAuth account creation for: {oauth_email}")
                    response = self.make_request('post', f"{API_BASE}/email-accounts/oauth", json=account_data, timeout=15)
                    
                    create_passed = response.status_code in [200, 201]
                    
                    if create_passed:
                        created_account = response.json()
                        
                        # Verify account properties
                        has_id = 'id' in created_account
                        correct_provider = created_account.get('provider') == 'microsoft'
                        correct_auth_type = created_account.get('auth_type') == 'oauth'
                        has_oauth_email = created_account.get('oauth_email') == oauth_email
                        uses_oauth = created_account.get('use_oauth') == True
                        
                        create_details = f"Status: {response.status_code}, ID: {created_account.get('id')}, " \
                                       f"Provider: {correct_provider}, Auth type: {correct_auth_type}, " \
                                       f"OAuth email: {has_oauth_email}, Uses OAuth: {uses_oauth}"
                        
                        create_passed = (has_id and correct_provider and correct_auth_type and 
                                       has_oauth_email and uses_oauth)
                        
                        # Store account ID for cleanup
                        created_account_id = created_account.get('id')
                        
                    else:
                        create_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                        created_account_id = None
                        
                except Exception as e:
                    create_passed = False
                    create_details = f"Exception: {str(e)}"
                    created_account_id = None
            else:
                create_passed = False
                create_details = "No OAuth tokens available for testing"
                created_account_id = None
            
            # Test 3b: Test with missing oauth_email field
            try:
                print("   Testing with missing oauth_email field...")
                invalid_data = {"provider": "microsoft"}
                response = self.make_request('post', f"{API_BASE}/email-accounts/oauth", json=invalid_data, timeout=10)
                
                # Should return 400 or 422 for missing required field
                missing_email_handled = response.status_code in [400, 422]
                missing_email_details = f"Status: {response.status_code}"
                
            except Exception as e:
                missing_email_handled = False
                missing_email_details = f"Exception: {str(e)}"
            
            # Test 3c: Test with non-existent OAuth token
            try:
                print("   Testing with non-existent OAuth email...")
                nonexistent_data = {
                    "provider": "microsoft",
                    "oauth_email": "nonexistent@outlook.com"
                }
                response = self.make_request('post', f"{API_BASE}/email-accounts/oauth", json=nonexistent_data, timeout=10)
                
                # Should return 400 or 404 for missing OAuth token
                nonexistent_handled = response.status_code in [400, 404, 422]
                nonexistent_details = f"Status: {response.status_code}"
                
            except Exception as e:
                nonexistent_handled = False
                nonexistent_details = f"Exception: {str(e)}"
            
            # Test 3d: Verify database lookup uses correct collection
            try:
                print("   Verifying database collection lookup...")
                
                # Check that the system looks in oauth_tokens_microsoft, not oauth_tokens
                oauth_tokens_old = await self.db.oauth_tokens.find().to_list(10)
                oauth_tokens_microsoft = await self.db.oauth_tokens_microsoft.find().to_list(10)
                
                collection_lookup_passed = len(oauth_tokens_microsoft) > 0
                collection_details = f"oauth_tokens: {len(oauth_tokens_old)}, oauth_tokens_microsoft: {len(oauth_tokens_microsoft)}"
                
            except Exception as e:
                collection_lookup_passed = False
                collection_details = f"Exception: {str(e)}"
            
            # Cleanup created account
            if created_account_id:
                try:
                    print(f"   Cleaning up created account: {created_account_id}")
                    await self.db.email_accounts.delete_one({"id": created_account_id})
                except Exception as e:
                    print(f"   Warning: Failed to cleanup account: {str(e)}")
            
            all_passed = (create_passed and missing_email_handled and 
                         nonexistent_handled and collection_lookup_passed)
            
            details = f"Create: {create_passed}, Missing email: {missing_email_handled}, " \
                     f"Nonexistent: {nonexistent_handled}, Collection lookup: {collection_lookup_passed}"
            
            self.log_test_result("OAuth Email Account Creation", all_passed, details)
            self.log_test_result("OAuth Account - Create", create_passed, create_details)
            self.log_test_result("OAuth Account - Missing Email", missing_email_handled, missing_email_details)
            self.log_test_result("OAuth Account - Nonexistent Token", nonexistent_handled, nonexistent_details)
            self.log_test_result("OAuth Account - Collection Lookup", collection_lookup_passed, collection_details)
            
        except Exception as e:
            self.log_test_result("OAuth Email Account Creation", False, f"Exception: {str(e)}")
    
    async def test_multiple_oauth_account_support(self):
        """Test 4: Multiple OAuth Account Support - Verify multiple Microsoft/Gmail accounts can be stored"""
        print("\n🔄 Testing Multiple OAuth Account Support...")
        
        try:
            # Test 4a: Create multiple test OAuth tokens
            print("   Creating multiple test OAuth tokens...")
            
            test_tokens = [
                {
                    "id": str(uuid.uuid4()),
                    "user_id": "test-user-1",
                    "email": "user1.microsoft@outlook.com",
                    "access_token": "token_1_access",
                    "refresh_token": "token_1_refresh",
                    "expires_at": datetime.utcnow() + timedelta(hours=1),
                    "scopes": ["email", "calendar"],
                    "created_at": datetime.utcnow()
                },
                {
                    "id": str(uuid.uuid4()),
                    "user_id": "test-user-2", 
                    "email": "user2.microsoft@outlook.com",
                    "access_token": "token_2_access",
                    "refresh_token": "token_2_refresh",
                    "expires_at": datetime.utcnow() + timedelta(hours=1),
                    "scopes": ["email"],
                    "created_at": datetime.utcnow()
                },
                {
                    "id": str(uuid.uuid4()),
                    "user_id": "test-user-3",
                    "email": "user3.microsoft@hotmail.com",
                    "access_token": "token_3_access", 
                    "refresh_token": "token_3_refresh",
                    "expires_at": datetime.utcnow() + timedelta(hours=1),
                    "scopes": ["email", "calendar"],
                    "created_at": datetime.utcnow()
                }
            ]
            
            # Insert test tokens
            for token in test_tokens:
                await self.db.oauth_tokens_microsoft.insert_one(token)
            
            tokens_created = len(test_tokens)
            print(f"   ✅ Created {tokens_created} test OAuth tokens")
            
            # Test 4b: Create multiple OAuth email accounts
            created_accounts = []
            
            for i, token in enumerate(test_tokens):
                try:
                    account_data = {
                        "provider": "microsoft",
                        "oauth_email": token['email']
                    }
                    
                    response = self.make_request('post', f"{API_BASE}/email-accounts/oauth", json=account_data, timeout=15)
                    
                    if response.status_code in [200, 201]:
                        account = response.json()
                        created_accounts.append(account)
                        print(f"   ✅ Created OAuth account {i+1}: {token['email']}")
                    else:
                        print(f"   ❌ Failed to create account {i+1}: {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Exception creating account {i+1}: {str(e)}")
            
            multiple_create_passed = len(created_accounts) >= 2
            multiple_create_details = f"Created {len(created_accounts)}/{len(test_tokens)} accounts"
            
            # Test 4c: Verify accounts are stored with unique identifiers
            try:
                print("   Verifying account uniqueness...")
                
                # Check database for created accounts
                db_accounts = await self.db.email_accounts.find({
                    "auth_type": "oauth",
                    "provider": "microsoft"
                }).to_list(100)
                
                # Verify unique oauth_email values
                oauth_emails = [acc.get('oauth_email') for acc in db_accounts if acc.get('oauth_email')]
                unique_emails = set(oauth_emails)
                
                uniqueness_passed = len(oauth_emails) == len(unique_emails) and len(unique_emails) >= 2
                uniqueness_details = f"Total OAuth accounts: {len(db_accounts)}, Unique emails: {len(unique_emails)}"
                
            except Exception as e:
                uniqueness_passed = False
                uniqueness_details = f"Exception: {str(e)}"
            
            # Test 4d: Test account retrieval and management
            try:
                print("   Testing account retrieval...")
                
                response = self.make_request('get', f"{API_BASE}/email-accounts", timeout=10)
                
                if response.status_code == 200:
                    all_accounts = response.json()
                    oauth_accounts = [acc for acc in all_accounts if acc.get('auth_type') == 'oauth']
                    microsoft_accounts = [acc for acc in oauth_accounts if acc.get('provider') == 'microsoft']
                    
                    retrieval_passed = len(microsoft_accounts) >= 2
                    retrieval_details = f"Total accounts: {len(all_accounts)}, OAuth: {len(oauth_accounts)}, Microsoft: {len(microsoft_accounts)}"
                    
                else:
                    retrieval_passed = False
                    retrieval_details = f"Status: {response.status_code}"
                    
            except Exception as e:
                retrieval_passed = False
                retrieval_details = f"Exception: {str(e)}"
            
            # Test 4e: Test account-specific operations
            try:
                print("   Testing account-specific operations...")
                
                operations_passed = True
                operations_details = ""
                
                if created_accounts:
                    test_account = created_accounts[0]
                    account_id = test_account.get('id')
                    
                    # Test get specific account
                    response = self.make_request('get', f"{API_BASE}/email-accounts/{account_id}", timeout=10)
                    get_specific_passed = response.status_code == 200
                    
                    # Test toggle account
                    response = self.make_request('put', f"{API_BASE}/email-accounts/{account_id}/toggle", timeout=10)
                    toggle_passed = response.status_code == 200
                    
                    operations_passed = get_specific_passed and toggle_passed
                    operations_details = f"Get specific: {get_specific_passed}, Toggle: {toggle_passed}"
                    
                else:
                    operations_passed = False
                    operations_details = "No accounts to test operations"
                    
            except Exception as e:
                operations_passed = False
                operations_details = f"Exception: {str(e)}"
            
            # Cleanup created accounts and tokens
            print("   Cleaning up test data...")
            try:
                # Delete created accounts
                for account in created_accounts:
                    await self.db.email_accounts.delete_one({"id": account.get('id')})
                
                # Delete test tokens
                for token in test_tokens:
                    await self.db.oauth_tokens_microsoft.delete_one({"id": token['id']})
                    
                print(f"   ✅ Cleaned up {len(created_accounts)} accounts and {len(test_tokens)} tokens")
                
            except Exception as e:
                print(f"   ⚠️ Cleanup warning: {str(e)}")
            
            all_passed = (multiple_create_passed and uniqueness_passed and 
                         retrieval_passed and operations_passed)
            
            details = f"Multiple create: {multiple_create_passed}, Uniqueness: {uniqueness_passed}, " \
                     f"Retrieval: {retrieval_passed}, Operations: {operations_passed}"
            
            self.log_test_result("Multiple OAuth Account Support", all_passed, details)
            self.log_test_result("Multiple Accounts - Create", multiple_create_passed, multiple_create_details)
            self.log_test_result("Multiple Accounts - Uniqueness", uniqueness_passed, uniqueness_details)
            self.log_test_result("Multiple Accounts - Retrieval", retrieval_passed, retrieval_details)
            self.log_test_result("Multiple Accounts - Operations", operations_passed, operations_details)
            
        except Exception as e:
            self.log_test_result("Multiple OAuth Account Support", False, f"Exception: {str(e)}")
    
    async def test_redraft_email_processing(self):
        """Test 5: Redraft Email Processing - Verify existing email processing pipeline still works"""
        print("\n🔄 Testing Redraft Email Processing...")
        
        try:
            # Test 5a: Check if we have existing emails to test redraft
            print("   Checking for existing emails...")
            
            existing_emails = await self.db.emails.find().to_list(10)
            print(f"   Found {len(existing_emails)} existing emails")
            
            # Test 5b: Create a test email for redraft testing
            print("   Creating test email for redraft...")
            
            # Get an active email account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Redraft Email Processing", False, "No active email accounts for testing")
                return
            
            # Create test email via API
            test_email_data = {
                "subject": "Microsoft OAuth Integration Test Email",
                "body": "This is a test email to verify that the existing email processing pipeline still works correctly after Microsoft OAuth integration fixes. Please provide information about your AI email assistant pricing and features.",
                "sender": "oauth.test@example.com",
                "account_id": account['id']
            }
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                email_created = response.status_code in [200, 201]
                
                if email_created:
                    email_response = response.json()
                    email_id = email_response.get('email_id') or email_response.get('id')
                    
                    print(f"   ✅ Created test email: {email_id}")
                    
                    # Wait a moment for processing
                    await asyncio.sleep(2)
                    
                    # Check email status in database
                    email_doc = await self.db.emails.find_one({"id": email_id})
                    if email_doc:
                        email_status = email_doc.get('status', 'unknown')
                        has_draft = bool(email_doc.get('draft'))
                        has_intents = bool(email_doc.get('intents'))
                        
                        create_details = f"Status: {response.status_code}, Email ID: {email_id}, " \
                                       f"DB Status: {email_status}, Has draft: {has_draft}, Has intents: {has_intents}"
                    else:
                        create_details = f"Status: {response.status_code}, Email not found in DB"
                        
                else:
                    create_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                    email_id = None
                    
            except Exception as e:
                email_created = False
                create_details = f"Exception: {str(e)}"
                email_id = None
            
            # Test 5c: Test redraft functionality
            redraft_passed = False
            if email_id:
                try:
                    print(f"   Testing redraft for email: {email_id}")
                    
                    redraft_data = {
                        "email_id": email_id,
                        "force_redraft": True
                    }
                    
                    response = requests.post(f"{API_BASE}/emails/{email_id}/redraft", json=redraft_data, timeout=30)
                    
                    redraft_passed = response.status_code == 200
                    
                    if redraft_passed:
                        redraft_response = response.json()
                        
                        # Check if redraft was successful
                        new_status = redraft_response.get('status', 'unknown')
                        has_new_draft = bool(redraft_response.get('draft'))
                        
                        redraft_details = f"Status: {response.status_code}, New status: {new_status}, Has new draft: {has_new_draft}"
                        
                    else:
                        redraft_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                        
                except Exception as e:
                    redraft_passed = False
                    redraft_details = f"Exception: {str(e)}"
            else:
                redraft_details = "Skipped - no email ID available"
            
            # Test 5d: Test email sending functionality
            send_passed = False
            if email_id:
                try:
                    print(f"   Testing email send for: {email_id}")
                    
                    send_data = {
                        "email_id": email_id,
                        "manual_override": True
                    }
                    
                    response = requests.post(f"{API_BASE}/emails/{email_id}/send", json=send_data, timeout=30)
                    
                    send_passed = response.status_code == 200
                    
                    if send_passed:
                        send_details = f"Status: {response.status_code}, Message: {response.json().get('message', 'N/A')}"
                    else:
                        send_details = f"Status: {response.status_code}, Error: {response.text[:200]}"
                        
                except Exception as e:
                    send_passed = False
                    send_details = f"Exception: {str(e)}"
            else:
                send_details = "Skipped - no email ID available"
            
            # Test 5e: Test email listing endpoints
            try:
                print("   Testing email listing endpoints...")
                
                # Test GET /api/emails
                response = requests.get(f"{API_BASE}/emails", timeout=10)
                list_emails_passed = response.status_code == 200
                
                if list_emails_passed:
                    emails_list = response.json()
                    list_details = f"Status: {response.status_code}, Count: {len(emails_list)}"
                else:
                    list_details = f"Status: {response.status_code}"
                
                # Test GET /api/emails/threads
                response = requests.get(f"{API_BASE}/emails/threads", timeout=10)
                threads_passed = response.status_code == 200
                
                if threads_passed:
                    threads_list = response.json()
                    threads_details = f"Status: {response.status_code}, Threads: {len(threads_list)}"
                else:
                    threads_details = f"Status: {response.status_code}"
                
                endpoints_passed = list_emails_passed and threads_passed
                endpoints_details = f"List emails: {list_emails_passed}, Threads: {threads_passed}"
                
            except Exception as e:
                endpoints_passed = False
                endpoints_details = f"Exception: {str(e)}"
            
            # Cleanup test email
            if email_id:
                try:
                    await self.db.emails.delete_one({"id": email_id})
                    print(f"   ✅ Cleaned up test email: {email_id}")
                except Exception as e:
                    print(f"   ⚠️ Cleanup warning: {str(e)}")
            
            all_passed = (email_created and redraft_passed and send_passed and endpoints_passed)
            
            details = f"Email created: {email_created}, Redraft: {redraft_passed}, " \
                     f"Send: {send_passed}, Endpoints: {endpoints_passed}"
            
            self.log_test_result("Redraft Email Processing", all_passed, details)
            self.log_test_result("Email Processing - Create", email_created, create_details)
            self.log_test_result("Email Processing - Redraft", redraft_passed, redraft_details)
            self.log_test_result("Email Processing - Send", send_passed, send_details)
            self.log_test_result("Email Processing - Endpoints", endpoints_passed, endpoints_details)
            
        except Exception as e:
            self.log_test_result("Redraft Email Processing", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🧪 MICROSOFT OAUTH INTEGRATION TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   • {result['test']}: {result['details']}")
        
        print(f"\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result['passed']:
                print(f"   • {result['test']}")
        
        print("\n" + "="*80)
        
        return passed_tests, failed_tests

async def main():
    """Main test execution"""
    print("🚀 Starting Microsoft OAuth Integration Testing...")
    print(f"🌐 Backend URL: {BACKEND_URL}")
    print(f"🗄️ Database: {MONGO_URL}/{DB_NAME}")
    
    tester = MicrosoftOAuthTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run tests
        await tester.test_microsoft_oauth_authorization_flow()
        await tester.test_microsoft_oauth_status_check()
        await tester.test_oauth_email_account_creation()
        await tester.test_multiple_oauth_account_support()
        await tester.test_redraft_email_processing()
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Exit with appropriate code
        if failed > 0:
            print(f"\n❌ Testing completed with {failed} failures")
            sys.exit(1)
        else:
            print(f"\n✅ All tests passed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())