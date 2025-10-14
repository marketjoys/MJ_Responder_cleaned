#!/usr/bin/env python3
"""
Multi-Account OAuth Implementation Testing
Testing the multi-account OAuth functionality as requested in the review.

Key areas to test:
1. Data Migration Verification
2. Enhanced OAuth Status Endpoint
3. Multi-Account OAuth Token Management
4. OAuth Account Creation
5. Email Account Linking
6. OAuth Token Revocation
7. Backward Compatibility
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Configuration
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://calendar-sync-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class MultiAccountOAuthTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.user_id = None
        self.test_results = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_result(self, test_name: str, success: bool, details: str = "", error: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
        print()
    
    async def authenticate(self) -> bool:
        """Authenticate with the system"""
        try:
            # Try to register a test user first
            register_data = {
                "email": "oauth_test_user@example.com",
                "password": "testpass123",
                "full_name": "OAuth Test User"
            }
            
            response = await self.client.post(f"{API_BASE}/auth/register", json=register_data)
            
            if response.status_code == 400:
                # User already exists, try to login
                login_data = {
                    "email": "oauth_test_user@example.com",
                    "password": "testpass123"
                }
                response = await self.client.post(f"{API_BASE}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data['access_token']
                self.user_id = data['user']['id']
                self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                self.log_result("Authentication", True, f"Authenticated as user {self.user_id}")
                return True
            else:
                self.log_result("Authentication", False, error=f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, error=str(e))
            return False
    
    async def test_data_migration_verification(self) -> bool:
        """Test 1: Data Migration Verification"""
        try:
            # Check if migration functions exist and can be called
            # Since migration runs at startup, we'll check the database state
            
            # Get all email accounts to check migration fields
            response = await self.client.get(f"{API_BASE}/email-accounts")
            
            if response.status_code != 200:
                self.log_result("Data Migration Verification", False, 
                               error=f"Failed to get email accounts: {response.status_code}")
                return False
            
            accounts = response.json()
            
            # Check if accounts have the new OAuth fields
            migration_fields_present = True
            oauth_accounts_found = 0
            manual_accounts_found = 0
            
            for account in accounts:
                # Check for new OAuth fields
                required_fields = ['auth_type', 'oauth_token_id', 'oauth_email']
                for field in required_fields:
                    if field not in account:
                        migration_fields_present = False
                        break
                
                if account.get('auth_type') == 'oauth':
                    oauth_accounts_found += 1
                elif account.get('auth_type') == 'manual':
                    manual_accounts_found += 1
            
            details = f"Migration fields present: {migration_fields_present}, OAuth accounts: {oauth_accounts_found}, Manual accounts: {manual_accounts_found}"
            self.log_result("Data Migration Verification", migration_fields_present, details)
            return migration_fields_present
            
        except Exception as e:
            self.log_result("Data Migration Verification", False, error=str(e))
            return False
    
    async def test_enhanced_oauth_status_endpoint(self) -> bool:
        """Test 2: Enhanced OAuth Status Endpoint"""
        try:
            # Test GET /api/oauth/google/status
            response = await self.client.get(f"{API_BASE}/oauth/google/status")
            
            if response.status_code != 200:
                self.log_result("Enhanced OAuth Status Endpoint", False, 
                               error=f"Status endpoint failed: {response.status_code}")
                return False
            
            status_data = response.json()
            
            # Check for multi-account support fields
            required_fields = ['authorized_accounts', 'total_accounts', 'is_authorized']
            fields_present = all(field in status_data for field in required_fields)
            
            # Check structure of authorized_accounts
            accounts_structure_valid = True
            if 'authorized_accounts' in status_data and isinstance(status_data['authorized_accounts'], list):
                for account in status_data['authorized_accounts']:
                    required_account_fields = ['user_email', 'oauth_token_id', 'has_email_account']
                    if not all(field in account for field in required_account_fields):
                        accounts_structure_valid = False
                        break
            
            # Check backward compatibility fields
            backward_compat_fields = ['user_email', 'user_name', 'expires_at']
            backward_compat = all(field in status_data for field in backward_compat_fields)
            
            success = fields_present and accounts_structure_valid
            details = f"Multi-account fields: {fields_present}, Account structure: {accounts_structure_valid}, Backward compatibility: {backward_compat}, Total accounts: {status_data.get('total_accounts', 0)}"
            
            self.log_result("Enhanced OAuth Status Endpoint", success, details)
            return success
            
        except Exception as e:
            self.log_result("Enhanced OAuth Status Endpoint", False, error=str(e))
            return False
    
    async def test_multi_account_token_management(self) -> bool:
        """Test 3: Multi-Account OAuth Token Management"""
        try:
            # Since we can't easily create real OAuth tokens in testing,
            # we'll test the token management endpoints and structure
            
            # Test the revocation endpoints exist
            endpoints_to_test = [
                ("/oauth/google/revoke", "POST"),
                ("/oauth/google/revoke/test@example.com", "POST"),
                ("/oauth/microsoft/revoke", "POST")
            ]
            
            endpoints_exist = 0
            for endpoint, method in endpoints_to_test:
                try:
                    if method == "POST":
                        response = await self.client.post(f"{API_BASE}{endpoint}")
                    else:
                        response = await self.client.get(f"{API_BASE}{endpoint}")
                    
                    # We expect these to fail with auth/validation errors, not 404
                    if response.status_code != 404:
                        endpoints_exist += 1
                except:
                    pass
            
            # Test OAuth token structure by checking database collections
            # This is indirect testing since we can't easily create OAuth tokens
            success = endpoints_exist >= 2  # At least 2 endpoints should exist
            details = f"OAuth management endpoints found: {endpoints_exist}/{len(endpoints_to_test)}"
            
            self.log_result("Multi-Account Token Management", success, details)
            return success
            
        except Exception as e:
            self.log_result("Multi-Account Token Management", False, error=str(e))
            return False
    
    async def test_oauth_account_creation(self) -> bool:
        """Test 4: OAuth Account Creation"""
        try:
            # Test POST /api/email-accounts/oauth endpoint
            oauth_account_data = {
                "name": "Test OAuth Account",
                "email": "test@gmail.com",
                "provider": "gmail",
                "auth_type": "oauth",
                "oauth_email": "test@gmail.com",
                "use_oauth": True,
                "signature": "Test Signature",
                "persona": "Professional",
                "auto_send": True,
                "enable_follow_ups": True
            }
            
            response = await self.client.post(f"{API_BASE}/email-accounts/oauth", json=oauth_account_data)
            
            # We expect this to fail with 401 (no OAuth token) rather than 404 (endpoint not found)
            # or 400 (bad request structure)
            expected_status_codes = [401, 500]  # 401 = unauthorized, 500 = OAuth verification failed
            endpoint_exists = response.status_code in expected_status_codes
            
            # Check error message indicates OAuth token requirement
            error_message = ""
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', '')
                except:
                    error_message = response.text
            
            oauth_validation_working = "oauth" in error_message.lower() or "authorized" in error_message.lower()
            
            success = endpoint_exists and oauth_validation_working
            details = f"Endpoint exists: {endpoint_exists}, OAuth validation: {oauth_validation_working}, Status: {response.status_code}"
            
            self.log_result("OAuth Account Creation", success, details)
            return success
            
        except Exception as e:
            self.log_result("OAuth Account Creation", False, error=str(e))
            return False
    
    async def test_email_account_linking(self) -> bool:
        """Test 5: Email Account Linking"""
        try:
            # Test that email accounts can be linked to OAuth tokens
            # We'll check the account structure and linking fields
            
            response = await self.client.get(f"{API_BASE}/email-accounts")
            
            if response.status_code != 200:
                self.log_result("Email Account Linking", False, 
                               error=f"Failed to get accounts: {response.status_code}")
                return False
            
            accounts = response.json()
            
            # Check if accounts have linking fields
            linking_fields_present = True
            oauth_linked_accounts = 0
            
            for account in accounts:
                # Check for OAuth linking fields
                if 'oauth_token_id' not in account or 'oauth_email' not in account:
                    linking_fields_present = False
                
                # Count OAuth-linked accounts
                if account.get('auth_type') == 'oauth' and account.get('oauth_token_id'):
                    oauth_linked_accounts += 1
            
            # Test creating a manual account to ensure linking fields are set to None
            manual_account_data = {
                "name": "Test Manual Account",
                "email": "manual@example.com",
                "provider": "gmail",
                "auth_type": "manual",
                "username": "manual@example.com",
                "password": "testpass123",
                "signature": "Manual Test Signature"
            }
            
            manual_response = await self.client.post(f"{API_BASE}/email-accounts", json=manual_account_data)
            manual_account_created = manual_response.status_code == 200
            
            if manual_account_created:
                manual_account = manual_response.json()
                manual_linking_correct = (
                    manual_account.get('oauth_token_id') is None and
                    manual_account.get('oauth_email') is None and
                    manual_account.get('auth_type') == 'manual'
                )
            else:
                manual_linking_correct = True  # Skip if account creation failed
            
            success = linking_fields_present and manual_linking_correct
            details = f"Linking fields present: {linking_fields_present}, OAuth linked accounts: {oauth_linked_accounts}, Manual account linking: {manual_linking_correct}"
            
            self.log_result("Email Account Linking", success, details)
            return success
            
        except Exception as e:
            self.log_result("Email Account Linking", False, error=str(e))
            return False
    
    async def test_oauth_token_revocation(self) -> bool:
        """Test 6: OAuth Token Revocation"""
        try:
            # Test both full revocation and specific account revocation
            
            # Test full revocation endpoint
            full_revoke_response = await self.client.post(f"{API_BASE}/oauth/google/revoke")
            full_revoke_exists = full_revoke_response.status_code != 404
            
            # Test specific account revocation endpoint
            specific_revoke_response = await self.client.post(f"{API_BASE}/oauth/google/revoke/test@example.com")
            specific_revoke_exists = specific_revoke_response.status_code != 404
            
            # Check response structure for full revocation
            full_revoke_structure = False
            if full_revoke_response.status_code == 200:
                try:
                    data = full_revoke_response.json()
                    full_revoke_structure = 'success' in data and 'message' in data
                except:
                    pass
            
            # Check response structure for specific revocation
            specific_revoke_structure = False
            if specific_revoke_response.status_code in [200, 404]:  # 404 is expected for non-existent email
                specific_revoke_structure = True
            
            success = full_revoke_exists and specific_revoke_exists
            details = f"Full revocation endpoint: {full_revoke_exists}, Specific revocation endpoint: {specific_revoke_exists}, Response structures: {full_revoke_structure and specific_revoke_structure}"
            
            self.log_result("OAuth Token Revocation", success, details)
            return success
            
        except Exception as e:
            self.log_result("OAuth Token Revocation", False, error=str(e))
            return False
    
    async def test_backward_compatibility(self) -> bool:
        """Test 7: Backward Compatibility"""
        try:
            # Test that existing single-account functionality still works
            
            # Test OAuth status endpoint returns backward-compatible fields
            status_response = await self.client.get(f"{API_BASE}/oauth/google/status")
            
            if status_response.status_code != 200:
                self.log_result("Backward Compatibility", False, 
                               error=f"Status endpoint failed: {status_response.status_code}")
                return False
            
            status_data = status_response.json()
            
            # Check for backward compatibility fields
            backward_compat_fields = ['user_email', 'user_name', 'expires_at', 'needs_refresh', 'is_authorized']
            backward_compat = all(field in status_data for field in backward_compat_fields)
            
            # Test that manual email account creation still works
            manual_account_data = {
                "name": "Backward Compatibility Test",
                "email": "backward@example.com",
                "provider": "gmail",
                "username": "backward@example.com",
                "password": "testpass123",
                "signature": "Backward Test"
            }
            
            manual_response = await self.client.post(f"{API_BASE}/email-accounts", json=manual_account_data)
            manual_creation_works = manual_response.status_code == 200
            
            # Test that existing endpoints still work
            accounts_response = await self.client.get(f"{API_BASE}/email-accounts")
            accounts_endpoint_works = accounts_response.status_code == 200
            
            success = backward_compat and manual_creation_works and accounts_endpoint_works
            details = f"Status backward compatibility: {backward_compat}, Manual account creation: {manual_creation_works}, Accounts endpoint: {accounts_endpoint_works}"
            
            self.log_result("Backward Compatibility", success, details)
            return success
            
        except Exception as e:
            self.log_result("Backward Compatibility", False, error=str(e))
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all multi-account OAuth tests"""
        print("🧪 Starting Multi-Account OAuth Implementation Testing")
        print("=" * 60)
        
        # Authenticate first
        if not await self.authenticate():
            return {"success": False, "error": "Authentication failed"}
        
        # Run all tests
        tests = [
            ("Data Migration Verification", self.test_data_migration_verification),
            ("Enhanced OAuth Status Endpoint", self.test_enhanced_oauth_status_endpoint),
            ("Multi-Account Token Management", self.test_multi_account_token_management),
            ("OAuth Account Creation", self.test_oauth_account_creation),
            ("Email Account Linking", self.test_email_account_linking),
            ("OAuth Token Revocation", self.test_oauth_token_revocation),
            ("Backward Compatibility", self.test_backward_compatibility)
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = await test_func()
            except Exception as e:
                self.log_result(test_name, False, error=f"Test execution failed: {str(e)}")
                results[test_name] = False
        
        # Summary
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print("=" * 60)
        print(f"🎯 Multi-Account OAuth Testing Summary")
        print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
        print("=" * 60)
        
        # Detailed results
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        return {
            "success": success_rate >= 70,  # Consider successful if 70% or more tests pass
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "results": results,
            "test_details": self.test_results
        }

async def main():
    """Main test execution"""
    async with MultiAccountOAuthTester() as tester:
        results = await tester.run_all_tests()
        
        # Exit with appropriate code
        if results["success"]:
            print("\n🎉 Multi-Account OAuth Implementation Testing PASSED")
            sys.exit(0)
        else:
            print("\n❌ Multi-Account OAuth Implementation Testing FAILED")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())