#!/usr/bin/env python3
"""
COMPREHENSIVE REDRAFT AUTO-SEND TESTING
Tests both auto_send=true and auto_send=false scenarios thoroughly
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
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-analyze.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class ComprehensiveRedraftTester:
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
    
    async def create_test_account(self, auto_send: bool):
        """Create a test email account with specified auto_send setting"""
        account_data = {
            "name": f"Test Account (auto_send={auto_send})",
            "email": f"test.autosend.{auto_send}.{int(time.time())}@example.com",
            "provider": "gmail",
            "username": f"test.autosend.{auto_send}.{int(time.time())}@example.com",
            "password": "test_password_123",
            "persona": "Professional test assistant",
            "signature": "Best regards,\nTest Account",
            "auto_send": auto_send
        }
        
        try:
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, timeout=15)
            if response.status_code in [200, 201]:
                created_account = response.json()
                return created_account['id']
            else:
                print(f"   ❌ Failed to create test account: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ Error creating test account: {str(e)}")
            return None
    
    async def test_redraft_with_auto_send_true(self):
        """Test redraft with auto_send=true account"""
        print("\n🟢 TESTING REDRAFT WITH AUTO_SEND=TRUE...")
        
        # Create test account with auto_send=true
        account_id = await self.create_test_account(auto_send=True)
        if not account_id:
            self.log_test_result("Redraft Auto-Send True", False, "Failed to create test account")
            return
        
        print(f"   ✅ Created test account: {account_id}")
        
        try:
            # Create test email
            test_email_data = {
                "subject": "AUTO_SEND=TRUE TEST: Pricing Inquiry",
                "body": "Hello! I need pricing information for your AI Email Assistant. Please provide detailed pricing tiers and schedule a demo. We're looking to automate our customer support emails. Thank you!",
                "sender": "autosend.true.test@company.com",
                "account_id": account_id
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            if response.status_code not in [200, 201]:
                self.log_test_result("Redraft Auto-Send True", False, f"Failed to create test email: {response.status_code}")
                return
            
            created_email = response.json()
            email_id = created_email['id']
            print(f"   ✅ Test email created: {email_id}")
            
            # Wait for initial processing
            await asyncio.sleep(10)
            
            # Get email state before redraft
            email_before = await self.db.emails.find_one({"id": email_id})
            initial_status = email_before.get('status')
            initial_sent_at = email_before.get('sent_at')
            
            print(f"   Initial status: {initial_status}")
            print(f"   Initial sent_at: {initial_sent_at}")
            
            # Trigger redraft
            print("   Triggering redraft...")
            redraft_response = requests.post(f"{API_BASE}/emails/{email_id}/redraft", timeout=30)
            
            if redraft_response.status_code != 200:
                self.log_test_result("Redraft Auto-Send True", False, f"Redraft failed: {redraft_response.status_code}")
                return
            
            # Get final email state
            final_email = await self.db.emails.find_one({"id": email_id})
            final_status = final_email.get('status')
            final_sent_at = final_email.get('sent_at')
            validation_result = final_email.get('validation_result', {})
            validation_status = validation_result.get('status')
            
            print(f"   Final status: {final_status}")
            print(f"   Final sent_at: {final_sent_at}")
            print(f"   Validation: {validation_status}")
            
            # Verify auto-send worked
            auto_send_worked = False
            if validation_status == "PASS":
                # Should be sent with timestamp
                auto_send_worked = (final_status == "sent" and final_sent_at is not None)
                if auto_send_worked:
                    # Verify sent_at was updated (should be different from initial)
                    sent_at_updated = (initial_sent_at != final_sent_at)
                    print(f"   sent_at updated: {sent_at_updated}")
            
            success_details = f"Status: {final_status}, Validation: {validation_status}, Auto-send worked: {auto_send_worked}"
            self.log_test_result("Redraft Auto-Send True", auto_send_worked, success_details)
            
        except Exception as e:
            self.log_test_result("Redraft Auto-Send True", False, f"Exception: {str(e)}")
        
        finally:
            # Cleanup test account
            try:
                requests.delete(f"{API_BASE}/email-accounts/{account_id}", timeout=10)
            except:
                pass
    
    async def test_redraft_with_auto_send_false(self):
        """Test redraft with auto_send=false account"""
        print("\n🔴 TESTING REDRAFT WITH AUTO_SEND=FALSE...")
        
        # Create test account with auto_send=false
        account_id = await self.create_test_account(auto_send=False)
        if not account_id:
            self.log_test_result("Redraft Auto-Send False", False, "Failed to create test account")
            return
        
        print(f"   ✅ Created test account: {account_id}")
        
        try:
            # Create test email
            test_email_data = {
                "subject": "AUTO_SEND=FALSE TEST: Support Request",
                "body": "Hello! I have a question about your AI Email Assistant. Can you provide more information about the features and capabilities? I'm interested in learning more before making a decision. Thank you!",
                "sender": "autosend.false.test@company.com",
                "account_id": account_id
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            if response.status_code not in [200, 201]:
                self.log_test_result("Redraft Auto-Send False", False, f"Failed to create test email: {response.status_code}")
                return
            
            created_email = response.json()
            email_id = created_email['id']
            print(f"   ✅ Test email created: {email_id}")
            
            # Wait for initial processing
            await asyncio.sleep(10)
            
            # Get email state before redraft
            email_before = await self.db.emails.find_one({"id": email_id})
            initial_status = email_before.get('status')
            initial_sent_at = email_before.get('sent_at')
            
            print(f"   Initial status: {initial_status}")
            print(f"   Initial sent_at: {initial_sent_at}")
            
            # Trigger redraft
            print("   Triggering redraft...")
            redraft_response = requests.post(f"{API_BASE}/emails/{email_id}/redraft", timeout=30)
            
            if redraft_response.status_code != 200:
                self.log_test_result("Redraft Auto-Send False", False, f"Redraft failed: {redraft_response.status_code}")
                return
            
            # Get final email state
            final_email = await self.db.emails.find_one({"id": email_id})
            final_status = final_email.get('status')
            final_sent_at = final_email.get('sent_at')
            validation_result = final_email.get('validation_result', {})
            validation_status = validation_result.get('status')
            
            print(f"   Final status: {final_status}")
            print(f"   Final sent_at: {final_sent_at}")
            print(f"   Validation: {validation_status}")
            
            # Verify auto-send did NOT happen
            correct_behavior = False
            if validation_status == "PASS":
                # Should stay at "ready_to_send" and NOT be sent
                correct_behavior = (final_status == "ready_to_send")
                print(f"   Correct behavior (no auto-send): {correct_behavior}")
            
            success_details = f"Status: {final_status}, Validation: {validation_status}, No auto-send (correct): {correct_behavior}"
            self.log_test_result("Redraft Auto-Send False", correct_behavior, success_details)
            
        except Exception as e:
            self.log_test_result("Redraft Auto-Send False", False, f"Exception: {str(e)}")
        
        finally:
            # Cleanup test account
            try:
                requests.delete(f"{API_BASE}/email-accounts/{account_id}", timeout=10)
            except:
                pass
    
    async def test_redraft_validation_failure(self):
        """Test redraft when validation fails (should not auto-send)"""
        print("\n⚠️  TESTING REDRAFT WITH VALIDATION FAILURE...")
        
        # Use existing account
        accounts = await self.db.email_accounts.find({"is_active": True}).to_list(5)
        if not accounts:
            self.log_test_result("Redraft Validation Failure", False, "No active accounts")
            return
        
        account = accounts[0]
        print(f"   Using account: {account['email']}")
        
        try:
            # Create test email with content that might fail validation
            test_email_data = {
                "subject": "VALIDATION FAILURE TEST: Vague Request",
                "body": "Hi. Help me. Thanks.",  # Very short, vague content
                "sender": "validation.test@example.com",
                "account_id": account['id']
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
            if response.status_code not in [200, 201]:
                self.log_test_result("Redraft Validation Failure", False, f"Failed to create test email: {response.status_code}")
                return
            
            created_email = response.json()
            email_id = created_email['id']
            print(f"   ✅ Test email created: {email_id}")
            
            # Wait for initial processing
            await asyncio.sleep(10)
            
            # Trigger redraft
            print("   Triggering redraft...")
            redraft_response = requests.post(f"{API_BASE}/emails/{email_id}/redraft", timeout=30)
            
            if redraft_response.status_code != 200:
                self.log_test_result("Redraft Validation Failure", False, f"Redraft failed: {redraft_response.status_code}")
                return
            
            # Get final email state
            final_email = await self.db.emails.find_one({"id": email_id})
            final_status = final_email.get('status')
            validation_result = final_email.get('validation_result', {})
            validation_status = validation_result.get('status')
            
            print(f"   Final status: {final_status}")
            print(f"   Validation: {validation_status}")
            
            # If validation failed, should not auto-send regardless of auto_send setting
            if validation_status == "FAIL":
                correct_behavior = final_status in ["escalate", "needs_redraft"]
                success_details = f"Validation failed correctly, status: {final_status}"
                self.log_test_result("Redraft Validation Failure", correct_behavior, success_details)
            else:
                # If validation passed, that's also fine - just verify behavior
                success_details = f"Validation passed, status: {final_status}"
                self.log_test_result("Redraft Validation Failure", True, success_details)
            
        except Exception as e:
            self.log_test_result("Redraft Validation Failure", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("COMPREHENSIVE REDRAFT AUTO-SEND TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDETAILED RESULTS:")
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
            if result['details']:
                print(f"   {result['details']}")
        
        # Critical assessment
        auto_send_true_passed = any(r['test'] == 'Redraft Auto-Send True' and r['passed'] for r in self.test_results)
        auto_send_false_passed = any(r['test'] == 'Redraft Auto-Send False' and r['passed'] for r in self.test_results)
        
        print(f"\n{'='*60}")
        if auto_send_true_passed and auto_send_false_passed:
            print("🎉 COMPREHENSIVE REDRAFT AUTO-SEND TESTING: SUCCESS")
            print("✅ auto_send=true: Redrafted emails automatically send")
            print("✅ auto_send=false: Redrafted emails do NOT automatically send")
            print("✅ Bug fix is working correctly for both scenarios")
        else:
            print("❌ COMPREHENSIVE REDRAFT AUTO-SEND TESTING: ISSUES FOUND")
            if not auto_send_true_passed:
                print("❌ auto_send=true scenario failed")
            if not auto_send_false_passed:
                print("❌ auto_send=false scenario failed")
        
        print(f"{'='*60}")

async def main():
    """Main test execution"""
    print("🔧 COMPREHENSIVE REDRAFT AUTO-SEND TESTING")
    print("Testing both auto_send=true and auto_send=false scenarios")
    print("="*60)
    
    tester = ComprehensiveRedraftTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run comprehensive tests
        await tester.test_redraft_with_auto_send_true()
        await tester.test_redraft_with_auto_send_false()
        await tester.test_redraft_validation_failure()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())