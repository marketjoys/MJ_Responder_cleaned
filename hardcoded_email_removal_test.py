#!/usr/bin/env python3
"""
Hardcoded Email Account Removal Verification Test
Tests that the backend starts up properly without creating hardcoded email accounts
and verifies that no "rohushanshinde@gmail.com" accounts exist in the database.
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-codebase-debug.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class HardcodedEmailRemovalTester:
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
    
    async def test_backend_startup_without_hardcoded_accounts(self):
        """Test 1: Verify backend starts up properly without creating hardcoded email accounts"""
        print("\n🚀 Testing Backend Startup Without Hardcoded Accounts...")
        
        try:
            # Test that backend is running and responding
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            backend_running = response.status_code == 200
            
            if backend_running:
                self.log_test_result("Backend Startup", True, f"Backend is running and responding (Status: {response.status_code})")
            else:
                self.log_test_result("Backend Startup", False, f"Backend not responding properly (Status: {response.status_code})")
                
        except Exception as e:
            self.log_test_result("Backend Startup", False, f"Exception: {str(e)}")
    
    async def test_no_hardcoded_email_accounts_in_database(self):
        """Test 2: Verify no hardcoded email accounts exist in database"""
        print("\n🔍 Testing No Hardcoded Email Accounts in Database...")
        
        try:
            # Check for the specific hardcoded email account that should be removed
            hardcoded_email = "rohushanshinde@gmail.com"
            
            # Search in email_accounts collection
            hardcoded_account = await self.db.email_accounts.find_one({"email": hardcoded_email})
            
            if hardcoded_account is None:
                self.log_test_result("No Hardcoded Email Accounts", True, f"No '{hardcoded_email}' account found in database")
            else:
                self.log_test_result("No Hardcoded Email Accounts", False, f"Found hardcoded account: {hardcoded_email} with ID: {hardcoded_account.get('id')}")
            
            # Also check for any other potentially hardcoded accounts (accounts with specific patterns)
            all_accounts = await self.db.email_accounts.find().to_list(100)
            suspicious_accounts = []
            
            for account in all_accounts:
                email = account.get('email', '').lower()
                # Check for common hardcoded patterns
                if any(pattern in email for pattern in ['rohushanshinde', 'hardcoded', 'default', 'test@test']):
                    suspicious_accounts.append(email)
            
            if not suspicious_accounts:
                self.log_test_result("No Suspicious Hardcoded Accounts", True, "No suspicious hardcoded accounts found")
            else:
                self.log_test_result("No Suspicious Hardcoded Accounts", False, f"Found suspicious accounts: {suspicious_accounts}")
                
        except Exception as e:
            self.log_test_result("No Hardcoded Email Accounts", False, f"Exception: {str(e)}")
    
    async def test_user_registration_functionality(self):
        """Test 3: Test that new users can register successfully"""
        print("\n👤 Testing User Registration Functionality...")
        
        try:
            # Generate unique test user data
            timestamp = int(time.time())
            test_email = f"test.user.{timestamp}@example.com"
            
            user_data = {
                "email": test_email,
                "password": "TestPassword123!",
                "full_name": "Test User Registration"
            }
            
            # Test user registration
            response = requests.post(f"{API_BASE}/auth/register", json=user_data, timeout=15)
            
            if response.status_code in [200, 201]:
                registration_data = response.json()
                self.auth_token = registration_data.get('access_token')
                self.test_user_id = registration_data.get('user', {}).get('id')
                
                self.log_test_result("User Registration", True, f"User registered successfully with email: {test_email}")
                
                # Test login with the new user
                login_data = {
                    "email": test_email,
                    "password": "TestPassword123!"
                }
                
                login_response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                
                if login_response.status_code == 200:
                    self.log_test_result("User Login After Registration", True, "User can login successfully after registration")
                else:
                    self.log_test_result("User Login After Registration", False, f"Login failed with status: {login_response.status_code}")
                    
            else:
                self.log_test_result("User Registration", False, f"Registration failed with status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test_result("User Registration", False, f"Exception: {str(e)}")
    
    def test_email_accounts_api_endpoints(self):
        """Test 4: Test that email accounts API endpoints work correctly"""
        print("\n📧 Testing Email Accounts API Endpoints...")
        
        try:
            # Test GET /api/email-accounts - List email accounts
            response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
            
            if response.status_code == 200:
                accounts = response.json()
                self.log_test_result("List Email Accounts API", True, f"API returned {len(accounts)} accounts")
                
                # Test GET /api/email-providers - Get email providers
                providers_response = requests.get(f"{API_BASE}/email-providers", timeout=10)
                
                if providers_response.status_code == 200:
                    providers = providers_response.json()
                    self.log_test_result("Get Email Providers API", True, f"API returned {len(providers)} providers")
                else:
                    self.log_test_result("Get Email Providers API", False, f"Failed with status: {providers_response.status_code}")
                    
            else:
                self.log_test_result("List Email Accounts API", False, f"Failed with status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Email Accounts API Endpoints", False, f"Exception: {str(e)}")
    
    def test_user_can_add_email_accounts(self):
        """Test 5: Test that users can add their own email accounts via API"""
        print("\n➕ Testing User Can Add Email Accounts...")
        
        created_account_id = None
        try:
            # Create a test email account
            timestamp = int(time.time())
            account_data = {
                "name": f"Test Account {timestamp}",
                "email": f"test.account.{timestamp}@example.com",
                "provider": "gmail",
                "username": f"test.account.{timestamp}@example.com",
                "password": "test_app_password_123",
                "persona": "Professional test assistant",
                "signature": "Best regards,\nTest Account",
                "auto_send": False
            }
            
            # Test creating email account
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
            
            if response.status_code in [200, 201]:
                created_account = response.json()
                created_account_id = created_account.get('id')
                
                # Verify password is masked in response
                password_masked = created_account.get('password') == '***'
                
                self.log_test_result("Create Email Account", True, f"Account created with ID: {created_account_id}, Password masked: {password_masked}")
                
                # Test retrieving the created account
                if created_account_id:
                    get_response = requests.get(f"{API_BASE}/email-accounts/{created_account_id}", timeout=10)
                    
                    if get_response.status_code == 200:
                        retrieved_account = get_response.json()
                        password_still_masked = retrieved_account.get('password') == '***'
                        
                        self.log_test_result("Retrieve Created Account", True, f"Account retrieved successfully, Password masked: {password_still_masked}")
                    else:
                        self.log_test_result("Retrieve Created Account", False, f"Failed to retrieve account with status: {get_response.status_code}")
                        
            else:
                self.log_test_result("Create Email Account", False, f"Failed to create account with status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test_result("User Can Add Email Accounts", False, f"Exception: {str(e)}")
        
        finally:
            # Cleanup: Delete the test account if it was created
            if created_account_id:
                try:
                    delete_response = requests.delete(f"{API_BASE}/email-accounts/{created_account_id}", timeout=10)
                    if delete_response.status_code in [200, 204]:
                        print(f"   ✅ Cleaned up test account: {created_account_id}")
                    else:
                        print(f"   ⚠️ Failed to cleanup test account: {created_account_id}")
                except Exception as e:
                    print(f"   ⚠️ Error during cleanup: {str(e)}")
    
    async def test_database_integrity_after_removal(self):
        """Test 6: Verify database integrity after hardcoded account removal"""
        print("\n🔧 Testing Database Integrity After Removal...")
        
        try:
            # Check that other collections are intact
            collections_to_check = ['intents', 'knowledge_base', 'users']
            all_collections_ok = True
            
            for collection_name in collections_to_check:
                try:
                    collection = getattr(self.db, collection_name)
                    count = await collection.count_documents({})
                    
                    if count >= 0:  # Any count is fine, just checking collection exists and is accessible
                        self.log_test_result(f"Database Collection - {collection_name}", True, f"Collection accessible with {count} documents")
                    else:
                        self.log_test_result(f"Database Collection - {collection_name}", False, "Collection not accessible")
                        all_collections_ok = False
                        
                except Exception as e:
                    self.log_test_result(f"Database Collection - {collection_name}", False, f"Error accessing collection: {str(e)}")
                    all_collections_ok = False
            
            # Check email_accounts collection specifically
            try:
                email_accounts_count = await self.db.email_accounts.count_documents({})
                self.log_test_result("Email Accounts Collection Integrity", True, f"Email accounts collection accessible with {email_accounts_count} documents")
            except Exception as e:
                self.log_test_result("Email Accounts Collection Integrity", False, f"Error accessing email_accounts collection: {str(e)}")
                all_collections_ok = False
            
            if all_collections_ok:
                self.log_test_result("Overall Database Integrity", True, "All database collections are accessible and intact")
            else:
                self.log_test_result("Overall Database Integrity", False, "Some database collections have issues")
                
        except Exception as e:
            self.log_test_result("Database Integrity", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("HARDCODED EMAIL ACCOUNT REMOVAL TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        print("\n✅ PASSED TESTS:")
        for test in passed_tests:
            print(f"  - {test['test']}")
        
        print("\n" + "="*80)
        
        # Overall assessment
        critical_tests = [
            "Backend Startup",
            "No Hardcoded Email Accounts", 
            "User Registration",
            "Create Email Account"
        ]
        
        critical_failures = [t for t in failed_tests if t['test'] in critical_tests]
        
        if not critical_failures:
            print("🎉 OVERALL RESULT: SUCCESS - Hardcoded email account removal verification PASSED")
            print("   - Backend starts up properly without hardcoded accounts")
            print("   - No rohushanshinde@gmail.com accounts found in database")
            print("   - User registration functionality works correctly")
            print("   - Users can add their own email accounts via API")
        else:
            print("⚠️ OVERALL RESULT: ISSUES FOUND - Some critical tests failed")
            for failure in critical_failures:
                print(f"   - {failure['test']}: {failure['details']}")

async def main():
    """Main test execution"""
    print("🧪 Starting Hardcoded Email Account Removal Verification Tests...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    
    tester = HardcodedEmailRemovalTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Failed to setup test environment")
            return
        
        # Run tests
        await tester.test_backend_startup_without_hardcoded_accounts()
        await tester.test_no_hardcoded_email_accounts_in_database()
        await tester.test_user_registration_functionality()
        tester.test_email_accounts_api_endpoints()
        tester.test_user_can_add_email_accounts()
        await tester.test_database_integrity_after_removal()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())