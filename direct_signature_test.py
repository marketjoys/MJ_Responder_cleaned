#!/usr/bin/env python3
"""
Direct Signature Processing Test - Test signature processing without API timeouts
"""
import asyncio
import sys
import os
import requests
import json
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://oauth-outlook-sync.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def test_signature_processing():
    """Test signature processing directly"""
    print("🧪 Direct Signature Processing Test")
    
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
        print(f"   Signature: {account['signature'][:100]}...")
        
        # Create test email
        test_email = EmailMessage(
            account_id=account['id'],
            message_id=f"<direct-test-{uuid.uuid4()}@example.com>",
            thread_id=f"thread-{uuid.uuid4()}",
            subject="Direct Signature Test",
            sender="direct.test@example.com",
            recipient=account['email'],
            body="Hello! I'm interested in your services. Could you please provide more information about pricing and features? Thank you!",
            received_at=datetime.utcnow(),
            status="new"
        )
        
        print("🔍 Testing email classification...")
        intents = await classify_email_intents(test_email)
        print(f"   Found {len(intents)} intents")
        
        print("📝 Testing draft generation...")
        draft = await generate_draft(test_email, intents)
        print(f"   Draft plain text length: {len(draft.get('plain_text', ''))}")
        print(f"   Draft HTML length: {len(draft.get('html', ''))}")
        
        print("✅ Testing signature validation...")
        validation_result = await validate_final_email(test_email, draft, intents, account)
        print(f"   Validation status: {validation_result.get('status', 'None')}")
        
        # Check signature processing
        signature = account.get('signature', '')
        draft_html = draft.get('html', '')
        draft_plain = draft.get('plain_text', '')
        
        # Check for signature inclusion
        signature_in_html = any(word in draft_html.lower() for word in ['regards', 'best', 'sincerely'])
        signature_in_plain = any(word in draft_plain.lower() for word in ['regards', 'best', 'sincerely'])
        
        # Check for double-encoding issues
        no_double_encoding = '&lt;br&gt;' not in draft_html and '&amp;' not in draft_html
        
        # Check BR tag count (should be reasonable)
        br_count = draft_html.lower().count('<br')
        reasonable_br_count = br_count < 15
        
        print(f"\n📊 Signature Processing Results:")
        print(f"   Signature in HTML: {signature_in_html}")
        print(f"   Signature in Plain: {signature_in_plain}")
        print(f"   No double-encoding: {no_double_encoding}")
        print(f"   BR tag count: {br_count} (reasonable: {reasonable_br_count})")
        print(f"   Validation passed: {validation_result.get('status') == 'PASS'}")
        
        # Show sample of HTML output
        print(f"\n📄 Sample HTML output (last 200 chars):")
        print(f"   {draft_html[-200:]}")
        
        # Show sample of plain text output
        print(f"\n📄 Sample Plain text output (last 200 chars):")
        print(f"   {draft_plain[-200:]}")
        
        # Overall assessment
        signature_processing_working = (signature_in_html and signature_in_plain and 
                                      no_double_encoding and reasonable_br_count)
        
        print(f"\n🎯 Overall Signature Processing: {'✅ WORKING' if signature_processing_working else '❌ ISSUES FOUND'}")
        
        return signature_processing_working
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        client.close()

async def test_api_endpoint_simple():
    """Test API endpoint with shorter timeout"""
    print("\n🌐 Testing API Endpoint (Simple)...")
    
    try:
        # Get accounts
        response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
        if response.status_code != 200 or not response.json():
            print("❌ No email accounts available")
            return False
        
        account = response.json()[0]
        account_id = account['id']
        
        # Simple test email
        test_data = {
            "subject": "Simple API Test",
            "body": "Hello, I need information about your services. Thank you!",
            "sender": "simple.test@example.com",
            "account_id": account_id
        }
        
        print("   Sending test email request...")
        response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=20)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   ✅ API call successful")
            print(f"   Status: {result.get('status', 'None')}")
            print(f"   Draft length: {len(result.get('draft', ''))}")
            print(f"   HTML length: {len(result.get('draft_html', ''))}")
            return True
        else:
            print(f"   ❌ API call failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ API test failed: {str(e)}")
        return False

async def main():
    print("🚀 Starting Direct Signature Tests...")
    
    # Test 1: Direct signature processing
    direct_test_passed = await test_signature_processing()
    
    # Test 2: Simple API test
    api_test_passed = await test_api_endpoint_simple()
    
    print(f"\n📋 Summary:")
    print(f"   Direct signature processing: {'✅ PASS' if direct_test_passed else '❌ FAIL'}")
    print(f"   API endpoint test: {'✅ PASS' if api_test_passed else '❌ FAIL'}")
    
    overall_passed = direct_test_passed and api_test_passed
    print(f"   Overall: {'✅ SIGNATURE PROCESSING WORKING' if overall_passed else '❌ ISSUES DETECTED'}")

if __name__ == "__main__":
    asyncio.run(main())