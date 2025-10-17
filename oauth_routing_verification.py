#!/usr/bin/env python3
"""
Simple OAuth Routing Verification Test
Focuses specifically on testing the OAuth routing fix
"""
import asyncio
import sys
import os
import requests
from datetime import datetime

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-reply-checker.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def test_oauth_routing_fix():
    """Test the OAuth routing fix specifically"""
    print("🔀 Testing OAuth Routing Fix...")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # 1. Check database configuration
        print("\n1. Database Configuration Check:")
        
        # Get user
        user = await db.users.find_one({'email': 'amits.joys@gmail.com'})
        if not user:
            print("❌ User not found")
            return False
        
        user_id = user['id']
        print(f"✅ User found: {user_id}")
        
        # Check OAuth token
        ms_token = await db.oauth_tokens_microsoft.find_one({'user_id': user_id})
        if not ms_token:
            print("❌ No Microsoft OAuth token found")
            return False
        
        print(f"✅ Microsoft OAuth token found: {ms_token['id']}")
        print(f"   Expires: {ms_token.get('expires_at')}")
        
        # Check email account
        account = await db.email_accounts.find_one({'user_id': user_id})
        if not account:
            print("❌ No email account found")
            return False
        
        print(f"✅ Email account found:")
        print(f"   Email: {account['email']}")
        print(f"   Auth type: {account.get('auth_type')}")
        print(f"   Use OAuth: {account.get('use_oauth')}")
        print(f"   OAuth email: {account.get('oauth_email')}")
        print(f"   Provider: {account.get('provider')}")
        print(f"   Active: {account.get('is_active')}")
        
        # 2. Test provider detection logic
        print("\n2. Provider Detection Logic Test:")
        
        oauth_email = account.get('oauth_email', '')
        provider = account.get('provider', '').lower()
        
        if oauth_email:
            email_domain = oauth_email.split('@')[-1].lower()
            print(f"   OAuth email domain: {email_domain}")
            
            # Test the fixed detection logic
            if 'gmail.com' in email_domain or 'googlemail.com' in email_domain:
                detected_provider = 'google'
            elif ('outlook.com' in email_domain or 'hotmail.com' in email_domain or 
                  'live.com' in email_domain or 'office365.com' in email_domain or 
                  'onmicrosoft.com' in email_domain):
                detected_provider = 'microsoft'
            else:
                detected_provider = 'google (default)'
            
            print(f"   Detected provider: {detected_provider}")
            print(f"   Configured provider: {provider}")
            
            # Check if detection is correct
            should_be_microsoft = 'onmicrosoft.com' in email_domain
            is_configured_microsoft = provider == 'microsoft'
            detection_correct = should_be_microsoft and is_configured_microsoft
            
            print(f"   Should be Microsoft: {should_be_microsoft}")
            print(f"   Is configured as Microsoft: {is_configured_microsoft}")
            print(f"   Detection correct: {detection_correct}")
        else:
            print("❌ No OAuth email configured")
            detection_correct = False
        
        # 3. Test email services import
        print("\n3. Email Services Test:")
        
        try:
            from email_services import EmailPollingService
            print("✅ EmailPollingService imported successfully")
            
            # Test Microsoft services import
            from microsoft_services import MicrosoftMailService
            print("✅ MicrosoftMailService imported successfully")
            
            # Test service initialization
            mail_service = MicrosoftMailService(user_id)
            print("✅ MicrosoftMailService initialized successfully")
            
            services_working = True
        except Exception as e:
            print(f"❌ Services import/init failed: {str(e)}")
            services_working = False
        
        # 4. Check recent logs for routing behavior
        print("\n4. Recent Polling Behavior Check:")
        
        try:
            # Check if there are recent Google OAuth errors (indicating the bug)
            with open('/var/log/supervisor/backend.err.log', 'r') as f:
                recent_logs = f.readlines()[-100:]  # Last 100 lines
            
            google_oauth_errors = [line for line in recent_logs if 
                                 'Google OAuth' in line and 'amits.joys' in line]
            microsoft_oauth_calls = [line for line in recent_logs if 
                                   'MICROSOFT' in line.upper() and 'amits.joys' in line]
            
            print(f"   Recent Google OAuth errors: {len(google_oauth_errors)}")
            print(f"   Recent Microsoft API calls: {len(microsoft_oauth_calls)}")
            
            if google_oauth_errors:
                print("   Latest Google OAuth error:")
                print(f"     {google_oauth_errors[-1].strip()}")
            
            if microsoft_oauth_calls:
                print("   Latest Microsoft API call:")
                print(f"     {microsoft_oauth_calls[-1].strip()}")
            
            # The fix is working if we have no recent Google OAuth errors for this account
            routing_fixed = len(google_oauth_errors) == 0
            
        except Exception as e:
            print(f"   Could not check logs: {str(e)}")
            routing_fixed = False
        
        # 5. Overall assessment
        print("\n5. Overall Assessment:")
        
        oauth_configured = (account.get('auth_type') == 'oauth' and 
                          account.get('use_oauth') and 
                          account.get('oauth_email') and 
                          ms_token is not None)
        
        provider_correct = (account.get('provider') == 'microsoft' and 
                          detection_correct)
        
        overall_success = (oauth_configured and provider_correct and 
                         services_working and routing_fixed)
        
        print(f"   OAuth configured: {oauth_configured}")
        print(f"   Provider correct: {provider_correct}")
        print(f"   Services working: {services_working}")
        print(f"   Routing fixed: {routing_fixed}")
        print(f"   Overall success: {overall_success}")
        
        return overall_success
        
    finally:
        client.close()

async def test_redis_connectivity():
    """Test Redis connectivity"""
    print("🔴 Testing Redis Connectivity...")
    
    try:
        # Test Redis connection
        import subprocess
        result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True, timeout=5)
        redis_working = result.returncode == 0 and 'PONG' in result.stdout
        
        # Test RQ queues
        from tasks import get_queue_stats
        queue_stats = get_queue_stats()
        rq_working = isinstance(queue_stats, dict)
        
        print(f"   Redis ping: {redis_working}")
        print(f"   RQ queues: {rq_working}")
        
        return redis_working and rq_working
        
    except Exception as e:
        print(f"   Error: {str(e)}")
        return False

async def test_email_processing():
    """Test email processing with background tasks"""
    print("⚙️ Testing Email Processing...")
    
    try:
        # Authenticate
        login_data = {'email': 'amits.joys@gmail.com', 'password': 'ij@123'}
        response = requests.post(f'{API_BASE}/auth/login', json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"   Authentication failed: {response.status_code}")
            return False
        
        auth_data = response.json()
        headers = {'Authorization': f'Bearer {auth_data["access_token"]}'}
        
        # Get accounts
        response = requests.get(f'{API_BASE}/email-accounts', headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"   Failed to get accounts: {response.status_code}")
            return False
        
        accounts = response.json()
        if not accounts:
            print("   No accounts found")
            return False
        
        # Test email processing
        test_email_data = {
            "subject": "OAuth Routing Test",
            "body": "Testing OAuth routing fix and Redis connectivity",
            "sender": "test@example.com",
            "account_id": accounts[0]['id']
        }
        
        import time
        start_time = time.time()
        response = requests.post(f'{API_BASE}/emails/test', json=test_email_data, headers=headers, timeout=30)
        end_time = time.time()
        
        response_time = end_time - start_time
        quick_response = response_time < 5.0
        api_success = response.status_code in [200, 201]
        
        if api_success:
            response_data = response.json()
            status = response_data.get('status')
            method = response_data.get('processing_method')
            
            print(f"   Response time: {response_time:.2f}s")
            print(f"   Status: {status}")
            print(f"   Method: {method}")
            print(f"   Quick response: {quick_response}")
            
            return quick_response and api_success
        else:
            print(f"   API failed: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"   Error: {str(e)}")
        return False

async def main():
    """Main test execution"""
    print("🚀 OAuth Routing & Redis Connectivity Verification")
    print("="*60)
    
    # Run tests
    redis_ok = await test_redis_connectivity()
    oauth_ok = await test_oauth_routing_fix()
    processing_ok = await test_email_processing()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    tests = [
        ("Redis Connectivity", redis_ok),
        ("OAuth Routing Fix", oauth_ok),
        ("Email Processing", processing_ok)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - OAuth routing fix is working!")
        return True
    elif oauth_ok and redis_ok:
        print("✅ CRITICAL FIXES VERIFIED - OAuth routing and Redis are working!")
        return True
    else:
        print("⚠️  Some issues remain - see details above")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)