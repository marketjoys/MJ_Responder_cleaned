#!/usr/bin/env python3
"""
Final Verification Test for Email Assistant System
Testing all specific endpoints mentioned in the review request
"""
import requests
import json
import time
from datetime import datetime, timedelta

# Configuration
BACKEND_URL = "https://redis-worker-setup.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def test_specific_endpoints():
    """Test all specific endpoints mentioned in the review request"""
    print("🔍 FINAL VERIFICATION - Testing Specific Endpoints from Review Request")
    print("=" * 80)
    
    # First, get authentication token
    test_user_email = f"final.test.{int(time.time())}@example.com"
    register_data = {
        "email": test_user_email,
        "password": "TestPassword123!",
        "full_name": "Final Test User"
    }
    
    response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
    if response.status_code != 200:
        print("❌ Failed to register test user")
        return
    
    auth_token = response.json().get('access_token')
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Get an email account for testing
    accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
    if accounts_response.status_code != 200 or not accounts_response.json():
        print("❌ No email accounts available for testing")
        return
    
    account_id = accounts_response.json()[0]['id']
    
    # Test specific endpoints from review request
    endpoints_to_test = [
        # Email Processing Workflow
        {
            "name": "/api/emails/test (Email processing workflow)",
            "method": "POST",
            "url": f"{API_BASE}/emails/test",
            "data": {
                "subject": "Test Email Processing with New GROQ API Key",
                "body": "Hello! I need information about your AI email assistant pricing and would like to schedule a demo meeting to discuss our requirements.",
                "sender": "test@company.com",
                "account_id": account_id
            },
            "expected_status": [200, 201]
        },
        
        # Polling Endpoints
        {
            "name": "/api/polling/status (Polling status)",
            "method": "GET",
            "url": f"{API_BASE}/polling/status",
            "expected_status": [200]
        },
        {
            "name": "/api/polling/accounts-status (All accounts polling status)",
            "method": "GET",
            "url": f"{API_BASE}/polling/accounts-status",
            "expected_status": [200]
        },
        
        # Calendar Endpoints
        {
            "name": "/api/calendar/providers (Calendar provider management)",
            "method": "GET",
            "url": f"{API_BASE}/calendar/providers",
            "headers": headers,
            "expected_status": [200]
        },
        {
            "name": "/api/calendar/calendars (Get all calendars)",
            "method": "GET",
            "url": f"{API_BASE}/calendar/calendars",
            "headers": headers,
            "expected_status": [200]
        },
        {
            "name": "/api/calendar/detect-meeting (Meeting detection AI)",
            "method": "POST",
            "url": f"{API_BASE}/calendar/detect-meeting",
            "headers": headers,
            "data": {
                "email_content": "Hi, I'd like to schedule a meeting with you next Tuesday at 2 PM to discuss our project.",
                "sender": "meeting@company.com",
                "subject": "Meeting Request",
                "user_timezone": "America/New_York"
            },
            "expected_status": [200]
        },
        {
            "name": "/api/calendar/meeting-intents (Meeting intents)",
            "method": "GET",
            "url": f"{API_BASE}/calendar/meeting-intents",
            "headers": headers,
            "expected_status": [200]
        },
        
        # Authentication Endpoints
        {
            "name": "/api/auth/me (User profile)",
            "method": "GET",
            "url": f"{API_BASE}/auth/me",
            "headers": headers,
            "expected_status": [200]
        },
        
        # CRUD Endpoints
        {
            "name": "/api/intents (Intents management)",
            "method": "GET",
            "url": f"{API_BASE}/intents",
            "expected_status": [200]
        },
        {
            "name": "/api/email-accounts (Email accounts management)",
            "method": "GET",
            "url": f"{API_BASE}/email-accounts",
            "expected_status": [200]
        },
        {
            "name": "/api/knowledge-base (Knowledge base operations)",
            "method": "GET",
            "url": f"{API_BASE}/knowledge-base",
            "expected_status": [200]
        }
    ]
    
    results = []
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\n🔍 Testing: {endpoint['name']}")
            
            # Prepare request parameters
            request_params = {
                "method": endpoint["method"],
                "url": endpoint["url"],
                "timeout": 30
            }
            
            if "headers" in endpoint:
                request_params["headers"] = endpoint["headers"]
            
            if "data" in endpoint:
                request_params["json"] = endpoint["data"]
            
            # Make request
            response = requests.request(**request_params)
            
            # Check result
            passed = response.status_code in endpoint["expected_status"]
            status_icon = "✅" if passed else "❌"
            
            print(f"   {status_icon} Status: {response.status_code}")
            
            if passed and response.status_code == 200:
                try:
                    response_data = response.json()
                    if isinstance(response_data, list):
                        print(f"   📊 Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        if "status" in response_data:
                            print(f"   📊 Response: {response_data.get('status')}")
                        elif "email" in response_data:
                            print(f"   📊 Response: User profile for {response_data.get('email')}")
                        elif "intents" in response_data:
                            print(f"   📊 Response: Email processed with {len(response_data.get('intents', []))} intents")
                        else:
                            print(f"   📊 Response: Valid JSON object")
                except:
                    print(f"   📊 Response: Valid response")
            
            results.append({
                "endpoint": endpoint["name"],
                "status": response.status_code,
                "passed": passed,
                "details": response.text[:100] if not passed else "OK"
            })
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                "endpoint": endpoint["name"],
                "status": "ERROR",
                "passed": False,
                "details": str(e)
            })
    
    # Print summary
    print("\n" + "=" * 80)
    print("🏁 FINAL VERIFICATION SUMMARY")
    print("=" * 80)
    
    passed_tests = [r for r in results if r["passed"]]
    failed_tests = [r for r in results if not r["passed"]]
    
    print(f"✅ PASSED: {len(passed_tests)}")
    print(f"❌ FAILED: {len(failed_tests)}")
    print(f"📊 SUCCESS RATE: {len(passed_tests)}/{len(results)} ({len(passed_tests)/len(results)*100:.1f}%)")
    
    if failed_tests:
        print(f"\n❌ FAILED ENDPOINTS:")
        for test in failed_tests:
            print(f"   - {test['endpoint']}: Status {test['status']} - {test['details']}")
    
    print(f"\n✅ SUCCESSFUL ENDPOINTS:")
    for test in passed_tests:
        print(f"   - {test['endpoint']}: Status {test['status']}")
    
    print("\n" + "=" * 80)
    
    # Test Cal.com integration specifically
    print("\n🔍 TESTING CAL.COM INTEGRATION SPECIFICALLY")
    print("=" * 40)
    
    try:
        # Create Cal.com provider
        calcom_data = {
            "provider_type": "calcom",
            "provider_name": "Final Test Cal.com Provider",
            "credentials": {
                "api_key": "cal_live_d133aaaf5ee692d561d43a45ecff15ee"
            },
            "timezone": "America/New_York"
        }
        
        response = requests.post(f"{API_BASE}/calendar/providers", json=calcom_data, headers=headers, timeout=15)
        if response.status_code == 200:
            provider_id = response.json().get('id')
            print(f"✅ Cal.com Provider Created: {provider_id}")
            
            # Test listing events
            response = requests.get(f"{API_BASE}/calendar/providers/{provider_id}/calendars/default/events", headers=headers, timeout=15)
            if response.status_code == 200:
                print(f"✅ Cal.com Events Listed Successfully")
            else:
                print(f"❌ Cal.com Events List Failed: {response.status_code}")
            
            # Cleanup
            requests.delete(f"{API_BASE}/calendar/providers/{provider_id}", headers=headers, timeout=10)
            print(f"✅ Cal.com Provider Cleaned Up")
        else:
            print(f"❌ Cal.com Provider Creation Failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Cal.com Test Error: {str(e)}")

if __name__ == "__main__":
    test_specific_endpoints()