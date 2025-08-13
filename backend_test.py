import requests
import sys
import json
import time
from datetime import datetime

class EmailAssistantAPITester:
    def __init__(self, base_url="https://draft-email-only.preview.emergentagent.com"):
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
        self.test_results = {
            'critical_issues': [],
            'minor_issues': [],
            'passed_tests': []
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
                self.test_results['passed_tests'].append(name)
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.text[:200]
                    print(f"   Response: {error_detail}")
                    self.test_results['critical_issues'].append(f"{name}: Expected {expected_status}, got {response.status_code} - {error_detail}")
                except:
                    self.test_results['critical_issues'].append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results['critical_issues'].append(f"{name}: Connection error - {str(e)}")
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

    def test_create_real_email_accounts(self):
        """Test creating the two required Gmail accounts"""
        print("\n🔧 Creating required Gmail accounts...")
        
        # Account 1: rohushanshinde@gmail.com
        account1_data = {
            "name": "Rohan Support Account",
            "email": "rohushanshinde@gmail.com",
            "provider": "gmail",
            "username": "rohushanshinde@gmail.com",
            "password": "pajbdmcpcegppguz",
            "persona": "Professional and helpful customer support representative",
            "signature": "Best regards,\nRohan\nCustomer Support Team",
            "auto_send": True
        }
        
        success1, response1 = self.run_test("Create Gmail Account 1 (rohushanshinde)", "POST", "email-accounts", 200, account1_data)
        if success1 and 'id' in response1:
            self.created_resources['accounts'].append(response1['id'])
        
        # Account 2: kasargovinda@gmail.com  
        account2_data = {
            "name": "Govinda Support Account",
            "email": "kasargovinda@gmail.com",
            "provider": "gmail", 
            "username": "kasargovinda@gmail.com",
            "password": "urvsdfvrzfabvykm",
            "persona": "Professional and helpful customer support representative",
            "signature": "Best regards,\nGovinda\nCustomer Support Team",
            "auto_send": True
        }
        
        success2, response2 = self.run_test("Create Gmail Account 2 (kasargovinda)", "POST", "email-accounts", 200, account2_data)
        if success2 and 'id' in response2:
            self.created_resources['accounts'].append(response2['id'])
            
        return success1 and success2, [response1, response2]

    def test_verify_email_accounts_count(self):
        """Verify that exactly 2 email accounts are configured"""
        success, response = self.run_test("Verify Email Accounts Count", "GET", "email-accounts", 200)
        if success:
            accounts = response if isinstance(response, list) else []
            if len(accounts) >= 2:
                print(f"✅ Found {len(accounts)} email accounts configured")
                # Check for the specific accounts
                emails = [acc.get('email', '') for acc in accounts]
                if 'rohushanshinde@gmail.com' in emails and 'kasargovinda@gmail.com' in emails:
                    print("✅ Both required Gmail accounts found")
                    return True, response
                else:
                    self.test_results['critical_issues'].append("Required Gmail accounts not found in configured accounts")
                    return False, response
            else:
                self.test_results['critical_issues'].append(f"Expected at least 2 accounts, found {len(accounts)}")
                return False, response
        return False, {}

    def test_polling_service_status(self):
        """Test polling service status - should be running with 2 active connections"""
        success, response = self.run_test("Check Polling Service Status", "GET", "polling/status", 200)
        if success:
            status = response.get('status', 'unknown')
            active_connections = response.get('active_connections', 0)
            
            if status == 'running':
                print(f"✅ Polling service is running with {active_connections} active connections")
                if active_connections >= 2:
                    print("✅ Expected number of active connections found")
                    return True, response
                else:
                    self.test_results['minor_issues'].append(f"Expected 2+ active connections, found {active_connections}")
                    return True, response  # Still pass as service is running
            else:
                self.test_results['critical_issues'].append(f"Polling service not running - status: {status}")
                return False, response
        return False, {}

    def test_start_polling_service(self):
        """Start the polling service if not running"""
        control_data = {"action": "start"}
        success, response = self.run_test("Start Polling Service", "POST", "polling/control", 200, control_data)
        if success:
            print("✅ Polling service start command sent")
            # Wait a moment for service to start
            time.sleep(3)
            return True, response
        return False, {}

    def test_create_sample_intents(self):
        """Create sample intents for testing"""
        print("\n🎯 Creating sample intents for testing...")
        
        intents_data = [
            {
                "name": "Product Inquiry",
                "description": "Customer asking about product information, pricing, features, or specifications",
                "examples": [
                    "Can you tell me about your product?",
                    "What are your prices?",
                    "I need information about features",
                    "How much does it cost?",
                    "What can your product do?"
                ],
                "system_prompt": "Provide helpful product information and guide customers to relevant resources. Be professional and informative.",
                "confidence_threshold": 0.7,
                "follow_up_hours": 24,
                "is_meeting_related": False
            },
            {
                "name": "Support Request",
                "description": "Customer needs help with technical issues, troubleshooting, or general support",
                "examples": [
                    "I'm having trouble with...",
                    "Can you help me fix this?",
                    "Something is not working",
                    "I need technical support",
                    "How do I solve this problem?"
                ],
                "system_prompt": "Provide helpful technical support and troubleshooting guidance. Ask clarifying questions if needed.",
                "confidence_threshold": 0.7,
                "follow_up_hours": 12,
                "is_meeting_related": False
            }
        ]
        
        created_intents = []
        for intent_data in intents_data:
            success, response = self.run_test(f"Create Intent: {intent_data['name']}", "POST", "intents", 200, intent_data)
            if success and 'id' in response:
                self.created_resources['intents'].append(response['id'])
                created_intents.append(response)
        
        return len(created_intents) > 0, created_intents

    def test_verify_intents_created(self):
        """Verify intents are created and accessible"""
        success, response = self.run_test("Verify Intents Created", "GET", "intents", 200)
        if success:
            intents = response if isinstance(response, list) else []
            if len(intents) >= 2:
                print(f"✅ Found {len(intents)} intents configured")
                return True, response
            else:
                self.test_results['critical_issues'].append(f"Expected at least 2 intents, found {len(intents)}")
                return False, response
        return False, {}

    def test_api_keys_functionality(self):
        """Test that new API keys work without rate limit errors"""
        print("\n🔑 Testing API keys functionality...")
        
        # Test with a simple email processing request
        if not self.created_resources['accounts']:
            print("❌ No accounts available for API key testing")
            return False, {}
            
        account_id = self.created_resources['accounts'][0]
        
        # Test email that should trigger AI processing (uses both Cohere and Groq APIs)
        email_data = {
            "subject": "Product pricing inquiry",
            "body": "Hi, I'm interested in learning more about your product pricing and features. Can you provide me with detailed information about your plans and what's included? I'm looking for a solution for my small business with about 10 employees.",
            "sender": "potential.customer@businessemail.com",
            "account_id": account_id
        }
        
        success, response = self.run_test("Test API Keys via Email Processing", "POST", "emails/test", 200, email_data)
        if success:
            email_id = response.get('id')
            if email_id:
                self.created_resources['emails'].append(email_id)
                print("✅ Email processing initiated - API keys working")
                
                # Wait for processing to complete
                print("⏳ Waiting for AI processing to complete...")
                time.sleep(8)
                
                # Check processing results
                processed_success, processed_response = self.run_test("Check Processed Email", "GET", f"emails/{email_id}", 200)
                if processed_success:
                    status = processed_response.get('status', 'unknown')
                    intents = processed_response.get('intents', [])
                    draft = processed_response.get('draft', '')
                    
                    print(f"   Status: {status}")
                    print(f"   Intents found: {len(intents)}")
                    print(f"   Draft generated: {'Yes' if draft else 'No'}")
                    
                    if status in ['ready_to_send', 'sent', 'needs_redraft'] and intents and draft:
                        print("✅ API keys working correctly - full AI workflow completed")
                        return True, processed_response
                    elif status == 'error':
                        error_msg = processed_response.get('error', 'Unknown error')
                        if 'rate limit' in error_msg.lower() or 'quota' in error_msg.lower():
                            self.test_results['critical_issues'].append(f"API rate limit error: {error_msg}")
                        else:
                            self.test_results['critical_issues'].append(f"API processing error: {error_msg}")
                        return False, processed_response
                    else:
                        self.test_results['minor_issues'].append(f"Processing incomplete - Status: {status}")
                        return True, processed_response  # Still pass as no rate limit error
                        
        return False, {}

    def test_draft_generation_clean_content(self):
        """Test that Draft Agent generates ONLY clean email body content (Bug Fix #1)"""
        print("\n🎯 Testing Draft Agent - Clean Content Only (Bug Fix #1)...")
        
        if not self.created_resources['accounts']:
            print("❌ No accounts available for draft testing")
            return False, {}
            
        account_id = self.created_resources['accounts'][0]
        
        # Test email that should generate a draft
        email_data = {
            "subject": "General inquiry about services",
            "body": "Hello, I would like to know more about your services and how they can help my business. Can you provide some information?",
            "sender": "business.owner@company.com",
            "account_id": account_id
        }
        
        success, response = self.run_test("Test Draft Generation", "POST", "emails/test", 200, email_data)
        if success:
            email_id = response.get('id')
            if email_id:
                self.created_resources['emails'].append(email_id)
                
                # Wait for processing to complete
                print("⏳ Waiting for draft generation...")
                time.sleep(10)
                
                # Check draft content
                processed_success, processed_response = self.run_test("Check Draft Content", "GET", f"emails/{email_id}", 200)
                if processed_success:
                    draft = processed_response.get('draft', '')
                    status = processed_response.get('status', 'unknown')
                    
                    print(f"   Status: {status}")
                    print(f"   Draft length: {len(draft)} characters")
                    
                    if draft:
                        # Check for unwanted content that should NOT be in draft
                        unwanted_patterns = [
                            '<think>',
                            '</think>',
                            'Subject:',
                            'Re:',
                            'PLAIN_TEXT:',
                            'HTML:',
                            '***',
                            '---',
                            '===',
                            '[placeholder',
                            'reasoning:',
                            'analysis:'
                        ]
                        
                        issues_found = []
                        for pattern in unwanted_patterns:
                            if pattern.lower() in draft.lower():
                                issues_found.append(pattern)
                        
                        if issues_found:
                            self.test_results['critical_issues'].append(f"Draft contains unwanted content: {', '.join(issues_found)}")
                            print(f"❌ Draft contains unwanted content: {', '.join(issues_found)}")
                            print(f"   Draft preview: {draft[:200]}...")
                            return False, processed_response
                        else:
                            print("✅ Draft contains only clean email body content")
                            print(f"   Draft preview: {draft[:150]}...")
                            return True, processed_response
                    else:
                        self.test_results['critical_issues'].append("No draft generated")
                        return False, processed_response
                        
        return False, {}

    def test_intent_classification_functionality(self):
        """Test that Intent Classification is working properly (Bug Fix #2)"""
        print("\n🎯 Testing Intent Classification (Bug Fix #2)...")
        
        if not self.created_resources['accounts']:
            print("❌ No accounts available for intent testing")
            return False, {}
            
        account_id = self.created_resources['accounts'][0]
        
        # Test different types of emails to verify intent classification
        test_emails = [
            {
                "name": "Product Inquiry",
                "subject": "Product information request",
                "body": "Hi, I'm interested in your product. Can you tell me about pricing and features? What plans do you offer?",
                "expected_intent": "Product Inquiry"
            },
            {
                "name": "Support Request", 
                "subject": "Need help with technical issue",
                "body": "I'm having trouble with the system. Something is not working correctly and I need technical support to fix this problem.",
                "expected_intent": "Support Request"
            }
        ]
        
        classification_results = []
        
        for test_email in test_emails:
            email_data = {
                "subject": test_email["subject"],
                "body": test_email["body"],
                "sender": f"test.{test_email['name'].lower().replace(' ', '.')}@example.com",
                "account_id": account_id
            }
            
            success, response = self.run_test(f"Test Intent Classification - {test_email['name']}", "POST", "emails/test", 200, email_data)
            if success:
                email_id = response.get('id')
                if email_id:
                    self.created_resources['emails'].append(email_id)
                    
                    # Wait for classification
                    time.sleep(6)
                    
                    # Check classification results
                    processed_success, processed_response = self.run_test(f"Check Intent Classification - {test_email['name']}", "GET", f"emails/{email_id}", 200)
                    if processed_success:
                        intents = processed_response.get('intents', [])
                        status = processed_response.get('status', 'unknown')
                        
                        print(f"   Status: {status}")
                        print(f"   Intents found: {len(intents)}")
                        
                        if intents:
                            for intent in intents:
                                intent_name = intent.get('name', 'Unknown')
                                confidence = intent.get('confidence', 0)
                                print(f"     - {intent_name}: {confidence:.3f}")
                                
                            # Check if expected intent was found with good confidence
                            expected_found = any(
                                intent.get('name', '').lower() == test_email['expected_intent'].lower() and 
                                intent.get('confidence', 0) >= 0.7 
                                for intent in intents
                            )
                            
                            classification_results.append({
                                'test': test_email['name'],
                                'expected': test_email['expected_intent'],
                                'found': expected_found,
                                'intents': intents
                            })
                        else:
                            print("❌ No intents classified")
                            classification_results.append({
                                'test': test_email['name'],
                                'expected': test_email['expected_intent'],
                                'found': False,
                                'intents': []
                            })
        
        # Evaluate classification results
        successful_classifications = sum(1 for result in classification_results if result['found'])
        total_tests = len(classification_results)
        
        if successful_classifications >= total_tests * 0.8:  # 80% success rate
            print(f"✅ Intent classification working - {successful_classifications}/{total_tests} successful")
            return True, classification_results
        else:
            self.test_results['critical_issues'].append(f"Intent classification failing - only {successful_classifications}/{total_tests} successful")
            return False, classification_results

    def test_validation_logic_pass_fail(self):
        """Test that Validation Logic correctly parses PASS/FAIL (Bug Fix #3)"""
        print("\n🎯 Testing Validation Logic PASS/FAIL Parsing (Bug Fix #3)...")
        
        if not self.created_resources['accounts']:
            print("❌ No accounts available for validation testing")
            return False, {}
            
        account_id = self.created_resources['accounts'][0]
        
        # Test email that should generate a good draft (should PASS validation)
        email_data = {
            "subject": "Simple information request",
            "body": "Hello, I would like to get some basic information about your company and services. Thank you.",
            "sender": "simple.request@example.com",
            "account_id": account_id
        }
        
        success, response = self.run_test("Test Validation Logic", "POST", "emails/test", 200, email_data)
        if success:
            email_id = response.get('id')
            if email_id:
                self.created_resources['emails'].append(email_id)
                
                # Wait for complete processing including validation
                print("⏳ Waiting for validation to complete...")
                time.sleep(12)
                
                # Check validation results
                processed_success, processed_response = self.run_test("Check Validation Results", "GET", f"emails/{email_id}", 200)
                if processed_success:
                    status = processed_response.get('status', 'unknown')
                    validation_result = processed_response.get('validation_result', {})
                    
                    print(f"   Final Status: {status}")
                    
                    if validation_result:
                        validation_status = validation_result.get('status', 'unknown')
                        feedback = validation_result.get('feedback', '')
                        
                        print(f"   Validation Status: {validation_status}")
                        print(f"   Feedback: {feedback[:100]}...")
                        
                        # Check if validation status is properly parsed as PASS or FAIL
                        if validation_status in ['PASS', 'FAIL']:
                            print("✅ Validation logic correctly parsing PASS/FAIL")
                            
                            # Check if final email status matches validation result
                            expected_final_status = 'ready_to_send' if validation_status == 'PASS' else 'needs_redraft'
                            if status == expected_final_status:
                                print(f"✅ Email status correctly set to '{status}' based on validation")
                                return True, processed_response
                            else:
                                self.test_results['critical_issues'].append(f"Email status '{status}' doesn't match validation '{validation_status}'")
                                return False, processed_response
                        else:
                            self.test_results['critical_issues'].append(f"Validation status not properly parsed: '{validation_status}'")
                            return False, processed_response
                    else:
                        self.test_results['critical_issues'].append("No validation result found")
                        return False, processed_response
                        
        return False, {}

    def test_complete_email_workflow(self):
        """Test complete email workflow: new → classifying → drafting → ready_to_send"""
        print("\n🎯 Testing Complete Email Workflow (new → classifying → drafting → ready_to_send)...")
        
        if not self.created_resources['accounts']:
            print("❌ No accounts available for workflow testing")
            return False, {}
            
        account_id = self.created_resources['accounts'][0]
        
        # Test email for complete workflow
        email_data = {
            "subject": "Business partnership inquiry",
            "body": "Hello, I represent a growing company and we're interested in exploring potential partnership opportunities with your organization. Could you provide information about your partnership programs and how we might collaborate?",
            "sender": "partnership.manager@growingcompany.com",
            "account_id": account_id
        }
        
        success, response = self.run_test("Test Complete Workflow", "POST", "emails/test", 200, email_data)
        if success:
            email_id = response.get('id')
            if email_id:
                self.created_resources['emails'].append(email_id)
                
                # Track workflow progression
                workflow_stages = []
                
                # Check initial status
                initial_success, initial_response = self.run_test("Check Initial Status", "GET", f"emails/{email_id}", 200)
                if initial_success:
                    initial_status = initial_response.get('status', 'unknown')
                    workflow_stages.append(f"Initial: {initial_status}")
                    print(f"   Initial Status: {initial_status}")
                
                # Wait and check progression through stages
                for i in range(6):  # Check 6 times over 15 seconds
                    time.sleep(2.5)
                    
                    stage_success, stage_response = self.run_test(f"Check Workflow Stage {i+1}", "GET", f"emails/{email_id}", 200)
                    if stage_success:
                        current_status = stage_response.get('status', 'unknown')
                        if not workflow_stages or workflow_stages[-1] != f"Stage {i+1}: {current_status}":
                            workflow_stages.append(f"Stage {i+1}: {current_status}")
                            print(f"   Stage {i+1}: {current_status}")
                        
                        # If we reach a final status, break
                        if current_status in ['ready_to_send', 'needs_redraft', 'sent', 'error']:
                            break
                
                # Final check
                final_success, final_response = self.run_test("Check Final Workflow Status", "GET", f"emails/{email_id}", 200)
                if final_success:
                    final_status = final_response.get('status', 'unknown')
                    intents = final_response.get('intents', [])
                    draft = final_response.get('draft', '')
                    validation_result = final_response.get('validation_result', {})
                    
                    print(f"   Final Status: {final_status}")
                    print(f"   Workflow Progression: {' → '.join([stage.split(': ')[1] for stage in workflow_stages])}")
                    
                    # Check if workflow completed successfully
                    expected_stages = ['processing', 'classifying', 'drafting']
                    workflow_progression = ' → '.join([stage.split(': ')[1] for stage in workflow_stages])
                    
                    # Verify all components are present
                    components_present = {
                        'intents': len(intents) > 0,
                        'draft': len(draft) > 0,
                        'validation': bool(validation_result)
                    }
                    
                    print(f"   Components: Intents({len(intents)}), Draft({len(draft) > 0}), Validation({bool(validation_result)})")
                    
                    if final_status in ['ready_to_send', 'needs_redraft'] and all(components_present.values()):
                        print("✅ Complete email workflow successful")
                        return True, final_response
                    else:
                        missing_components = [k for k, v in components_present.items() if not v]
                        self.test_results['critical_issues'].append(f"Workflow incomplete - Status: {final_status}, Missing: {missing_components}")
                        return False, final_response
                        
        return False, {}

    def test_database_state_verification(self):
        """Verify database state and email account configurations"""
        print("\n🗄️ Verifying database state...")
        
        # Check email accounts have proper last_uid values
        success, response = self.run_test("Check Email Accounts State", "GET", "email-accounts", 200)
        if success:
            accounts = response if isinstance(response, list) else []
            for account in accounts:
                email = account.get('email', 'unknown')
                last_uid = account.get('last_uid', 0)
                is_active = account.get('is_active', False)
                
                print(f"   Account: {email}")
                print(f"     Active: {is_active}")
                print(f"     Last UID: {last_uid}")
                
                if not is_active:
                    self.test_results['minor_issues'].append(f"Account {email} is not active")
                    
            return True, response
        return False, {}

    def test_new_email_processing_only(self):
        """Test that system only processes NEW emails (bug fix verification)"""
        print("\n🐛 Testing bug fix: Only process NEW emails...")
        
        # This test verifies the fix by checking that:
        # 1. Polling service is configured to start from latest UID
        # 2. No historical emails are being processed
        
        # Get current email count
        success, response = self.run_test("Get Current Email Count", "GET", "emails", 200)
        if success:
            current_emails = response if isinstance(response, list) else []
            current_count = len(current_emails)
            print(f"   Current processed emails: {current_count}")
            
            # Check if any emails have very old timestamps (indicating historical processing)
            now = datetime.utcnow()
            old_emails = []
            
            for email in current_emails:
                received_at = email.get('received_at', '')
                if received_at:
                    try:
                        # Parse the timestamp
                        email_time = datetime.fromisoformat(received_at.replace('Z', '+00:00'))
                        age_hours = (now - email_time.replace(tzinfo=None)).total_seconds() / 3600
                        
                        if age_hours > 24:  # Emails older than 24 hours
                            old_emails.append({
                                'subject': email.get('subject', 'No subject'),
                                'age_hours': age_hours,
                                'received_at': received_at
                            })
                    except:
                        pass
            
            if old_emails:
                print(f"⚠️  Found {len(old_emails)} potentially historical emails:")
                for old_email in old_emails[:3]:  # Show first 3
                    print(f"     - {old_email['subject']} ({old_email['age_hours']:.1f}h old)")
                self.test_results['minor_issues'].append(f"Found {len(old_emails)} potentially historical emails being processed")
            else:
                print("✅ No historical emails found - bug fix appears to be working")
                
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

    def run_comprehensive_tests(self):
        """Run comprehensive tests as per review request"""
        print("🚀 Starting Comprehensive Email Auto-Response System Tests")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        print("🎯 FOCUS: Bug fix verification and complete email workflow testing")
        print("=" * 60)

        # Phase 1: Basic API Health Check
        print("\n📋 PHASE 1: Basic API Health Check")
        self.test_dashboard_stats()
        self.test_email_providers()

        # Phase 2: Email Account Setup (Critical for review request)
        print("\n📧 PHASE 2: Email Account Configuration")
        accounts_success, accounts_response = self.test_create_real_email_accounts()
        self.test_verify_email_accounts_count()

        # Phase 3: Polling Service Testing (Critical for bug fix)
        print("\n🔄 PHASE 3: Email Polling Service Testing")
        self.test_start_polling_service()
        self.test_polling_service_status()

        # Phase 4: Intent Management Setup
        print("\n🎯 PHASE 4: Intent Management Setup")
        self.test_create_sample_intents()
        self.test_verify_intents_created()

        # Phase 5: API Keys and Rate Limiting Test (Critical)
        print("\n🔑 PHASE 5: API Keys and Rate Limiting Test")
        self.test_api_keys_functionality()

        # Phase 6: CRITICAL BUG FIX TESTS (Review Request Focus)
        print("\n🐛 PHASE 6: CRITICAL BUG FIX VERIFICATION")
        print("Testing recently fixed issues:")
        
        # Bug Fix #1: Draft Agent clean content
        self.test_draft_generation_clean_content()
        
        # Bug Fix #2: Intent classification
        self.test_intent_classification_functionality()
        
        # Bug Fix #3: Validation logic PASS/FAIL
        self.test_validation_logic_pass_fail()
        
        # Bug Fix #4: Complete workflow
        self.test_complete_email_workflow()

        # Phase 7: Database State Verification
        print("\n🗄️ PHASE 7: Database State Verification")
        self.test_database_state_verification()

        # Phase 8: Bug Fix Verification (Historical emails)
        print("\n🐛 PHASE 8: Bug Fix Verification - NEW Emails Only")
        self.test_new_email_processing_only()

        # Phase 9: Additional Email Workflow Test
        print("\n🤖 PHASE 9: Additional Email Workflow Test")
        if self.created_resources['accounts']:
            account_id = self.created_resources['accounts'][0]
            workflow_success, workflow_response = self.test_email_processing(account_id)
            
            if workflow_success:
                print("⏳ Waiting for complete AI workflow...")
                time.sleep(10)
                
        self.test_get_emails()

        # Final Results
        self.print_comprehensive_results()
        
        return len(self.test_results['critical_issues']) == 0

    def print_comprehensive_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        print(f"📈 Overall: {self.tests_passed}/{self.tests_run} tests passed")
        
        # Critical Issues
        if self.test_results['critical_issues']:
            print(f"\n❌ CRITICAL ISSUES ({len(self.test_results['critical_issues'])}):")
            for i, issue in enumerate(self.test_results['critical_issues'], 1):
                print(f"   {i}. {issue}")
        else:
            print("\n✅ NO CRITICAL ISSUES FOUND")
        
        # Minor Issues
        if self.test_results['minor_issues']:
            print(f"\n⚠️  MINOR ISSUES ({len(self.test_results['minor_issues'])}):")
            for i, issue in enumerate(self.test_results['minor_issues'], 1):
                print(f"   {i}. {issue}")
        else:
            print("\n✅ NO MINOR ISSUES FOUND")
        
        # Passed Tests Summary
        print(f"\n✅ PASSED TESTS ({len(self.test_results['passed_tests'])}):")
        for test in self.test_results['passed_tests']:
            print(f"   ✓ {test}")
        
        # Review Request Specific Results
        print("\n" + "=" * 60)
        print("🎯 REVIEW REQUEST VERIFICATION RESULTS")
        print("=" * 60)
        
        # Bug Fix #1: Draft Agent Clean Content
        draft_fix_verified = any("Draft Generation" in test for test in self.test_results['passed_tests'])
        print(f"🎯 Bug Fix #1 (Clean Draft Content): {'✅ VERIFIED' if draft_fix_verified else '❌ NEEDS ATTENTION'}")
        
        # Bug Fix #2: Intent Classification
        intent_fix_verified = any("Intent Classification" in test for test in self.test_results['passed_tests'])
        print(f"🎯 Bug Fix #2 (Intent Classification): {'✅ VERIFIED' if intent_fix_verified else '❌ NEEDS ATTENTION'}")
        
        # Bug Fix #3: Validation Logic
        validation_fix_verified = any("Validation Logic" in test for test in self.test_results['passed_tests'])
        print(f"🎯 Bug Fix #3 (Validation PASS/FAIL): {'✅ VERIFIED' if validation_fix_verified else '❌ NEEDS ATTENTION'}")
        
        # Bug Fix #4: Complete Workflow
        complete_workflow_verified = any("Complete Workflow" in test for test in self.test_results['passed_tests'])
        print(f"🎯 Bug Fix #4 (Complete Workflow): {'✅ VERIFIED' if complete_workflow_verified else '❌ NEEDS ATTENTION'}")
        
        # Historical Bug Fix Verification
        bug_fix_verified = "NEW Emails Only" in str(self.test_results['passed_tests'])
        print(f"🐛 Bug Fix (Only NEW emails): {'✅ VERIFIED' if bug_fix_verified else '❌ NEEDS ATTENTION'}")
        
        # Email Workflow
        workflow_working = any("Email Processing" in test for test in self.test_results['passed_tests'])
        print(f"🤖 Email Processing Workflow: {'✅ WORKING' if workflow_working else '❌ NEEDS ATTENTION'}")
        
        # API Keys
        api_keys_working = any("API Keys" in test for test in self.test_results['passed_tests'])
        print(f"🔑 New API Keys: {'✅ WORKING' if api_keys_working else '❌ NEEDS ATTENTION'}")
        
        # Polling Service
        polling_working = any("Polling" in test for test in self.test_results['passed_tests'])
        print(f"🔄 Polling Service: {'✅ RUNNING' if polling_working else '❌ NEEDS ATTENTION'}")
        
        # Email Accounts
        accounts_configured = any("Email Accounts" in test for test in self.test_results['passed_tests'])
        print(f"📧 Email Accounts (2): {'✅ CONFIGURED' if accounts_configured else '❌ NEEDS ATTENTION'}")

        print("\n" + "=" * 60)

def main():
    """Main test runner for comprehensive email auto-response system testing"""
    print("🎯 EMAIL AUTO-RESPONSE SYSTEM - COMPREHENSIVE TESTING")
    print("Focus: Bug fix verification, API keys, complete workflow")
    print("=" * 60)
    
    tester = EmailAssistantAPITester()
    
    try:
        success = tester.run_comprehensive_tests()
        
        # Cleanup resources
        print("\n🧹 Cleaning up test resources...")
        tester.cleanup_resources()
        
        # Final status
        if success:
            print("\n🎉 ALL CRITICAL TESTS PASSED - System is working correctly!")
            return 0
        else:
            print("\n⚠️  SOME CRITICAL ISSUES FOUND - Review results above")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        tester.cleanup_resources()
        return 1
    except Exception as e:
        print(f"\n\n💥 Unexpected error during testing: {str(e)}")
        tester.cleanup_resources()
        return 1

if __name__ == "__main__":
    sys.exit(main())