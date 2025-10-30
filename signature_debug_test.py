#!/usr/bin/env python3
"""
Debug Signature Processing - Check what's happening with signature processing
"""
import asyncio
import sys
import os
import requests
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://setup-redis-sync.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def debug_signature_processing():
    """Debug signature processing step by step"""
    print("🔍 Debug Signature Processing")
    
    # Connect to database
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Import required functions
        from server import EmailMessage, validate_final_email, generate_draft, classify_email_intents
        
        # Get an existing account with signature
        account = await db.email_accounts.find_one({"signature": {"$ne": ""}})
        if not account:
            print("❌ No account with signature found")
            return
        
        print(f"✅ Using account: {account['email']}")
        print(f"   Signature: '{account['signature']}'")
        print(f"   Signature length: {len(account['signature'])}")
        
        # Create test email
        test_email = EmailMessage(
            account_id=account['id'],
            message_id=f"<debug-test-{uuid.uuid4()}@example.com>",
            thread_id=f"thread-{uuid.uuid4()}",
            subject="Debug Signature Test",
            sender="debug.test@example.com",
            recipient=account['email'],
            body="Hello! I'm interested in your services. Could you please provide more information about pricing and features? Thank you!",
            received_at=datetime.utcnow(),
            status="new"
        )
        
        print("\n🔍 Step 1: Testing email classification...")
        intents = await classify_email_intents(test_email)
        print(f"   Found {len(intents)} intents")
        
        print("\n📝 Step 2: Testing draft generation...")
        draft = await generate_draft(test_email, intents)
        print(f"   Draft plain text length: {len(draft.get('plain_text', ''))}")
        print(f"   Draft HTML length: {len(draft.get('html', ''))}")
        print(f"   Draft plain text (last 100 chars): '{draft.get('plain_text', '')[-100:]}'")
        print(f"   Draft HTML (last 100 chars): '{draft.get('html', '')[-100:]}'")
        
        print("\n✅ Step 3: Testing signature validation...")
        validation_result = await validate_final_email(test_email, draft, intents, account)
        print(f"   Validation status: {validation_result.get('status', 'None')}")
        print(f"   Has final_plain_text: {'final_plain_text' in validation_result}")
        print(f"   Has final_html: {'final_html' in validation_result}")
        
        if 'final_plain_text' in validation_result:
            final_plain = validation_result['final_plain_text']
            final_html = validation_result['final_html']
            print(f"   Final plain text length: {len(final_plain)}")
            print(f"   Final HTML length: {len(final_html)}")
            print(f"   Final plain text (last 200 chars): '{final_plain[-200:]}'")
            print(f"   Final HTML (last 200 chars): '{final_html[-200:]}'")
            
            # Check if signature is in final content
            signature_text = account['signature']
            signature_in_final_plain = signature_text in final_plain
            signature_in_final_html = signature_text in final_html
            
            print(f"   Signature in final plain: {signature_in_final_plain}")
            print(f"   Signature in final HTML: {signature_in_final_html}")
            
            # Check for signature keywords
            signature_keywords = ['regards', 'best', 'sincerely', 'assistant', 'team']
            keywords_in_plain = [kw for kw in signature_keywords if kw.lower() in final_plain.lower()]
            keywords_in_html = [kw for kw in signature_keywords if kw.lower() in final_html.lower()]
            
            print(f"   Signature keywords in plain: {keywords_in_plain}")
            print(f"   Signature keywords in HTML: {keywords_in_html}")
        else:
            print("   ❌ No final content returned from validation")
        
        return validation_result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        client.close()

async def test_api_with_signature():
    """Test API endpoint and check database result"""
    print("\n🌐 Testing API with Signature Check...")
    
    try:
        # Get accounts
        response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
        if response.status_code != 200 or not response.json():
            print("❌ No email accounts available")
            return False
        
        account = response.json()[0]
        account_id = account['id']
        print(f"   Using account: {account_id}")
        
        # Test email with signature request
        test_data = {
            "subject": "API Signature Test",
            "body": "Hello, I need information about your services and pricing. Please provide details. Thank you!",
            "sender": "api.signature.test@example.com",
            "account_id": account_id
        }
        
        print("   Sending test email request...")
        response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=30)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   ✅ API call successful")
            print(f"   Status: {result.get('status', 'None')}")
            print(f"   Draft length: {len(result.get('draft', ''))}")
            print(f"   HTML length: {len(result.get('draft_html', ''))}")
            
            # Check for signature in response
            draft_text = result.get('draft', '')
            draft_html = result.get('draft_html', '')
            
            print(f"   Draft (last 200 chars): '{draft_text[-200:]}'")
            print(f"   HTML (last 200 chars): '{draft_html[-200:]}'")
            
            # Check for signature keywords
            signature_keywords = ['regards', 'best', 'sincerely', 'assistant', 'team']
            keywords_in_draft = [kw for kw in signature_keywords if kw.lower() in draft_text.lower()]
            keywords_in_html = [kw for kw in signature_keywords if kw.lower() in draft_html.lower()]
            
            print(f"   Signature keywords in draft: {keywords_in_draft}")
            print(f"   Signature keywords in HTML: {keywords_in_html}")
            
            # Check validation result
            validation = result.get('validation_result', {})
            print(f"   Validation status: {validation.get('status', 'None')}")
            print(f"   Signature included (validation): {validation.get('automated_checks', {}).get('signature_included', False)}")
            
            return len(keywords_in_draft) > 0 or len(keywords_in_html) > 0
        else:
            print(f"   ❌ API call failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ API test failed: {str(e)}")
        return False

async def main():
    print("🚀 Starting Signature Debug Tests...")
    
    # Test 1: Direct signature processing debug
    validation_result = await debug_signature_processing()
    
    # Test 2: API endpoint with signature check
    api_signature_working = await test_api_with_signature()
    
    print(f"\n📋 Debug Summary:")
    print(f"   Direct validation working: {'✅' if validation_result else '❌'}")
    print(f"   API signature working: {'✅' if api_signature_working else '❌'}")
    
    if validation_result and 'final_plain_text' in validation_result:
        print(f"   Signature processing: ✅ WORKING (validation returns final content)")
    else:
        print(f"   Signature processing: ❌ NOT WORKING (validation doesn't return final content)")

if __name__ == "__main__":
    asyncio.run(main())