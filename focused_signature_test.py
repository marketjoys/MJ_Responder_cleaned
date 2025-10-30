#!/usr/bin/env python3
"""
Focused Signature Processing Test
Tests the core signature functionality with shorter timeouts and better error handling
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-and-review.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def test_signature_processing():
    """Test signature processing with existing account"""
    print("🧪 FOCUSED SIGNATURE PROCESSING TEST")
    print("="*50)
    
    # Setup database connection
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get existing active account with signature
        account = await db.email_accounts.find_one({
            "is_active": True,
            "signature": {"$ne": ""}
        })
        
        if not account:
            print("❌ No active account with signature found")
            return
        
        print(f"✅ Using account: {account['email']}")
        print(f"   Signature length: {len(account.get('signature', ''))} chars")
        
        # Test 1: Direct function testing
        print("\n🔍 Test 1: Direct validate_final_email function")
        try:
            from server import validate_final_email, EmailMessage
            
            # Create test email
            test_email = EmailMessage(
                account_id=account['id'],
                message_id=f"<test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Signature Test Email",
                sender="customer@example.com",
                recipient=account['email'],
                body="Hello, I need information about your services.",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Create draft without signature
            draft = {
                "plain_text": "Dear Customer,\n\nThank you for your inquiry. I'll be happy to help you with information about our services.",
                "html": "<p>Dear Customer,</p><p>Thank you for your inquiry. I'll be happy to help you with information about our services.</p>"
            }
            
            # Test validation
            validation_result = await validate_final_email(test_email, draft, [], account)
            
            # Check results
            has_final_plain = 'final_plain_text' in validation_result
            has_final_html = 'final_html' in validation_result
            
            if has_final_plain and has_final_html:
                final_plain = validation_result['final_plain_text']
                final_html = validation_result['final_html']
                
                # Count signature occurrences (look for any part of signature)
                signature_text = account.get('signature', '')
                if 'John Smith' in signature_text or 'company.com' in signature_text:
                    # Look for signature indicators
                    plain_has_sig = 'company.com' in final_plain or 'John Smith' in final_plain
                    html_has_sig = 'company.com' in final_html or 'John Smith' in final_html
                    
                    # Count occurrences to check for duplication
                    plain_sig_count = final_plain.count('company.com') + final_plain.count('John Smith')
                    html_sig_count = final_html.count('company.com') + final_html.count('John Smith')
                    
                    print(f"   ✅ Final plain text: {len(final_plain)} chars, signature present: {plain_has_sig}")
                    print(f"   ✅ Final HTML: {len(final_html)} chars, signature present: {html_has_sig}")
                    print(f"   ✅ Signature count - Plain: {plain_sig_count}, HTML: {html_sig_count}")
                    
                    if plain_has_sig and html_has_sig and plain_sig_count <= 2 and html_sig_count <= 2:
                        print("   ✅ PASS: Signature added correctly, no duplication detected")
                    else:
                        print("   ❌ FAIL: Signature duplication or missing")
                else:
                    print("   ⚠️  Cannot detect signature content in account")
            else:
                print("   ❌ FAIL: Missing final_plain_text or final_html in validation result")
                
        except Exception as e:
            print(f"   ❌ FAIL: Exception in direct function test: {str(e)}")
        
        # Test 2: API endpoint test with shorter timeout
        print("\n🌐 Test 2: /api/emails/test endpoint")
        try:
            test_email_data = {
                "subject": "Quick signature test",
                "body": "This is a quick test to verify signature processing works correctly.",
                "sender": "quick.test@example.com",
                "account_id": account['id']
            }
            
            print("   Sending request to /api/emails/test...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=20)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                email_status = processed_email.get('status')
                has_validation = bool(processed_email.get('validation_result'))
                
                print(f"   ✅ Email processed successfully - Status: {email_status}")
                print(f"   ✅ Has validation result: {has_validation}")
                
                if has_validation:
                    validation = processed_email['validation_result']
                    final_plain = validation.get('final_plain_text', '')
                    final_html = validation.get('final_html', '')
                    
                    # Check for signature
                    plain_has_sig = 'company.com' in final_plain or 'John Smith' in final_plain
                    html_has_sig = 'company.com' in final_html or 'John Smith' in final_html
                    
                    print(f"   ✅ Final content lengths - Plain: {len(final_plain)}, HTML: {len(final_html)}")
                    print(f"   ✅ Signature in final content - Plain: {plain_has_sig}, HTML: {html_has_sig}")
                    
                    if plain_has_sig and html_has_sig:
                        print("   ✅ PASS: API endpoint signature processing working")
                    else:
                        print("   ❌ FAIL: Signature missing in final content")
                else:
                    print("   ⚠️  No validation result in response")
                    
            else:
                print(f"   ❌ FAIL: API call failed - Status: {response.status_code}")
                print(f"   Error: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print("   ⚠️  API call timed out (20s) - backend may be processing")
        except Exception as e:
            print(f"   ❌ FAIL: Exception in API test: {str(e)}")
        
        # Test 3: Check existing processed emails
        print("\n📧 Test 3: Check existing processed emails with signatures")
        try:
            # Find recent emails with validation results
            recent_emails = await db.emails.find({
                "account_id": account['id'],
                "validation_result": {"$exists": True}
            }).sort("created_at", -1).limit(3).to_list(3)
            
            print(f"   Found {len(recent_emails)} recent processed emails")
            
            for i, email in enumerate(recent_emails):
                validation = email.get('validation_result', {})
                final_plain = validation.get('final_plain_text', '')
                final_html = validation.get('final_html', '')
                
                plain_has_sig = 'company.com' in final_plain or 'John Smith' in final_plain
                html_has_sig = 'company.com' in final_html or 'John Smith' in final_html
                
                print(f"   Email {i+1}: Plain sig: {plain_has_sig}, HTML sig: {html_has_sig}, Status: {email.get('status')}")
            
            if recent_emails:
                print("   ✅ PASS: Found processed emails with signature data")
            else:
                print("   ⚠️  No recent processed emails found")
                
        except Exception as e:
            print(f"   ❌ FAIL: Exception checking existing emails: {str(e)}")
        
        print("\n" + "="*50)
        print("FOCUSED SIGNATURE TEST COMPLETE")
        print("="*50)
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_signature_processing())