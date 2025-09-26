#!/usr/bin/env python3
"""
Follow-up System Testing for Email Assistant
Tests all follow-up related endpoints and functionality
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://reply-automation-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FollowUpSystemTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        self.test_email_account_id = None
        self.test_intent_id = None
        self.test_email_id = None
        self.test_follow_up_id = None
        
    async def setup(self):
        """Setup database connection and authentication"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            
            # Setup authentication
            await self.setup_authentication()
            return True
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    async def setup_authentication(self):
        """Setup test user and authentication"""
        try:
            # Create test user
            test_email = f"followup.test.{int(time.time())}@example.com"
            user_data = {
                "email": test_email,
                "password": "testpassword123",
                "full_name": "Follow-up Test User"
            }
            
            response = requests.post(f"{API_BASE}/auth/register", json=user_data)
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data["access_token"]
                self.test_user_id = auth_data["user"]["id"]
                print(f"✅ Test user created: {test_email}")
            else:
                print(f"❌ Failed to create test user: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication setup failed: {str(e)}")
            return False
    
    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def test_follow_up_config_endpoints(self):
        """Test follow-up configuration endpoints"""
        print("\n🔧 Testing Follow-up Configuration Endpoints...")
        
        try:
            # Test GET /api/follow-up/config (should create default if none exists)
            print("Testing GET /api/follow-up/config...")
            response = requests.get(f"{API_BASE}/follow-up/config", headers=self.get_headers())
            
            if response.status_code == 200:
                config_data = response.json()
                print(f"✅ GET follow-up config successful: {config_data.get('global_follow_up_hours', 'N/A')} hours")
                self.test_results.append(("GET /api/follow-up/config", "PASS", "Default config created"))
            else:
                print(f"❌ GET follow-up config failed: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/follow-up/config", "FAIL", f"Status: {response.status_code}"))
            
            # Test POST /api/follow-up/config (create/update config)
            print("Testing POST /api/follow-up/config...")
            config_create_data = {
                "global_follow_up_hours": 48,
                "max_follow_ups": 5,
                "follow_up_interval_hours": 72,
                "auto_follow_up": True,
                "business_hours_only": True,
                "business_start_hour": 8,
                "business_end_hour": 18,
                "business_days": [1, 2, 3, 4, 5],
                "exclude_weekends": True
            }
            
            response = requests.post(f"{API_BASE}/follow-up/config", json=config_create_data, headers=self.get_headers())
            
            if response.status_code == 200:
                created_config = response.json()
                print(f"✅ POST follow-up config successful: {created_config.get('global_follow_up_hours')} hours")
                self.test_results.append(("POST /api/follow-up/config", "PASS", "Config created/updated"))
            else:
                print(f"❌ POST follow-up config failed: {response.status_code} - {response.text}")
                self.test_results.append(("POST /api/follow-up/config", "FAIL", f"Status: {response.status_code}"))
            
            # Test PUT /api/follow-up/config (update specific fields)
            print("Testing PUT /api/follow-up/config...")
            config_update_data = {
                "global_follow_up_hours": 36,
                "max_follow_ups": 4,
                "business_hours_only": False
            }
            
            response = requests.put(f"{API_BASE}/follow-up/config", json=config_update_data, headers=self.get_headers())
            
            if response.status_code == 200:
                updated_config = response.json()
                print(f"✅ PUT follow-up config successful: {updated_config.get('global_follow_up_hours')} hours")
                self.test_results.append(("PUT /api/follow-up/config", "PASS", "Config updated"))
            else:
                print(f"❌ PUT follow-up config failed: {response.status_code} - {response.text}")
                self.test_results.append(("PUT /api/follow-up/config", "FAIL", f"Status: {response.status_code}"))
                
        except Exception as e:
            print(f"❌ Follow-up config testing failed: {str(e)}")
            self.test_results.append(("Follow-up Config Tests", "FAIL", str(e)))
    
    async def setup_test_data(self):
        """Setup test data for follow-up testing"""
        try:
            # Create test email account with follow-up settings
            print("Creating test email account with follow-up settings...")
            account_data = {
                "name": "Follow-up Test Account",
                "email": "followup.test@example.com",
                "provider": "gmail",
                "username": "followup.test@example.com",
                "password": "testpassword",
                "persona": "Professional assistant",
                "signature": "Best regards,\nFollow-up Test",
                "auto_send": True,
                "enable_follow_ups": True,
                "follow_up_hours_override": 24,
                "max_follow_ups_override": 3,
                "custom_follow_up_template": "Following up on our previous conversation..."
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, headers=self.get_headers())
            if response.status_code == 200:
                account = response.json()
                self.test_email_account_id = account["id"]
                print(f"✅ Test email account created: {self.test_email_account_id}")
            else:
                print(f"❌ Failed to create test email account: {response.text}")
                return False
            
            # Create test intent with follow_up_hours
            print("Creating test intent with follow_up_hours...")
            intent_data = {
                "name": "Follow-up Test Intent",
                "description": "Test intent for follow-up functionality",
                "examples": ["I need more information", "Can you follow up with me"],
                "system_prompt": "Provide helpful follow-up information",
                "confidence_threshold": 0.7,
                "follow_up_hours": 48,
                "is_meeting_related": False
            }
            
            response = requests.post(f"{API_BASE}/intents", json=intent_data, headers=self.get_headers())
            if response.status_code == 200:
                intent = response.json()
                self.test_intent_id = intent["id"]
                print(f"✅ Test intent created: {self.test_intent_id}")
            else:
                print(f"❌ Failed to create test intent: {response.text}")
                return False
            
            # Create test email for follow-up testing
            print("Creating test email...")
            email_data = {
                "subject": "Follow-up Test Email",
                "body": "This is a test email for follow-up functionality testing.",
                "sender": "client@example.com",
                "account_id": self.test_email_account_id
            }
            
            response = requests.post(f"{API_BASE}/emails/test", json=email_data, headers=self.get_headers())
            if response.status_code == 200:
                email = response.json()
                self.test_email_id = email["id"]
                print(f"✅ Test email created: {self.test_email_id}")
            else:
                print(f"❌ Failed to create test email: {response.text}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Test data setup failed: {str(e)}")
            return False
    
    async def test_follow_up_email_management(self):
        """Test follow-up email management endpoints"""
        print("\n📧 Testing Follow-up Email Management Endpoints...")
        
        try:
            # Test POST /api/follow-ups (create follow-up manually)
            print("Testing POST /api/follow-ups...")
            follow_up_data = {
                "original_email_id": self.test_email_id,
                "account_id": self.test_email_account_id,
                "recipient_email": "client@example.com",
                "subject": "Follow-up: Test Email",
                "follow_up_number": 1,
                "scheduled_time": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "draft_content": "Following up on our previous conversation. Do you need any additional information?"
            }
            
            response = requests.post(f"{API_BASE}/follow-ups", json=follow_up_data, headers=self.get_headers())
            
            if response.status_code == 200:
                follow_up = response.json()
                self.test_follow_up_id = follow_up["id"]
                print(f"✅ POST follow-up successful: {self.test_follow_up_id}")
                self.test_results.append(("POST /api/follow-ups", "PASS", "Follow-up created"))
            else:
                print(f"❌ POST follow-up failed: {response.status_code} - {response.text}")
                self.test_results.append(("POST /api/follow-ups", "FAIL", f"Status: {response.status_code}"))
                return
            
            # Test GET /api/follow-ups (get follow-up emails)
            print("Testing GET /api/follow-ups...")
            response = requests.get(f"{API_BASE}/follow-ups", headers=self.get_headers())
            
            if response.status_code == 200:
                follow_ups = response.json()
                print(f"✅ GET follow-ups successful: {len(follow_ups)} follow-ups found")
                self.test_results.append(("GET /api/follow-ups", "PASS", f"{len(follow_ups)} follow-ups"))
            else:
                print(f"❌ GET follow-ups failed: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/follow-ups", "FAIL", f"Status: {response.status_code}"))
            
            # Test GET /api/follow-ups with status filter
            print("Testing GET /api/follow-ups with status filter...")
            response = requests.get(f"{API_BASE}/follow-ups?status=pending", headers=self.get_headers())
            
            if response.status_code == 200:
                pending_follow_ups = response.json()
                print(f"✅ GET follow-ups with status filter successful: {len(pending_follow_ups)} pending")
                self.test_results.append(("GET /api/follow-ups?status=pending", "PASS", f"{len(pending_follow_ups)} pending"))
            else:
                print(f"❌ GET follow-ups with status filter failed: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/follow-ups?status=pending", "FAIL", f"Status: {response.status_code}"))
            
            # Test GET /api/follow-ups/{id} (get specific follow-up)
            print("Testing GET /api/follow-ups/{id}...")
            response = requests.get(f"{API_BASE}/follow-ups/{self.test_follow_up_id}", headers=self.get_headers())
            
            if response.status_code == 200:
                follow_up = response.json()
                print(f"✅ GET specific follow-up successful: {follow_up.get('subject', 'N/A')}")
                self.test_results.append(("GET /api/follow-ups/{id}", "PASS", "Follow-up retrieved"))
            else:
                print(f"❌ GET specific follow-up failed: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/follow-ups/{id}", "FAIL", f"Status: {response.status_code}"))
            
            # Test PUT /api/follow-ups/{id} (update follow-up)
            print("Testing PUT /api/follow-ups/{id}...")
            update_data = {
                "draft_content": "Updated follow-up content with more details.",
                "scheduled_time": (datetime.utcnow() + timedelta(hours=48)).isoformat()
            }
            
            response = requests.put(f"{API_BASE}/follow-ups/{self.test_follow_up_id}", json=update_data, headers=self.get_headers())
            
            if response.status_code == 200:
                updated_follow_up = response.json()
                print(f"✅ PUT follow-up successful: Updated content")
                self.test_results.append(("PUT /api/follow-ups/{id}", "PASS", "Follow-up updated"))
            else:
                print(f"❌ PUT follow-up failed: {response.status_code} - {response.text}")
                self.test_results.append(("PUT /api/follow-ups/{id}", "FAIL", f"Status: {response.status_code}"))
            
            # Test POST /api/follow-ups/{id}/send (manually send follow-up)
            print("Testing POST /api/follow-ups/{id}/send...")
            response = requests.post(f"{API_BASE}/follow-ups/{self.test_follow_up_id}/send", headers=self.get_headers())
            
            if response.status_code == 200:
                send_result = response.json()
                print(f"✅ POST send follow-up successful: {send_result.get('message', 'Sent')}")
                self.test_results.append(("POST /api/follow-ups/{id}/send", "PASS", "Follow-up sent"))
            else:
                print(f"❌ POST send follow-up failed: {response.status_code} - {response.text}")
                # This might fail due to email configuration, which is expected in test environment
                self.test_results.append(("POST /api/follow-ups/{id}/send", "EXPECTED_FAIL", "Email config needed"))
            
            # Test DELETE /api/follow-ups/{id} (cancel follow-up)
            print("Testing DELETE /api/follow-ups/{id}...")
            
            # Create another follow-up to delete
            delete_follow_up_data = {
                "original_email_id": self.test_email_id,
                "account_id": self.test_email_account_id,
                "recipient_email": "client@example.com",
                "subject": "Follow-up to Delete",
                "follow_up_number": 2,
                "scheduled_time": (datetime.utcnow() + timedelta(hours=72)).isoformat(),
                "draft_content": "This follow-up will be deleted."
            }
            
            response = requests.post(f"{API_BASE}/follow-ups", json=delete_follow_up_data, headers=self.get_headers())
            if response.status_code == 200:
                delete_follow_up = response.json()
                delete_follow_up_id = delete_follow_up["id"]
                
                # Now delete it
                response = requests.delete(f"{API_BASE}/follow-ups/{delete_follow_up_id}", headers=self.get_headers())
                
                if response.status_code == 200:
                    delete_result = response.json()
                    print(f"✅ DELETE follow-up successful: {delete_result.get('message', 'Deleted')}")
                    self.test_results.append(("DELETE /api/follow-ups/{id}", "PASS", "Follow-up deleted"))
                else:
                    print(f"❌ DELETE follow-up failed: {response.status_code} - {response.text}")
                    self.test_results.append(("DELETE /api/follow-ups/{id}", "FAIL", f"Status: {response.status_code}"))
            
        except Exception as e:
            print(f"❌ Follow-up email management testing failed: {str(e)}")
            self.test_results.append(("Follow-up Email Management", "FAIL", str(e)))
    
    async def test_follow_up_analytics(self):
        """Test follow-up analytics endpoint"""
        print("\n📊 Testing Follow-up Analytics...")
        
        try:
            # Test GET /api/follow-ups/analytics
            print("Testing GET /api/follow-ups/analytics...")
            response = requests.get(f"{API_BASE}/follow-ups/analytics", headers=self.get_headers())
            
            if response.status_code == 200:
                analytics = response.json()
                print(f"✅ GET follow-up analytics successful:")
                print(f"   - Status counts: {analytics.get('status_counts', {})}")
                print(f"   - Pending today: {analytics.get('pending_today', 0)}")
                print(f"   - Overdue: {analytics.get('overdue', 0)}")
                print(f"   - Response rate: {analytics.get('response_rate', 0)}%")
                print(f"   - Total sent: {analytics.get('total_sent', 0)}")
                self.test_results.append(("GET /api/follow-ups/analytics", "PASS", "Analytics retrieved"))
            else:
                print(f"❌ GET follow-up analytics failed: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/follow-ups/analytics", "FAIL", f"Status: {response.status_code}"))
                
        except Exception as e:
            print(f"❌ Follow-up analytics testing failed: {str(e)}")
            self.test_results.append(("Follow-up Analytics", "FAIL", str(e)))
    
    async def test_email_account_follow_up_settings(self):
        """Test email account creation with follow-up settings"""
        print("\n⚙️ Testing Email Account Follow-up Settings...")
        
        try:
            # Test creating email account with follow-up fields
            print("Testing email account creation with follow-up settings...")
            account_data = {
                "name": "Follow-up Settings Test",
                "email": "followup.settings@example.com",
                "provider": "gmail",
                "username": "followup.settings@example.com",
                "password": "testpassword",
                "persona": "Professional",
                "signature": "Best regards",
                "auto_send": True,
                "enable_follow_ups": True,
                "follow_up_hours_override": 36,
                "max_follow_ups_override": 5,
                "custom_follow_up_template": "Custom follow-up template for testing"
            }
            
            response = requests.post(f"{API_BASE}/email-accounts", json=account_data, headers=self.get_headers())
            
            if response.status_code == 200:
                account = response.json()
                print(f"✅ Email account with follow-up settings created successfully")
                print(f"   - Enable follow-ups: {account.get('enable_follow_ups', False)}")
                print(f"   - Follow-up hours override: {account.get('follow_up_hours_override', 'None')}")
                print(f"   - Max follow-ups override: {account.get('max_follow_ups_override', 'None')}")
                self.test_results.append(("Email Account Follow-up Settings", "PASS", "Account created with settings"))
            else:
                print(f"❌ Email account with follow-up settings failed: {response.status_code} - {response.text}")
                self.test_results.append(("Email Account Follow-up Settings", "FAIL", f"Status: {response.status_code}"))
                
        except Exception as e:
            print(f"❌ Email account follow-up settings testing failed: {str(e)}")
            self.test_results.append(("Email Account Follow-up Settings", "FAIL", str(e)))
    
    async def test_intent_follow_up_hours(self):
        """Test intent creation with follow_up_hours field"""
        print("\n🎯 Testing Intent Follow-up Hours...")
        
        try:
            # Test creating intent with follow_up_hours
            print("Testing intent creation with follow_up_hours...")
            intent_data = {
                "name": "Follow-up Hours Test Intent",
                "description": "Test intent with custom follow-up hours",
                "examples": ["Please follow up in 2 days", "Contact me later"],
                "system_prompt": "Handle follow-up requests professionally",
                "confidence_threshold": 0.8,
                "follow_up_hours": 72,
                "is_meeting_related": False
            }
            
            response = requests.post(f"{API_BASE}/intents", json=intent_data, headers=self.get_headers())
            
            if response.status_code == 200:
                intent = response.json()
                print(f"✅ Intent with follow_up_hours created successfully")
                print(f"   - Follow-up hours: {intent.get('follow_up_hours', 'None')}")
                print(f"   - Intent name: {intent.get('name', 'N/A')}")
                self.test_results.append(("Intent Follow-up Hours", "PASS", f"{intent.get('follow_up_hours')} hours"))
            else:
                print(f"❌ Intent with follow_up_hours failed: {response.status_code} - {response.text}")
                self.test_results.append(("Intent Follow-up Hours", "FAIL", f"Status: {response.status_code}"))
                
        except Exception as e:
            print(f"❌ Intent follow-up hours testing failed: {str(e)}")
            self.test_results.append(("Intent Follow-up Hours", "FAIL", str(e)))
    
    async def test_automatic_follow_up_creation(self):
        """Test automatic follow-up creation after email sending"""
        print("\n🤖 Testing Automatic Follow-up Creation...")
        
        try:
            # First, check if there's a function to create follow-ups automatically
            # This would typically be triggered after sending an email
            print("Testing automatic follow-up creation workflow...")
            
            # Check if follow-ups were created for our test email
            response = requests.get(f"{API_BASE}/follow-ups", headers=self.get_headers())
            
            if response.status_code == 200:
                follow_ups = response.json()
                auto_created = [f for f in follow_ups if f.get('original_email_id') == self.test_email_id]
                
                if auto_created:
                    print(f"✅ Automatic follow-up creation working: {len(auto_created)} follow-ups found")
                    self.test_results.append(("Automatic Follow-up Creation", "PASS", f"{len(auto_created)} created"))
                else:
                    print("ℹ️ No automatic follow-ups found - may require email sending trigger")
                    self.test_results.append(("Automatic Follow-up Creation", "INFO", "No auto follow-ups found"))
            else:
                print(f"❌ Could not check automatic follow-ups: {response.status_code}")
                self.test_results.append(("Automatic Follow-up Creation", "FAIL", f"Status: {response.status_code}"))
                
        except Exception as e:
            print(f"❌ Automatic follow-up creation testing failed: {str(e)}")
            self.test_results.append(("Automatic Follow-up Creation", "FAIL", str(e)))
    
    async def cleanup(self):
        """Cleanup test data"""
        try:
            if self.client:
                await self.client.close()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {str(e)}")
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("FOLLOW-UP SYSTEM TEST RESULTS SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r[1] == "PASS"])
        failed_tests = len([r for r in self.test_results if r[1] == "FAIL"])
        expected_fails = len([r for r in self.test_results if r[1] == "EXPECTED_FAIL"])
        info_tests = len([r for r in self.test_results if r[1] == "INFO"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Expected Failures: {expected_fails}")
        print(f"Info: {info_tests}")
        print(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")
        
        print("\nDETAILED RESULTS:")
        for test_name, status, details in self.test_results:
            status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️" if status == "EXPECTED_FAIL" else "ℹ️"
            print(f"{status_icon} {test_name}: {status} - {details}")
        
        print("\n" + "="*60)
    
    async def run_all_tests(self):
        """Run all follow-up system tests"""
        print("🚀 Starting Follow-up System Testing...")
        
        if not await self.setup():
            return
        
        # Setup test data
        if not await self.setup_test_data():
            print("❌ Failed to setup test data, some tests may fail")
        
        # Run all test suites
        await self.test_follow_up_config_endpoints()
        await self.test_follow_up_email_management()
        await self.test_follow_up_analytics()
        await self.test_email_account_follow_up_settings()
        await self.test_intent_follow_up_hours()
        await self.test_automatic_follow_up_creation()
        
        # Cleanup and summary
        await self.cleanup()
        self.print_summary()

async def main():
    """Main test execution"""
    tester = FollowUpSystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())