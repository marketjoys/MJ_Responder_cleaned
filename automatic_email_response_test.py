#!/usr/bin/env python3
"""
Automatic Email Response System Testing
Focus on testing the ACTUAL automatic email response system for real incoming emails
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://calendar-sync-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class AutomaticEmailResponseTester:
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
    
    async def test_email_polling_service_status(self):
        """Test 1: Email Polling Service - Check if background email polling is running"""
        print("\n📡 Testing Email Polling Service Status...")
        
        try:
            # Check polling service status
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            polling_running = (response.status_code == 200 and 
                             response.json().get('status') == 'running')
            
            if polling_running:
                polling_data = response.json()
                active_connections = polling_data.get('active_connections', 0)
                details = f"Status: running, Active connections: {active_connections}"
            else:
                details = f"Status: {response.json().get('status', 'unknown') if response.status_code == 200 else 'error'}"
            
            # Get detailed account polling status
            try:
                accounts_response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                if accounts_response.status_code == 200:
                    accounts_data = accounts_response.json()
                    total_accounts = accounts_data.get('total_accounts', 0)
                    active_accounts = accounts_data.get('active_accounts', 0)
                    connected_accounts = accounts_data.get('connected_accounts', 0)
                    
                    details += f", Total accounts: {total_accounts}, Active: {active_accounts}, Connected: {connected_accounts}"
                    
                    # Check individual account status
                    accounts = accounts_data.get('accounts', [])
                    auto_send_accounts = [acc for acc in accounts if acc.get('polling_active', False)]
                    
                    details += f", Auto-send enabled accounts: {len(auto_send_accounts)}"
                    
            except Exception as e:
                details += f", Account status check failed: {str(e)}"
            
            self.log_test_result("Email Polling Service Status", polling_running, details)
            
        except Exception as e:
            self.log_test_result("Email Polling Service Status", False, f"Exception: {str(e)}")
    
    async def test_email_account_configuration(self):
        """Test 2: Email Account Status - Check configured accounts with auto_send enabled"""
        print("\n📧 Testing Email Account Configuration...")
        
        try:
            # Get all email accounts
            accounts = await self.db.email_accounts.find().to_list(100)
            
            if not accounts:
                self.log_test_result("Email Account Configuration", False, "No email accounts found")
                return
            
            active_accounts = [acc for acc in accounts if acc.get('is_active', False)]
            auto_send_accounts = [acc for acc in active_accounts if acc.get('auto_send', False)]
            
            # Check account details
            account_details = []
            for acc in active_accounts:
                email = acc.get('email', 'unknown')
                auto_send = acc.get('auto_send', False)
                last_polled = acc.get('last_polled')
                last_uid = acc.get('last_uid', 0)
                
                account_details.append({
                    'email': email,
                    'auto_send': auto_send,
                    'last_polled': last_polled.isoformat() if last_polled else 'Never',
                    'last_uid': last_uid
                })
            
            # Test passed if we have at least one active account with auto_send enabled
            test_passed = len(auto_send_accounts) > 0
            
            details = f"Total: {len(accounts)}, Active: {len(active_accounts)}, Auto-send enabled: {len(auto_send_accounts)}"
            
            # Add individual account info
            for acc_detail in account_details[:3]:  # Show first 3 accounts
                details += f"\n   - {acc_detail['email']}: auto_send={acc_detail['auto_send']}, last_polled={acc_detail['last_polled']}, last_uid={acc_detail['last_uid']}"
            
            self.log_test_result("Email Account Configuration", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Account Configuration", False, f"Exception: {str(e)}")
    
    async def test_real_email_processing_pipeline(self):
        """Test 3: Real Email Processing - Check database for emails that went through full pipeline"""
        print("\n🔄 Testing Real Email Processing Pipeline...")
        
        try:
            # Get all emails from database
            all_emails = await self.db.emails.find().to_list(1000)
            
            if not all_emails:
                self.log_test_result("Real Email Processing Pipeline", False, "No emails found in database")
                return
            
            # Filter out test emails to focus on real emails
            real_emails = [email for email in all_emails if not email.get('message_id', '').startswith('test-')]
            
            # Analyze email status progression
            status_counts = {}
            for email in real_emails:
                status = email.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Check for emails that completed the full pipeline
            completed_statuses = ['ready_to_send', 'sent']
            completed_emails = [email for email in real_emails if email.get('status') in completed_statuses]
            
            # Check for emails that progressed through classification and drafting
            processed_emails = [email for email in real_emails if 
                              email.get('intents') and email.get('draft')]
            
            # Check for recent email activity (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_emails = [email for email in real_emails if 
                           email.get('received_at') and email.get('received_at') > recent_cutoff]
            
            # Test passes if we have evidence of real email processing
            test_passed = len(processed_emails) > 0 or len(completed_emails) > 0
            
            details = f"Total real emails: {len(real_emails)}, Processed: {len(processed_emails)}, Completed: {len(completed_emails)}, Recent (24h): {len(recent_emails)}"
            details += f"\nStatus breakdown: {status_counts}"
            
            # Show examples of processed emails
            if processed_emails:
                example_email = processed_emails[0]
                details += f"\nExample processed email: {example_email.get('subject', 'No subject')[:50]}... (Status: {example_email.get('status')}, Intents: {len(example_email.get('intents', []))}, Draft length: {len(example_email.get('draft', ''))})"
            
            self.log_test_result("Real Email Processing Pipeline", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Real Email Processing Pipeline", False, f"Exception: {str(e)}")
    
    async def test_auto_send_functionality(self):
        """Test 4: Auto-Send Functionality - Check if emails marked as ready_to_send are being sent"""
        print("\n📤 Testing Auto-Send Functionality...")
        
        try:
            # Get emails that should be auto-sent
            ready_to_send_emails = await self.db.emails.find({"status": "ready_to_send"}).to_list(100)
            sent_emails = await self.db.emails.find({"status": "sent"}).to_list(100)
            
            # Check for emails that have been automatically sent
            auto_sent_emails = [email for email in sent_emails if 
                              email.get('sent_at') and not email.get('manual_override', False)]
            
            # Check for emails stuck in ready_to_send status
            stuck_emails = []
            for email in ready_to_send_emails:
                # Check if email has been in ready_to_send status for more than 5 minutes
                processed_at = email.get('processed_at')
                if processed_at and (datetime.utcnow() - processed_at).total_seconds() > 300:
                    stuck_emails.append(email)
            
            # Get email accounts with auto_send enabled
            auto_send_accounts = await self.db.email_accounts.find({"auto_send": True, "is_active": True}).to_list(100)
            
            # Test passes if we have evidence of auto-sending or no emails are stuck
            test_passed = len(auto_sent_emails) > 0 or (len(ready_to_send_emails) == 0 and len(auto_send_accounts) > 0)
            
            details = f"Ready to send: {len(ready_to_send_emails)}, Auto-sent: {len(auto_sent_emails)}, Stuck: {len(stuck_emails)}, Auto-send accounts: {len(auto_send_accounts)}"
            
            # Show examples
            if auto_sent_emails:
                example = auto_sent_emails[0]
                sent_time = example.get('sent_at')
                details += f"\nExample auto-sent: {example.get('subject', 'No subject')[:50]}... (Sent: {sent_time.isoformat() if sent_time else 'Unknown'})"
            
            if stuck_emails:
                example = stuck_emails[0]
                processed_time = example.get('processed_at')
                details += f"\nExample stuck: {example.get('subject', 'No subject')[:50]}... (Processed: {processed_time.isoformat() if processed_time else 'Unknown'})"
            
            self.log_test_result("Auto-Send Functionality", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Auto-Send Functionality", False, f"Exception: {str(e)}")
    
    async def test_email_monitoring_recent_activity(self):
        """Test 5: Email Monitoring - Check for recent email activity and processing"""
        print("\n📊 Testing Email Monitoring - Recent Activity...")
        
        try:
            # Check for recent email activity (last 7 days)
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            
            # Get recent emails
            recent_emails = await self.db.emails.find({
                "received_at": {"$gte": recent_cutoff}
            }).to_list(1000)
            
            # Get recent email account polling activity
            recently_polled_accounts = await self.db.email_accounts.find({
                "last_polled": {"$gte": recent_cutoff}
            }).to_list(100)
            
            # Analyze recent activity patterns
            daily_activity = {}
            for email in recent_emails:
                received_date = email.get('received_at')
                if received_date:
                    date_key = received_date.strftime('%Y-%m-%d')
                    daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
            
            # Check processing success rate for recent emails
            processed_recent = [email for email in recent_emails if 
                              email.get('status') not in ['new', 'error']]
            
            success_rate = (len(processed_recent) / len(recent_emails) * 100) if recent_emails else 0
            
            # Test passes if we have recent activity and good processing rate
            test_passed = len(recent_emails) > 0 and success_rate > 50
            
            details = f"Recent emails (7d): {len(recent_emails)}, Processed: {len(processed_recent)}, Success rate: {success_rate:.1f}%, Recently polled accounts: {len(recently_polled_accounts)}"
            
            # Show daily activity
            if daily_activity:
                details += f"\nDaily activity: {dict(sorted(daily_activity.items())[-3:])}"  # Last 3 days
            
            self.log_test_result("Email Monitoring - Recent Activity", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Monitoring - Recent Activity", False, f"Exception: {str(e)}")
    
    async def test_service_health_background_tasks(self):
        """Test 6: Service Health - Check if background tasks/polling services are running properly"""
        print("\n🏥 Testing Service Health - Background Tasks...")
        
        try:
            # Test polling service control endpoints
            try:
                status_response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                polling_status_ok = status_response.status_code == 200
                
                if polling_status_ok:
                    status_data = status_response.json()
                    service_running = status_data.get('status') == 'running'
                    active_connections = status_data.get('active_connections', 0)
                else:
                    service_running = False
                    active_connections = 0
            except Exception as e:
                polling_status_ok = False
                service_running = False
                active_connections = 0
            
            # Test individual account polling control
            try:
                accounts_status_response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                accounts_status_ok = accounts_status_response.status_code == 200
                
                if accounts_status_ok:
                    accounts_data = accounts_status_response.json()
                    polling_service_running = accounts_data.get('polling_service_running', False)
                    connected_accounts = accounts_data.get('connected_accounts', 0)
                else:
                    polling_service_running = False
                    connected_accounts = 0
            except Exception as e:
                accounts_status_ok = False
                polling_service_running = False
                connected_accounts = 0
            
            # Check for any error patterns in recent emails
            error_emails = await self.db.emails.find({"status": "error"}).to_list(100)
            recent_errors = [email for email in error_emails if 
                           email.get('created_at') and 
                           (datetime.utcnow() - email.get('created_at')).total_seconds() < 86400]  # Last 24 hours
            
            # Test passes if services are healthy
            test_passed = (polling_status_ok and service_running and 
                          accounts_status_ok and len(recent_errors) < 10)
            
            details = f"Polling status OK: {polling_status_ok}, Service running: {service_running}, Active connections: {active_connections}, Connected accounts: {connected_accounts}, Recent errors: {len(recent_errors)}"
            
            # Show error examples if any
            if recent_errors:
                example_error = recent_errors[0]
                error_msg = example_error.get('error', 'Unknown error')
                details += f"\nExample recent error: {error_msg[:100]}..."
            
            self.log_test_result("Service Health - Background Tasks", test_passed, details)
            
        except Exception as e:
            self.log_test_result("Service Health - Background Tasks", False, f"Exception: {str(e)}")
    
    async def test_end_to_end_automatic_workflow(self):
        """Test 7: End-to-End Automatic Workflow - Test the complete automatic email processing"""
        print("\n🔄 Testing End-to-End Automatic Workflow...")
        
        try:
            # Get a sample of emails that went through the complete workflow
            complete_workflow_emails = await self.db.emails.find({
                "$and": [
                    {"intents": {"$exists": True, "$ne": []}},
                    {"draft": {"$exists": True, "$ne": ""}},
                    {"validation_result": {"$exists": True}},
                    {"status": {"$in": ["ready_to_send", "sent"]}}
                ]
            }).to_list(50)
            
            # Analyze workflow completion times
            workflow_times = []
            for email in complete_workflow_emails:
                received_at = email.get('received_at')
                processed_at = email.get('processed_at')
                if received_at and processed_at:
                    processing_time = (processed_at - received_at).total_seconds()
                    workflow_times.append(processing_time)
            
            # Check for emails that completed within reasonable time (< 5 minutes)
            fast_processed = [t for t in workflow_times if t < 300]
            
            # Get emails by account to check auto-send configuration
            account_workflow_stats = {}
            for email in complete_workflow_emails:
                account_id = email.get('account_id')
                if account_id:
                    if account_id not in account_workflow_stats:
                        account_workflow_stats[account_id] = {'total': 0, 'sent': 0}
                    account_workflow_stats[account_id]['total'] += 1
                    if email.get('status') == 'sent':
                        account_workflow_stats[account_id]['sent'] += 1
            
            # Test passes if we have evidence of complete automatic workflow
            test_passed = len(complete_workflow_emails) > 0 and len(fast_processed) > 0
            
            avg_processing_time = sum(workflow_times) / len(workflow_times) if workflow_times else 0
            
            details = f"Complete workflows: {len(complete_workflow_emails)}, Avg processing time: {avg_processing_time:.1f}s, Fast processed (<5min): {len(fast_processed)}, Accounts with workflow: {len(account_workflow_stats)}"
            
            # Show account statistics
            for account_id, stats in list(account_workflow_stats.items())[:3]:
                send_rate = (stats['sent'] / stats['total'] * 100) if stats['total'] > 0 else 0
                details += f"\n   Account {account_id[:8]}...: {stats['total']} processed, {stats['sent']} sent ({send_rate:.1f}%)"
            
            self.log_test_result("End-to-End Automatic Workflow", test_passed, details)
            
        except Exception as e:
            self.log_test_result("End-to-End Automatic Workflow", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🤖 AUTOMATIC EMAIL RESPONSE SYSTEM TEST SUMMARY")
        print("="*80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📊 Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            print("\n❌ FAILED TESTS (Issues requiring attention):")
            for test in failed_tests:
                print(f"  - {test['test']}")
                print(f"    Details: {test['details']}")
                print()
        
        if passed_tests:
            print("\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"  - {test['test']}")
        
        print("\n" + "="*80)
        
        # Overall assessment
        critical_tests = [
            "Email Polling Service Status",
            "Email Account Configuration", 
            "Real Email Processing Pipeline",
            "Auto-Send Functionality"
        ]
        
        critical_passed = [t for t in passed_tests if t['test'] in critical_tests]
        critical_failed = [t for t in failed_tests if t['test'] in critical_tests]
        
        print(f"\n🎯 CRITICAL FUNCTIONALITY ASSESSMENT:")
        print(f"Critical tests passed: {len(critical_passed)}/{len(critical_tests)}")
        
        if len(critical_failed) == 0:
            print("✅ All critical automatic email response functionality is working")
        else:
            print("❌ Critical issues found in automatic email response system:")
            for test in critical_failed:
                print(f"   - {test['test']}")

async def main():
    """Main test execution"""
    print("🚀 Starting Automatic Email Response System Testing...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    print("Focus: Testing ACTUAL automatic email processing for real incoming emails")
    print("="*80)
    
    tester = AutomaticEmailResponseTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Run comprehensive tests for automatic email response system
        await tester.test_email_polling_service_status()
        await tester.test_email_account_configuration()
        await tester.test_real_email_processing_pipeline()
        await tester.test_auto_send_functionality()
        await tester.test_email_monitoring_recent_activity()
        await tester.test_service_health_background_tasks()
        await tester.test_end_to_end_automatic_workflow()
        
        # Print comprehensive summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Critical error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())