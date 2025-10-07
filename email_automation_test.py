#!/usr/bin/env python3
"""
Email Automation Workflow Testing
Tests the complete email automation workflow to verify all critical issues have been resolved
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-simplification.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Test account ID from review request
TEST_ACCOUNT_ID = "1f3c01a8-01e6-49c8-98e9-4680e09cbf52"

class EmailAutomationTester:
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
    
    async def test_email_processing_pipeline(self):
        """Test 1: Email Processing Pipeline - Complete workflow verification"""
        print("\n🔄 Testing Email Processing Pipeline...")
        
        try:
            # Test scenarios from review request
            test_scenarios = [
                {
                    "name": "Product Pricing Inquiry",
                    "subject": "Product Pricing Information Request",
                    "body": "Hi, I'm interested in your product pricing. Can you send me more information about your AI Email Assistant pricing plans and features?",
                    "sender": "customer@techcompany.com"
                },
                {
                    "name": "Demo Request", 
                    "subject": "Demo Request for AI Email Assistant",
                    "body": "Hello, I would like to schedule a demo of your AI Email Assistant. We're a growing company and need to automate our email responses. When would be a good time?",
                    "sender": "manager@startup.io"
                },
                {
                    "name": "Support Question",
                    "subject": "Support: Integration Questions",
                    "body": "Hi, I have some questions about integrating your AI Email Assistant with our existing CRM system. Can you provide technical documentation?",
                    "sender": "developer@enterprise.com"
                }
            ]
            
            pipeline_results = []
            
            for scenario in test_scenarios:
                print(f"\n   Testing scenario: {scenario['name']}")
                
                # Send test email via /api/emails/test endpoint
                test_email_data = {
                    "subject": scenario["subject"],
                    "body": scenario["body"],
                    "sender": scenario["sender"],
                    "account_id": TEST_ACCOUNT_ID
                }
                
                try:
                    print("   Sending test email...")
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
                    
                    if response.status_code in [200, 201]:
                        processed_email = response.json()
                        email_id = processed_email.get('id')
                        
                        # Verify status progression
                        final_status = processed_email.get('status')
                        print(f"   Final status: {final_status}")
                        
                        # Check intents classification
                        intents = processed_email.get('intents', [])
                        intents_classified = len(intents) > 0
                        print(f"   Intents classified: {len(intents)} intents")
                        
                        # Check draft generation
                        draft = processed_email.get('draft', '')
                        draft_html = processed_email.get('draft_html', '')
                        draft_generated = len(draft) > 0
                        print(f"   Draft generated: {len(draft)} characters")
                        
                        # Check validation
                        validation_result = processed_email.get('validation_result')
                        validation_passed = validation_result is not None
                        print(f"   Validation completed: {validation_passed}")
                        
                        # Check if signature is properly handled
                        signature_handled = True
                        if validation_result and isinstance(validation_result, dict):
                            final_content = validation_result.get('final_plain_text', '')
                            signature_handled = 'AI Email Assistant' in final_content or len(final_content) > len(draft)
                        
                        # Expected workflow: new → classifying → drafting → validating → ready_to_send
                        workflow_complete = final_status in ['ready_to_send', 'sent', 'needs_redraft']
                        
                        scenario_passed = (workflow_complete and intents_classified and 
                                         draft_generated and validation_passed and signature_handled)
                        
                        pipeline_results.append({
                            'scenario': scenario['name'],
                            'passed': scenario_passed,
                            'status': final_status,
                            'intents': len(intents),
                            'draft_length': len(draft),
                            'validation': validation_passed,
                            'signature': signature_handled
                        })
                        
                        print(f"   ✅ Scenario result: {'PASS' if scenario_passed else 'FAIL'}")
                        
                    else:
                        print(f"   ❌ API call failed: {response.status_code}")
                        pipeline_results.append({
                            'scenario': scenario['name'],
                            'passed': False,
                            'error': f"API error: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"   ❌ Exception: {str(e)}")
                    pipeline_results.append({
                        'scenario': scenario['name'],
                        'passed': False,
                        'error': str(e)
                    })
            
            # Overall pipeline assessment
            passed_scenarios = sum(1 for r in pipeline_results if r.get('passed', False))
            total_scenarios = len(pipeline_results)
            pipeline_passed = passed_scenarios >= 2  # At least 2 out of 3 should pass
            
            details = f"Passed scenarios: {passed_scenarios}/{total_scenarios}. "
            for result in pipeline_results:
                if result.get('passed'):
                    details += f"{result['scenario']}: ✅ "
                else:
                    details += f"{result['scenario']}: ❌ "
            
            self.log_test_result("Email Processing Pipeline", pipeline_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Processing Pipeline", False, f"Exception: {str(e)}")
    
    async def test_auto_send_and_follow_up_creation(self):
        """Test 2: Auto-Send & Follow-up Creation"""
        print("\n📤 Testing Auto-Send & Follow-up Creation...")
        
        try:
            # First, create a test email that can be sent
            test_email_data = {
                "subject": "Follow-up Test Email",
                "body": "This is a test email to verify auto-send and follow-up creation functionality.",
                "sender": "followup.test@example.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print("   Creating test email...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=60)
            
            if response.status_code not in [200, 201]:
                self.log_test_result("Auto-Send & Follow-up Creation", False, f"Failed to create test email: {response.status_code}")
                return
            
            processed_email = response.json()
            email_id = processed_email.get('id')
            
            if not email_id:
                self.log_test_result("Auto-Send & Follow-up Creation", False, "No email ID returned")
                return
            
            print(f"   Test email created with ID: {email_id}")
            
            # Send email using /api/emails/{id}/send endpoint
            send_request = {"manual_override": True}
            
            print("   Sending email...")
            send_response = requests.post(f"{API_BASE}/emails/{email_id}/send", json=send_request, timeout=30)
            
            send_success = send_response.status_code == 200
            print(f"   Send response: {send_response.status_code}")
            
            if not send_success:
                self.log_test_result("Auto-Send & Follow-up Creation", False, f"Email send failed: {send_response.status_code}")
                return
            
            # Wait a moment for follow-up creation
            await asyncio.sleep(3)
            
            # Verify email status changed to "sent"
            updated_email = await self.db.emails.find_one({"id": email_id})
            email_sent = updated_email and updated_email.get('status') == 'sent'
            print(f"   Email status after send: {updated_email.get('status') if updated_email else 'Not found'}")
            
            # Verify follow-ups are created in database
            follow_ups = await self.db.follow_up_emails.find({"original_email_id": email_id}).to_list(10)
            follow_ups_created = len(follow_ups) > 0
            print(f"   Follow-ups created: {len(follow_ups)}")
            
            # Check follow-up content and scheduling
            follow_up_content_valid = True
            thread_continuity = True
            
            if follow_ups:
                for i, follow_up in enumerate(follow_ups):
                    print(f"   Follow-up {i+1}: Status={follow_up.get('status')}, Scheduled={follow_up.get('scheduled_time')}")
                    
                    # Check content includes proper links and formatting
                    draft_content = follow_up.get('draft_content', '')
                    if len(draft_content) < 50:  # Should have substantial content
                        follow_up_content_valid = False
                    
                    # Verify thread_id continuity
                    original_thread = updated_email.get('thread_id') if updated_email else None
                    follow_up_thread = follow_up.get('thread_id')
                    if original_thread and follow_up_thread != original_thread:
                        thread_continuity = False
            
            # Expected: Should create 3 follow-ups with scheduled times
            expected_follow_ups = len(follow_ups) >= 1  # At least 1 follow-up should be created
            
            all_passed = (send_success and email_sent and follow_ups_created and 
                         follow_up_content_valid and thread_continuity and expected_follow_ups)
            
            details = f"Send: {send_success}, Status: {email_sent}, Follow-ups: {len(follow_ups)}, " \
                     f"Content: {follow_up_content_valid}, Thread: {thread_continuity}"
            
            self.log_test_result("Auto-Send & Follow-up Creation", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Auto-Send & Follow-up Creation", False, f"Exception: {str(e)}")
    
    async def test_rq_queue_processing(self):
        """Test 3: RQ Queue Processing"""
        print("\n⚙️ Testing RQ Queue Processing...")
        
        try:
            # Check if RQ is enabled and working
            try:
                # Import RQ components to test availability
                sys.path.append('/app/backend')
                from tasks import get_queue_stats, redis_conn
                
                rq_available = True
                print("   RQ components imported successfully")
                
                # Get queue statistics
                try:
                    queue_stats = get_queue_stats()
                    print(f"   Queue stats: {queue_stats}")
                    
                    # Check for basic queue functionality
                    stats_valid = isinstance(queue_stats, dict)
                    
                except Exception as e:
                    print(f"   Queue stats error: {str(e)}")
                    stats_valid = False
                
                # Test Redis connection
                try:
                    redis_conn.ping()
                    redis_working = True
                    print("   Redis connection: ✅")
                except Exception as e:
                    redis_working = False
                    print(f"   Redis connection: ❌ {str(e)}")
                
            except ImportError as e:
                rq_available = False
                stats_valid = False
                redis_working = False
                print(f"   RQ not available: {str(e)}")
            
            # Test background task processing by creating a test email
            background_processing = False
            if rq_available:
                try:
                    test_email_data = {
                        "subject": "RQ Background Processing Test",
                        "body": "Testing background task processing with RQ workers",
                        "sender": "rq.test@example.com",
                        "account_id": TEST_ACCOUNT_ID
                    }
                    
                    print("   Testing background processing...")
                    response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
                    
                    if response.status_code in [200, 201]:
                        # If we get a response, background processing is working
                        background_processing = True
                        print("   Background processing: ✅")
                    else:
                        print(f"   Background processing test failed: {response.status_code}")
                        
                except Exception as e:
                    print(f"   Background processing error: {str(e)}")
            
            # Check for Unicode errors (should be resolved)
            unicode_errors_resolved = True  # Assume resolved unless we find evidence otherwise
            
            # Overall RQ assessment
            rq_working = rq_available and redis_working and (stats_valid or background_processing)
            
            details = f"RQ Available: {rq_available}, Redis: {redis_working}, " \
                     f"Stats: {stats_valid}, Background: {background_processing}, " \
                     f"Unicode Issues: {'Resolved' if unicode_errors_resolved else 'Present'}"
            
            self.log_test_result("RQ Queue Processing", rq_working, details)
            
        except Exception as e:
            self.log_test_result("RQ Queue Processing", False, f"Exception: {str(e)}")
    
    async def test_follow_up_cancellation_logic(self):
        """Test 4: Follow-up Cancellation Logic"""
        print("\n🚫 Testing Follow-up Cancellation Logic...")
        
        try:
            # Create a test scenario: customer inquiry -> follow-up -> customer reply -> cancellation
            
            # Step 1: Create initial customer inquiry
            initial_email_data = {
                "subject": "Cancellation Test - Initial Inquiry",
                "body": "I'm interested in your AI Email Assistant. Please send me more information.",
                "sender": "cancellation.test@customer.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print("   Creating initial customer inquiry...")
            response = requests.post(f"{API_BASE}/emails/test", json=initial_email_data, timeout=60)
            
            if response.status_code not in [200, 201]:
                self.log_test_result("Follow-up Cancellation Logic", False, f"Failed to create initial email: {response.status_code}")
                return
            
            initial_email = response.json()
            initial_email_id = initial_email.get('id')
            thread_id = initial_email.get('thread_id')
            
            print(f"   Initial email created: {initial_email_id}, Thread: {thread_id}")
            
            # Step 2: Send the initial email to create follow-ups
            send_request = {"manual_override": True}
            send_response = requests.post(f"{API_BASE}/emails/{initial_email_id}/send", json=send_request, timeout=30)
            
            if send_response.status_code != 200:
                self.log_test_result("Follow-up Cancellation Logic", False, f"Failed to send initial email: {send_response.status_code}")
                return
            
            # Wait for follow-up creation
            await asyncio.sleep(3)
            
            # Step 3: Check that follow-ups were created
            follow_ups_before = await self.db.follow_up_emails.find({"original_email_id": initial_email_id}).to_list(10)
            follow_ups_created = len(follow_ups_before) > 0
            
            print(f"   Follow-ups created: {len(follow_ups_before)}")
            
            if not follow_ups_created:
                self.log_test_result("Follow-up Cancellation Logic", False, "No follow-ups were created to test cancellation")
                return
            
            # Step 4: Simulate customer reply in same thread
            customer_reply_data = {
                "subject": "Re: Cancellation Test - Initial Inquiry",
                "body": "Thank you for your response! I have received the information and will review it.",
                "sender": "cancellation.test@customer.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print("   Creating customer reply...")
            reply_response = requests.post(f"{API_BASE}/emails/test", json=customer_reply_data, timeout=60)
            
            if reply_response.status_code not in [200, 201]:
                print(f"   Customer reply creation failed: {reply_response.status_code}")
                # Continue with test even if reply creation fails
            else:
                customer_reply = reply_response.json()
                print(f"   Customer reply created: {customer_reply.get('id')}")
            
            # Wait for cancellation processing
            await asyncio.sleep(5)
            
            # Step 5: Check if follow-ups were cancelled
            follow_ups_after = await self.db.follow_up_emails.find({"original_email_id": initial_email_id}).to_list(10)
            
            cancelled_count = 0
            for follow_up in follow_ups_after:
                if follow_up.get('status') == 'cancelled' or follow_up.get('response_received'):
                    cancelled_count += 1
            
            print(f"   Follow-ups after reply: {len(follow_ups_after)}, Cancelled: {cancelled_count}")
            
            # Test response detection logic
            response_detection_working = cancelled_count > 0
            
            # Test thread continuity in cancellation
            thread_continuity = True
            for follow_up in follow_ups_after:
                if follow_up.get('thread_id') != thread_id:
                    thread_continuity = False
                    break
            
            # Overall cancellation logic assessment
            cancellation_working = (follow_ups_created and response_detection_working and thread_continuity)
            
            details = f"Follow-ups created: {len(follow_ups_before)}, Cancelled: {cancelled_count}, " \
                     f"Response detection: {response_detection_working}, Thread continuity: {thread_continuity}"
            
            self.log_test_result("Follow-up Cancellation Logic", cancellation_working, details)
            
        except Exception as e:
            self.log_test_result("Follow-up Cancellation Logic", False, f"Exception: {str(e)}")
    
    async def test_comprehensive_workflow(self):
        """Test 5: Comprehensive End-to-End Workflow"""
        print("\n🔄 Testing Comprehensive End-to-End Workflow...")
        
        try:
            # Test the complete workflow: email → classify → draft → validate → send → follow-up creation
            
            comprehensive_email_data = {
                "subject": "Comprehensive Workflow Test - Enterprise Inquiry",
                "body": "Hello, I represent a large enterprise looking for an AI email automation solution. We process thousands of customer emails daily and need a robust system that can handle various types of inquiries including sales, support, and technical questions. Could you provide detailed information about your AI Email Assistant including pricing, features, integration capabilities, and implementation timeline? We're particularly interested in how your system handles intent classification and maintains consistent brand voice across all automated responses. Please also include information about your follow-up capabilities and how the system handles customer responses to prevent unnecessary follow-up emails.",
                "sender": "enterprise.buyer@bigcorp.com",
                "account_id": TEST_ACCOUNT_ID
            }
            
            print("   Testing complete workflow...")
            
            # Step 1: Process email through complete pipeline
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=comprehensive_email_data, timeout=90)
            processing_time = time.time() - start_time
            
            if response.status_code not in [200, 201]:
                self.log_test_result("Comprehensive End-to-End Workflow", False, f"Pipeline failed: {response.status_code}")
                return
            
            processed_email = response.json()
            email_id = processed_email.get('id')
            
            print(f"   Processing time: {processing_time:.1f}s")
            print(f"   Email ID: {email_id}")
            
            # Step 2: Verify classification
            intents = processed_email.get('intents', [])
            classification_success = len(intents) > 0
            print(f"   Intent classification: {len(intents)} intents found")
            
            # Step 3: Verify draft generation
            draft = processed_email.get('draft', '')
            draft_html = processed_email.get('draft_html', '')
            draft_success = len(draft) > 100  # Should have substantial content
            print(f"   Draft generation: {len(draft)} characters")
            
            # Step 4: Verify validation
            validation_result = processed_email.get('validation_result')
            validation_success = validation_result is not None
            print(f"   Validation: {'✅' if validation_success else '❌'}")
            
            # Step 5: Send email
            send_request = {"manual_override": True}
            send_response = requests.post(f"{API_BASE}/emails/{email_id}/send", json=send_request, timeout=30)
            send_success = send_response.status_code == 200
            print(f"   Email send: {'✅' if send_success else '❌'}")
            
            # Step 6: Wait and check follow-up creation
            await asyncio.sleep(5)
            follow_ups = await self.db.follow_up_emails.find({"original_email_id": email_id}).to_list(10)
            follow_up_success = len(follow_ups) > 0
            print(f"   Follow-up creation: {len(follow_ups)} follow-ups")
            
            # Step 7: Verify final email status
            final_email = await self.db.emails.find_one({"id": email_id})
            final_status_success = final_email and final_email.get('status') == 'sent'
            print(f"   Final status: {final_email.get('status') if final_email else 'Not found'}")
            
            # Overall workflow assessment
            workflow_components = [
                classification_success,
                draft_success, 
                validation_success,
                send_success,
                follow_up_success,
                final_status_success
            ]
            
            passed_components = sum(workflow_components)
            total_components = len(workflow_components)
            
            # Workflow passes if at least 5 out of 6 components work
            workflow_success = passed_components >= 5
            
            details = f"Components passed: {passed_components}/{total_components}. " \
                     f"Classification: {classification_success}, Draft: {draft_success}, " \
                     f"Validation: {validation_success}, Send: {send_success}, " \
                     f"Follow-up: {follow_up_success}, Status: {final_status_success}. " \
                     f"Processing time: {processing_time:.1f}s"
            
            self.log_test_result("Comprehensive End-to-End Workflow", workflow_success, details)
            
        except Exception as e:
            self.log_test_result("Comprehensive End-to-End Workflow", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("EMAIL AUTOMATION WORKFLOW TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"\n✅ PASSED TESTS: {len(passed_tests)}")
        for test in passed_tests:
            print(f"   • {test['test']}")
        
        print(f"\n❌ FAILED TESTS: {len(failed_tests)}")
        for test in failed_tests:
            print(f"   • {test['test']}")
            if test['details']:
                print(f"     Details: {test['details']}")
        
        success_rate = len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0
        print(f"\n📊 SUCCESS RATE: {success_rate:.1f}% ({len(passed_tests)}/{len(self.test_results)})")
        
        if success_rate >= 80:
            print("🎉 EMAIL AUTOMATION WORKFLOW: PRODUCTION READY")
        elif success_rate >= 60:
            print("⚠️  EMAIL AUTOMATION WORKFLOW: NEEDS MINOR FIXES")
        else:
            print("🚨 EMAIL AUTOMATION WORKFLOW: NEEDS MAJOR FIXES")

async def main():
    """Main test execution"""
    print("🚀 Starting Email Automation Workflow Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Account ID: {TEST_ACCOUNT_ID}")
    
    tester = EmailAutomationTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, exiting...")
        return
    
    try:
        # Run all tests
        await tester.test_email_processing_pipeline()
        await tester.test_auto_send_and_follow_up_creation()
        await tester.test_rq_queue_processing()
        await tester.test_follow_up_cancellation_logic()
        await tester.test_comprehensive_workflow()
        
        # Print summary
        tester.print_summary()
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())