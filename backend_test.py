import requests
import sys
import json
from datetime import datetime

class EmailAssistantAPITester:
    def __init__(self, base_url="https://auto-respond-repair.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'intents': [],
            'accounts': [],
            'knowledge': [],
            'emails': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.text[:200]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        return self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)

    def test_email_providers(self):
        """Test email providers endpoint"""
        return self.run_test("Email Providers", "GET", "email-providers", 200)

    def test_create_intent(self):
        """Test creating an intent"""
        intent_data = {
            "name": "Product Inquiry",
            "description": "Customer asking about product information, pricing, or features",
            "examples": [
                "Can you tell me about your product?",
                "What are your prices?",
                "I need information about features"
            ],
            "system_prompt": "Provide helpful product information and guide customers to relevant resources.",
            "confidence_threshold": 0.7,
            "follow_up_hours": 24,
            "is_meeting_related": False
        }
        
        success, response = self.run_test("Create Intent", "POST", "intents", 200, intent_data)
        if success and 'id' in response:
            self.created_resources['intents'].append(response['id'])
            return True, response
        return False, {}

    def test_get_intents(self):
        """Test getting all intents"""
        return self.run_test("Get Intents", "GET", "intents", 200)

    def test_create_email_account(self):
        """Test creating an email account"""
        account_data = {
            "name": "Test Support Account",
            "email": "test@gmail.com",
            "provider": "gmail",
            "username": "test@gmail.com",
            "password": "dummypass",
            "persona": "Professional and helpful",
            "signature": "Best regards,\nTest Support Team"
        }
        
        success, response = self.run_test("Create Email Account", "POST", "email-accounts", 200, account_data)
        if success and 'id' in response:
            self.created_resources['accounts'].append(response['id'])
            return True, response
        return False, {}

    def test_get_email_accounts(self):
        """Test getting all email accounts"""
        return self.run_test("Get Email Accounts", "GET", "email-accounts", 200)

    def test_create_knowledge_base(self):
        """Test creating a knowledge base item"""
        kb_data = {
            "title": "Product Pricing",
            "content": "Our basic plan starts at $29/month and includes all core features. Premium plan is $99/month with advanced analytics and priority support. Enterprise plans are available with custom pricing.",
            "tags": ["pricing", "plans", "product"]
        }
        
        success, response = self.run_test("Create Knowledge Base", "POST", "knowledge-base", 200, kb_data)
        if success and 'id' in response:
            self.created_resources['knowledge'].append(response['id'])
            return True, response
        return False, {}

    def test_get_knowledge_base(self):
        """Test getting all knowledge base items"""
        return self.run_test("Get Knowledge Base", "GET", "knowledge-base", 200)

    def test_email_processing(self, account_id):
        """Test the core AI email processing workflow"""
        if not account_id:
            print("❌ Cannot test email processing - no account ID available")
            return False, {}
            
        email_data = {
            "subject": "Need product information",
            "body": "Hi, I'm interested in your product. Can you tell me about pricing and features? I'm looking for a solution for my small business.",
            "sender": "customer@example.com",
            "account_id": account_id
        }
        
        success, response = self.run_test("Test Email Processing", "POST", "emails/test", 200, email_data)
        if success and 'id' in response:
            self.created_resources['emails'].append(response['id'])
            return True, response
        return False, {}

    def test_get_emails(self):
        """Test getting all processed emails"""
        return self.run_test("Get Emails", "GET", "emails", 200)

    def cleanup_resources(self):
        """Clean up created test resources"""
        print("\n🧹 Cleaning up test resources...")
        
        # Delete intents
        for intent_id in self.created_resources['intents']:
            self.run_test(f"Delete Intent {intent_id}", "DELETE", f"intents/{intent_id}", 200)
        
        # Delete email accounts
        for account_id in self.created_resources['accounts']:
            self.run_test(f"Delete Account {account_id}", "DELETE", f"email-accounts/{account_id}", 200)
        
        # Delete knowledge base items
        for kb_id in self.created_resources['knowledge']:
            self.run_test(f"Delete Knowledge {kb_id}", "DELETE", f"knowledge-base/{kb_id}", 200)

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Email Assistant API Tests")
        print(f"Base URL: {self.base_url}")
        print("=" * 50)

        # Test basic endpoints
        self.test_dashboard_stats()
        self.test_email_providers()

        # Test intent management
        intent_success, intent_response = self.test_create_intent()
        self.test_get_intents()

        # Test email account management
        account_success, account_response = self.test_create_email_account()
        self.test_get_email_accounts()

        # Test knowledge base management
        kb_success, kb_response = self.test_create_knowledge_base()
        self.test_get_knowledge_base()

        # Test core AI workflow
        account_id = account_response.get('id') if account_success else None
        email_success, email_response = self.test_email_processing(account_id)
        
        # Wait a moment for processing
        if email_success:
            import time
            print("⏳ Waiting for AI processing to complete...")
            time.sleep(5)
            
        self.test_get_emails()

        # Print results
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if email_success and email_response:
            print("\n🤖 AI Processing Results:")
            print(f"   Email ID: {email_response.get('id', 'N/A')}")
            print(f"   Status: {email_response.get('status', 'N/A')}")
            print(f"   Intents Found: {len(email_response.get('intents', []))}")
            if email_response.get('intents'):
                for intent in email_response.get('intents', []):
                    print(f"     - {intent.get('name', 'Unknown')}: {intent.get('confidence', 0)*100:.1f}%")
            print(f"   Draft Generated: {'Yes' if email_response.get('draft') else 'No'}")
            print(f"   Validation: {email_response.get('validation_result', {}).get('status', 'N/A')}")

        # Cleanup
        self.cleanup_resources()
        
        return self.tests_passed == self.tests_run

def main():
    tester = EmailAssistantAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())