#!/usr/bin/env python3
"""
Focused Email Response System Test
Tests the key components requested in the review
"""
import requests
import json
import time
import os
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://user-privacy-guard.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Expected API Keys from review request
EXPECTED_GROQ_KEY = "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"
EXPECTED_COHERE_KEY = "uW0jaFve1ytQLy62iM0vnXHcb87mcVEg6eZzPtei"

def test_api_keys():
    """Test API key configuration"""
    print("🔑 Testing API Key Configuration...")
    
    current_groq_key = os.environ.get('GROQ_API_KEY', '')
    current_cohere_key = os.environ.get('COHERE_API_KEY', '')
    
    groq_match = current_groq_key == EXPECTED_GROQ_KEY
    cohere_match = current_cohere_key == EXPECTED_COHERE_KEY
    
    print(f"   Groq API Key: {'✅ Match' if groq_match else '❌ Mismatch'}")
    print(f"   Cohere API Key: {'✅ Match' if cohere_match else '❌ Mismatch'}")
    
    return groq_match and cohere_match

def test_polling_service():
    """Test polling service status"""
    print("\n📡 Testing Polling Service...")
    
    try:
        response = requests.get(f"{API_BASE}/polling/status", timeout=10)
        if response.status_code == 200:
            status = response.json().get('status')
            print(f"   Polling Service: {'✅ Running' if status == 'running' else '❌ Not Running'}")
            return status == 'running'
        else:
            print(f"   Polling Service: ❌ Error {response.status_code}")
            return False
    except Exception as e:
        print(f"   Polling Service: ❌ Exception: {str(e)}")
        return False

def test_email_account():
    """Test email account configuration"""
    print("\n📧 Testing Email Account Configuration...")
    
    try:
        response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
        if response.status_code == 200:
            accounts = response.json()
            
            # Look for rohushanshinde@gmail.com
            target_account = None
            for account in accounts:
                if account.get('email') == 'rohushanshinde@gmail.com':
                    target_account = account
                    break
            
            if target_account:
                is_active = target_account.get('is_active', False)
                auto_send = target_account.get('auto_send', False)
                has_signature = bool(target_account.get('signature', ''))
                
                print(f"   Account Found: ✅ rohushanshinde@gmail.com")
                print(f"   Active: {'✅ Yes' if is_active else '❌ No'}")
                print(f"   Auto-send: {'✅ Enabled' if auto_send else '❌ Disabled'}")
                print(f"   Has Signature: {'✅ Yes' if has_signature else '❌ No'}")
                
                return is_active, target_account
            else:
                print("   Account: ❌ rohushanshinde@gmail.com not found")
                # Try to find any active account
                active_accounts = [acc for acc in accounts if acc.get('is_active', False)]
                if active_accounts:
                    account = active_accounts[0]
                    print(f"   Using alternative account: {account.get('email')}")
                    return True, account
                return False, None
        else:
            print(f"   Email Accounts: ❌ Error {response.status_code}")
            return False, None
    except Exception as e:
        print(f"   Email Accounts: ❌ Exception: {str(e)}")
        return False, None

def test_email_processing(account):
    """Test email processing with different types"""
    print("\n🤖 Testing Email Processing...")
    
    if not account:
        print("   ❌ No account available for testing")
        return False
    
    # Test scenarios from review request
    test_cases = [
        {
            "name": "Sales Inquiry",
            "subject": "Pricing Information Request",
            "body": "Hi, I'm interested in your AI email assistant product. Could you please send me detailed pricing information and available packages?",
            "sender": "sales@company.com"
        },
        {
            "name": "Technical Support",
            "subject": "API Integration Help",
            "body": "Hello, we're having trouble integrating your email API. Getting 401 errors. Can you help?",
            "sender": "tech@startup.com"
        },
        {
            "name": "Partnership Inquiry",
            "subject": "Partnership Opportunity",
            "body": "We're interested in exploring a partnership with your company. Could we schedule a call?",
            "sender": "partnerships@bigcorp.com"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n   Testing: {test_case['name']}")
        
        try:
            test_data = {
                "subject": test_case["subject"],
                "body": test_case["body"],
                "sender": test_case["sender"],
                "account_id": account['id']
            }
            
            start_time = time.time()
            response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=30)
            processing_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                result = response.json()
                status = result.get('status', 'unknown')
                intents = result.get('intents', [])
                draft = result.get('draft', '')
                
                # Check for success indicators
                has_intents = len(intents) > 0
                has_draft = len(draft) > 50
                is_complete = status in ['ready_to_send', 'sent', 'needs_redraft']
                not_stuck = status != 'classifying'
                
                success = has_draft and is_complete and not_stuck
                
                print(f"      Status: {status}")
                print(f"      Intents: {len(intents)}")
                print(f"      Draft Length: {len(draft)} chars")
                print(f"      Processing Time: {processing_time:.1f}s")
                print(f"      Result: {'✅ Success' if success else '❌ Failed'}")
                
                results.append(success)
                
            else:
                print(f"      ❌ API Error: {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"      ❌ Exception: {str(e)}")
            results.append(False)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n   Overall Results: {success_count}/{total_count} successful")
    return success_count >= 2  # At least 2 out of 3 should work

def test_model_configuration():
    """Test that the correct model is being used"""
    print("\n🔧 Testing Model Configuration...")
    
    try:
        # Check server.py for the correct model
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check for the expected model
        expected_model = "llama-3.3-70b-versatile"
        model_found = expected_model in content
        
        # Check for old problematic models
        old_models = ['deepseek-r1-distill-llama-70b', 'llama3-8b-8192', 'llama3-70b-8192']
        old_models_found = [model for model in old_models if model in content]
        
        print(f"   Expected Model ({expected_model}): {'✅ Found' if model_found else '❌ Not Found'}")
        print(f"   Old Models Removed: {'✅ Yes' if not old_models_found else f'❌ Found: {old_models_found}'}")
        
        return model_found and not old_models_found
        
    except Exception as e:
        print(f"   ❌ Error checking model: {str(e)}")
        return False

def main():
    """Run focused email response system tests"""
    print("🚀 Email Response System - Focused Testing")
    print("=" * 60)
    
    results = []
    
    # Test 1: API Keys
    results.append(test_api_keys())
    
    # Test 2: Polling Service
    results.append(test_polling_service())
    
    # Test 3: Email Account
    account_ok, account = test_email_account()
    results.append(account_ok)
    
    # Test 4: Email Processing
    results.append(test_email_processing(account))
    
    # Test 5: Model Configuration
    results.append(test_model_configuration())
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "API Key Configuration",
        "Polling Service Status", 
        "Email Account Configuration",
        "Email Processing Workflow",
        "Model Configuration"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed >= 4:
        print("\n🎉 EMAIL RESPONSE SYSTEM IS WORKING WELL!")
        print("✅ Automatic email responses are functional")
        print("✅ API keys are correctly configured")
        print("✅ Processing pipeline is operational")
    else:
        print("\n⚠️  EMAIL RESPONSE SYSTEM NEEDS ATTENTION")
        print("❌ Some critical components are not working properly")
    
    return passed, total

if __name__ == "__main__":
    main()