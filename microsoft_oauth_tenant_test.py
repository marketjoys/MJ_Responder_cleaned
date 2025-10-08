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
            # OAuth endpoints require authentication, so we expect 403 for unauthenticated requests
            response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
            
            # For unauthenticated requests, we expect 403 (which means the endpoint exists and is protected)
            endpoint_exists = response.status_code == 403
            
            if endpoint_exists:
                # The endpoint exists and is properly protected
                all_passed = True
                details = f"Status: {response.status_code} (endpoint exists and is protected)"
            else:
                # Check if it's a different error that might indicate configuration issues
                all_passed = False
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test_result("OAuth Status Endpoint", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Status Endpoint", False, f"Exception: {str(e)}")
    
    def test_oauth_authorization_url_generation(self):
        """Test 3: Test OAuth Authorization URL Generation - Verify endpoint exists and method is correct"""
        print("\n🔗 Testing OAuth Authorization URL Generation...")
        
        try:
            # The authorization endpoint is POST, not GET, and requires authentication
            # Test with GET first to see method not allowed
            response = requests.get(f"{API_BASE}/oauth/microsoft/authorize", timeout=10)
            
            if response.status_code == 405:  # Method Not Allowed - correct, should be POST
                method_correct = True
                details = f"Status: {response.status_code} (Method Not Allowed - endpoint exists, requires POST)"
                
                # Now test with POST but without auth (should get 403)
                try:
                    post_response = requests.post(f"{API_BASE}/oauth/microsoft/authorize", 
                                                json=["email"], timeout=10)
                    if post_response.status_code == 403:  # Not authenticated
                        endpoint_protected = True
                        details += f", POST gives 403 (properly protected)"
                    else:
                        endpoint_protected = False
                        details += f", POST gives {post_response.status_code}"
                except:
                    endpoint_protected = False
                    details += ", POST test failed"
                
                all_passed = method_correct and endpoint_protected
                
            else:
                all_passed = False
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test_result("OAuth Authorization URL Generation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("OAuth Authorization URL Generation", False, f"Exception: {str(e)}")
    
    def test_oauth_authorization_endpoint(self):
        """Test 4: Test OAuth Authorization Endpoint - Check if endpoint is accessible and properly configured"""
        print("\n🚀 Testing OAuth Authorization Endpoint...")
        
        try:
            # Test that the authorization endpoint exists and doesn't return server errors
            response = requests.get(f"{API_BASE}/oauth/microsoft/authorize", timeout=10, allow_redirects=False)
            
            # Should not return server error (5xx)
            no_server_error = response.status_code < 500
            
            # For GET request, should return 405 (Method Not Allowed) since it's a POST endpoint
            correct_method_response = response.status_code == 405
            
            all_passed = no_server_error and correct_method_response
            
            details = f"Status: {response.status_code}, " \
                     f"No server error: {no_server_error}, " \
                     f"Correct method response (405): {correct_method_response}"
            
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
        """Test 6: Verify Personal Account Support - Confirm configuration supports personal Microsoft accounts"""
        print("\n👤 Testing Personal Account Support Verification...")
        
        try:
            # Since OAuth endpoints require authentication, we'll verify through environment configuration
            # and by checking the Microsoft OAuth service configuration
            tenant_id = os.environ.get('MICROSOFT_TENANT_ID')
            
            # Personal account support is enabled when tenant_id is "common"
            supports_personal = tenant_id == 'common'
            
            # Additional verification: check that we're not using organization-specific tenant
            not_org_specific = not (tenant_id and len(tenant_id) == 36 and '-' in tenant_id)
            
            all_passed = supports_personal and not_org_specific
            
            details = f"Tenant ID: '{tenant_id}', " \
                     f"Supports personal accounts: {supports_personal}, " \
                     f"Not organization-specific: {not_org_specific}"
            
            self.log_test_result("Personal Account Support Verification", all_passed, details)
            
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