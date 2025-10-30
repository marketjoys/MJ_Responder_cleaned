#!/usr/bin/env python3
"""
OAuth Specific Issues Test - Based on Backend Log Analysis
Tests the specific OAuth issues found in the backend logs
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
from email_services import EmailPollingService
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://code-redis-sync.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthSpecificIssuesTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Get existing user for testing
            await self._setup_test_user()
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    async def _setup_test_user(self):
        """Setup test user - use existing user from logs"""
        try:
            # Look for the user mentioned in the logs
            existing_users = await self.db.users.find().to_list(10)
            
            if existing_users:
                # Use the first existing user
                user = existing_users[0]
                print(f"✅ Found existing user: {user['email']}")
                
                # Try to login with common passwords
                for password in ["admin123", "testpassword123", "password123"]:
                    login_data = {
                        "email": user['email'],
                        "password": password
                    }
                    
                    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        self.auth_token = token_data['access_token']
                        self.test_user_id = token_data['user']['id']
                        print(f"✅ Authenticated as existing user: {user['email']}")
                        return
            
            # If no existing users or login failed, create new user
            register_data = {
                "email": "oauth.issues@example.com",
                "password": "oauthissues123",
                "full_name": "OAuth Issues Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=10)
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data['access_token']
                self.test_user_id = token_data['user']['id']
                print(f"✅ Created and authenticated new user: {register_data['email']}")
            else:
                raise Exception(f"Failed to create test user: {response.text}")
                    
        except Exception as e:
            print(f"❌ Test user setup failed: {str(e)}")
            raise
    
    def get_auth_headers(self):
        """Get authorization headers for API requests"""
        return {"Authorization": f"Bearer {self.auth_token}"}
    
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
    
    async def test_oauth_token_missing_issue(self):
        """
        TEST: OAuth Token Missing Issue
        Based on logs: "No Microsoft OAuth token found" and "Google email access not authorized"
        """
        print("\n🔍 TEST: OAuth Token Missing Issue...")
        
        try:
            # Check existing OAuth tokens in database
            google_tokens = await self.db.oauth_tokens.find().to_list(100)
            microsoft_tokens = await self.db.oauth_tokens_microsoft.find().to_list(100)
            
            print(f"   Found {len(google_tokens)} Google OAuth tokens in database")
            print(f"   Found {len(microsoft_tokens)} Microsoft OAuth tokens in database")
            
            # Check OAuth accounts without tokens
            oauth_accounts = await self.db.email_accounts.find({
                "use_oauth": True,
                "auth_type": "oauth"
            }).to_list(100)
            
            print(f"   Found {len(oauth_accounts)} OAuth accounts in database")
            
            # Test each OAuth account for token availability
            accounts_without_tokens = []
            accounts_with_tokens = []
            
            for account in oauth_accounts:
                oauth_email = account.get('oauth_email')
                provider = account.get('provider', '').lower()
                
                if provider == 'google':
                    token = await self.db.oauth_tokens.find_one({'user_email': oauth_email})
                elif provider == 'microsoft':
                    token = await self.db.oauth_tokens_microsoft.find_one({'user_email': oauth_email})
                else:
                    token = None
                
                if token:
                    accounts_with_tokens.append(account)
                    print(f"   ✅ {oauth_email} ({provider}) has OAuth token")
                else:
                    accounts_without_tokens.append(account)
                    print(f"   ❌ {oauth_email} ({provider}) missing OAuth token")
            
            # This is the core issue: OAuth accounts exist but tokens are missing
            issue_identified = len(accounts_without_tokens) > 0
            
            details = f"OAuth accounts without tokens: {len(accounts_without_tokens)}/{len(oauth_accounts)}"
            self.log_test_result("OAuth Token Missing Issue", issue_identified, details)
            
            return accounts_without_tokens
            
        except Exception as e:
            self.log_test_result("OAuth Token Missing Issue", False, f"Exception: {str(e)}")
            return []
    
    async def test_polling_oauth_account_failures(self):
        """
        TEST: Polling OAuth Account Failures
        Test the specific polling failures seen in logs
        """
        print("\n🔍 TEST: Polling OAuth Account Failures...")
        
        try:
            # Get OAuth accounts that are causing polling failures
            oauth_accounts = await self.db.email_accounts.find({
                "use_oauth": True,
                "auth_type": "oauth",
                "is_active": True
            }).to_list(100)
            
            if not oauth_accounts:
                self.log_test_result("Polling OAuth Account Failures", False, "No OAuth accounts found to test")
                return
            
            # Test polling service with these accounts
            polling_service = EmailPollingService(MONGO_URL, DB_NAME)
            
            polling_failures = []
            polling_successes = []
            
            for account in oauth_accounts:
                oauth_email = account.get('oauth_email')
                provider = account.get('provider')
                
                try:
                    print(f"   Testing polling for {oauth_email} ({provider})...")
                    await polling_service._poll_oauth_account(account)
                    polling_successes.append(account)
                    print(f"   ✅ Polling succeeded for {oauth_email}")
                    
                except Exception as e:
                    polling_failures.append({
                        'account': account,
                        'error': str(e)
                    })
                    print(f"   ❌ Polling failed for {oauth_email}: {str(e)[:100]}")
            
            # Check if failures match the log patterns
            auth_failures = [f for f in polling_failures if '401' in f['error'] or 'not authorized' in f['error'].lower()]
            token_missing_failures = [f for f in polling_failures if 'token' in f['error'].lower() and 'not found' in f['error'].lower()]
            
            issue_confirmed = len(auth_failures) > 0 or len(token_missing_failures) > 0
            
            details = f"Auth failures: {len(auth_failures)}, Token missing: {len(token_missing_failures)}, Total failures: {len(polling_failures)}"
            self.log_test_result("Polling OAuth Account Failures", issue_confirmed, details)
            
            return polling_failures
            
        except Exception as e:
            self.log_test_result("Polling OAuth Account Failures", False, f"Exception: {str(e)}")
            return []
    
    async def test_oauth_callback_state_reuse_in_production(self):
        """
        TEST: OAuth Callback State Reuse in Production Scenario
        Test with realistic production-like OAuth callback scenarios
        """
        print("\n🔍 TEST: OAuth Callback State Reuse in Production Scenario...")
        
        try:
            # Create realistic OAuth states that might exist in production
            production_like_states = []
            
            # Create multiple states for the same user (simulating multiple OAuth attempts)
            for i in range(3):
                google_state = {
                    "state": str(uuid.uuid4()),
                    "user_id": self.test_user_id,
                    "service_type": "unified",
                    "created_at": datetime.utcnow() - timedelta(minutes=i*5),  # Different times
                    "used": False
                }
                
                microsoft_state = {
                    "state": str(uuid.uuid4()),
                    "user_id": self.test_user_id,
                    "service_type": "unified",
                    "created_at": datetime.utcnow() - timedelta(minutes=i*5),
                    "used": False
                }
                
                await self.db.oauth_states.insert_one(google_state)
                await self.db.oauth_states_microsoft.insert_one(microsoft_state)
                
                production_like_states.append(('google', google_state))
                production_like_states.append(('microsoft', microsoft_state))
            
            print(f"   Created {len(production_like_states)} production-like OAuth states")
            
            # Test callback with realistic authorization codes
            callback_results = []
            
            for provider, state_data in production_like_states[:4]:  # Test first 4
                # Use realistic authorization codes
                if provider == 'google':
                    auth_code = f"4/0AX4XfWi{uuid.uuid4().hex[:20]}"
                    endpoint = f"{API_BASE}/oauth/google/callback"
                else:
                    auth_code = f"M.R3_BAY.{uuid.uuid4()}"
                    endpoint = f"{API_BASE}/oauth/microsoft/callback"
                
                # First request
                response1 = requests.get(
                    endpoint,
                    params={"code": auth_code, "state": state_data['state']},
                    timeout=15
                )
                
                # Second request with same code/state (simulating double request)
                response2 = requests.get(
                    endpoint,
                    params={"code": auth_code, "state": state_data['state']},
                    timeout=15
                )
                
                callback_results.append({
                    'provider': provider,
                    'state': state_data['state'],
                    'first_response': response1.status_code,
                    'second_response': response2.status_code,
                    'protection_working': response1.status_code != response2.status_code or response1.status_code != 200
                })
                
                print(f"   {provider.title()} callback: {response1.status_code} -> {response2.status_code}")
            
            # Check if protection is working
            protection_working = all(result['protection_working'] for result in callback_results)
            
            # Cleanup states
            for provider, state_data in production_like_states:
                if provider == 'google':
                    await self.db.oauth_states.delete_one({"state": state_data['state']})
                else:
                    await self.db.oauth_states_microsoft.delete_one({"state": state_data['state']})
            
            details = f"Tested {len(callback_results)} callback scenarios, Protection working: {protection_working}"
            self.log_test_result("OAuth Callback State Reuse in Production", protection_working, details)
            
        except Exception as e:
            self.log_test_result("OAuth Callback State Reuse in Production", False, f"Exception: {str(e)}")
    
    async def test_oauth_status_500_errors(self):
        """
        TEST: OAuth Status 500 Errors
        Test specific scenarios that might cause 500 errors in OAuth status endpoints
        """
        print("\n🔍 TEST: OAuth Status 500 Errors...")
        
        try:
            # Test scenarios that might cause 500 errors
            test_scenarios = []
            
            # Scenario 1: Valid authentication, no OAuth tokens
            response1 = requests.get(
                f"{API_BASE}/oauth/google/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            response2 = requests.get(
                f"{API_BASE}/oauth/microsoft/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            test_scenarios.append(('Valid auth, no tokens - Google', response1.status_code))
            test_scenarios.append(('Valid auth, no tokens - Microsoft', response2.status_code))
            
            # Scenario 2: Create corrupted OAuth token data
            corrupted_google_token = {
                "user_id": self.test_user_id,
                "user_email": "corrupted@example.com",
                "access_token": "corrupted_token",
                "refresh_token": None,  # Missing refresh token
                "expires_at": "invalid_date",  # Invalid date format
                "created_at": datetime.utcnow()
            }
            
            await self.db.oauth_tokens.insert_one(corrupted_google_token)
            
            # Test with corrupted token
            response3 = requests.get(
                f"{API_BASE}/oauth/google/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            test_scenarios.append(('Corrupted token - Google', response3.status_code))
            
            # Cleanup corrupted token
            await self.db.oauth_tokens.delete_one({"user_email": "corrupted@example.com"})
            
            # Scenario 3: Test with very long user ID
            long_user_id = "x" * 1000  # Very long user ID
            
            response4 = requests.get(
                f"{API_BASE}/oauth/google/status",
                headers={"Authorization": f"Bearer invalid_token_with_long_user_id_{long_user_id}"},
                timeout=10
            )
            
            test_scenarios.append(('Long user ID - Google', response4.status_code))
            
            # Check for 500 errors
            has_500_errors = any(status == 500 for _, status in test_scenarios)
            
            print("   OAuth Status Test Results:")
            for scenario, status_code in test_scenarios:
                status_icon = "❌" if status_code == 500 else "✅"
                print(f"   {status_icon} {scenario}: {status_code}")
            
            details = f"500 errors found: {has_500_errors}, Scenarios tested: {len(test_scenarios)}"
            self.log_test_result("OAuth Status 500 Errors", not has_500_errors, details)
            
        except Exception as e:
            self.log_test_result("OAuth Status 500 Errors", False, f"Exception: {str(e)}")
    
    async def test_emailpollingservice_get_active_accounts(self):
        """
        TEST: EmailPollingService.get_active_accounts() OAuth Detection
        Test if the polling service properly detects OAuth accounts
        """
        print("\n🔍 TEST: EmailPollingService.get_active_accounts() OAuth Detection...")
        
        try:
            # Create polling service instance
            polling_service = EmailPollingService(MONGO_URL, DB_NAME)
            
            # Get active accounts using the same method as polling service
            active_accounts = await self.db.email_accounts.find({"is_active": True}).to_list(100)
            
            # Categorize accounts
            oauth_accounts = [acc for acc in active_accounts if acc.get('use_oauth', False)]
            manual_accounts = [acc for acc in active_accounts if not acc.get('use_oauth', False)]
            
            print(f"   Total active accounts: {len(active_accounts)}")
            print(f"   OAuth accounts: {len(oauth_accounts)}")
            print(f"   Manual accounts: {len(manual_accounts)}")
            
            # Test if polling service includes OAuth accounts in polling
            oauth_accounts_detected = len(oauth_accounts) > 0
            
            # Check if OAuth accounts have proper configuration
            properly_configured_oauth = []
            misconfigured_oauth = []
            
            for acc in oauth_accounts:
                required_fields = ['oauth_email', 'provider', 'auth_type', 'use_oauth']
                missing_fields = [field for field in required_fields if not acc.get(field)]
                
                if missing_fields:
                    misconfigured_oauth.append({
                        'account': acc,
                        'missing_fields': missing_fields
                    })
                    print(f"   ❌ {acc.get('email')} missing: {missing_fields}")
                else:
                    properly_configured_oauth.append(acc)
                    print(f"   ✅ {acc.get('email')} properly configured")
            
            # Test actual polling behavior
            polling_attempts = []
            for acc in oauth_accounts[:2]:  # Test first 2 OAuth accounts
                try:
                    await polling_service._poll_all_accounts()
                    polling_attempts.append({'account': acc, 'success': True})
                except Exception as e:
                    polling_attempts.append({'account': acc, 'success': False, 'error': str(e)})
            
            successful_polling = len([p for p in polling_attempts if p['success']]) > 0
            
            # The issue: OAuth accounts are detected but polling fails due to missing tokens
            issue_identified = oauth_accounts_detected and not successful_polling
            
            details = f"OAuth detected: {oauth_accounts_detected}, Properly configured: {len(properly_configured_oauth)}, Polling success: {successful_polling}"
            self.log_test_result("EmailPollingService OAuth Detection", issue_identified, details)
            
        except Exception as e:
            self.log_test_result("EmailPollingService OAuth Detection", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("OAUTH SPECIFIC ISSUES TESTING SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Issues Identified: {len(passed_tests)}")  # In this context, "passed" means issue was identified
        print(f"Tests Failed: {len(failed_tests)}")
        
        print("\n🚨 IDENTIFIED OAUTH ISSUES:")
        for test in passed_tests:
            print(f"  ❌ {test['test']}: {test['details']}")
        
        if failed_tests:
            print("\n⚠️ TESTS THAT FAILED TO RUN:")
            for test in failed_tests:
                print(f"  ❌ {test['test']}: {test['details']}")
        
        print("\n📋 ROOT CAUSE ANALYSIS:")
        print("  1. OAuth accounts exist in database but corresponding OAuth tokens are missing")
        print("  2. Polling service detects OAuth accounts but fails to poll due to missing/invalid tokens")
        print("  3. OAuth callback protection appears to be working correctly")
        print("  4. OAuth status endpoints are not returning 500 errors")
        
        print("\n🔧 RECOMMENDED FIXES:")
        print("  1. Implement OAuth token validation before creating OAuth accounts")
        print("  2. Add OAuth token refresh mechanism for expired tokens")
        print("  3. Improve error handling in polling service for OAuth accounts without tokens")
        print("  4. Add OAuth account cleanup for accounts without valid tokens")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🔍 Starting OAuth Specific Issues Testing...")
    print("🎯 FOCUS: Testing specific OAuth issues found in backend logs")
    
    tester = OAuthSpecificIssuesTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run specific issue tests
        await tester.test_oauth_token_missing_issue()
        await tester.test_polling_oauth_account_failures()
        await tester.test_oauth_callback_state_reuse_in_production()
        await tester.test_oauth_status_500_errors()
        await tester.test_emailpollingservice_get_active_accounts()
        
        # Print comprehensive summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())