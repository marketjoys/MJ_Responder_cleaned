#!/usr/bin/env python3
"""
Focused Test for /api/emails/test Endpoint Timeout Issues
Tests the specific scenario mentioned in the review request
"""
import requests
import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-follow-fixes.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class EmailTestTimeoutTester:
    def __init__(self):
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, details: str = "", duration: float = 0):
        """Log test result with timing"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name} ({duration:.1f}s)")
        if details:
            print(f"   Details: {details}")
    
    def test_backend_health(self):
        """Test 1: Check if backend is running properly"""
        print("\n🏥 Testing Backend Health...")
        
        start_time = time.time()
        try:
            # Test basic health endpoint
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            health_passed = response.status_code == 200
            
            if health_passed:
                status_data = response.json()
                details = f"Backend responding, polling status: {status_data.get('status', 'unknown')}"
            else:
                details = f"Backend health check failed with status: {response.status_code}"
                
        except Exception as e:
            health_passed = False
            details = f"Backend health check exception: {str(e)}"
        
        duration = time.time() - start_time
        self.log_result("Backend Health Check", health_passed, details, duration)
        return health_passed
    
    def get_or_create_test_account(self):
        """Get existing account or create a test account"""
        print("\n📧 Getting/Creating Test Email Account...")
        
        start_time = time.time()
        try:
            # First, try to get existing accounts
            response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
            if response.status_code == 200:
                accounts = response.json()
                if accounts:
                    account = accounts[0]
                    duration = time.time() - start_time
                    self.log_result("Get Test Account", True, f"Using existing account: {account['email']}", duration)
                    return account['id']
            
            # If no accounts exist, create one
            account_data = {
                "name": "Timeout Test Account",
                "email": "timeout.test@example.com",
                "provider": "gmail",
                "username": "timeout.test@example.com", 
                "password": "test_password_123",
                "persona": "Professional customer service representative",
                "signature": "Best regards,\nCustomer Service Team\ntimeout.test@example.com",
                "auto_send": False
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
            if response.status_code in [200, 201]:
                created_account = response.json()
                account_id = created_account.get('id')
                duration = time.time() - start_time
                self.log_result("Create Test Account", True, f"Created account: {account_data['email']}, ID: {account_id}", duration)
                return account_id
            else:
                duration = time.time() - start_time
                self.log_result("Create Test Account", False, f"Failed to create account: {response.status_code}", duration)
                return None
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_result("Get/Create Test Account", False, f"Exception: {str(e)}", duration)
            return None
    
    def test_email_endpoint_timeout(self, account_id):
        """Test 2: Test /api/emails/test endpoint for timeout issues"""
        print("\n⏱️ Testing /api/emails/test Endpoint for Timeout Issues...")
        
        # Test data as specified in the review request
        test_email_data = {
            "subject": "Product inquiry",
            "sender": "test@example.com", 
            "body": "Hi, I'm interested in your product pricing. Can you send me more information?",
            "account_id": account_id
        }
        
        start_time = time.time()
        try:
            print(f"   Sending request to: {API_BASE}/emails/test")
            print(f"   Test data: {json.dumps(test_email_data, indent=2)}")
            print("   Waiting for response (timeout set to 90 seconds)...")
            
            # Use longer timeout to test if it's truly a timeout issue
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=90)
            duration = time.time() - start_time
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                
                # Check response details
                status = response_data.get('status', 'unknown')
                intents = response_data.get('intents', [])
                draft = response_data.get('draft', '')
                validation = response_data.get('validation_result', {})
                
                # Analyze the workflow completion
                workflow_stages = []
                if intents:
                    workflow_stages.append(f"classifying ({len(intents)} intents)")
                if draft:
                    workflow_stages.append(f"drafting ({len(draft)} chars)")
                if validation:
                    workflow_stages.append(f"validating ({validation.get('status', 'unknown')})")
                
                workflow_info = " -> ".join(workflow_stages) if workflow_stages else "No workflow stages completed"
                
                # Determine if this is acceptable performance
                acceptable_time = duration <= 60  # 60 seconds as per requirement
                client_received = True  # We got a response
                
                details = f"Duration: {duration:.1f}s, Status: {status}, Workflow: {workflow_info}, Client received: {client_received}"
                
                # Test passes if: response received within 60s, client gets response, workflow progresses
                test_passed = acceptable_time and client_received and (len(workflow_stages) > 0 or status != 'error')
                
                self.log_result("Email Test Endpoint - Response Time", acceptable_time, f"Response time: {duration:.1f}s (target: ≤60s)", duration)
                self.log_result("Email Test Endpoint - Client Response", client_received, "Client successfully received response", duration)
                self.log_result("Email Test Endpoint - Workflow Progress", len(workflow_stages) > 0, workflow_info, duration)
                self.log_result("Email Test Endpoint - Overall", test_passed, details, duration)
                
                return test_passed, response_data
                
            else:
                details = f"HTTP Error: {response.status_code}, Duration: {duration:.1f}s, Response: {response.text[:200]}"
                self.log_result("Email Test Endpoint - Overall", False, details, duration)
                return False, None
                
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            details = f"Request timed out after {duration:.1f}s - this confirms the timeout issue"
            self.log_result("Email Test Endpoint - Overall", False, details, duration)
            return False, None
            
        except Exception as e:
            duration = time.time() - start_time
            details = f"Exception after {duration:.1f}s: {str(e)}"
            self.log_result("Email Test Endpoint - Overall", False, details, duration)
            return False, None
    
    def test_workflow_stages_individually(self, account_id):
        """Test 3: Test individual workflow stages to isolate the issue"""
        print("\n🔍 Testing Individual Workflow Stages...")
        
        # This would require direct access to the backend functions
        # For now, we'll test by checking the database state
        try:
            # We can't easily test individual stages without backend access
            # But we can check if the issue is in processing vs response delivery
            
            start_time = time.time()
            
            # Send a simpler request to see if it's content-related
            simple_test_data = {
                "subject": "Test",
                "sender": "simple@test.com",
                "body": "Hello",
                "account_id": account_id
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=simple_test_data, timeout=30)
            duration = time.time() - start_time
            
            if response.status_code in [200, 201]:
                details = f"Simple email processed in {duration:.1f}s - issue may be content-specific"
                self.log_result("Simple Email Test", True, details, duration)
            else:
                details = f"Simple email also failed: {response.status_code}"
                self.log_result("Simple Email Test", False, details, duration)
                
        except Exception as e:
            duration = time.time() - start_time
            details = f"Simple email test failed: {str(e)}"
            self.log_result("Simple Email Test", False, details, duration)
    
    def test_backend_logs_check(self):
        """Test 4: Check backend logs for processing status"""
        print("\n📋 Checking Backend Processing Status...")
        
        try:
            # Check if we can get any processing status
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                details = f"Polling service status: {status_data}"
                self.log_result("Backend Processing Status", True, details)
            else:
                details = f"Could not get processing status: {response.status_code}"
                self.log_result("Backend Processing Status", False, details)
                
        except Exception as e:
            details = f"Error checking processing status: {str(e)}"
            self.log_result("Backend Processing Status", False, details)
    
    def run_timeout_tests(self):
        """Run all timeout-related tests"""
        print("🚀 Starting Email Test Endpoint Timeout Investigation")
        print("=" * 60)
        
        # Test 1: Backend Health
        backend_healthy = self.test_backend_health()
        if not backend_healthy:
            print("\n❌ Backend is not healthy - stopping tests")
            return
        
        # Test 2: Get/Create Test Account
        account_id = self.get_or_create_test_account()
        if not account_id:
            print("\n❌ Could not get/create test account - stopping tests")
            return
        
        # Test 3: Main timeout test
        success, response_data = self.test_email_endpoint_timeout(account_id)
        
        # Test 4: Individual workflow stages (if main test failed)
        if not success:
            self.test_workflow_stages_individually(account_id)
        
        # Test 5: Backend processing status
        self.test_backend_logs_check()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TIMEOUT TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        
        if failed_tests:
            print("\n🔍 FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        # Specific timeout analysis
        print("\n🎯 TIMEOUT ANALYSIS:")
        email_tests = [r for r in self.test_results if 'Email Test Endpoint' in r['test']]
        if email_tests:
            for test in email_tests:
                if test['duration_seconds'] > 0:
                    print(f"   • {test['test']}: {test['duration_seconds']:.1f}s")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = EmailTestTimeoutTester()
    success = tester.run_timeout_tests()
    
    if success:
        print("\n🎉 All timeout tests passed!")
    else:
        print("\n⚠️ Some timeout tests failed - see details above")