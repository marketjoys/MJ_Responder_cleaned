#!/usr/bin/env python3
"""
Final OAuth Flow Testing for amits.joys@gmail.com
Direct database and API testing without authentication complications
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://calendar-agent-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test target
OAUTH_EMAIL = "amits.joys@gmail.com"

class FinalOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.oauth_account_id = None
        self.calendar_provider_id = None
        self.oauth_user_id = None
        
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
    
    async def test_oauth_account_verification(self):
        """Test 1: Comprehensive OAuth Account Verification"""
        print(f"\n🔍 Testing OAuth Account Verification for {OAUTH_EMAIL}...")
        
        try:
            # Check OAuth account exists with correct structure
            oauth_account = await self.db.email_accounts.find_one({
                "oauth_email": OAUTH_EMAIL,
                "auth_type": "oauth",
                "use_oauth": True
            })
            
            if oauth_account:
                self.oauth_account_id = oauth_account['id']
                self.oauth_user_id = oauth_account.get('user_id')
                
                # Verify all required OAuth fields
                required_fields = {
                    'oauth_email': OAUTH_EMAIL,
                    'auth_type': 'oauth',
                    'use_oauth': True,
                    'oauth_token_id': True,  # Should exist
                    'is_active': True
                }
                
                field_checks = {}
                for field, expected in required_fields.items():
                    actual = oauth_account.get(field)
                    if field == 'oauth_token_id':
                        field_checks[field] = bool(actual)
                    else:
                        field_checks[field] = actual == expected
                
                all_fields_correct = all(field_checks.values())
                
                details = f"Account ID: {oauth_account['id']}, Provider: {oauth_account.get('provider')}, " \
                         f"Field checks: {field_checks}, All correct: {all_fields_correct}"
                
                self.log_test_result("OAuth Account Structure", all_fields_correct, details)
                return all_fields_correct
            else:
                self.log_test_result("OAuth Account Structure", False, f"No OAuth account found for {OAUTH_EMAIL}")
                return False
                
        except Exception as e:
            self.log_test_result("OAuth Account Structure", False, f"Exception: {str(e)}")
            return False
    
    async def test_email_polling_status(self):
        """Test 2: Email Polling Status Verification"""
        print(f"\n📧 Testing Email Polling Status for {OAUTH_EMAIL}...")
        
        if not self.oauth_account_id:
            self.log_test_result("Email Polling Status", False, "No OAuth account ID available")
            return False
        
        try:
            # Check polling status via API (no auth required for status endpoint)
            response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                accounts = status_data.get('accounts', [])
                
                # Find our OAuth account
                oauth_account_status = None
                for account in accounts:
                    if account.get('account_id') == self.oauth_account_id:
                        oauth_account_status = account
                        break
                
                if oauth_account_status:
                    polling_active = oauth_account_status.get('polling_active', False)
                    last_polled = oauth_account_status.get('last_polled')
                    
                    # Check database for OAuth sync timestamp
                    oauth_account = await self.db.email_accounts.find_one({"id": self.oauth_account_id})
                    last_oauth_sync = oauth_account.get('last_oauth_sync')
                    
                    # Check if sync happened recently (within last 2 hours)
                    recent_sync = False
                    if last_oauth_sync:
                        sync_time = last_oauth_sync
                        if isinstance(sync_time, str):
                            sync_time = datetime.fromisoformat(sync_time.replace('Z', '+00:00'))
                        
                        time_diff = datetime.utcnow() - sync_time.replace(tzinfo=None)
                        recent_sync = time_diff.total_seconds() < 7200  # Within 2 hours
                    
                    polling_working = polling_active and recent_sync
                    
                    details = f"Polling active: {polling_active}, Last polled: {last_polled}, " \
                             f"Last OAuth sync: {last_oauth_sync}, Recent sync: {recent_sync}"
                    
                    self.log_test_result("Email Polling Status", polling_working, details)
                    return polling_working
                else:
                    self.log_test_result("Email Polling Status", False, "OAuth account not found in polling status")
                    return False
            else:
                self.log_test_result("Email Polling Status", False, f"API call failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Email Polling Status", False, f"Exception: {str(e)}")
            return False
    
    async def test_calendar_provider_verification(self):
        """Test 3: Calendar Provider Verification"""
        print(f"\n📅 Testing Calendar Provider Verification for {OAUTH_EMAIL}...")
        
        try:
            # Check calendar provider exists with OAuth email
            calendar_provider = await self.db.calendar_providers.find_one({
                "oauth_email": OAUTH_EMAIL,
                "use_oauth": True
            })
            
            if calendar_provider:
                self.calendar_provider_id = calendar_provider['id']
                
                # Verify provider structure
                required_fields = {
                    'oauth_email': OAUTH_EMAIL,
                    'use_oauth': True,
                    'provider_type': 'google',
                    'is_active': True
                }
                
                field_checks = {}
                for field, expected in required_fields.items():
                    actual = calendar_provider.get(field)
                    field_checks[field] = actual == expected
                
                all_fields_correct = all(field_checks.values())
                
                # Check if user IDs match
                calendar_user_id = calendar_provider.get('user_id')
                user_ids_match = calendar_user_id == self.oauth_user_id
                
                provider_valid = all_fields_correct and user_ids_match
                
                details = f"Provider ID: {calendar_provider['id']}, Type: {calendar_provider.get('provider_type')}, " \
                         f"Field checks: {field_checks}, User IDs match: {user_ids_match}"
                
                self.log_test_result("Calendar Provider Structure", provider_valid, details)
                return provider_valid
            else:
                self.log_test_result("Calendar Provider Structure", False, f"No calendar provider found for {OAUTH_EMAIL}")
                return False
                
        except Exception as e:
            self.log_test_result("Calendar Provider Structure", False, f"Exception: {str(e)}")
            return False
    
    async def test_oauth_tokens_verification(self):
        """Test 4: OAuth Tokens Verification"""
        print(f"\n🔑 Testing OAuth Tokens Verification for {OAUTH_EMAIL}...")
        
        try:
            # Check OAuth tokens exist and are valid
            oauth_tokens = await self.db.oauth_tokens.find({"user_email": OAUTH_EMAIL}).to_list(10)
            
            if oauth_tokens:
                latest_token = max(oauth_tokens, key=lambda x: x.get('created_at', datetime.min))
                
                # Verify token structure
                has_access_token = bool(latest_token.get('access_token'))
                has_refresh_token = bool(latest_token.get('refresh_token'))
                has_correct_email = latest_token.get('user_email') == OAUTH_EMAIL
                
                # Check token validity
                expires_at = latest_token.get('expires_at', datetime.min)
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                token_valid = expires_at > datetime.utcnow()
                
                # Check authorized services
                authorized_services = latest_token.get('authorized_services', [])
                has_email_service = 'email' in authorized_services
                has_calendar_service = 'calendar' in authorized_services
                
                # Check scope
                scope = latest_token.get('scope', '')
                has_gmail_scope = 'gmail' in scope
                has_calendar_scope = 'calendar' in scope
                
                tokens_valid = (has_access_token and has_refresh_token and has_correct_email and 
                               token_valid and has_email_service and has_calendar_service and
                               has_gmail_scope and has_calendar_scope)
                
                details = f"Tokens: {len(oauth_tokens)}, Access: {has_access_token}, Refresh: {has_refresh_token}, " \
                         f"Valid: {token_valid}, Services: email={has_email_service}/calendar={has_calendar_service}, " \
                         f"Scopes: gmail={has_gmail_scope}/calendar={has_calendar_scope}"
                
                self.log_test_result("OAuth Tokens Verification", tokens_valid, details)
                return tokens_valid
            else:
                self.log_test_result("OAuth Tokens Verification", False, f"No OAuth tokens found for {OAUTH_EMAIL}")
                return False
                
        except Exception as e:
            self.log_test_result("OAuth Tokens Verification", False, f"Exception: {str(e)}")
            return False
    
    def test_api_endpoints_without_auth(self):
        """Test 5: API Endpoints That Don't Require Authentication"""
        print(f"\n🌐 Testing Public API Endpoints...")
        
        try:
            # Test polling status endpoint
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                polling_status_ok = response.status_code == 200
                polling_details = f"Status: {response.status_code}"
                if polling_status_ok:
                    data = response.json()
                    polling_details += f", Service status: {data.get('status', 'unknown')}"
            except Exception as e:
                polling_status_ok = False
                polling_details = f"Exception: {str(e)}"
            
            # Test accounts status endpoint
            try:
                response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                accounts_status_ok = response.status_code == 200
                accounts_details = f"Status: {response.status_code}"
                if accounts_status_ok:
                    data = response.json()
                    accounts_count = len(data.get('accounts', []))
                    accounts_details += f", Accounts: {accounts_count}"
            except Exception as e:
                accounts_status_ok = False
                accounts_details = f"Exception: {str(e)}"
            
            # Test OAuth status endpoints
            try:
                response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
                google_oauth_ok = response.status_code == 200
                google_details = f"Status: {response.status_code}"
            except Exception as e:
                google_oauth_ok = False
                google_details = f"Exception: {str(e)}"
            
            all_endpoints_ok = polling_status_ok and accounts_status_ok and google_oauth_ok
            
            # Log individual results
            self.log_test_result("API - Polling Status", polling_status_ok, polling_details)
            self.log_test_result("API - Accounts Status", accounts_status_ok, accounts_details)
            self.log_test_result("API - Google OAuth Status", google_oauth_ok, google_details)
            
            details = f"Polling: {polling_status_ok}, Accounts: {accounts_status_ok}, OAuth: {google_oauth_ok}"
            self.log_test_result("Public API Endpoints", all_endpoints_ok, details)
            
            return all_endpoints_ok
            
        except Exception as e:
            self.log_test_result("Public API Endpoints", False, f"Exception: {str(e)}")
            return False
    
    async def test_backend_services_integration(self):
        """Test 6: Backend Services Integration"""
        print(f"\n🔧 Testing Backend Services Integration...")
        
        try:
            # Check if GoogleCalendarService can be imported and used
            try:
                from google_services import GoogleCalendarService
                service_import_ok = True
                import_details = "GoogleCalendarService imported successfully"
            except Exception as e:
                service_import_ok = False
                import_details = f"Import failed: {str(e)}"
            
            # Check if OAuth tokens can be retrieved
            oauth_token_retrieval_ok = False
            if self.oauth_user_id:
                try:
                    oauth_tokens = await self.db.oauth_tokens.find({"user_id": self.oauth_user_id}).to_list(1)
                    oauth_token_retrieval_ok = len(oauth_tokens) > 0
                    token_details = f"Tokens found: {len(oauth_tokens)}"
                except Exception as e:
                    token_details = f"Token retrieval failed: {str(e)}"
            else:
                token_details = "No OAuth user ID available"
            
            # Check if email polling service is working
            try:
                from email_services import get_polling_service
                polling_service = get_polling_service(MONGO_URL, DB_NAME)
                polling_service_ok = polling_service is not None
                polling_details = f"Polling service initialized: {polling_service_ok}"
            except Exception as e:
                polling_service_ok = False
                polling_details = f"Polling service failed: {str(e)}"
            
            integration_ok = service_import_ok and oauth_token_retrieval_ok and polling_service_ok
            
            # Log individual results
            self.log_test_result("Backend - Service Import", service_import_ok, import_details)
            self.log_test_result("Backend - Token Retrieval", oauth_token_retrieval_ok, token_details)
            self.log_test_result("Backend - Polling Service", polling_service_ok, polling_details)
            
            details = f"Import: {service_import_ok}, Tokens: {oauth_token_retrieval_ok}, Polling: {polling_service_ok}"
            self.log_test_result("Backend Services Integration", integration_ok, details)
            
            return integration_ok
            
        except Exception as e:
            self.log_test_result("Backend Services Integration", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print(f"COMPREHENSIVE OAUTH TESTING SUMMARY FOR {OAUTH_EMAIL}")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL:  {len(self.test_results)}")
        
        # Calculate success rate
        success_rate = (len(passed_tests) / len(self.test_results)) * 100 if self.test_results else 0
        print(f"📈 SUCCESS RATE: {success_rate:.1f}%")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        if success_rate >= 80:
            print("✅ OAuth integration is working well")
        elif success_rate >= 60:
            print("⚠️ OAuth integration has some issues but core functionality works")
        else:
            print("❌ OAuth integration has significant issues")
        
        print("\n" + "="*80)
        
        # Return overall success (80% threshold)
        return success_rate >= 80

async def main():
    """Main test execution"""
    print(f"🚀 Starting Comprehensive OAuth Testing for {OAUTH_EMAIL}")
    print(f"🌐 Backend URL: {BACKEND_URL}")
    print(f"🗄️ Database: {MONGO_URL}/{DB_NAME}")
    
    tester = FinalOAuthTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting")
            return False
        
        # Run comprehensive tests
        print("\n" + "="*60)
        print("STARTING COMPREHENSIVE OAUTH TESTS")
        print("="*60)
        
        # Test 1: OAuth Account Verification
        await tester.test_oauth_account_verification()
        
        # Test 2: Email Polling Status
        await tester.test_email_polling_status()
        
        # Test 3: Calendar Provider Verification
        await tester.test_calendar_provider_verification()
        
        # Test 4: OAuth Tokens Verification
        await tester.test_oauth_tokens_verification()
        
        # Test 5: API Endpoints (No Auth Required)
        tester.test_api_endpoints_without_auth()
        
        # Test 6: Backend Services Integration
        await tester.test_backend_services_integration()
        
        # Print comprehensive summary
        success = tester.print_summary()
        
        return success
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)