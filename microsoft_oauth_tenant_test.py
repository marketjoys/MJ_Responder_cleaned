#!/usr/bin/env python3
"""
Microsoft OAuth Tenant Configuration Fix Verification Test
Tests the fix for MICROSOFT_TENANT_ID change from specific tenant to "common"
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

from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-restart-all.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class MicrosoftOAuthTenantTester:
    def __init__(self):
        self.test_results = []
        
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
    
    def test_environment_variables_verification(self):
        """Test 1: Verify Environment Variables - Confirm new tenant ID is loaded"""
        print("\n🔍 Testing Environment Variables Verification...")
        
        try:
            # Check MICROSOFT_TENANT_ID in environment
            tenant_id = os.environ.get('MICROSOFT_TENANT_ID')
            
            # Verify it's set to "common"
            tenant_correct = tenant_id == "common"
            
            # Check other Microsoft OAuth variables are present
            client_id = os.environ.get('MICROSOFT_CLIENT_ID')
            client_secret = os.environ.get('MICROSOFT_CLIENT_SECRET')
            redirect_uri = os.environ.get('MICROSOFT_REDIRECT_URI')
            
            oauth_vars_present = all([client_id, client_secret, redirect_uri])
            
            all_passed = tenant_correct and oauth_vars_present
            
            details = f"MICROSOFT_TENANT_ID: '{tenant_id}' (should be 'common'), " \
                     f"Other OAuth vars present: {oauth_vars_present}"
            
            self.log_test_result("Environment Variables Verification", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Environment Variables Verification", False, f"Exception: {str(e)}")
    
    def test_oauth_status_endpoint(self):
        """Test 2: Test OAuth Status Endpoint - Check if /api/oauth/microsoft/status returns proper response"""
        print("\n📊 Testing OAuth Status Endpoint...")
        
        try:
            response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
            
            status_code_ok = response.status_code == 200
            
            if status_code_ok:
                response_data = response.json()
                # Check for expected fields in status response
                has_required_fields = all(key in response_data for key in ['configured', 'tenant_id'])
                
                # Verify tenant_id in response is "common"
                tenant_in_response = response_data.get('tenant_id') == 'common'
                
                all_passed = status_code_ok and has_required_fields and tenant_in_response
                
                details = f"Status: {response.status_code}, " \
                         f"Required fields: {has_required_fields}, " \
                         f"Tenant ID in response: '{response_data.get('tenant_id')}'"
            else:
                all_passed = False
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test_result("OAuth Status Endpoint", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Status Endpoint", False, f"Exception: {str(e)}")
    
    def test_oauth_authorization_url_generation(self):
        """Test 3: Test OAuth Authorization URL Generation - Generate OAuth URL and verify it uses common tenant endpoint"""
        print("\n🔗 Testing OAuth Authorization URL Generation...")
        
        try:
            # Test the authorization endpoint that should generate the OAuth URL
            response = requests.get(f"{API_BASE}/oauth/microsoft/authorize", timeout=10)
            
            if response.status_code == 302:  # Redirect response expected
                # Check the Location header for the redirect URL
                location = response.headers.get('Location', '')
                
                # Verify it uses the common tenant endpoint
                uses_common_tenant = 'login.microsoftonline.com/common/oauth2/v2.0/authorize' in location
                
                # Verify it contains required OAuth parameters
                has_client_id = 'client_id=' in location
                has_response_type = 'response_type=code' in location
                has_redirect_uri = 'redirect_uri=' in location
                has_scope = 'scope=' in location
                
                oauth_params_present = all([has_client_id, has_response_type, has_redirect_uri, has_scope])
                
                all_passed = uses_common_tenant and oauth_params_present
                
                details = f"Status: {response.status_code}, " \
                         f"Uses common tenant: {uses_common_tenant}, " \
                         f"OAuth params present: {oauth_params_present}, " \
                         f"URL: {location[:100]}..."
                
            elif response.status_code == 200:
                # Some implementations might return the URL in response body
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                auth_url = response_data.get('authorization_url', '')
                
                uses_common_tenant = 'login.microsoftonline.com/common/oauth2/v2.0/authorize' in auth_url
                
                all_passed = uses_common_tenant and bool(auth_url)
                
                details = f"Status: {response.status_code}, " \
                         f"Uses common tenant: {uses_common_tenant}, " \
                         f"URL: {auth_url[:100]}..."
                
            else:
                all_passed = False
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test_result("OAuth Authorization URL Generation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Authorization URL Generation", False, f"Exception: {str(e)}")
    
    def test_oauth_authorization_endpoint(self):
        """Test 4: Test OAuth Authorization Endpoint - Check if /api/oauth/microsoft/authorize works without errors"""
        print("\n🚀 Testing OAuth Authorization Endpoint...")
        
        try:
            # Test that the authorization endpoint is accessible and doesn't return server errors
            response = requests.get(f"{API_BASE}/oauth/microsoft/authorize", timeout=10, allow_redirects=False)
            
            # Should either redirect (302) or return success (200), not server error (5xx)
            no_server_error = response.status_code < 500
            
            # Should be either redirect or success response
            valid_response = response.status_code in [200, 302]
            
            all_passed = no_server_error and valid_response
            
            details = f"Status: {response.status_code}, " \
                     f"No server error: {no_server_error}, " \
                     f"Valid response: {valid_response}"
            
            self.log_test_result("OAuth Authorization Endpoint", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Authorization Endpoint", False, f"Exception: {str(e)}")
    
    def test_tenant_configuration_verification(self):
        """Test 5: Verify Tenant Configuration - Check that Microsoft OAuth service is using common tenant endpoint"""
        print("\n⚙️ Testing Tenant Configuration Verification...")
        
        try:
            # Import Microsoft OAuth service to check configuration
            sys.path.append('/app/backend')
            from oauth_microsoft import microsoft_oauth_service
            
            # Check if the service is configured with common tenant
            tenant_id = microsoft_oauth_service.tenant_id if hasattr(microsoft_oauth_service, 'tenant_id') else None
            
            if tenant_id:
                tenant_correct = tenant_id == "common"
                details = f"Service tenant ID: '{tenant_id}' (should be 'common')"
            else:
                # Try to get tenant from environment as fallback
                env_tenant = os.environ.get('MICROSOFT_TENANT_ID')
                tenant_correct = env_tenant == "common"
                details = f"Environment tenant ID: '{env_tenant}' (should be 'common')"
            
            self.log_test_result("Tenant Configuration Verification", tenant_correct, details)
            
        except Exception as e:
            self.log_test_result("Tenant Configuration Verification", False, f"Exception: {str(e)}")
    
    def test_personal_account_support_verification(self):
        """Test 6: Verify Personal Account Support - Confirm OAuth URLs support both organizational AND personal Microsoft accounts"""
        print("\n👤 Testing Personal Account Support Verification...")
        
        try:
            # Test the OAuth status to see if it indicates support for personal accounts
            response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check if the configuration indicates support for personal accounts
                # This is typically indicated by tenant_id being "common"
                tenant_supports_personal = response_data.get('tenant_id') == 'common'
                
                # Check if there's any explicit indication of account type support
                supports_personal = (
                    tenant_supports_personal or 
                    response_data.get('supports_personal_accounts', False) or
                    response_data.get('account_types', '').lower() in ['common', 'both', 'personal_and_organizational']
                )
                
                details = f"Status: {response.status_code}, " \
                         f"Tenant supports personal: {tenant_supports_personal}, " \
                         f"Overall personal support: {supports_personal}"
                
                self.log_test_result("Personal Account Support Verification", supports_personal, details)
            else:
                self.log_test_result("Personal Account Support Verification", False, 
                                   f"Status endpoint failed: {response.status_code}")
            
        except Exception as e:
            self.log_test_result("Personal Account Support Verification", False, f"Exception: {str(e)}")
    
    def test_no_aadsts50020_error_potential(self):
        """Test 7: Verify No AADSTS50020 Error Potential - Confirm configuration should not cause tenant-specific errors"""
        print("\n🚫 Testing No AADSTS50020 Error Potential...")
        
        try:
            # Check that the tenant configuration is set to avoid AADSTS50020 errors
            tenant_id = os.environ.get('MICROSOFT_TENANT_ID')
            
            # AADSTS50020 occurs when tenant is specific but user doesn't exist in that tenant
            # Using "common" should avoid this error
            avoids_tenant_error = tenant_id == "common"
            
            # Additional check: ensure we're not using a specific tenant GUID
            is_not_specific_tenant = not (tenant_id and len(tenant_id) == 36 and '-' in tenant_id)
            
            all_passed = avoids_tenant_error and is_not_specific_tenant
            
            details = f"Tenant ID: '{tenant_id}', " \
                     f"Avoids AADSTS50020: {avoids_tenant_error}, " \
                     f"Not specific tenant GUID: {is_not_specific_tenant}"
            
            self.log_test_result("No AADSTS50020 Error Potential", all_passed, details)
            
        except Exception as e:
            self.log_test_result("No AADSTS50020 Error Potential", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all Microsoft OAuth tenant configuration tests"""
        print("🧪 Starting Microsoft OAuth Tenant Configuration Fix Verification Tests...")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Testing tenant configuration change from specific tenant to 'common'")
        print("=" * 80)
        
        # Run all tests
        self.test_environment_variables_verification()
        self.test_oauth_status_endpoint()
        self.test_oauth_authorization_url_generation()
        self.test_oauth_authorization_endpoint()
        self.test_tenant_configuration_verification()
        self.test_personal_account_support_verification()
        self.test_no_aadsts50020_error_potential()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 MICROSOFT OAUTH TENANT FIX VERIFICATION SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}/{len(self.test_results)} tests")
        print(f"❌ FAILED: {len(failed_tests)}/{len(self.test_results)} tests")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   - {test['test']}")
        
        # Overall assessment
        overall_success = len(failed_tests) == 0
        print(f"\n🎯 OVERALL RESULT: {'✅ SUCCESS' if overall_success else '❌ NEEDS ATTENTION'}")
        
        if overall_success:
            print("🎉 Microsoft OAuth tenant configuration fix is working correctly!")
            print("   - Tenant ID is set to 'common'")
            print("   - OAuth endpoints are functional")
            print("   - Personal Microsoft accounts should now be supported")
            print("   - AADSTS50020 errors should be resolved")
        else:
            print("⚠️  Some issues were found with the Microsoft OAuth tenant configuration.")
            print("   Please review the failed tests above.")
        
        return overall_success

def main():
    """Main test execution"""
    tester = MicrosoftOAuthTenantTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()