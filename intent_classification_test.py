#!/usr/bin/env python3
"""
Intent Classification Test for Automatic Email Response System
Tests the specific intent classification fix with lowered confidence thresholds
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-without-waste.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class IntentClassificationTester:
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
    
    async def test_intent_classification_thresholds(self):
        """Test 1: Intent Classification with Lowered Thresholds (0.65)"""
        print("\n🎯 Testing Intent Classification with Lowered Thresholds...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Intent Classification Thresholds", False, "No active email accounts")
                return
            
            # Test the specific example from the review request
            test_email_data = {
                "subject": "Product inquiry",
                "body": "Hi, I'm interested in your product pricing. Can you send me more information?",
                "sender": "test@example.com",
                "account_id": account['id']
            }
            
            print(f"   Testing with email: '{test_email_data['subject']}' - '{test_email_data['body'][:50]}...'")
            
            # Test via API endpoint
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
            processing_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                intents = processed_email.get('intents', [])
                status = processed_email.get('status', 'unknown')
                
                print(f"   Processing time: {processing_time:.1f}s")
                print(f"   Final status: {status}")
                print(f"   Intents found: {len(intents)}")
                
                # Check intent classification results
                intent_classification_working = len(intents) > 0
                if intent_classification_working:
                    for i, intent in enumerate(intents):
                        confidence = intent.get('confidence', 0)
                        name = intent.get('name', 'Unknown')
                        print(f"   Intent {i+1}: {name} (confidence: {confidence:.4f})")
                        
                        # Check if confidence is above the lowered threshold (0.65)
                        if confidence >= 0.65:
                            print(f"   ✅ Intent '{name}' meets lowered threshold (0.65)")
                        else:
                            print(f"   ⚠️  Intent '{name}' below threshold but still matched")
                
                # Check if workflow completed successfully
                workflow_completed = status in ['ready_to_send', 'sent', 'needs_redraft']
                has_draft = bool(processed_email.get('draft'))
                
                print(f"   Workflow completed: {workflow_completed}")
                print(f"   Draft generated: {has_draft}")
                
                # Test passes if intents are classified and workflow progresses
                test_passed = intent_classification_working and (workflow_completed or has_draft)
                
                details = f"Intents: {len(intents)}, Status: {status}, Time: {processing_time:.1f}s, Draft: {has_draft}"
                
            else:
                test_passed = False
                details = f"API Error: {response.status_code} - {response.text[:200]}"
                print(f"   ❌ API request failed: {response.status_code}")
            
            self.log_test_result("Intent Classification Thresholds", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Intent Classification Thresholds", False, f"Exception: {str(e)}")
    
    async def test_multiple_intent_types(self):
        """Test 2: Multiple Intent Types - Sales, Support, General"""
        print("\n📧 Testing Multiple Intent Types...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Multiple Intent Types", False, "No active email accounts")
                return
            
            # Test different email types
            test_emails = [
                {
                    "name": "Sales Inquiry",
                    "subject": "Pricing Information Request",
                    "body": "Hello, I'm interested in purchasing your AI email assistant. Could you please provide pricing details and available packages? We're a medium-sized company looking to automate our customer support emails.",
                    "sender": "sales.inquiry@company.com"
                },
                {
                    "name": "Support Request", 
                    "subject": "Technical Help Needed",
                    "body": "Hi, I'm having trouble setting up the email integration. The IMAP connection keeps failing and I'm getting authentication errors. Can you help me troubleshoot this issue?",
                    "sender": "support.request@techfirm.com"
                },
                {
                    "name": "General Inquiry",
                    "subject": "Information about your services",
                    "body": "Good morning, I came across your website and I'm curious about your AI email automation solution. Could you tell me more about how it works and what industries you serve?",
                    "sender": "info@business.com"
                }
            ]
            
            results = []
            
            for test_email in test_emails:
                print(f"\n   Testing {test_email['name']}...")
                
                email_data = {
                    "subject": test_email['subject'],
                    "body": test_email['body'],
                    "sender": test_email['sender'],
                    "account_id": account['id']
                }
                
                try:
                    start_time = time.time()
                    response = requests.post(f"{API_BASE}/emails/test", json=email_data, timeout=60)
                    processing_time = time.time() - start_time
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        intents = processed_email.get('intents', [])
                        status = processed_email.get('status', 'unknown')
                        has_draft = bool(processed_email.get('draft'))
                        
                        print(f"   - Processing time: {processing_time:.1f}s")
                        print(f"   - Status: {status}")
                        print(f"   - Intents: {len(intents)}")
                        print(f"   - Draft generated: {has_draft}")
                        
                        if intents:
                            best_intent = intents[0]
                            print(f"   - Best match: {best_intent.get('name')} ({best_intent.get('confidence', 0):.4f})")
                        
                        # Check if this email type was processed successfully
                        email_success = len(intents) > 0 and (status in ['ready_to_send', 'sent', 'needs_redraft'] or has_draft)
                        results.append({
                            'name': test_email['name'],
                            'success': email_success,
                            'intents_count': len(intents),
                            'status': status,
                            'processing_time': processing_time
                        })
                        
                    else:
                        print(f"   - ❌ Failed: {response.status_code}")
                        results.append({
                            'name': test_email['name'],
                            'success': False,
                            'error': f"HTTP {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"   - ❌ Exception: {str(e)}")
                    results.append({
                        'name': test_email['name'],
                        'success': False,
                        'error': str(e)
                    })
                
                # Wait between requests to avoid rate limiting
                time.sleep(2)
            
            # Evaluate overall results
            successful_tests = [r for r in results if r.get('success', False)]
            test_passed = len(successful_tests) >= 2  # At least 2 out of 3 should work
            
            details = f"Successful: {len(successful_tests)}/3 - " + ", ".join([f"{r['name']}: {'✅' if r.get('success') else '❌'}" for r in results])
            
            self.log_test_result("Multiple Intent Types", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Multiple Intent Types", False, f"Exception: {str(e)}")
    
    async def test_end_to_end_workflow(self):
        """Test 3: End-to-End Workflow Verification"""
        print("\n🔄 Testing End-to-End Workflow...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("End-to-End Workflow", False, "No active email accounts")
                return
            
            # Use a comprehensive test email that should trigger the full workflow
            test_email_data = {
                "subject": "Urgent: Need AI Email Assistant Demo and Pricing",
                "body": "Hello! I'm the Operations Manager at TechCorp Inc. We're experiencing a high volume of customer inquiries and need an automated email response solution. Could you please provide: 1) Detailed pricing information for your AI Email Assistant, 2) Schedule a demo to see the intent classification in action, 3) Information about integration with our existing systems. We're looking to make a decision within the next two weeks. Our budget is flexible for the right solution. Please respond as soon as possible. Thank you!",
                "sender": "operations@techcorp.com",
                "account_id": account['id']
            }
            
            print("   Testing comprehensive workflow with detailed inquiry...")
            
            # Track the workflow stages
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
            total_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                
                # Check each stage of the workflow
                email_received = True  # We sent it successfully
                intents_classified = len(processed_email.get('intents', [])) > 0
                draft_generated = bool(processed_email.get('draft'))
                validation_completed = processed_email.get('validation_result') is not None
                final_status = processed_email.get('status', 'unknown')
                
                print(f"   📨 Email received: {email_received}")
                print(f"   🎯 Intents classified: {intents_classified} ({len(processed_email.get('intents', []))} intents)")
                print(f"   ✍️  Draft generated: {draft_generated} ({len(processed_email.get('draft', ''))} chars)")
                print(f"   ✅ Validation completed: {validation_completed}")
                print(f"   🏁 Final status: {final_status}")
                print(f"   ⏱️  Total processing time: {total_time:.1f}s")
                
                # Check intent details
                if intents_classified:
                    intents = processed_email.get('intents', [])
                    for i, intent in enumerate(intents[:3]):  # Show top 3
                        confidence = intent.get('confidence', 0)
                        name = intent.get('name', 'Unknown')
                        print(f"   Intent {i+1}: {name} (confidence: {confidence:.4f})")
                        
                        # Verify confidence meets lowered threshold
                        if confidence >= 0.65:
                            print(f"      ✅ Meets threshold (≥0.65)")
                        else:
                            print(f"      ⚠️  Below threshold but matched")
                
                # Workflow is successful if we progress through the main stages
                workflow_success = (email_received and intents_classified and draft_generated and 
                                  final_status in ['ready_to_send', 'sent', 'needs_redraft', 'validating'])
                
                # Additional checks
                proper_intent_matching = any(intent.get('confidence', 0) >= 0.65 for intent in processed_email.get('intents', []))
                reasonable_processing_time = total_time < 60  # Should complete within 60 seconds
                
                overall_success = workflow_success and proper_intent_matching and reasonable_processing_time
                
                details = f"Workflow: {workflow_success}, Intent matching: {proper_intent_matching}, Time: {total_time:.1f}s, Status: {final_status}"
                
            else:
                overall_success = False
                details = f"API Error: {response.status_code} - {response.text[:200]}"
                print(f"   ❌ API request failed: {response.status_code}")
            
            self.log_test_result("End-to-End Workflow", overall_success, details)
            
        except Exception as e:
            self.log_test_result("End-to-End Workflow", False, f"Exception: {str(e)}")
    
    async def test_intent_confidence_verification(self):
        """Test 4: Verify Intent Confidence Scores Above 0.65"""
        print("\n📊 Testing Intent Confidence Score Verification...")
        
        try:
            # Get existing intents from database to check thresholds
            intents = await self.db.intents.find().to_list(100)
            
            if not intents:
                self.log_test_result("Intent Confidence Verification", False, "No intents found in database")
                return
            
            print(f"   Found {len(intents)} intents in database")
            
            # Check intent thresholds
            threshold_check_passed = True
            lowered_threshold_count = 0
            
            for intent in intents:
                name = intent.get('name', 'Unknown')
                threshold = intent.get('confidence_threshold', 0.75)  # Default was 0.75
                
                print(f"   Intent '{name}': threshold = {threshold}")
                
                if threshold <= 0.65:
                    lowered_threshold_count += 1
                    print(f"      ✅ Lowered threshold (≤0.65)")
                else:
                    print(f"      ⚠️  High threshold (>{threshold})")
            
            # Check if thresholds have been lowered
            thresholds_lowered = lowered_threshold_count > 0
            
            # Test with a borderline email that should match with lowered thresholds
            account = await self.db.email_accounts.find_one({"is_active": True})
            if account:
                borderline_email = {
                    "subject": "Question about your service",
                    "body": "I saw your website and have some questions about pricing and features. Can you help?",
                    "sender": "borderline@test.com",
                    "account_id": account['id']
                }
                
                print("\n   Testing borderline email that should match with lowered thresholds...")
                
                try:
                    response = requests.post(f"{API_BASE}/emails/test", json=borderline_email, timeout=30)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        intents_found = processed_email.get('intents', [])
                        
                        print(f"   Borderline email matched {len(intents_found)} intents")
                        
                        # Check if any intents have confidence >= 0.65
                        good_confidence_intents = [i for i in intents_found if i.get('confidence', 0) >= 0.65]
                        
                        if good_confidence_intents:
                            print(f"   ✅ {len(good_confidence_intents)} intents with confidence ≥ 0.65")
                            for intent in good_confidence_intents:
                                print(f"      - {intent.get('name')}: {intent.get('confidence', 0):.4f}")
                        else:
                            print(f"   ⚠️  No intents with confidence ≥ 0.65")
                        
                        borderline_test_passed = len(good_confidence_intents) > 0
                    else:
                        borderline_test_passed = False
                        print(f"   ❌ Borderline test failed: {response.status_code}")
                        
                except Exception as e:
                    borderline_test_passed = False
                    print(f"   ❌ Borderline test exception: {str(e)}")
            else:
                borderline_test_passed = False
                print("   ⚠️  No active account for borderline test")
            
            # Overall test passes if thresholds are lowered AND borderline email works
            overall_passed = thresholds_lowered and borderline_test_passed
            
            details = f"Lowered thresholds: {lowered_threshold_count}/{len(intents)}, Borderline test: {borderline_test_passed}"
            
            self.log_test_result("Intent Confidence Verification", overall_passed, details)
            
        except Exception as e:
            self.log_test_result("Intent Confidence Verification", False, f"Exception: {str(e)}")
    
    async def run_all_tests(self):
        """Run all intent classification tests"""
        print("🚀 Starting Intent Classification Testing Suite...")
        print("=" * 60)
        
        if not await self.setup():
            return
        
        try:
            # Run all tests
            await self.test_intent_classification_thresholds()
            await self.test_multiple_intent_types()
            await self.test_end_to_end_workflow()
            await self.test_intent_confidence_verification()
            
            # Summary
            print("\n" + "=" * 60)
            print("📋 TEST SUMMARY")
            print("=" * 60)
            
            passed_tests = [r for r in self.test_results if r['passed']]
            failed_tests = [r for r in self.test_results if not r['passed']]
            
            print(f"✅ PASSED: {len(passed_tests)}")
            print(f"❌ FAILED: {len(failed_tests)}")
            print(f"📊 TOTAL:  {len(self.test_results)}")
            
            if failed_tests:
                print("\n❌ FAILED TESTS:")
                for test in failed_tests:
                    print(f"   - {test['test']}: {test['details']}")
            
            if passed_tests:
                print("\n✅ PASSED TESTS:")
                for test in passed_tests:
                    print(f"   - {test['test']}")
            
            # Overall assessment
            success_rate = len(passed_tests) / len(self.test_results) * 100
            print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}%")
            
            if success_rate >= 75:
                print("🎉 INTENT CLASSIFICATION FIX VERIFICATION: SUCCESS")
                print("   The lowered confidence thresholds (0.65) are working correctly!")
            else:
                print("⚠️  INTENT CLASSIFICATION FIX VERIFICATION: NEEDS ATTENTION")
                print("   Some issues remain with the intent classification system.")
            
        finally:
            await self.cleanup()

async def main():
    """Main test runner"""
    tester = IntentClassificationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())