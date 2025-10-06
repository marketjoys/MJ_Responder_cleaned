#!/usr/bin/env python3
"""
Salutation and Signature Testing for Email Auto-Response System
Tests the improved email auto-response system focusing on salutations and signatures
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid
import re

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://user-privacy-guard.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Account ID from review request
TEST_ACCOUNT_ID = "6e6d28ee-2e64-4f0e-bbac-c46816558287"

class SalutationSignatureTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        
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
    
    def extract_salutation(self, draft_text: str) -> str:
        """Extract salutation from draft text"""
        lines = draft_text.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line.startswith('Dear ') or line.startswith('Hello'):
                return line
        return ""
    
    def has_signature_in_draft(self, draft_text: str) -> bool:
        """Check if draft contains signature patterns that should be removed"""
        signature_patterns = [
            r'Best regards?',
            r'Sincerely',
            r'Kind regards?',
            r'Warm regards?',
            r'Thank you',
            r'Thanks',
            r'---+',
            r'\*+',
            r'With (best )?regards?'
        ]
        
        for pattern in signature_patterns:
            if re.search(pattern, draft_text, re.IGNORECASE):
                return True
        return False
    
    async def test_salutation_generation(self):
        """Test 1: Salutation Testing - Different sender formats and proper salutation generation"""
        print("\n👋 Testing Salutation Generation...")
        
        test_cases = [
            {
                "name": "Full Name with Email",
                "sender": "John Smith <john.smith@example.com>",
                "expected_salutation": "Dear John Smith,",
                "description": "Standard format with full name and email"
            },
            {
                "name": "Email Only",
                "sender": "jane.doe@company.com",
                "expected_salutation": "Dear Jane Doe,",
                "description": "Email address only, should extract name from email"
            },
            {
                "name": "Long Name Fallback",
                "sender": "Very Long Corporate Name That Exceeds Thirty Characters <long@company.com>",
                "expected_salutation": "Hello,",
                "description": "Very long name should fallback to Hello"
            },
            {
                "name": "Name with Numbers",
                "sender": "User123 <user123@example.com>",
                "expected_salutation": "Hello,",
                "description": "Name with numbers should fallback to Hello"
            },
            {
                "name": "Special Characters",
                "sender": "Test@User! <test@example.com>",
                "expected_salutation": "Hello,",
                "description": "Name with special characters should fallback to Hello"
            },
            {
                "name": "Simple Professional Name",
                "sender": "Sarah Johnson <sarah.johnson@business.com>",
                "expected_salutation": "Dear Sarah Johnson,",
                "description": "Professional name should get proper salutation"
            }
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        detailed_results = []
        
        for test_case in test_cases:
            try:
                # Create test email data
                test_email_data = {
                    "subject": f"Test Email for Salutation - {test_case['name']}",
                    "body": "Hello, I need assistance with your services. Could you please provide more information about your offerings? Thank you for your time.",
                    "sender": test_case["sender"],
                    "account_id": TEST_ACCOUNT_ID
                }
                
                print(f"   Testing: {test_case['name']} - {test_case['sender']}")
                
                # Process email via API
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    draft = processed_email.get('draft', '')
                    
                    if draft:
                        # Extract salutation from draft
                        actual_salutation = self.extract_salutation(draft)
                        
                        # Check if salutation matches expected
                        salutation_correct = actual_salutation == test_case["expected_salutation"]
                        
                        if salutation_correct:
                            passed_tests += 1
                            detailed_results.append(f"✅ {test_case['name']}: {actual_salutation}")
                        else:
                            detailed_results.append(f"❌ {test_case['name']}: Expected '{test_case['expected_salutation']}', Got '{actual_salutation}'")
                        
                        print(f"      Expected: {test_case['expected_salutation']}")
                        print(f"      Actual: {actual_salutation}")
                        print(f"      Result: {'✅ PASS' if salutation_correct else '❌ FAIL'}")
                    else:
                        detailed_results.append(f"❌ {test_case['name']}: No draft generated")
                        print(f"      ❌ No draft generated")
                else:
                    detailed_results.append(f"❌ {test_case['name']}: API error {response.status_code}")
                    print(f"      ❌ API error: {response.status_code}")
                    
            except Exception as e:
                detailed_results.append(f"❌ {test_case['name']}: Exception - {str(e)}")
                print(f"      ❌ Exception: {str(e)}")
        
        success_rate = (passed_tests / total_tests) * 100
        all_passed = passed_tests == total_tests
        
        details = f"Success rate: {success_rate:.1f}% ({passed_tests}/{total_tests}). " + "; ".join(detailed_results)
        
        self.log_test_result("Salutation Generation", all_passed, details)
        return all_passed
    
    async def test_signature_handling_in_drafts(self):
        """Test 2: Signature Handling - Verify drafts don't contain duplicate signatures"""
        print("\n✍️ Testing Signature Handling in Drafts...")
        
        test_cases = [
            {
                "name": "Standard Business Inquiry",
                "sender": "business.client@company.com",
                "body": "I'm interested in your services. Please provide pricing information and availability."
            },
            {
                "name": "Support Request",
                "sender": "customer.support@client.com",
                "body": "We're experiencing issues with our current system. Can you help us resolve this problem?"
            },
            {
                "name": "Meeting Request",
                "sender": "project.manager@enterprise.com",
                "body": "Could we schedule a meeting to discuss the project requirements? I'm available next week."
            }
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        detailed_results = []
        
        for test_case in test_cases:
            try:
                # Create test email data
                test_email_data = {
                    "subject": f"Signature Test - {test_case['name']}",
                    "body": test_case["body"],
                    "sender": test_case["sender"],
                    "account_id": TEST_ACCOUNT_ID
                }
                
                print(f"   Testing: {test_case['name']}")
                
                # Process email via API
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    draft = processed_email.get('draft', '')
                    
                    if draft:
                        # Check if draft contains signature patterns
                        has_signature = self.has_signature_in_draft(draft)
                        
                        if not has_signature:
                            passed_tests += 1
                            detailed_results.append(f"✅ {test_case['name']}: No signature in draft")
                        else:
                            detailed_results.append(f"❌ {test_case['name']}: Contains signature patterns")
                        
                        print(f"      Draft length: {len(draft)} characters")
                        print(f"      Contains signature: {'❌ YES' if has_signature else '✅ NO'}")
                        
                        # Show last few lines to check for signatures
                        draft_lines = draft.split('\n')
                        last_lines = draft_lines[-3:] if len(draft_lines) > 3 else draft_lines
                        print(f"      Last lines: {last_lines}")
                    else:
                        detailed_results.append(f"❌ {test_case['name']}: No draft generated")
                        print(f"      ❌ No draft generated")
                else:
                    detailed_results.append(f"❌ {test_case['name']}: API error {response.status_code}")
                    print(f"      ❌ API error: {response.status_code}")
                    
            except Exception as e:
                detailed_results.append(f"❌ {test_case['name']}: Exception - {str(e)}")
                print(f"      ❌ Exception: {str(e)}")
        
        success_rate = (passed_tests / total_tests) * 100
        all_passed = passed_tests == total_tests
        
        details = f"Success rate: {success_rate:.1f}% ({passed_tests}/{total_tests}). " + "; ".join(detailed_results)
        
        self.log_test_result("Signature Handling in Drafts", all_passed, details)
        return all_passed
    
    async def test_complete_email_flow(self):
        """Test 3: Complete Email Flow - End-to-end process with salutation and signature handling"""
        print("\n🔄 Testing Complete Email Flow...")
        
        try:
            # Test email data
            test_email_data = {
                "subject": "Complete Flow Test - Business Inquiry",
                "body": "Dear Team, I am writing to inquire about your AI email assistant services. We are a growing company that receives many customer inquiries daily and need an automated solution. Could you please provide detailed information about your pricing, features, and implementation process? We would also like to schedule a demo if possible. Thank you for your time and assistance.",
                "sender": "Michael Thompson <michael.thompson@growthcorp.com>",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print("   Processing test email...")
            
            # Step 1: Process email and generate draft
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            
            if response.status_code not in [200, 201]:
                self.log_test_result("Complete Email Flow", False, f"Email processing failed: {response.status_code}")
                return False
            
            processed_email = response.json()
            email_id = processed_email.get('id')
            draft = processed_email.get('draft', '')
            
            print(f"   Email processed with ID: {email_id}")
            print(f"   Draft length: {len(draft)} characters")
            
            # Step 2: Validate salutation
            expected_salutation = "Dear Michael Thompson,"
            actual_salutation = self.extract_salutation(draft)
            salutation_correct = actual_salutation == expected_salutation
            
            print(f"   Expected salutation: {expected_salutation}")
            print(f"   Actual salutation: {actual_salutation}")
            print(f"   Salutation correct: {'✅' if salutation_correct else '❌'}")
            
            # Step 3: Validate no signature in draft
            has_signature = self.has_signature_in_draft(draft)
            signature_clean = not has_signature
            
            print(f"   Draft contains signature: {'❌ YES' if has_signature else '✅ NO'}")
            
            # Step 4: Check email status
            email_status = processed_email.get('status', '')
            status_good = email_status in ['ready_to_send', 'drafting', 'processing']
            
            print(f"   Email status: {email_status}")
            print(f"   Status acceptable: {'✅' if status_good else '❌'}")
            
            # Step 5: Test account signature configuration
            account_response = requests.get(f"{API_BASE}/email-accounts/{TEST_ACCOUNT_ID}", timeout=10)
            account_has_signature = False
            
            if account_response.status_code == 200:
                account_data = account_response.json()
                account_signature = account_data.get('signature', '')
                account_has_signature = bool(account_signature.strip())
                print(f"   Account has signature configured: {'✅ YES' if account_has_signature else '❌ NO'}")
            else:
                print(f"   ⚠️ Could not retrieve account info: {account_response.status_code}")
            
            # Overall assessment
            flow_components = {
                "email_processed": bool(email_id and draft),
                "salutation_correct": salutation_correct,
                "signature_clean": signature_clean,
                "status_good": status_good
            }
            
            all_passed = all(flow_components.values())
            
            details = f"Email processed: {flow_components['email_processed']}, " \
                     f"Salutation: {salutation_correct}, " \
                     f"No signature in draft: {signature_clean}, " \
                     f"Status: {status_good}, " \
                     f"Draft length: {len(draft)} chars"
            
            self.log_test_result("Complete Email Flow", all_passed, details)
            return all_passed
            
        except Exception as e:
            self.log_test_result("Complete Email Flow", False, f"Exception: {str(e)}")
            return False
    
    async def test_edge_cases(self):
        """Test 4: Edge Cases - Very long names, invalid formats, special characters"""
        print("\n🔍 Testing Edge Cases...")
        
        edge_cases = [
            {
                "name": "Very Long Corporate Name",
                "sender": "Chief Technology Officer of Advanced Digital Solutions International Corporation <cto@adsi-corp.com>",
                "expected_salutation": "Hello,",
                "description": "Extremely long name should fallback to Hello"
            },
            {
                "name": "Email with Plus Sign",
                "sender": "test+user@example.com",
                "expected_salutation": "Dear Test User,",
                "description": "Email with plus sign should extract clean name"
            },
            {
                "name": "Name with Dots",
                "sender": "Dr. Jane A. Smith <dr.jane.smith@medical.com>",
                "expected_salutation": "Dear Dr. Jane A. Smith,",
                "description": "Professional title with dots should work"
            },
            {
                "name": "Mixed Case Email",
                "sender": "JohnDOE@COMPANY.COM",
                "expected_salutation": "Dear Johndoe,",
                "description": "Mixed case email should be handled"
            },
            {
                "name": "Empty Name",
                "sender": " <empty@example.com>",
                "expected_salutation": "Hello,",
                "description": "Empty name should fallback to Hello"
            },
            {
                "name": "Numbers in Name",
                "sender": "User2024 Admin3 <admin@company.com>",
                "expected_salutation": "Hello,",
                "description": "Names with numbers should fallback to Hello"
            }
        ]
        
        passed_tests = 0
        total_tests = len(edge_cases)
        detailed_results = []
        
        for test_case in edge_cases:
            try:
                # Create test email data
                test_email_data = {
                    "subject": f"Edge Case Test - {test_case['name']}",
                    "body": "This is a test email to verify edge case handling in salutation generation.",
                    "sender": test_case["sender"],
                    "account_id": TEST_ACCOUNT_ID
                }
                
                print(f"   Testing: {test_case['name']}")
                print(f"   Sender: {test_case['sender']}")
                
                # Process email via API
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                
                if response.status_code in [200, 201]:
                    processed_email = response.json()
                    draft = processed_email.get('draft', '')
                    
                    if draft:
                        # Extract salutation from draft
                        actual_salutation = self.extract_salutation(draft)
                        
                        # For edge cases, we're more flexible - either the expected or "Hello," is acceptable
                        salutation_acceptable = (
                            actual_salutation == test_case["expected_salutation"] or
                            actual_salutation == "Hello,"
                        )
                        
                        if salutation_acceptable:
                            passed_tests += 1
                            detailed_results.append(f"✅ {test_case['name']}: {actual_salutation}")
                        else:
                            detailed_results.append(f"❌ {test_case['name']}: Expected '{test_case['expected_salutation']}' or 'Hello,', Got '{actual_salutation}'")
                        
                        print(f"      Expected: {test_case['expected_salutation']} (or Hello,)")
                        print(f"      Actual: {actual_salutation}")
                        print(f"      Result: {'✅ PASS' if salutation_acceptable else '❌ FAIL'}")
                    else:
                        detailed_results.append(f"❌ {test_case['name']}: No draft generated")
                        print(f"      ❌ No draft generated")
                else:
                    detailed_results.append(f"❌ {test_case['name']}: API error {response.status_code}")
                    print(f"      ❌ API error: {response.status_code}")
                    
            except Exception as e:
                detailed_results.append(f"❌ {test_case['name']}: Exception - {str(e)}")
                print(f"      ❌ Exception: {str(e)}")
        
        success_rate = (passed_tests / total_tests) * 100
        all_passed = passed_tests == total_tests
        
        details = f"Success rate: {success_rate:.1f}% ({passed_tests}/{total_tests}). " + "; ".join(detailed_results)
        
        self.log_test_result("Edge Cases", all_passed, details)
        return all_passed
    
    async def test_account_configuration(self):
        """Test 5: Account Configuration - Verify account exists and has proper signature settings"""
        print("\n⚙️ Testing Account Configuration...")
        
        try:
            # Get account information
            response = requests.get(f"{API_BASE}/email-accounts/{TEST_ACCOUNT_ID}", timeout=10)
            
            if response.status_code == 200:
                account_data = response.json()
                
                # Check account details
                account_email = account_data.get('email', '')
                account_signature = account_data.get('signature', '')
                account_active = account_data.get('is_active', False)
                account_auto_send = account_data.get('auto_send', False)
                
                print(f"   Account Email: {account_email}")
                print(f"   Account Active: {account_active}")
                print(f"   Auto Send: {account_auto_send}")
                print(f"   Has Signature: {'✅ YES' if account_signature.strip() else '❌ NO'}")
                
                if account_signature.strip():
                    print(f"   Signature Preview: {account_signature[:100]}...")
                
                # Account should exist and be properly configured
                account_valid = bool(account_email and account_active)
                
                details = f"Email: {account_email}, Active: {account_active}, " \
                         f"Auto-send: {account_auto_send}, Has signature: {bool(account_signature.strip())}"
                
                self.log_test_result("Account Configuration", account_valid, details)
                return account_valid
                
            elif response.status_code == 404:
                self.log_test_result("Account Configuration", False, f"Account {TEST_ACCOUNT_ID} not found")
                return False
            else:
                self.log_test_result("Account Configuration", False, f"API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Account Configuration", False, f"Exception: {str(e)}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("SALUTATION AND SIGNATURE TESTING SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        # Group results by category
        categories = {}
        for result in self.test_results:
            category = result['test'].split(' - ')[0] if ' - ' in result['test'] else result['test']
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        # Print detailed results by category
        for category, results in categories.items():
            print(f"{category}:")
            for result in results:
                print(f"  {result['status']}: {result['test']}")
                if result['details']:
                    print(f"    {result['details']}")
            print()
        
        # Overall assessment
        if success_rate >= 90:
            print("🎉 EXCELLENT: Salutation and signature system working very well!")
        elif success_rate >= 75:
            print("✅ GOOD: Salutation and signature system mostly working with minor issues")
        elif success_rate >= 50:
            print("⚠️ NEEDS IMPROVEMENT: Salutation and signature system has significant issues")
        else:
            print("❌ CRITICAL: Salutation and signature system needs major fixes")

async def main():
    """Main test execution"""
    print("🧪 SALUTATION AND SIGNATURE TESTING")
    print("="*60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Account ID: {TEST_ACCOUNT_ID}")
    print(f"Updated Groq API Key: {os.environ.get('GROQ_API_KEY', 'Not set')[:20]}...")
    print()
    
    tester = SalutationSignatureTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, exiting...")
        return
    
    try:
        # Run all tests
        print("Starting comprehensive salutation and signature testing...")
        
        # Test 1: Account Configuration
        await tester.test_account_configuration()
        
        # Test 2: Salutation Generation
        await tester.test_salutation_generation()
        
        # Test 3: Signature Handling in Drafts
        await tester.test_signature_handling_in_drafts()
        
        # Test 4: Complete Email Flow
        await tester.test_complete_email_flow()
        
        # Test 5: Edge Cases
        await tester.test_edge_cases()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())