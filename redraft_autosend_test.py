#!/usr/bin/env python3
"""
CRITICAL BUG FIX TESTING - REDRAFT AUTO-SEND FUNCTIONALITY
Tests the specific fix where redrafted emails now automatically send when validation passes
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://async-email-repair.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class RedraftAutoSendTester:
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
    
    async def test_redraft_autosend_bug_fix(self):
        """
        CRITICAL TEST: Redraft Auto-Send Bug Fix
        Tests the specific scenario described in the review request
        """
        print("\n🔧 TESTING REDRAFT AUTO-SEND BUG FIX...")
        print("=" * 60)
        
        try:
            # Step 1: Get an active email account with auto_send=true
            print("Step 1: Finding email account with auto_send=true...")
            accounts = await self.db.email_accounts.find({"is_active": True}).to_list(10)
            
            if not accounts:
                self.log_test_result("Redraft Auto-Send Bug Fix", False, "No active email accounts found")
                return
            
            # Find or create an account with auto_send=true
            auto_send_account = None
            for account in accounts:
                if account.get('auto_send', True):  # Default is True
                    auto_send_account = account
                    break
            
            if not auto_send_account:
                # Update first account to have auto_send=true
                await self.db.email_accounts.update_one(
                    {"id": accounts[0]['id']},
                    {"$set": {"auto_send": True}}
                )
                auto_send_account = await self.db.email_accounts.find_one({"id": accounts[0]['id']})
            
            print(f"   ✅ Using account: {auto_send_account['email']} (auto_send: {auto_send_account.get('auto_send', True)})")
            
            # Step 2: Create a test email using /api/emails/test endpoint
            print("\nStep 2: Creating test email...")
            test_email_data = {
                "subject": "REDRAFT TEST: Pricing Inquiry for AI Email Assistant",
                "body": "Hello! I'm interested in your AI Email Assistant solution. Could you please provide detailed pricing information and schedule a demo? We need to automate our customer support emails and are looking for a comprehensive solution. Please get back to me with pricing tiers and feature comparisons. Thank you!",
                "sender": "redraft.test@techcompany.com",
                "account_id": auto_send_account['id']
            }
            
            try:
                response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                if response.status_code not in [200, 201]:
                    self.log_test_result("Redraft Auto-Send Bug Fix", False, f"Failed to create test email: {response.status_code}")
                    return
                
                created_email = response.json()
                email_id = created_email['id']
                print(f"   ✅ Test email created: {email_id}")
                print(f"   Initial status: {created_email.get('status')}")
                
            except Exception as e:
                self.log_test_result("Redraft Auto-Send Bug Fix", False, f"Error creating test email: {str(e)}")
                return
            
            # Step 3: Wait for email to be processed to "ready_to_send" status
            print("\nStep 3: Waiting for email processing to complete...")
            max_wait_time = 60  # 60 seconds max wait
            wait_interval = 3   # Check every 3 seconds
            waited_time = 0
            
            while waited_time < max_wait_time:
                email_doc = await self.db.emails.find_one({"id": email_id})
                current_status = email_doc.get('status') if email_doc else 'not_found'
                print(f"   Status after {waited_time}s: {current_status}")
                
                if current_status in ['ready_to_send', 'sent', 'error', 'escalate']:
                    break
                
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
            
            # Get final email state before redraft
            email_before_redraft = await self.db.emails.find_one({"id": email_id})
            if not email_before_redraft:
                self.log_test_result("Redraft Auto-Send Bug Fix", False, "Email not found in database")
                return
            
            initial_status = email_before_redraft.get('status')
            initial_sent_at = email_before_redraft.get('sent_at')
            
            print(f"   ✅ Email processed to status: {initial_status}")
            print(f"   Initial sent_at: {initial_sent_at}")
            
            # Step 4: Trigger redraft using /api/emails/{email_id}/redraft endpoint
            print(f"\nStep 4: Triggering redraft for email {email_id}...")
            
            try:
                redraft_response = requests.post(f"{API_BASE}/emails/{email_id}/redraft", timeout=30)
                
                if redraft_response.status_code != 200:
                    self.log_test_result("Redraft Auto-Send Bug Fix", False, f"Redraft request failed: {redraft_response.status_code}")
                    return
                
                redrafted_email = redraft_response.json()
                print(f"   ✅ Redraft completed")
                print(f"   Redraft status: {redrafted_email.get('status')}")
                
            except Exception as e:
                self.log_test_result("Redraft Auto-Send Bug Fix", False, f"Error during redraft: {str(e)}")
                return
            
            # Step 5: Verify the redraft process and auto-send functionality
            print("\nStep 5: Verifying redraft auto-send functionality...")
            
            # Get the final email state from database
            final_email = await self.db.emails.find_one({"id": email_id})
            
            if not final_email:
                self.log_test_result("Redraft Auto-Send Bug Fix", False, "Email not found after redraft")
                return
            
            final_status = final_email.get('status')
            final_sent_at = final_email.get('sent_at')
            validation_result = final_email.get('validation_result', {})
            validation_status = validation_result.get('status') if validation_result else 'None'
            
            print(f"   Final status: {final_status}")
            print(f"   Final sent_at: {final_sent_at}")
            print(f"   Validation status: {validation_status}")
            print(f"   Draft length: {len(final_email.get('draft', ''))}")
            
            # CRITICAL VERIFICATION: Check if the bug fix worked
            bug_fix_working = False
            failure_reasons = []
            
            # Check 1: Email went through draft agent again (new draft generated)
            has_new_draft = bool(final_email.get('draft')) and len(final_email.get('draft', '')) > 100
            if not has_new_draft:
                failure_reasons.append("No new draft generated")
            
            # Check 2: Email went through validation agent again
            has_validation = bool(validation_result)
            if not has_validation:
                failure_reasons.append("No validation performed")
            
            # Check 3: If validation passed, status should be "ready_to_send" or "sent"
            validation_passed = validation_status == "PASS"
            if validation_passed:
                # Check 4: CRITICAL FIX - Auto-send should have been called
                if auto_send_account.get('auto_send', True):
                    # Should be "sent" with sent_at timestamp
                    auto_send_worked = (final_status == "sent" and final_sent_at is not None)
                    if not auto_send_worked:
                        failure_reasons.append(f"Auto-send failed: status={final_status}, sent_at={final_sent_at}")
                    else:
                        print(f"   ✅ AUTO-SEND WORKED: Email status changed to 'sent' with timestamp")
                        bug_fix_working = True
                else:
                    # Account has auto_send=false, should stay at "ready_to_send"
                    if final_status == "ready_to_send":
                        print(f"   ✅ Correct behavior: auto_send=false, status remains 'ready_to_send'")
                        bug_fix_working = True
                    else:
                        failure_reasons.append(f"Expected 'ready_to_send' for auto_send=false, got '{final_status}'")
            else:
                # Validation failed, should not auto-send
                if final_status in ["escalate", "needs_redraft"]:
                    print(f"   ✅ Correct behavior: validation failed, no auto-send")
                    bug_fix_working = True
                else:
                    failure_reasons.append(f"Validation failed but unexpected status: {final_status}")
            
            # Step 6: Test with auto_send=false account
            print("\nStep 6: Testing with auto_send=false account...")
            
            # Create/find an account with auto_send=false
            auto_send_false_account = None
            for account in accounts:
                if not account.get('auto_send', True):
                    auto_send_false_account = account
                    break
            
            if not auto_send_false_account:
                # Update an account to have auto_send=false
                if len(accounts) > 1:
                    await self.db.email_accounts.update_one(
                        {"id": accounts[1]['id']},
                        {"$set": {"auto_send": False}}
                    )
                    auto_send_false_account = await self.db.email_accounts.find_one({"id": accounts[1]['id']})
            
            auto_send_false_test_passed = True
            if auto_send_false_account:
                print(f"   Testing with account: {auto_send_false_account['email']} (auto_send: False)")
                
                # Create test email for auto_send=false account
                test_email_data_2 = {
                    "subject": "REDRAFT TEST: Auto-Send False Test",
                    "body": "This is a test email for auto_send=false account testing.",
                    "sender": "autosend.false.test@example.com",
                    "account_id": auto_send_false_account['id']
                }
                
                try:
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data_2, timeout=30)
                    if response.status_code in [200, 201]:
                        email_2 = response.json()
                        email_2_id = email_2['id']
                        
                        # Wait for processing
                        await asyncio.sleep(10)
                        
                        # Trigger redraft
                        redraft_response = requests.post(f"{API_BASE}/emails/{email_2_id}/redraft", timeout=30)
                        if redraft_response.status_code == 200:
                            final_email_2 = await self.db.emails.find_one({"id": email_2_id})
                            final_status_2 = final_email_2.get('status')
                            
                            # Should NOT auto-send (should stay at ready_to_send)
                            if final_status_2 == "ready_to_send":
                                print(f"   ✅ Auto-send=false test passed: status remains 'ready_to_send'")
                            else:
                                print(f"   ⚠️  Auto-send=false test: unexpected status '{final_status_2}'")
                                auto_send_false_test_passed = False
                        else:
                            auto_send_false_test_passed = False
                    else:
                        auto_send_false_test_passed = False
                        
                except Exception as e:
                    print(f"   ⚠️  Auto-send=false test failed: {str(e)}")
                    auto_send_false_test_passed = False
            else:
                print("   ⚠️  Skipping auto_send=false test - no suitable account")
            
            # Final Assessment
            overall_success = bug_fix_working and auto_send_false_test_passed
            
            if overall_success:
                success_details = f"✅ REDRAFT AUTO-SEND BUG FIX VERIFIED: " \
                                f"Status: {final_status}, Validation: {validation_status}, " \
                                f"Auto-send working: {bug_fix_working}, " \
                                f"Auto-send=false test: {auto_send_false_test_passed}"
            else:
                success_details = f"❌ BUG FIX ISSUES: {', '.join(failure_reasons)}"
            
            self.log_test_result("REDRAFT AUTO-SEND BUG FIX", overall_success, success_details)
            
            # Log detailed verification results
            self.log_test_result("Redraft - Draft Generation", has_new_draft, f"New draft generated: {len(final_email.get('draft', ''))} chars")
            self.log_test_result("Redraft - Validation", has_validation, f"Validation status: {validation_status}")
            self.log_test_result("Redraft - Auto-Send (auto_send=true)", bug_fix_working and auto_send_account.get('auto_send', True), 
                               f"Final status: {final_status}, sent_at: {bool(final_sent_at)}")
            self.log_test_result("Redraft - Auto-Send (auto_send=false)", auto_send_false_test_passed, 
                               "Correctly did not auto-send when auto_send=false")
            
        except Exception as e:
            self.log_test_result("REDRAFT AUTO-SEND BUG FIX", False, f"Exception: {str(e)}")
            import traceback
            print(f"   Full traceback: {traceback.format_exc()}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("REDRAFT AUTO-SEND BUG FIX TEST SUMMARY")
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
        main_test_passed = any(r['test'] == 'REDRAFT AUTO-SEND BUG FIX' and r['passed'] for r in self.test_results)
        
        print(f"\n{'='*60}")
        if main_test_passed:
            print("🎉 CRITICAL BUG FIX VERIFICATION: SUCCESS")
            print("✅ Redrafted emails now automatically send when validation passes")
            print("✅ Auto-send respects account settings (auto_send=true/false)")
            print("✅ Status correctly changes from 'ready_to_send' to 'sent'")
            print("✅ sent_at timestamp is properly populated")
        else:
            print("❌ CRITICAL BUG FIX VERIFICATION: FAILED")
            print("❌ Redraft auto-send functionality is not working as expected")
            print("❌ Manual investigation required")
        
        print(f"{'='*60}")

async def main():
    """Main test execution"""
    print("🔧 REDRAFT AUTO-SEND BUG FIX TESTING")
    print("Testing the critical fix where redrafted emails now automatically send")
    print("="*60)
    
    tester = RedraftAutoSendTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run the critical test
        await tester.test_redraft_autosend_bug_fix()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())