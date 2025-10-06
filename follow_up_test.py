#!/usr/bin/env python3
"""
Follow-up Email System Testing - Focus on Draft Agent & Validation Integration
Tests the updated follow-up email system with comprehensive validation integration
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://user-privacy-guard.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FollowUpSystemTester:
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
            await self.setup_authentication()
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
    
    async def test_follow_up_draft_generation(self):
        """Test 1: Follow-up Draft Generation - Uses generate_follow_up_draft() function"""
        print("\n🎯 Testing Follow-up Draft Generation...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Follow-up Draft Generation", False, "No active email accounts")
                return
            
            # Create test original email
            original_email = {
                "id": str(uuid.uuid4()),
                "account_id": account['id'],
                "message_id": f"<test-original-{uuid.uuid4()}@example.com>",
                "thread_id": f"thread-{uuid.uuid4()}",
                "subject": "Product Inquiry - Need Pricing Information",
                "sender": "customer@techcompany.com",
                "recipient": account['email'],
                "body": "Hi, I'm interested in your AI email assistant product. Could you please send me detailed pricing information and schedule a demo? We're looking to automate our customer support emails.",
                "received_at": datetime.utcnow(),
                "status": "sent",
                "intents": [
                    {
                        "intent_id": "sales_inquiry",
                        "name": "Sales Inquiry",
                        "confidence": 0.85
                    }
                ]
            }
            
            # Store original email
            await self.db.emails.insert_one(original_email)
            
            # Test direct function call
            try:
                from server import generate_follow_up_draft
                
                # Test follow-up draft generation
                draft_result = await generate_follow_up_draft(original_email, 1, account)
                
                # Verify draft structure
                has_plain_text = bool(draft_result.get('plain_text'))
                has_html = bool(draft_result.get('html'))
                has_reasoning = bool(draft_result.get('reasoning'))
                
                # Check content quality
                plain_text = draft_result.get('plain_text', '')
                contains_salutation = any(greeting in plain_text.lower() for greeting in ['dear', 'hello', 'hi'])
                has_follow_up_context = 'follow' in plain_text.lower() or 'previous' in plain_text.lower()
                reasonable_length = 50 < len(plain_text) < 500
                
                # Check if it uses same AI pipeline as regular emails
                uses_ai_pipeline = has_reasoning and len(plain_text) > 0
                
                draft_generation_passed = (has_plain_text and has_html and contains_salutation and 
                                         reasonable_length and uses_ai_pipeline)
                
                details = f"Plain text: {len(plain_text)} chars, HTML: {bool(has_html)}, " \
                         f"Salutation: {contains_salutation}, Follow-up context: {has_follow_up_context}, " \
                         f"AI pipeline: {uses_ai_pipeline}"
                
                self.log_test_result("Follow-up Draft Generation", draft_generation_passed, details)
                
                # Test follow-up intents creation
                if draft_result.get('intents'):
                    intents_created = len(draft_result['intents']) > 0
                    follow_up_intent = any('follow' in intent.get('name', '').lower() for intent in draft_result['intents'])
                    
                    self.log_test_result("Follow-up Intent Creation", intents_created, 
                                       f"Intents created: {len(draft_result.get('intents', []))}, Follow-up specific: {follow_up_intent}")
                
                # Test persona consistency
                if account.get('persona'):
                    persona_maintained = account['persona'].lower() in draft_result.get('reasoning', '').lower()
                    self.log_test_result("Follow-up Persona Consistency", persona_maintained, 
                                       f"Persona maintained in follow-up: {persona_maintained}")
                
            except Exception as e:
                self.log_test_result("Follow-up Draft Generation", False, f"Function call failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Follow-up Draft Generation", False, f"Exception: {str(e)}")
    
    async def test_follow_up_validation_process(self):
        """Test 2: Follow-up Validation Process - Uses validate_follow_up_email() function"""
        print("\n🔍 Testing Follow-up Validation Process...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Follow-up Validation Process", False, "No active email accounts")
                return
            
            # Create test follow-up email record
            follow_up = {
                "id": str(uuid.uuid4()),
                "original_email_id": str(uuid.uuid4()),
                "account_id": account['id'],
                "user_id": "test-user",
                "thread_id": f"thread-{uuid.uuid4()}",
                "recipient_email": "customer@techcompany.com",
                "subject": "Follow-up: Product Inquiry - Need Pricing Information",
                "status": "pending",
                "follow_up_number": 1,
                "scheduled_time": datetime.utcnow() + timedelta(hours=24),
                "draft_content": "Dear Customer,\n\nI wanted to follow up on your inquiry about our AI email assistant product. Have you had a chance to review the information I sent earlier?\n\nI'd be happy to schedule a demo at your convenience to show you how our solution can help automate your customer support emails.\n\nPlease let me know if you have any questions or would like to proceed with the demo.",
                "draft_html": "<p>Dear Customer,</p><p>I wanted to follow up on your inquiry about our AI email assistant product. Have you had a chance to review the information I sent earlier?</p><p>I'd be happy to schedule a demo at your convenience to show you how our solution can help automate your customer support emails.</p><p>Please let me know if you have any questions or would like to proceed with the demo.</p>",
                "validation_status": "pending",
                "created_at": datetime.utcnow()
            }
            
            # Store follow-up
            await self.db.follow_up_emails.insert_one(follow_up)
            
            # Test validation function
            try:
                from server import validate_follow_up_email
                
                validation_result = await validate_follow_up_email(follow_up, account)
                
                # Check validation structure
                has_status = 'status' in validation_result
                has_feedback = 'feedback' in validation_result
                has_final_content = 'final_content' in validation_result
                has_final_html = 'final_html' in validation_result
                
                # Check if validation uses same validate_final_email function
                uses_same_validation = (has_final_content and has_final_html and 
                                      validation_result.get('status') in ['PASS', 'FAIL', 'NEEDS_IMPROVEMENT'])
                
                # Check signature handling
                final_content = validation_result.get('final_content', '')
                final_html = validation_result.get('final_html', '')
                
                signature_in_content = account.get('signature', '') in final_content if account.get('signature') else True
                signature_in_html = account.get('signature', '') in final_html if account.get('signature') else True
                
                # Check for double signatures (should not happen)
                signature_count_content = final_content.count(account.get('signature', '')) if account.get('signature') else 0
                signature_count_html = final_html.count(account.get('signature', '')) if account.get('signature') else 0
                no_double_signatures = signature_count_content <= 1 and signature_count_html <= 1
                
                # Check salutation validation
                has_proper_salutation = any(greeting in final_content.lower() for greeting in ['dear', 'hello', 'hi'])
                
                validation_passed = (has_status and has_feedback and uses_same_validation and 
                                   signature_in_content and signature_in_html and no_double_signatures and
                                   has_proper_salutation)
                
                details = f"Status: {validation_result.get('status')}, Uses same validation: {uses_same_validation}, " \
                         f"Signature added: {signature_in_content}, No double signatures: {no_double_signatures}, " \
                         f"Proper salutation: {has_proper_salutation}"
                
                self.log_test_result("Follow-up Validation Process", validation_passed, details)
                
                # Test validation result storage
                if validation_result:
                    # Update follow-up with validation results
                    await self.db.follow_up_emails.update_one(
                        {"id": follow_up['id']},
                        {"$set": {
                            "final_content": validation_result.get('final_content', ''),
                            "final_html": validation_result.get('final_html', ''),
                            "validation_result": validation_result,
                            "validation_status": "validated"
                        }}
                    )
                    
                    # Verify storage
                    updated_follow_up = await self.db.follow_up_emails.find_one({"id": follow_up['id']})
                    storage_passed = (updated_follow_up.get('validation_status') == 'validated' and
                                    bool(updated_follow_up.get('final_content')) and
                                    bool(updated_follow_up.get('validation_result')))
                    
                    self.log_test_result("Follow-up Validation Storage", storage_passed, 
                                       f"Validation results stored: {storage_passed}")
                
            except Exception as e:
                self.log_test_result("Follow-up Validation Process", False, f"Function call failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Follow-up Validation Process", False, f"Exception: {str(e)}")
    
    async def test_follow_up_sending_process(self):
        """Test 3: Follow-up Sending Process - Tests process_scheduled_follow_ups() and manual send"""
        print("\n📤 Testing Follow-up Sending Process...")
        
        try:
            # Get active account
            account = await self.db.email_accounts.find_one({"is_active": True})
            if not account:
                self.log_test_result("Follow-up Sending Process", False, "No active email accounts")
                return
            
            # Create test follow-up ready for sending
            follow_up_id = str(uuid.uuid4())
            follow_up = {
                "id": follow_up_id,
                "original_email_id": str(uuid.uuid4()),
                "account_id": account['id'],
                "user_id": "test-user",
                "thread_id": f"thread-{uuid.uuid4()}",
                "recipient_email": "customer@techcompany.com",
                "subject": "Follow-up: Product Inquiry - Need Pricing Information",
                "status": "scheduled",
                "follow_up_number": 1,
                "scheduled_time": datetime.utcnow() - timedelta(minutes=5),  # Past due for sending
                "draft_content": "Dear Customer,\n\nI wanted to follow up on your inquiry about our AI email assistant product.",
                "draft_html": "<p>Dear Customer,</p><p>I wanted to follow up on your inquiry about our AI email assistant product.</p>",
                "final_content": "",
                "final_html": "",
                "validation_status": "pending",
                "created_at": datetime.utcnow()
            }
            
            # Store follow-up
            await self.db.follow_up_emails.insert_one(follow_up)
            
            # Test 3a: Scheduled follow-up processing
            try:
                from server import process_scheduled_follow_ups
                
                # Run scheduled follow-up processing
                await process_scheduled_follow_ups()
                
                # Check if follow-up was processed
                processed_follow_up = await self.db.follow_up_emails.find_one({"id": follow_up_id})
                
                # Should have validation results after processing
                has_validation = bool(processed_follow_up.get('validation_result'))
                has_final_content = bool(processed_follow_up.get('final_content'))
                validation_before_send = processed_follow_up.get('validation_status') in ['validated', 'failed']
                
                scheduled_processing_passed = has_validation and has_final_content and validation_before_send
                
                details = f"Validation performed: {has_validation}, Final content: {has_final_content}, " \
                         f"Validation status: {processed_follow_up.get('validation_status')}"
                
                self.log_test_result("Scheduled Follow-up Processing", scheduled_processing_passed, details)
                
            except Exception as e:
                self.log_test_result("Scheduled Follow-up Processing", False, f"Function call failed: {str(e)}")
            
            # Test 3b: Manual send follow-up endpoint
            try:
                # Create another follow-up for manual sending
                manual_follow_up_id = str(uuid.uuid4())
                manual_follow_up = {
                    "id": manual_follow_up_id,
                    "original_email_id": str(uuid.uuid4()),
                    "account_id": account['id'],
                    "user_id": "test-user",
                    "thread_id": f"thread-{uuid.uuid4()}",
                    "recipient_email": "manual@techcompany.com",
                    "subject": "Manual Follow-up: Product Inquiry",
                    "status": "pending",
                    "follow_up_number": 1,
                    "scheduled_time": datetime.utcnow() + timedelta(hours=1),
                    "draft_content": "Dear Customer,\n\nThis is a manual follow-up test.",
                    "draft_html": "<p>Dear Customer,</p><p>This is a manual follow-up test.</p>",
                    "validation_status": "pending",
                    "created_at": datetime.utcnow()
                }
                
                await self.db.follow_up_emails.insert_one(manual_follow_up)
                
                # Test manual send endpoint
                response = requests.post(f"{API_BASE}/follow-ups/{manual_follow_up_id}/send", timeout=30)
                
                manual_send_passed = response.status_code in [200, 201]
                
                if manual_send_passed:
                    # Check if validation was performed
                    sent_follow_up = await self.db.follow_up_emails.find_one({"id": manual_follow_up_id})
                    
                    validation_performed = bool(sent_follow_up.get('validation_result'))
                    has_final_content = bool(sent_follow_up.get('final_content'))
                    signature_included = sent_follow_up.get('validation_status') == 'validated'
                    
                    manual_details = f"Status: {response.status_code}, Validation: {validation_performed}, " \
                                   f"Final content: {has_final_content}, Signature handling: {signature_included}"
                else:
                    manual_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
                
                self.log_test_result("Manual Send Follow-up", manual_send_passed, manual_details)
                
            except Exception as e:
                self.log_test_result("Manual Send Follow-up", False, f"Endpoint test failed: {str(e)}")
            
            # Test 3c: Thread continuity
            try:
                # Check if follow-ups maintain proper threading
                follow_ups = await self.db.follow_up_emails.find({"thread_id": {"$exists": True}}).to_list(10)
                
                thread_continuity_passed = True
                if follow_ups:
                    for fu in follow_ups:
                        # Check if thread_id is properly set
                        has_thread_id = bool(fu.get('thread_id'))
                        # Check if references would be set (this would be in the actual email sending)
                        has_original_ref = bool(fu.get('original_email_id'))
                        
                        if not (has_thread_id and has_original_ref):
                            thread_continuity_passed = False
                            break
                
                thread_details = f"Follow-ups with proper threading: {len([fu for fu in follow_ups if fu.get('thread_id')])}/{len(follow_ups)}"
                
                self.log_test_result("Thread Continuity", thread_continuity_passed, thread_details)
                
            except Exception as e:
                self.log_test_result("Thread Continuity", False, f"Thread check failed: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Follow-up Sending Process", False, f"Exception: {str(e)}")
    
    async def test_database_integration(self):
        """Test 4: Database Integration - Validation fields and status tracking"""
        print("\n🗄️ Testing Database Integration...")
        
        try:
            # Test follow-up model with new validation fields
            follow_up_data = {
                "id": str(uuid.uuid4()),
                "original_email_id": str(uuid.uuid4()),
                "account_id": str(uuid.uuid4()),
                "user_id": "test-user",
                "thread_id": f"thread-{uuid.uuid4()}",
                "recipient_email": "test@example.com",
                "subject": "Test Follow-up",
                "status": "pending",
                "follow_up_number": 1,
                "scheduled_time": datetime.utcnow() + timedelta(hours=24),
                "draft_content": "Test draft content",
                "draft_html": "<p>Test draft content</p>",
                # New validation fields
                "final_content": "Test final content with signature",
                "final_html": "<p>Test final content with signature</p>",
                "validation_result": {
                    "status": "PASS",
                    "feedback": "Email looks good",
                    "coverage_report": "All requirements met"
                },
                "validation_status": "validated",
                "intents": [
                    {
                        "intent_id": "follow_up",
                        "name": "Follow-up Intent",
                        "confidence": 0.9
                    }
                ],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Test insertion
            try:
                await self.db.follow_up_emails.insert_one(follow_up_data)
                insertion_passed = True
                insertion_details = "Follow-up record inserted successfully"
            except Exception as e:
                insertion_passed = False
                insertion_details = f"Insertion failed: {str(e)}"
            
            # Test retrieval and field verification
            try:
                retrieved = await self.db.follow_up_emails.find_one({"id": follow_up_data["id"]})
                
                if retrieved:
                    # Check all new validation fields are present
                    has_final_content = 'final_content' in retrieved
                    has_final_html = 'final_html' in retrieved
                    has_validation_result = 'validation_result' in retrieved
                    has_validation_status = 'validation_status' in retrieved
                    has_intents = 'intents' in retrieved
                    
                    # Check validation result structure
                    validation_result = retrieved.get('validation_result', {})
                    validation_structure_ok = ('status' in validation_result and 
                                             'feedback' in validation_result)
                    
                    retrieval_passed = (has_final_content and has_final_html and 
                                      has_validation_result and has_validation_status and 
                                      has_intents and validation_structure_ok)
                    
                    retrieval_details = f"All validation fields present: {retrieval_passed}, " \
                                      f"Validation structure: {validation_structure_ok}"
                else:
                    retrieval_passed = False
                    retrieval_details = "Record not found after insertion"
                    
            except Exception as e:
                retrieval_passed = False
                retrieval_details = f"Retrieval failed: {str(e)}"
            
            # Test status tracking updates
            try:
                # Update validation status
                await self.db.follow_up_emails.update_one(
                    {"id": follow_up_data["id"]},
                    {"$set": {
                        "validation_status": "failed",
                        "validation_result": {
                            "status": "FAIL",
                            "feedback": "Needs improvement",
                            "issues": ["Missing salutation", "Too long"]
                        },
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                # Verify update
                updated = await self.db.follow_up_emails.find_one({"id": follow_up_data["id"]})
                
                status_update_passed = (updated.get('validation_status') == 'failed' and
                                      updated.get('validation_result', {}).get('status') == 'FAIL')
                
                status_details = f"Status updated correctly: {status_update_passed}"
                
            except Exception as e:
                status_update_passed = False
                status_details = f"Status update failed: {str(e)}"
            
            # Test querying by validation status
            try:
                validated_follow_ups = await self.db.follow_up_emails.find({
                    "validation_status": "validated"
                }).to_list(10)
                
                failed_follow_ups = await self.db.follow_up_emails.find({
                    "validation_status": "failed"
                }).to_list(10)
                
                query_passed = True  # If no errors, queries work
                query_details = f"Validated: {len(validated_follow_ups)}, Failed: {len(failed_follow_ups)}"
                
            except Exception as e:
                query_passed = False
                query_details = f"Query failed: {str(e)}"
            
            # Overall database integration assessment
            db_integration_passed = (insertion_passed and retrieval_passed and 
                                   status_update_passed and query_passed)
            
            # Log individual results
            self.log_test_result("Database - Follow-up Insertion", insertion_passed, insertion_details)
            self.log_test_result("Database - Field Retrieval", retrieval_passed, retrieval_details)
            self.log_test_result("Database - Status Tracking", status_update_passed, status_details)
            self.log_test_result("Database - Validation Queries", query_passed, query_details)
            
            overall_details = f"Insertion: {insertion_passed}, Retrieval: {retrieval_passed}, " \
                            f"Status tracking: {status_update_passed}, Queries: {query_passed}"
            
            self.log_test_result("Database Integration", db_integration_passed, overall_details)
            
        except Exception as e:
            self.log_test_result("Database Integration", False, f"Exception: {str(e)}")
    
    async def test_error_handling(self):
        """Test 5: Error Handling - Validation failures and error messages"""
        print("\n⚠️ Testing Error Handling...")
        
        try:
            # Test validation failure handling
            try:
                from server import validate_follow_up_email
                
                # Create follow-up with problematic content
                problematic_follow_up = {
                    "id": str(uuid.uuid4()),
                    "draft_content": "",  # Empty content should fail validation
                    "draft_html": "",
                    "recipient_email": "test@example.com",
                    "subject": "Test",
                    "validation_status": "pending"
                }
                
                account = await self.db.email_accounts.find_one({"is_active": True})
                if account:
                    validation_result = await validate_follow_up_email(problematic_follow_up, account)
                    
                    # Should handle empty content gracefully
                    handles_empty_content = validation_result.get('status') in ['FAIL', 'NEEDS_IMPROVEMENT']
                    has_error_feedback = bool(validation_result.get('feedback'))
                    
                    validation_error_handling = handles_empty_content and has_error_feedback
                    
                    validation_details = f"Handles empty content: {handles_empty_content}, " \
                                       f"Provides feedback: {has_error_feedback}, " \
                                       f"Status: {validation_result.get('status')}"
                else:
                    validation_error_handling = False
                    validation_details = "No account available for testing"
                
            except Exception as e:
                validation_error_handling = False
                validation_details = f"Validation error handling failed: {str(e)}"
            
            # Test manual send error handling
            try:
                # Try to send non-existent follow-up
                response = requests.post(f"{API_BASE}/follow-ups/non-existent-id/send", timeout=10)
                
                handles_missing_follow_up = response.status_code == 404
                missing_details = f"Status: {response.status_code}"
                
            except Exception as e:
                handles_missing_follow_up = False
                missing_details = f"Error: {str(e)}"
            
            # Test validation failure prevention of sending
            try:
                # Create follow-up that will fail validation
                failing_follow_up_id = str(uuid.uuid4())
                failing_follow_up = {
                    "id": failing_follow_up_id,
                    "original_email_id": str(uuid.uuid4()),
                    "account_id": str(uuid.uuid4()),
                    "user_id": "test-user",
                    "thread_id": f"thread-{uuid.uuid4()}",
                    "recipient_email": "test@example.com",
                    "subject": "Test Follow-up",
                    "status": "pending",
                    "follow_up_number": 1,
                    "scheduled_time": datetime.utcnow(),
                    "draft_content": "x",  # Too short, should fail validation
                    "draft_html": "<p>x</p>",
                    "validation_status": "pending",
                    "created_at": datetime.utcnow()
                }
                
                await self.db.follow_up_emails.insert_one(failing_follow_up)
                
                # Try to send it
                response = requests.post(f"{API_BASE}/follow-ups/{failing_follow_up_id}/send", timeout=15)
                
                # Should either fail or handle validation failure gracefully
                prevents_bad_send = response.status_code in [400, 422, 500]  # Various error codes acceptable
                
                prevention_details = f"Status: {response.status_code}, Prevents bad send: {prevents_bad_send}"
                
            except Exception as e:
                prevents_bad_send = False
                prevention_details = f"Error: {str(e)}"
            
            # Overall error handling assessment
            error_handling_passed = (validation_error_handling and handles_missing_follow_up and 
                                   prevents_bad_send)
            
            # Log individual results
            self.log_test_result("Error Handling - Validation Failures", validation_error_handling, validation_details)
            self.log_test_result("Error Handling - Missing Follow-up", handles_missing_follow_up, missing_details)
            self.log_test_result("Error Handling - Prevents Bad Send", prevents_bad_send, prevention_details)
            
            overall_details = f"Validation errors: {validation_error_handling}, " \
                            f"Missing follow-up: {handles_missing_follow_up}, " \
                            f"Prevents bad send: {prevents_bad_send}"
            
            self.log_test_result("Error Handling", error_handling_passed, overall_details)
            
        except Exception as e:
            self.log_test_result("Error Handling", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("FOLLOW-UP SYSTEM TEST SUMMARY")
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
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"  - {test['test']}")
        
        return len(failed_tests) == 0

async def main():
    """Main test execution"""
    print("🧪 Starting Follow-up Email System Testing...")
    print("Focus: Draft Agent & Validation Integration")
    print("="*80)
    
    tester = FollowUpSystemTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, exiting...")
        return False
    
    try:
        # Run all tests
        await tester.test_follow_up_draft_generation()
        await tester.test_follow_up_validation_process()
        await tester.test_follow_up_sending_process()
        await tester.test_database_integration()
        await tester.test_error_handling()
        
        # Print summary
        success = tester.print_summary()
        
        return success
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)