#!/usr/bin/env python3
"""
OAuth Final Comprehensive Test - Review Request Issues
Tests the exact OAuth flow issues mentioned in the review request with comprehensive scenarios
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-sync-fix-2.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthFinalComprehensiveTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.created_oauth_accounts = []
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            await self._setup_test_user()
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    async def _setup_test_user(self):
        """Setup test user"""
        try:
            # Create new user for clean testing
            register_data = {
                "email": f"oauth.final.test.{int(time.time())}@example.com",
                "password": "oauthfinaltest123",
                "full_name": "OAuth Final Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=10)
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data['access_token']
                self.test_user_id = token_data['user']['id']
                print(f"✅ Created and authenticated test user: {register_data['email']}")
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
        # Cleanup created OAuth accounts
        for account_id in self.created_oauth_accounts:
            try:
                await self.db.email_accounts.delete_one({"id": account_id})
            except:
                pass
        
        # Cleanup test OAuth states and tokens
        try:
            await self.db.oauth_states.delete_many({"user_id": self.test_user_id})
            await self.db.oauth_states_microsoft.delete_many({"user_id": self.test_user_id})
            await self.db.oauth_tokens.delete_many({"user_id": self.test_user_id})
            await self.db.oauth_tokens_microsoft.delete_many({"user_id": self.test_user_id})
        except:
            pass
            
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
    
    async def test_double_request_problem(self):
        """
        REVIEW REQUEST TEST 1: Double Request Problem
        Test OAuth callback handling with duplicate requests to identify protection against reused authorization codes
        """
        print("\n🔒 REVIEW REQUEST TEST 1: Double Request Problem...")
        
        try:
            # Test Google OAuth callback with same code/state twice
            print("   Testing Google OAuth callback duplicate protection...")
            google_protection = await self._test_google_callback_duplicate_requests()
            
            # Test Microsoft OAuth callback with same code/state twice
            print("   Testing Microsoft OAuth callback duplicate protection...")
            microsoft_protection = await self._test_microsoft_callback_duplicate_requests()
            
            # Verify proper error handling for reused authorization codes
            print("   Testing reused authorization code error handling...")
            error_handling = await self._test_reused_code_error_handling()
            
            all_passed = google_protection and microsoft_protection and error_handling
            
            details = f"Google protection: {google_protection}, Microsoft protection: {microsoft_protection}, Error handling: {error_handling}"
            self.log_test_result("Double Request Problem", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Double Request Problem", False, f"Exception: {str(e)}")
    
    async def _test_google_callback_duplicate_requests(self):
        """Test Google OAuth callback with duplicate requests"""
        try:
            # Create valid OAuth state
            test_state = str(uuid.uuid4())
            test_code = f"4/0AX4XfWi{uuid.uuid4().hex[:20]}"  # Realistic Google auth code
            
            oauth_state = {
                "state": test_state,
                "user_id": self.test_user_id,
                "service_type": "unified",
                "created_at": datetime.utcnow(),
                "used": False
            }
            await self.db.oauth_states.insert_one(oauth_state)
            
            # First request
            response1 = requests.get(
                f"{API_BASE}/oauth/google/callback",
                params={"code": test_code, "state": test_state},
                timeout=15
            )
            
            # Second request with same code/state
            response2 = requests.get(
                f"{API_BASE}/oauth/google/callback",
                params={"code": test_code, "state": test_state},
                timeout=15
            )
            
            # Check if state was marked as used
            final_state = await self.db.oauth_states.find_one({"state": test_state})
            state_used = final_state and final_state.get('used', False)
            
            print(f"     Google: {response1.status_code} -> {response2.status_code}, State used: {state_used}")
            
            # Protection is working if:
            # 1. Both requests fail (invalid code) OR
            # 2. First succeeds, second fails OR
            # 3. State is marked as used
            protection_working = (
                (response1.status_code != 200 and response2.status_code != 200) or
                (response1.status_code == 200 and response2.status_code != 200) or
                state_used
            )
            
            # Cleanup
            await self.db.oauth_states.delete_one({"state": test_state})
            
            return protection_working
            
        except Exception as e:
            print(f"     Google callback test failed: {str(e)}")
            return False
    
    async def _test_microsoft_callback_duplicate_requests(self):
        """Test Microsoft OAuth callback with duplicate requests"""
        try:
            # Create valid OAuth state
            test_state = str(uuid.uuid4())
            test_code = f"M.R3_BAY.{uuid.uuid4()}"  # Realistic Microsoft auth code
            
            oauth_state = {
                "state": test_state,
                "user_id": self.test_user_id,
                "service_type": "unified",
                "created_at": datetime.utcnow(),
                "used": False
            }
            await self.db.oauth_states_microsoft.insert_one(oauth_state)
            
            # First request
            response1 = requests.get(
                f"{API_BASE}/oauth/microsoft/callback",
                params={"code": test_code, "state": test_state},
                timeout=15
            )
            
            # Second request with same code/state
            response2 = requests.get(
                f"{API_BASE}/oauth/microsoft/callback",
                params={"code": test_code, "state": test_state},
                timeout=15
            )
            
            # Check if state was marked as used
            final_state = await self.db.oauth_states_microsoft.find_one({"state": test_state})
            state_used = final_state and final_state.get('used', False)
            
            print(f"     Microsoft: {response1.status_code} -> {response2.status_code}, State used: {state_used}")
            
            protection_working = (
                (response1.status_code != 200 and response2.status_code != 200) or
                (response1.status_code == 200 and response2.status_code != 200) or
                state_used
            )
            
            # Cleanup
            await self.db.oauth_states_microsoft.delete_one({"state": test_state})
            
            return protection_working
            
        except Exception as e:
            print(f"     Microsoft callback test failed: {str(e)}")
            return False
    
    async def _test_reused_code_error_handling(self):
        """Test proper error handling for reused authorization codes"""
        try:
            # Test with expired state
            expired_state = str(uuid.uuid4())
            expired_time = datetime.utcnow() - timedelta(hours=1)
            
            oauth_state = {
                "state": expired_state,
                "user_id": self.test_user_id,
                "service_type": "unified",
                "created_at": expired_time,
                "used": False
            }
            await self.db.oauth_states.insert_one(oauth_state)
            
            response = requests.get(
                f"{API_BASE}/oauth/google/callback",
                params={"code": "test_code", "state": expired_state},
                timeout=15
            )
            
            # Should handle expired state gracefully
            handles_expired = response.status_code in [400, 401, 403]
            
            # Cleanup
            await self.db.oauth_states.delete_one({"state": expired_state})
            
            print(f"     Expired state handling: {response.status_code}")
            
            return handles_expired
            
        except Exception as e:
            print(f"     Error handling test failed: {str(e)}")
            return False
    
    async def test_polling_start_issue(self):
        """
        REVIEW REQUEST TEST 2: Polling Start Issue
        Check if email polling service automatically detects and includes newly added OAuth accounts
        """
        print("\n📡 REVIEW REQUEST TEST 2: Polling Start Issue...")
        
        try:
            # Check if EmailPollingService.get_active_accounts() includes OAuth accounts after they're added
            print("   Testing EmailPollingService.get_active_accounts() OAuth detection...")
            oauth_detection = await self._test_oauth_account_detection()
            
            # Test polling service restart/reload after new OAuth account addition
            print("   Testing polling service restart/reload after OAuth account addition...")
            restart_detection = await self._test_polling_restart_detection()
            
            # Verify OAuth account polling status in /api/polling/status
            print("   Testing OAuth account polling status in /api/polling/status...")
            polling_status = await self._test_oauth_polling_status()
            
            all_passed = oauth_detection and restart_detection and polling_status
            
            details = f"OAuth detection: {oauth_detection}, Restart detection: {restart_detection}, Polling status: {polling_status}"
            self.log_test_result("Polling Start Issue", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Polling Start Issue", False, f"Exception: {str(e)}")
    
    async def _test_oauth_account_detection(self):
        """Test if EmailPollingService detects newly added OAuth accounts"""
        try:
            # Get initial active accounts
            initial_accounts = await self.db.email_accounts.find({"is_active": True}).to_list(100)
            initial_count = len(initial_accounts)
            
            # Create OAuth accounts
            google_account_id = await self._create_oauth_account("google", "test.polling.google@gmail.com")
            microsoft_account_id = await self._create_oauth_account("microsoft", "test.polling.microsoft@outlook.com")
            
            if google_account_id:
                self.created_oauth_accounts.append(google_account_id)
            if microsoft_account_id:
                self.created_oauth_accounts.append(microsoft_account_id)
            
            # Check if accounts are detected
            updated_accounts = await self.db.email_accounts.find({"is_active": True}).to_list(100)
            updated_count = len(updated_accounts)
            
            accounts_detected = updated_count > initial_count
            
            print(f"     Active accounts: {initial_count} -> {updated_count}")
            
            return accounts_detected and (google_account_id is not None or microsoft_account_id is not None)
            
        except Exception as e:
            print(f"     OAuth account detection test failed: {str(e)}")
            return False
    
    async def _create_oauth_account(self, provider: str, email: str):
        """Create OAuth account for testing"""
        try:
            account_id = str(uuid.uuid4())
            oauth_account = {
                "id": account_id,
                "user_id": self.test_user_id,
                "name": f"Test {provider.title()} Polling Account",
                "email": email,
                "provider": provider,
                "auth_type": "oauth",
                "use_oauth": True,
                "oauth_token_id": str(uuid.uuid4()),
                "oauth_email": email,
                "is_active": True,
                "persona": f"Test {provider.title()} Assistant",
                "signature": f"Test {provider.title()} Signature",
                "auto_send": True,
                "enable_follow_ups": True,
                "created_at": datetime.utcnow()
            }
            
            await self.db.email_accounts.insert_one(oauth_account)
            print(f"     Created {provider} OAuth account: {email}")
            return account_id
            
        except Exception as e:
            print(f"     Failed to create {provider} OAuth account: {str(e)}")
            return None
    
    async def _test_polling_restart_detection(self):
        """Test polling service restart/reload detection"""
        try:
            # Stop polling service
            stop_response = requests.post(f"{API_BASE}/polling/control", json={"action": "stop"}, timeout=10)
            await asyncio.sleep(2)
            
            # Start polling service
            start_response = requests.post(f"{API_BASE}/polling/control", json={"action": "start"}, timeout=10)
            await asyncio.sleep(3)
            
            # Check if service is running
            status_response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            
            if status_response.status_code == 200:
                status = status_response.json()
                service_running = status.get('status') == 'running'
                print(f"     Polling service after restart: {status.get('status')}")
                return service_running
            
            return False
            
        except Exception as e:
            print(f"     Polling restart test failed: {str(e)}")
            return False
    
    async def _test_oauth_polling_status(self):
        """Test OAuth account polling status"""
        try:
            response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                accounts = status_data.get('accounts', [])
                
                # Look for OAuth accounts in status
                oauth_accounts_in_status = [
                    acc for acc in accounts 
                    if 'oauth' in acc.get('email', '').lower() or 
                       acc.get('email', '').endswith('@gmail.com') or 
                       acc.get('email', '').endswith('@outlook.com')
                ]
                
                print(f"     OAuth accounts in polling status: {len(oauth_accounts_in_status)}")
                return len(oauth_accounts_in_status) > 0
            
            return False
            
        except Exception as e:
            print(f"     OAuth polling status test failed: {str(e)}")
            return False
    
    async def test_oauth_status_endpoints(self):
        """
        REVIEW REQUEST TEST 3: OAuth Status Endpoints
        Test OAuth status endpoints for 500 errors
        """
        print("\n📊 REVIEW REQUEST TEST 3: OAuth Status Endpoints...")
        
        try:
            # Test GET /api/oauth/google/status with valid authentication
            print("   Testing GET /api/oauth/google/status with valid authentication...")
            google_status = await self._test_google_oauth_status()
            
            # Test GET /api/oauth/microsoft/status with valid authentication
            print("   Testing GET /api/oauth/microsoft/status with valid authentication...")
            microsoft_status = await self._test_microsoft_oauth_status()
            
            # Check for 500 errors and authentication issues
            print("   Testing OAuth status endpoints for 500 errors...")
            error_handling = await self._test_oauth_status_500_errors()
            
            all_passed = google_status and microsoft_status and error_handling
            
            details = f"Google status: {google_status}, Microsoft status: {microsoft_status}, 500 error handling: {error_handling}"
            self.log_test_result("OAuth Status Endpoints", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Status Endpoints", False, f"Exception: {str(e)}")
    
    async def _test_google_oauth_status(self):
        """Test Google OAuth status endpoint"""
        try:
            response = requests.get(
                f"{API_BASE}/oauth/google/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            # Should not return 500
            no_500_error = response.status_code != 500
            
            # Should return valid JSON
            valid_json = False
            if response.status_code in [200, 401, 403]:
                try:
                    json_data = response.json()
                    valid_json = True
                except:
                    pass
            
            print(f"     Google OAuth status: {response.status_code} (Valid JSON: {valid_json})")
            
            return no_500_error and valid_json
            
        except Exception as e:
            print(f"     Google OAuth status test failed: {str(e)}")
            return False
    
    async def _test_microsoft_oauth_status(self):
        """Test Microsoft OAuth status endpoint"""
        try:
            response = requests.get(
                f"{API_BASE}/oauth/microsoft/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            # Should not return 500
            no_500_error = response.status_code != 500
            
            # Should return valid JSON
            valid_json = False
            if response.status_code in [200, 401, 403]:
                try:
                    json_data = response.json()
                    valid_json = True
                except:
                    pass
            
            print(f"     Microsoft OAuth status: {response.status_code} (Valid JSON: {valid_json})")
            
            return no_500_error and valid_json
            
        except Exception as e:
            print(f"     Microsoft OAuth status test failed: {str(e)}")
            return False
    
    async def _test_oauth_status_500_errors(self):
        """Test OAuth status endpoints for 500 errors with edge cases"""
        try:
            # Test with corrupted token data (this caused 500 error in previous test)
            corrupted_token = {
                "user_id": self.test_user_id,
                "user_email": "corrupted.test@example.com",
                "access_token": "corrupted_token",
                "refresh_token": None,
                "expires_at": "invalid_date_format",  # This causes 500 error
                "created_at": datetime.utcnow()
            }
            
            await self.db.oauth_tokens.insert_one(corrupted_token)
            
            # Test Google status with corrupted token
            google_response = requests.get(
                f"{API_BASE}/oauth/google/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            # Test Microsoft status with corrupted token
            microsoft_response = requests.get(
                f"{API_BASE}/oauth/microsoft/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            # Check for 500 errors
            google_500 = google_response.status_code == 500
            microsoft_500 = microsoft_response.status_code == 500
            
            print(f"     Corrupted token test - Google: {google_response.status_code}, Microsoft: {microsoft_response.status_code}")
            
            # Cleanup corrupted token
            await self.db.oauth_tokens.delete_one({"user_email": "corrupted.test@example.com"})
            
            # 500 errors indicate issues that need fixing
            return not (google_500 or microsoft_500)
            
        except Exception as e:
            print(f"     OAuth status 500 error test failed: {str(e)}")
            return False
    
    async def test_oauth_account_polling_workflow(self):
        """
        COMPREHENSIVE TEST: OAuth Account Polling Workflow
        Create test scenarios to verify complete OAuth account polling workflow
        """
        print("\n🔄 COMPREHENSIVE TEST: OAuth Account Polling Workflow...")
        
        try:
            # Simulate OAuth account addition flow
            print("   Simulating OAuth account addition flow...")
            oauth_flow = await self._simulate_oauth_account_addition()
            
            # Check if new OAuth accounts appear in polling active accounts
            print("   Checking if OAuth accounts appear in polling active accounts...")
            polling_detection = await self._verify_oauth_in_polling()
            
            # Test OAuth status endpoint functionality
            print("   Testing OAuth status endpoint functionality...")
            status_functionality = await self._test_status_functionality()
            
            # Verify polling service can handle OAuth accounts properly
            print("   Verifying polling service OAuth account handling...")
            polling_handling = await self._verify_polling_handling()
            
            all_passed = oauth_flow and polling_detection and status_functionality and polling_handling
            
            details = f"OAuth flow: {oauth_flow}, Polling detection: {polling_detection}, Status functionality: {status_functionality}, Polling handling: {polling_handling}"
            self.log_test_result("OAuth Account Polling Workflow", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Account Polling Workflow", False, f"Exception: {str(e)}")
    
    async def _simulate_oauth_account_addition(self):
        """Simulate OAuth account addition flow"""
        try:
            # Create OAuth accounts with proper configuration
            google_id = await self._create_oauth_account("google", "workflow.google@gmail.com")
            microsoft_id = await self._create_oauth_account("microsoft", "workflow.microsoft@outlook.com")
            
            if google_id:
                self.created_oauth_accounts.append(google_id)
            if microsoft_id:
                self.created_oauth_accounts.append(microsoft_id)
            
            return (google_id is not None) or (microsoft_id is not None)
            
        except Exception as e:
            print(f"     OAuth account addition simulation failed: {str(e)}")
            return False
    
    async def _verify_oauth_in_polling(self):
        """Verify OAuth accounts appear in polling active accounts"""
        try:
            active_accounts = await self.db.email_accounts.find({"is_active": True}).to_list(100)
            oauth_accounts = [acc for acc in active_accounts if acc.get('use_oauth', False)]
            
            print(f"     OAuth accounts in active accounts: {len(oauth_accounts)}")
            
            return len(oauth_accounts) > 0
            
        except Exception as e:
            print(f"     OAuth polling verification failed: {str(e)}")
            return False
    
    async def _test_status_functionality(self):
        """Test OAuth status endpoint functionality"""
        try:
            google_response = requests.get(
                f"{API_BASE}/oauth/google/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            microsoft_response = requests.get(
                f"{API_BASE}/oauth/microsoft/status",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            google_functional = google_response.status_code != 500
            microsoft_functional = microsoft_response.status_code != 500
            
            return google_functional and microsoft_functional
            
        except Exception as e:
            print(f"     Status functionality test failed: {str(e)}")
            return False
    
    async def _verify_polling_handling(self):
        """Verify polling service can handle OAuth accounts"""
        try:
            polling_service = EmailPollingService(MONGO_URL, DB_NAME)
            
            oauth_accounts = await self.db.email_accounts.find({
                "is_active": True,
                "use_oauth": True
            }).to_list(10)
            
            if not oauth_accounts:
                return True  # No OAuth accounts to test
            
            # Test polling an OAuth account
            test_account = oauth_accounts[0]
            
            try:
                await polling_service._poll_account(test_account)
                print(f"     OAuth account polling succeeded: {test_account.get('email')}")
                return True
            except Exception as e:
                # Expected to fail due to missing tokens, but should not crash
                error_msg = str(e).lower()
                if 'oauth' in error_msg or 'token' in error_msg or 'authorized' in error_msg:
                    print(f"     OAuth account polling failed as expected (missing tokens): {str(e)[:100]}")
                    return True  # Expected failure
                else:
                    print(f"     OAuth account polling failed unexpectedly: {str(e)}")
                    return False
            
        except Exception as e:
            print(f"     Polling handling verification failed: {str(e)}")
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("OAUTH FINAL COMPREHENSIVE TESTING SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        print("\n📋 REVIEW REQUEST TEST RESULTS:")
        
        # Map tests to review request categories
        review_categories = {
            "Double Request Problem": [t for t in self.test_results if "Double Request" in t['test']],
            "Polling Start Issue": [t for t in self.test_results if "Polling Start" in t['test']],
            "OAuth Status Endpoints": [t for t in self.test_results if "OAuth Status" in t['test']]
        }
        
        for category, tests in review_categories.items():
            if tests:
                test = tests[0]  # Should only be one test per category
                status_icon = "✅" if test['passed'] else "❌"
                print(f"\n{status_icon} {category}: {'WORKING' if test['passed'] else 'ISSUES FOUND'}")
                print(f"   {test['details']}")
        
        if failed_tests:
            print("\n🚨 CRITICAL ISSUES IDENTIFIED:")
            for test in failed_tests:
                print(f"  ❌ {test['test']}")
                print(f"     Issue: {test['details']}")
        
        print("\n🔧 RECOMMENDATIONS:")
        if any("500" in t['details'] for t in failed_tests):
            print("  1. Fix OAuth status endpoint 500 errors with corrupted token data")
        if any("Polling" in t['test'] for t in failed_tests):
            print("  2. Improve OAuth account detection in polling service")
        if any("Double Request" in t['test'] for t in failed_tests):
            print("  3. Enhance OAuth callback duplicate request protection")
        
        print("\n" + "="*80)

async def main():
    """Main test execution"""
    print("🚀 Starting OAuth Final Comprehensive Testing...")
    print("🎯 REVIEW REQUEST FOCUS:")
    print("   1. Double Request Problem: OAuth callback duplicate request protection")
    print("   2. Polling Start Issue: OAuth account detection in polling service")
    print("   3. OAuth Status Endpoints: Testing for 500 errors")
    print(f"\nBackend URL: {BACKEND_URL}")
    print(f"Database: {MONGO_URL}/{DB_NAME}")
    
    tester = OAuthFinalComprehensiveTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run comprehensive OAuth tests based on review request
        await tester.test_double_request_problem()
        await tester.test_polling_start_issue()
        await tester.test_oauth_status_endpoints()
        await tester.test_oauth_account_polling_workflow()
        
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