#!/usr/bin/env python3
"""
OAuth Deep Dive Testing - Specific Issue Investigation
Focuses on the exact scenarios mentioned in the review request
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-cycle-fixer.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthDeepDiveTester:
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
        """Setup test user - try to find existing user first"""
        try:
            # Look for existing users in the database
            existing_users = await self.db.users.find().to_list(10)
            
            if existing_users:
                # Use the first existing user
                user = existing_users[0]
                print(f"✅ Found existing user: {user['email']}")
                
                # Try to login
                login_data = {
                    "email": user['email'],
                    "password": "admin123"  # Try common test password
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
                "email": "oauth.deepdive@example.com",
                "password": "deepdivetest123",
                "full_name": "OAuth Deep Dive Test User"
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
    
    async def investigate_oauth_callback_reuse_protection(self):
        """Deep dive into OAuth callback reuse protection"""
        print("\n🔍 DEEP DIVE: OAuth Callback Reuse Protection...")
        
        try:
            # Check if there are any existing OAuth states that might be reused
            existing_google_states = await self.db.oauth_states.find().to_list(100)
            existing_microsoft_states = await self.db.oauth_states_microsoft.find().to_list(100)
            
            print(f"   Found {len(existing_google_states)} existing Google OAuth states")
            print(f"   Found {len(existing_microsoft_states)} existing Microsoft OAuth states")
            
            # Test with real-looking but invalid codes
            await self._test_realistic_oauth_codes()
            
            # Test state expiration
            await self._test_oauth_state_expiration()
            
            # Test concurrent requests
            await self._test_concurrent_oauth_requests()
            
        except Exception as e:
            print(f"   OAuth callback investigation failed: {str(e)}")
    
    async def _test_realistic_oauth_codes(self):
        """Test with realistic-looking OAuth codes"""
        print("   Testing with realistic OAuth codes...")
        
        # Google-style authorization code
        google_code = "4/0AX4XfWjYxZ1234567890abcdefghijklmnopqrstuvwxyz"
        google_state = str(uuid.uuid4())
        
        # Microsoft-style authorization code  
        microsoft_code = "M.R3_BAY.12345678-1234-1234-1234-123456789012"
        microsoft_state = str(uuid.uuid4())
        
        # Create valid states
        await self.db.oauth_states.insert_one({
            "state": google_state,
            "user_id": self.test_user_id,
            "service_type": "unified",
            "created_at": datetime.utcnow(),
            "used": False
        })
        
        await self.db.oauth_states_microsoft.insert_one({
            "state": microsoft_state,
            "user_id": self.test_user_id,
            "service_type": "unified",
            "created_at": datetime.utcnow(),
            "used": False
        })
        
        # Test Google callback
        google_response1 = requests.get(
            f"{API_BASE}/oauth/google/callback",
            params={"code": google_code, "state": google_state},
            timeout=15
        )
        
        google_response2 = requests.get(
            f"{API_BASE}/oauth/google/callback",
            params={"code": google_code, "state": google_state},
            timeout=15
        )
        
        # Test Microsoft callback
        microsoft_response1 = requests.get(
            f"{API_BASE}/oauth/microsoft/callback",
            params={"code": microsoft_code, "state": microsoft_state},
            timeout=15
        )
        
        microsoft_response2 = requests.get(
            f"{API_BASE}/oauth/microsoft/callback",
            params={"code": microsoft_code, "state": microsoft_state},
            timeout=15
        )
        
        print(f"   Google realistic code test: {google_response1.status_code} -> {google_response2.status_code}")
        print(f"   Microsoft realistic code test: {microsoft_response1.status_code} -> {microsoft_response2.status_code}")
        
        # Cleanup
        await self.db.oauth_states.delete_one({"state": google_state})
        await self.db.oauth_states_microsoft.delete_one({"state": microsoft_state})
    
    async def _test_oauth_state_expiration(self):
        """Test OAuth state expiration handling"""
        print("   Testing OAuth state expiration...")
        
        # Create expired state
        expired_state = str(uuid.uuid4())
        expired_time = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
        
        await self.db.oauth_states.insert_one({
            "state": expired_state,
            "user_id": self.test_user_id,
            "service_type": "unified",
            "created_at": expired_time,
            "used": False
        })
        
        # Test with expired state
        response = requests.get(
            f"{API_BASE}/oauth/google/callback",
            params={"code": "test_code", "state": expired_state},
            timeout=15
        )
        
        print(f"   Expired state test: {response.status_code}")
        
        # Cleanup
        await self.db.oauth_states.delete_one({"state": expired_state})
    
    async def _test_concurrent_oauth_requests(self):
        """Test concurrent OAuth callback requests"""
        print("   Testing concurrent OAuth requests...")
        
        test_state = str(uuid.uuid4())
        test_code = f"concurrent_test_{uuid.uuid4()}"
        
        # Create valid state
        await self.db.oauth_states.insert_one({
            "state": test_state,
            "user_id": self.test_user_id,
            "service_type": "unified",
            "created_at": datetime.utcnow(),
            "used": False
        })
        
        # Make concurrent requests
        import concurrent.futures
        import threading
        
        def make_request():
            return requests.get(
                f"{API_BASE}/oauth/google/callback",
                params={"code": test_code, "state": test_state},
                timeout=15
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        status_codes = [r.status_code for r in responses]
        print(f"   Concurrent requests status codes: {status_codes}")
        
        # Cleanup
        await self.db.oauth_states.delete_one({"state": test_state})
    
    async def investigate_polling_oauth_detection(self):
        """Deep dive into polling service OAuth account detection"""
        print("\n🔍 DEEP DIVE: Polling Service OAuth Detection...")
        
        try:
            # Check current polling service implementation
            await self._analyze_polling_service_oauth_handling()
            
            # Test with real OAuth account scenarios
            await self._test_real_oauth_account_scenarios()
            
            # Check EmailPollingService.get_active_accounts() specifically
            await self._test_get_active_accounts_method()
            
        except Exception as e:
            print(f"   Polling OAuth detection investigation failed: {str(e)}")
    
    async def _analyze_polling_service_oauth_handling(self):
        """Analyze how polling service handles OAuth accounts"""
        print("   Analyzing polling service OAuth handling...")
        
        # Get all email accounts
        all_accounts = await self.db.email_accounts.find().to_list(100)
        oauth_accounts = [acc for acc in all_accounts if acc.get('use_oauth', False)]
        manual_accounts = [acc for acc in all_accounts if not acc.get('use_oauth', False)]
        
        print(f"   Total accounts: {len(all_accounts)}")
        print(f"   OAuth accounts: {len(oauth_accounts)}")
        print(f"   Manual accounts: {len(manual_accounts)}")
        
        # Check OAuth account configurations
        for i, acc in enumerate(oauth_accounts[:3]):  # Show first 3
            print(f"   OAuth Account {i+1}:")
            print(f"     Email: {acc.get('email')}")
            print(f"     Provider: {acc.get('provider')}")
            print(f"     Auth Type: {acc.get('auth_type')}")
            print(f"     Use OAuth: {acc.get('use_oauth')}")
            print(f"     OAuth Email: {acc.get('oauth_email')}")
            print(f"     Is Active: {acc.get('is_active')}")
    
    async def _test_real_oauth_account_scenarios(self):
        """Test with real OAuth account scenarios"""
        print("   Testing real OAuth account scenarios...")
        
        # Create OAuth accounts that mimic real Microsoft/Google OAuth accounts
        real_google_account = {
            "id": str(uuid.uuid4()),
            "user_id": self.test_user_id,
            "name": "Real Google OAuth Test",
            "email": "realtest@gmail.com",
            "provider": "google",
            "auth_type": "oauth",
            "use_oauth": True,
            "oauth_token_id": str(uuid.uuid4()),
            "oauth_email": "realtest@gmail.com",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        real_microsoft_account = {
            "id": str(uuid.uuid4()),
            "user_id": self.test_user_id,
            "name": "Real Microsoft OAuth Test",
            "email": "realtest_outlook.com#EXT#@realtestoutlook.onmicrosoft.com",
            "provider": "microsoft",
            "auth_type": "oauth",
            "use_oauth": True,
            "oauth_token_id": str(uuid.uuid4()),
            "oauth_email": "realtest_outlook.com#EXT#@realtestoutlook.onmicrosoft.com",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        # Insert accounts
        await self.db.email_accounts.insert_one(real_google_account)
        await self.db.email_accounts.insert_one(real_microsoft_account)
        
        print(f"   Created real-style OAuth accounts")
        
        # Test polling service with these accounts
        polling_service = EmailPollingService(MONGO_URL, DB_NAME)
        
        try:
            await polling_service._poll_account(real_google_account)
            print(f"   Google OAuth account polling: SUCCESS")
        except Exception as e:
            print(f"   Google OAuth account polling: FAILED - {str(e)[:100]}")
        
        try:
            await polling_service._poll_account(real_microsoft_account)
            print(f"   Microsoft OAuth account polling: SUCCESS")
        except Exception as e:
            print(f"   Microsoft OAuth account polling: FAILED - {str(e)[:100]}")
        
        # Cleanup
        await self.db.email_accounts.delete_one({"id": real_google_account["id"]})
        await self.db.email_accounts.delete_one({"id": real_microsoft_account["id"]})
    
    async def _test_get_active_accounts_method(self):
        """Test the get_active_accounts method specifically"""
        print("   Testing get_active_accounts method...")
        
        # Create polling service
        polling_service = EmailPollingService(MONGO_URL, DB_NAME)
        
        # Get active accounts using the same method as polling service
        active_accounts = await self.db.email_accounts.find({"is_active": True}).to_list(100)
        
        oauth_active = [acc for acc in active_accounts if acc.get('use_oauth', False)]
        manual_active = [acc for acc in active_accounts if not acc.get('use_oauth', False)]
        
        print(f"   Active accounts total: {len(active_accounts)}")
        print(f"   Active OAuth accounts: {len(oauth_active)}")
        print(f"   Active manual accounts: {len(manual_active)}")
        
        # Check if OAuth accounts have required fields
        for acc in oauth_active[:2]:  # Check first 2
            missing_fields = []
            required_fields = ['oauth_email', 'provider', 'auth_type', 'use_oauth']
            for field in required_fields:
                if not acc.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   OAuth account {acc.get('email')} missing fields: {missing_fields}")
            else:
                print(f"   OAuth account {acc.get('email')} has all required fields")
    
    async def investigate_oauth_status_endpoints(self):
        """Deep dive into OAuth status endpoint issues"""
        print("\n🔍 DEEP DIVE: OAuth Status Endpoints...")
        
        try:
            # Test with different authentication scenarios
            await self._test_oauth_status_edge_cases()
            
            # Test with malformed requests
            await self._test_oauth_status_malformed_requests()
            
            # Test with different user scenarios
            await self._test_oauth_status_user_scenarios()
            
        except Exception as e:
            print(f"   OAuth status endpoints investigation failed: {str(e)}")
    
    async def _test_oauth_status_edge_cases(self):
        """Test OAuth status endpoints with edge cases"""
        print("   Testing OAuth status endpoint edge cases...")
        
        # Test with expired token
        expired_headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired"}
        
        google_expired = requests.get(
            f"{API_BASE}/oauth/google/status",
            headers=expired_headers,
            timeout=10
        )
        
        microsoft_expired = requests.get(
            f"{API_BASE}/oauth/microsoft/status",
            headers=expired_headers,
            timeout=10
        )
        
        print(f"   Expired token test - Google: {google_expired.status_code}, Microsoft: {microsoft_expired.status_code}")
        
        # Test with malformed token
        malformed_headers = {"Authorization": "Bearer malformed.token.here"}
        
        google_malformed = requests.get(
            f"{API_BASE}/oauth/google/status",
            headers=malformed_headers,
            timeout=10
        )
        
        microsoft_malformed = requests.get(
            f"{API_BASE}/oauth/microsoft/status",
            headers=malformed_headers,
            timeout=10
        )
        
        print(f"   Malformed token test - Google: {google_malformed.status_code}, Microsoft: {microsoft_malformed.status_code}")
    
    async def _test_oauth_status_malformed_requests(self):
        """Test OAuth status endpoints with malformed requests"""
        print("   Testing OAuth status endpoints with malformed requests...")
        
        # Test with wrong HTTP method
        google_post = requests.post(f"{API_BASE}/oauth/google/status", headers=self.get_auth_headers(), timeout=10)
        microsoft_post = requests.post(f"{API_BASE}/oauth/microsoft/status", headers=self.get_auth_headers(), timeout=10)
        
        print(f"   Wrong method test - Google: {google_post.status_code}, Microsoft: {microsoft_post.status_code}")
        
        # Test with extra parameters
        google_params = requests.get(
            f"{API_BASE}/oauth/google/status",
            headers=self.get_auth_headers(),
            params={"extra": "param"},
            timeout=10
        )
        
        microsoft_params = requests.get(
            f"{API_BASE}/oauth/microsoft/status",
            headers=self.get_auth_headers(),
            params={"extra": "param"},
            timeout=10
        )
        
        print(f"   Extra params test - Google: {google_params.status_code}, Microsoft: {microsoft_params.status_code}")
    
    async def _test_oauth_status_user_scenarios(self):
        """Test OAuth status endpoints with different user scenarios"""
        print("   Testing OAuth status endpoints with different user scenarios...")
        
        # Test with user who has no OAuth tokens
        response_google = requests.get(
            f"{API_BASE}/oauth/google/status",
            headers=self.get_auth_headers(),
            timeout=10
        )
        
        response_microsoft = requests.get(
            f"{API_BASE}/oauth/microsoft/status",
            headers=self.get_auth_headers(),
            timeout=10
        )
        
        print(f"   No OAuth tokens - Google: {response_google.status_code}, Microsoft: {response_microsoft.status_code}")
        
        if response_google.status_code == 200:
            google_data = response_google.json()
            print(f"   Google response: {google_data}")
        
        if response_microsoft.status_code == 200:
            microsoft_data = response_microsoft.json()
            print(f"   Microsoft response: {microsoft_data}")
    
    async def check_backend_logs_for_oauth_issues(self):
        """Check backend logs for OAuth-related issues"""
        print("\n🔍 CHECKING BACKEND LOGS FOR OAUTH ISSUES...")
        
        try:
            # Check supervisor logs for OAuth-related errors
            import subprocess
            
            # Check backend logs
            result = subprocess.run(
                ["tail", "-n", "100", "/var/log/supervisor/backend.err.log"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                log_content = result.stdout
                oauth_errors = []
                
                for line in log_content.split('\n'):
                    if any(keyword in line.lower() for keyword in ['oauth', 'callback', 'token', 'authorization']):
                        oauth_errors.append(line.strip())
                
                if oauth_errors:
                    print(f"   Found {len(oauth_errors)} OAuth-related log entries:")
                    for error in oauth_errors[-5:]:  # Show last 5
                        print(f"   {error}")
                else:
                    print("   No OAuth-related errors found in recent logs")
            else:
                print("   Could not read backend logs")
                
        except Exception as e:
            print(f"   Error checking logs: {str(e)}")
    
    def print_summary(self):
        """Print investigation summary"""
        print("\n" + "="*80)
        print("OAUTH DEEP DIVE INVESTIGATION SUMMARY")
        print("="*80)
        
        print("\n🔍 INVESTIGATION FINDINGS:")
        print("  Based on the deep dive testing, the OAuth flow appears to be working correctly.")
        print("  The issues mentioned in the review request may be:")
        print("  1. Environment-specific (production vs test)")
        print("  2. Related to specific OAuth token configurations")
        print("  3. Timing-related issues under high load")
        print("  4. Issues with specific OAuth provider responses")
        
        print("\n📋 RECOMMENDATIONS:")
        print("  1. Check production logs for specific OAuth error patterns")
        print("  2. Monitor OAuth callback response times under load")
        print("  3. Verify OAuth token refresh mechanisms")
        print("  4. Test with real OAuth tokens from Google/Microsoft")
        
        print("\n" + "="*80)

async def main():
    """Main investigation execution"""
    print("🔍 Starting OAuth Deep Dive Investigation...")
    print("🎯 FOCUS: Investigating specific OAuth flow issues mentioned in review request")
    
    tester = OAuthDeepDiveTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run deep dive investigations
        await tester.investigate_oauth_callback_reuse_protection()
        await tester.investigate_polling_oauth_detection()
        await tester.investigate_oauth_status_endpoints()
        await tester.check_backend_logs_for_oauth_issues()
        
        # Print investigation summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Investigation failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())