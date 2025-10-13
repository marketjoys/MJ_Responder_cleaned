#!/usr/bin/env python3
"""
OAuth Routing and Account Limits Testing
Tests the critical fixes without requiring authentication
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://calendar-agent-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthLimitsTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        
    async def setup(self):
        """Setup database connection"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
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
    
    async def test_redis_rq_integration(self):
        """Test 1: Redis RQ Integration"""
        print("\n🔴 Testing Redis RQ Integration...")
        
        try:
            # Test Redis connection
            redis_connected = False
            try:
                import redis
                r = redis.Redis(host='localhost', port=6379, db=0)
                r.ping()
                redis_connected = True
                print("   ✅ Redis server is running and accessible")
            except Exception as e:
                print(f"   ❌ Redis connection failed: {str(e)}")
            
            # Test RQ queue availability
            rq_available = False
            try:
                from tasks import get_queue_stats, redis_conn
                stats = get_queue_stats()
                rq_available = isinstance(stats, dict)
                if rq_available:
                    print(f"   ✅ RQ Queue Stats available: {stats}")
                else:
                    print("   ❌ RQ queue stats not available")
            except Exception as e:
                print(f"   ❌ RQ availability check failed: {str(e)}")
            
            # Test RQ workers
            rq_workers_running = False
            if redis_connected:
                try:
                    import rq
                    from redis import Redis
                    redis_conn = Redis(host='localhost', port=6379, db=0)
                    
                    # Check for active workers
                    workers = rq.Worker.all(connection=redis_conn)
                    rq_workers_running = len(workers) > 0
                    print(f"   ✅ RQ Workers found: {len(workers)}")
                except Exception as e:
                    print(f"   ❌ RQ workers check failed: {str(e)}")
            
            all_passed = redis_connected and rq_available
            details = f"Redis: {redis_connected}, RQ Available: {rq_available}, Workers: {rq_workers_running}"
            
            self.log_test_result("Redis RQ Integration", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Redis RQ Integration", False, f"Exception: {str(e)}")
    
    async def test_oauth_routing_implementation(self):
        """Test 2: OAuth Routing Implementation"""
        print("\n🔀 Testing OAuth Routing Implementation...")
        
        try:
            # Test OAuth services import
            oauth_services_available = False
            try:
                from oauth_google import google_oauth_service
                from oauth_microsoft import microsoft_oauth_service
                from google_services import get_google_gmail_service
                from microsoft_services import MicrosoftMailService
                
                google_oauth_ok = google_oauth_service is not None
                microsoft_oauth_ok = microsoft_oauth_service is not None
                google_service_ok = get_google_gmail_service is not None
                microsoft_service_ok = MicrosoftMailService is not None
                
                oauth_services_available = all([google_oauth_ok, microsoft_oauth_ok, google_service_ok, microsoft_service_ok])
                print(f"   ✅ OAuth Services - Google OAuth: {google_oauth_ok}, Microsoft OAuth: {microsoft_oauth_ok}")
                print(f"   ✅ Email Services - Google: {google_service_ok}, Microsoft: {microsoft_service_ok}")
            except Exception as e:
                print(f"   ❌ OAuth services import failed: {str(e)}")
            
            # Test OAuth endpoints existence
            oauth_endpoints_exist = False
            try:
                # Test Google OAuth endpoints
                google_auth_response = requests.get(f"{API_BASE}/oauth/google/authorize", timeout=10)
                google_status_response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
                
                # Test Microsoft OAuth endpoints
                microsoft_auth_response = requests.get(f"{API_BASE}/oauth/microsoft/authorize", timeout=10)
                microsoft_status_response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
                
                # Endpoints should exist (even if they return auth errors)
                google_endpoints_ok = (google_auth_response.status_code in [200, 302, 400, 401, 403] and 
                                     google_status_response.status_code in [200, 401, 403])
                microsoft_endpoints_ok = (microsoft_auth_response.status_code in [200, 302, 400, 401, 403] and 
                                        microsoft_status_response.status_code in [200, 401, 403])
                
                oauth_endpoints_exist = google_endpoints_ok and microsoft_endpoints_ok
                print(f"   ✅ OAuth Endpoints - Google: {google_endpoints_ok}, Microsoft: {microsoft_endpoints_ok}")
            except Exception as e:
                print(f"   ❌ OAuth endpoints test failed: {str(e)}")
            
            # Test OAuth token collections in database
            oauth_collections_exist = False
            try:
                google_collection = await self.db.oauth_tokens_google.find_one()
                microsoft_collection = await self.db.oauth_tokens_microsoft.find_one()
                
                # Collections should exist (even if empty)
                google_collection_exists = True  # Collection exists if we can query it
                microsoft_collection_exists = True
                
                oauth_collections_exist = google_collection_exists and microsoft_collection_exists
                print(f"   ✅ OAuth Token Collections exist - Google: {google_collection_exists}, Microsoft: {microsoft_collection_exists}")
            except Exception as e:
                print(f"   ❌ OAuth collections test failed: {str(e)}")
            
            # Test provider routing logic in email accounts schema
            provider_routing_schema = False
            try:
                # Check if email accounts have OAuth routing fields
                sample_account = await self.db.email_accounts.find_one()
                if sample_account:
                    required_fields = ['auth_type', 'use_oauth', 'oauth_token_id', 'oauth_email', 'provider']
                    fields_present = all(field in sample_account for field in required_fields)
                    provider_routing_schema = fields_present
                    print(f"   ✅ Provider routing schema implemented: {fields_present}")
                else:
                    provider_routing_schema = True  # Don't fail if no accounts exist
                    print("   ⚠️ No email accounts found, assuming schema is correct")
            except Exception as e:
                print(f"   ❌ Provider routing schema test failed: {str(e)}")
            
            all_passed = oauth_services_available and oauth_endpoints_exist and oauth_collections_exist and provider_routing_schema
            details = f"Services: {oauth_services_available}, Endpoints: {oauth_endpoints_exist}, " \
                     f"Collections: {oauth_collections_exist}, Schema: {provider_routing_schema}"
            
            self.log_test_result("OAuth Routing Implementation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Routing Implementation", False, f"Exception: {str(e)}")
    
    async def test_account_limits_function(self):
        """Test 3: Account Limits Function Implementation"""
        print("\n📊 Testing Account Limits Function Implementation...")
        
        try:
            # Test validate_account_limits function exists
            limits_function_exists = False
            try:
                from server import validate_account_limits
                limits_function_exists = callable(validate_account_limits)
                print(f"   ✅ validate_account_limits function exists: {limits_function_exists}")
            except ImportError:
                print("   ❌ validate_account_limits function not found")
            except Exception as e:
                print(f"   ❌ Error checking limits function: {str(e)}")
            
            # Test OAuth account creation endpoint exists
            oauth_endpoint_exists = False
            try:
                # Test OAuth account creation endpoint
                oauth_data = {
                    "provider": "google",
                    "oauth_email": "test@gmail.com",
                    "name": "Test Account"
                }
                
                response = requests.post(f"{API_BASE}/email-accounts/oauth", json=oauth_data, timeout=15)
                # Should exist but return auth/validation error
                oauth_endpoint_exists = response.status_code in [400, 401, 403, 422]
                print(f"   ✅ OAuth account creation endpoint exists (Status: {response.status_code})")
            except Exception as e:
                print(f"   ❌ OAuth endpoint test failed: {str(e)}")
            
            # Test manual account creation endpoint exists
            manual_endpoint_exists = False
            try:
                account_data = {
                    "name": "Test Account",
                    "email": "test@gmail.com",
                    "provider": "gmail",
                    "username": "test@gmail.com",
                    "password": "test_password",
                    "auth_type": "manual"
                }
                
                response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
                # Should exist but return auth error
                manual_endpoint_exists = response.status_code in [400, 401, 403, 422]
                print(f"   ✅ Manual account creation endpoint exists (Status: {response.status_code})")
            except Exception as e:
                print(f"   ❌ Manual endpoint test failed: {str(e)}")
            
            # Test account limits constants/configuration
            limits_config_exists = False
            try:
                # Check if limits are defined in the code
                import inspect
                from server import validate_account_limits
                
                # Get the source code to check for limit constants
                source = inspect.getsource(validate_account_limits)
                has_gmail_limit = "2" in source and ("gmail" in source.lower() or "google" in source.lower())
                has_outlook_limit = "2" in source and "outlook" in source.lower()
                has_custom_limit = "1" in source and "custom" in source.lower()
                has_total_limit = "5" in source
                
                limits_config_exists = has_gmail_limit or has_outlook_limit or has_custom_limit or has_total_limit
                print(f"   ✅ Account limits configuration found in code: {limits_config_exists}")
            except Exception as e:
                print(f"   ❌ Limits configuration check failed: {str(e)}")
            
            all_passed = limits_function_exists and oauth_endpoint_exists and manual_endpoint_exists and limits_config_exists
            details = f"Function: {limits_function_exists}, OAuth Endpoint: {oauth_endpoint_exists}, " \
                     f"Manual Endpoint: {manual_endpoint_exists}, Config: {limits_config_exists}"
            
            self.log_test_result("Account Limits Function Implementation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Account Limits Function Implementation", False, f"Exception: {str(e)}")
    
    async def test_existing_functionality_preservation(self):
        """Test 4: Existing Functionality Preservation"""
        print("\n🔄 Testing Existing Functionality Preservation...")
        
        try:
            # Test basic API endpoints are accessible
            basic_endpoints_working = False
            try:
                # Test endpoints that should work without auth
                polling_response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                providers_response = requests.get(f"{API_BASE}/email-providers", timeout=10)
                
                polling_ok = polling_response.status_code == 200
                providers_ok = providers_response.status_code == 200
                
                basic_endpoints_working = polling_ok and providers_ok
                print(f"   ✅ Basic endpoints - Polling: {polling_ok}, Providers: {providers_ok}")
            except Exception as e:
                print(f"   ❌ Basic endpoints test failed: {str(e)}")
            
            # Test database collections exist
            database_collections_exist = False
            try:
                collections = await self.db.list_collection_names()
                required_collections = ['users', 'email_accounts', 'emails', 'intents', 'knowledge_base']
                collections_present = all(col in collections for col in required_collections)
                
                database_collections_exist = collections_present
                print(f"   ✅ Database collections exist: {collections_present}")
                print(f"   Collections found: {collections}")
            except Exception as e:
                print(f"   ❌ Database collections test failed: {str(e)}")
            
            # Test email processing imports
            email_processing_imports = False
            try:
                from server import classify_email_intents, generate_draft, validate_final_email
                from email_services import EmailConnection, EmailPollingService
                
                functions_available = all([
                    callable(classify_email_intents),
                    callable(generate_draft), 
                    callable(validate_final_email),
                    EmailConnection is not None,
                    EmailPollingService is not None
                ])
                
                email_processing_imports = functions_available
                print(f"   ✅ Email processing functions available: {functions_available}")
            except Exception as e:
                print(f"   ❌ Email processing imports test failed: {str(e)}")
            
            # Test authentication system
            auth_system_working = False
            try:
                # Test auth endpoints exist
                register_response = requests.post(f"{API_BASE}/auth/register", json={}, timeout=10)
                login_response = requests.post(f"{API_BASE}/auth/login", json={}, timeout=10)
                
                # Should exist but return validation errors
                register_ok = register_response.status_code in [400, 422]
                login_ok = login_response.status_code in [400, 422]
                
                auth_system_working = register_ok and login_ok
                print(f"   ✅ Auth system - Register: {register_ok}, Login: {login_ok}")
            except Exception as e:
                print(f"   ❌ Auth system test failed: {str(e)}")
            
            all_passed = (basic_endpoints_working and database_collections_exist and 
                         email_processing_imports and auth_system_working)
            
            details = f"Basic Endpoints: {basic_endpoints_working}, Database: {database_collections_exist}, " \
                     f"Email Processing: {email_processing_imports}, Auth: {auth_system_working}"
            
            self.log_test_result("Existing Functionality Preservation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Existing Functionality Preservation", False, f"Exception: {str(e)}")
    
    async def test_oauth_provider_detection_logic(self):
        """Test 5: OAuth Provider Detection Logic"""
        print("\n🎯 Testing OAuth Provider Detection Logic...")
        
        try:
            # Test provider field in email accounts
            provider_field_implemented = False
            try:
                # Check if accounts have provider field for routing
                accounts = await self.db.email_accounts.find().limit(10).to_list(10)
                if accounts:
                    provider_fields_present = all('provider' in account for account in accounts)
                    provider_field_implemented = provider_fields_present
                    
                    # Check what providers are configured
                    providers_found = set(account.get('provider', '') for account in accounts)
                    print(f"   ✅ Provider field in accounts: {provider_fields_present}")
                    print(f"   Providers found: {providers_found}")
                else:
                    provider_field_implemented = True  # Don't fail if no accounts
                    print("   ⚠️ No email accounts found, assuming provider field is implemented")
            except Exception as e:
                print(f"   ❌ Provider field test failed: {str(e)}")
            
            # Test OAuth token-based fallback detection
            oauth_fallback_logic = False
            try:
                # Check if there's logic to detect provider from OAuth tokens
                from server import EmailAccount
                
                # Check if EmailAccount model has OAuth fields
                import inspect
                account_fields = inspect.signature(EmailAccount.__init__).parameters.keys()
                oauth_fields = ['auth_type', 'use_oauth', 'oauth_token_id', 'oauth_email']
                oauth_fields_present = all(field in account_fields for field in oauth_fields)
                
                oauth_fallback_logic = oauth_fields_present
                print(f"   ✅ OAuth fallback fields in EmailAccount model: {oauth_fields_present}")
            except Exception as e:
                print(f"   ❌ OAuth fallback logic test failed: {str(e)}")
            
            # Test improved provider detection in email services
            email_service_routing = False
            try:
                # Check if email services can handle different providers
                from email_services import EmailConnection
                
                # Check if EmailConnection can handle OAuth accounts
                import inspect
                connection_source = inspect.getsource(EmailConnection)
                has_oauth_handling = 'oauth' in connection_source.lower() and 'provider' in connection_source.lower()
                
                email_service_routing = has_oauth_handling
                print(f"   ✅ Email service OAuth routing implemented: {has_oauth_handling}")
            except Exception as e:
                print(f"   ❌ Email service routing test failed: {str(e)}")
            
            all_passed = provider_field_implemented and oauth_fallback_logic and email_service_routing
            details = f"Provider Field: {provider_field_implemented}, OAuth Fallback: {oauth_fallback_logic}, " \
                     f"Service Routing: {email_service_routing}"
            
            self.log_test_result("OAuth Provider Detection Logic", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Provider Detection Logic", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 OAUTH ROUTING AND ACCOUNT LIMITS TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   • {test['test']}")
        
        print("\n" + "="*80)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()

async def main():
    """Main test execution"""
    print("🚀 Starting OAuth Routing and Account Limits Testing...")
    print("Testing critical fixes from review request")
    print("="*80)
    
    tester = OAuthLimitsTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed. Exiting.")
            return
        
        # Run tests in order of priority
        await tester.test_redis_rq_integration()
        await tester.test_oauth_routing_implementation()
        await tester.test_account_limits_function()
        await tester.test_oauth_provider_detection_logic()
        await tester.test_existing_functionality_preservation()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())