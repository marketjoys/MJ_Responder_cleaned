#!/usr/bin/env python3
"""
Comprehensive Timeout Test - Multiple scenarios and edge cases
"""
import requests
import json
import time
import os
import asyncio
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-outlook-sync.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class ComprehensiveTimeoutTester:
    def __init__(self):
        self.test_results = []
        self.account_id = None
        
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
    
    def setup_test_account(self):
        """Get test account ID"""
        try:
            response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
            if response.status_code == 200:
                accounts = response.json()
                if accounts:
                    self.account_id = accounts[0]['id']
                    return True
        except Exception as e:
            print(f"Failed to get account: {e}")
        return False
    
    def test_multiple_concurrent_requests(self):
        """Test multiple concurrent requests to check for race conditions"""
        print("\n🔄 Testing Multiple Concurrent Requests...")
        
        if not self.account_id:
            self.log_result("Concurrent Requests", False, "No account ID available")
            return
        
        test_data = {
            "subject": "Concurrent Test",
            "sender": "concurrent@test.com",
            "body": "Testing concurrent request handling",
            "account_id": self.account_id
        }
        
        def make_request(request_id):
            start_time = time.time()
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=60)
                duration = time.time() - start_time
                return {
                    "id": request_id,
                    "success": response.status_code in [200, 201],
                    "duration": duration,
                    "status_code": response.status_code
                }
            except Exception as e:
                duration = time.time() - start_time
                return {
                    "id": request_id,
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                }
        
        start_time = time.time()
        
        # Run 3 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request, i) for i in range(3)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_duration = time.time() - start_time
        
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        avg_duration = sum(r['duration'] for r in results) / len(results)
        
        test_passed = len(successful_requests) >= 2  # At least 2 out of 3 should succeed
        
        details = f"Successful: {len(successful_requests)}/3, Failed: {len(failed_requests)}/3, Avg duration: {avg_duration:.1f}s, Total time: {total_duration:.1f}s"
        
        self.log_result("Concurrent Requests", test_passed, details, total_duration)
        
        # Log individual request results
        for result in results:
            if result['success']:
                self.log_result(f"Concurrent Request {result['id']}", True, f"Duration: {result['duration']:.1f}s", result['duration'])
            else:
                error_msg = result.get('error', f"HTTP {result.get('status_code', 'unknown')}")
                self.log_result(f"Concurrent Request {result['id']}", False, error_msg, result['duration'])
    
    def test_large_email_content(self):
        """Test with large email content to check processing limits"""
        print("\n📄 Testing Large Email Content...")
        
        if not self.account_id:
            self.log_result("Large Email Content", False, "No account ID available")
            return
        
        # Create a large email body (simulate a long customer inquiry)
        large_body = """
        Dear Customer Service Team,
        
        I hope this email finds you well. I am writing to inquire about your comprehensive AI Email Assistant solution for our growing enterprise. Our company has been experiencing significant challenges with email management and customer response times, and we believe your solution could be the answer we've been looking for.
        
        Let me provide you with some background about our organization. We are a mid-sized technology company with approximately 500 employees across multiple departments including sales, marketing, customer support, product development, and operations. Our customer base has grown exponentially over the past two years, and we now receive over 2,000 customer inquiries per day across various channels, with email being the primary communication method.
        
        Our current challenges include:
        1. Response time delays - We're currently averaging 24-48 hours for initial responses
        2. Inconsistent messaging - Different team members provide varying levels of detail and tone
        3. Manual classification - We spend significant time routing emails to appropriate departments
        4. Knowledge base utilization - Our extensive documentation isn't being effectively leveraged
        5. Follow-up management - We often miss follow-up opportunities with prospects and customers
        
        We're particularly interested in the following features of your AI Email Assistant:
        - Automated email classification and intent recognition
        - Intelligent draft generation using our knowledge base
        - Multi-language support for our international customers
        - Integration capabilities with our existing CRM system (Salesforce)
        - Customizable response templates and personas
        - Analytics and reporting on email performance metrics
        - Escalation workflows for complex inquiries
        - Compliance features for our regulated industry requirements
        
        Could you please provide detailed information about:
        1. Pricing structure and available plans
        2. Implementation timeline and onboarding process
        3. Training requirements for our team
        4. Integration capabilities and API documentation
        5. Security and compliance certifications
        6. Performance metrics and SLA guarantees
        7. Support options and response times
        8. Customization possibilities for our specific use cases
        
        We would also appreciate the opportunity to schedule a comprehensive demo where we can see the system in action with our actual email scenarios. Our decision-making team includes representatives from IT, Customer Service, Sales, and Executive leadership, so we would need to accommodate multiple stakeholders in the demonstration.
        
        Our budget for this solution is flexible, as we understand the value of investing in quality automation tools. However, we would need to see a clear ROI projection and implementation plan before moving forward.
        
        Please let me know your availability for a call or meeting in the next two weeks. We are eager to move forward with a solution that can help us improve our customer experience and operational efficiency.
        
        Thank you for your time and consideration. I look forward to hearing from you soon.
        
        Best regards,
        John Smith
        Director of Operations
        TechCorp Solutions Inc.
        Phone: (555) 123-4567
        Email: john.smith@techcorp.com
        """
        
        test_data = {
            "subject": "Comprehensive AI Email Assistant Inquiry - Enterprise Implementation",
            "sender": "john.smith@techcorp.com",
            "body": large_body.strip(),
            "account_id": self.account_id
        }
        
        start_time = time.time()
        try:
            response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=90)
            duration = time.time() - start_time
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                draft_length = len(response_data.get('draft', ''))
                status = response_data.get('status', 'unknown')
                
                # Check if the system handled the large content appropriately
                handled_well = draft_length > 500 and status != 'error'
                
                details = f"Duration: {duration:.1f}s, Status: {status}, Draft length: {draft_length} chars, Input length: {len(large_body)} chars"
                self.log_result("Large Email Content", handled_well, details, duration)
            else:
                details = f"HTTP Error: {response.status_code}, Duration: {duration:.1f}s"
                self.log_result("Large Email Content", False, details, duration)
                
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            details = f"Request timed out after {duration:.1f}s with large content"
            self.log_result("Large Email Content", False, details, duration)
        except Exception as e:
            duration = time.time() - start_time
            details = f"Exception: {str(e)}"
            self.log_result("Large Email Content", False, details, duration)
    
    def test_edge_case_scenarios(self):
        """Test various edge cases"""
        print("\n🎯 Testing Edge Case Scenarios...")
        
        if not self.account_id:
            self.log_result("Edge Cases", False, "No account ID available")
            return
        
        edge_cases = [
            {
                "name": "Empty Body",
                "data": {
                    "subject": "Empty email test",
                    "sender": "empty@test.com",
                    "body": "",
                    "account_id": self.account_id
                }
            },
            {
                "name": "Special Characters",
                "data": {
                    "subject": "Special chars: àáâãäåæçèéêë",
                    "sender": "special@test.com",
                    "body": "Testing special characters: àáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ and emojis: 🚀🎉💡",
                    "account_id": self.account_id
                }
            },
            {
                "name": "Very Long Subject",
                "data": {
                    "subject": "This is an extremely long subject line that goes on and on and on to test how the system handles very long subject lines that might cause issues with processing or storage limitations",
                    "sender": "longsubject@test.com",
                    "body": "Testing very long subject line handling",
                    "account_id": self.account_id
                }
            }
        ]
        
        for case in edge_cases:
            start_time = time.time()
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=case["data"], timeout=60)
                duration = time.time() - start_time
                
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    status = response_data.get('status', 'unknown')
                    details = f"Duration: {duration:.1f}s, Status: {status}"
                    self.log_result(f"Edge Case - {case['name']}", True, details, duration)
                else:
                    details = f"HTTP Error: {response.status_code}, Duration: {duration:.1f}s"
                    self.log_result(f"Edge Case - {case['name']}", False, details, duration)
                    
            except Exception as e:
                duration = time.time() - start_time
                details = f"Exception: {str(e)}"
                self.log_result(f"Edge Case - {case['name']}", False, details, duration)
    
    def test_repeated_requests(self):
        """Test repeated requests to check for consistency"""
        print("\n🔁 Testing Repeated Requests...")
        
        if not self.account_id:
            self.log_result("Repeated Requests", False, "No account ID available")
            return
        
        test_data = {
            "subject": "Repeated test inquiry",
            "sender": "repeat@test.com",
            "body": "This is a repeated test to check consistency of response times and processing",
            "account_id": self.account_id
        }
        
        durations = []
        successes = 0
        
        for i in range(5):
            start_time = time.time()
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=60)
                duration = time.time() - start_time
                durations.append(duration)
                
                if response.status_code in [200, 201]:
                    successes += 1
                    self.log_result(f"Repeated Request {i+1}", True, f"Duration: {duration:.1f}s", duration)
                else:
                    self.log_result(f"Repeated Request {i+1}", False, f"HTTP {response.status_code}, Duration: {duration:.1f}s", duration)
                    
            except Exception as e:
                duration = time.time() - start_time
                durations.append(duration)
                self.log_result(f"Repeated Request {i+1}", False, f"Exception: {str(e)}", duration)
            
            # Small delay between requests
            time.sleep(1)
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            consistency_good = (max_duration - min_duration) < 30  # Variation less than 30 seconds
            success_rate_good = successes >= 4  # At least 4 out of 5 should succeed
            
            overall_passed = consistency_good and success_rate_good
            
            details = f"Success rate: {successes}/5, Avg: {avg_duration:.1f}s, Min: {min_duration:.1f}s, Max: {max_duration:.1f}s, Variation: {max_duration - min_duration:.1f}s"
            self.log_result("Repeated Requests - Overall", overall_passed, details, avg_duration)
    
    def run_comprehensive_tests(self):
        """Run all comprehensive timeout tests"""
        print("🚀 Starting Comprehensive Email Test Endpoint Analysis")
        print("=" * 70)
        
        # Setup
        if not self.setup_test_account():
            print("❌ Could not setup test account - stopping tests")
            return False
        
        print(f"Using account ID: {self.account_id}")
        
        # Run all tests
        self.test_multiple_concurrent_requests()
        self.test_large_email_content()
        self.test_edge_case_scenarios()
        self.test_repeated_requests()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        
        if failed_tests:
            print("\n🔍 FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        # Performance analysis
        timed_tests = [r for r in self.test_results if r['duration_seconds'] > 0]
        if timed_tests:
            durations = [r['duration_seconds'] for r in timed_tests]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            
            print(f"\n⏱️ PERFORMANCE ANALYSIS:")
            print(f"   • Average response time: {avg_duration:.1f}s")
            print(f"   • Maximum response time: {max_duration:.1f}s")
            print(f"   • Tests within 60s target: {len([d for d in durations if d <= 60])}/{len(durations)}")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = ComprehensiveTimeoutTester()
    success = tester.run_comprehensive_tests()
    
    if success:
        print("\n🎉 All comprehensive tests passed!")
    else:
        print("\n⚠️ Some tests failed - see details above")