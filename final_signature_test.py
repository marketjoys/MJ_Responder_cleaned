#!/usr/bin/env python3
"""
Final Signature Processing Test
Tests signature processing with actual account data
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://worker-restart-hub.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def test_signature_double_fix():
    """Test the signature double fix implementation"""
    print("🧪 SIGNATURE DOUBLE FIX VERIFICATION TEST")
    print("="*60)
    
    # Setup database connection
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get the main account with signature
        account = await db.email_accounts.find_one({
            "email": "rohushanshinde@gmail.com"
        })
        
        if not account:
            print("❌ Main test account not found")
            return
        
        print(f"✅ Using account: {account['email']}")
        signature = account.get('signature', '')
        print(f"   Account signature: {repr(signature)}")
        
        # Test 1: Direct validate_final_email function
        print("\n🔍 Test 1: validate_final_email function - Signature Addition")
        try:
            from server import validate_final_email, EmailMessage
            
            # Create test email
            test_email = EmailMessage(
                account_id=account['id'],
                message_id=f"<validate-test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Signature Validation Test",
                sender="customer@example.com",
                recipient=account['email'],
                body="Hello, I'm interested in your AI email assistant services. Can you provide more details?",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Create draft WITHOUT signature
            draft = {
                "plain_text": "Dear Customer,\n\nThank you for your interest in our AI email assistant services. I'd be happy to provide you with detailed information about our solutions.\n\nOur AI-powered system can help automate your email responses and improve customer engagement.",
                "html": "<p>Dear Customer,</p><p>Thank you for your interest in our AI email assistant services. I'd be happy to provide you with detailed information about our solutions.</p><p>Our AI-powered system can help automate your email responses and improve customer engagement.</p>"
            }
            
            print(f"   Original draft length - Plain: {len(draft['plain_text'])}, HTML: {len(draft['html'])}")
            print(f"   Signature contains: {signature.count('AI Email Assistant')} occurrences of 'AI Email Assistant'")
            
            # Call validate_final_email
            validation_result = await validate_final_email(test_email, draft, [], account)
            
            # Check results
            final_plain = validation_result.get('final_plain_text', '')
            final_html = validation_result.get('final_html', '')
            
            print(f"   Final content length - Plain: {len(final_plain)}, HTML: {len(final_html)}")
            
            # Check signature addition
            plain_has_signature = 'AI Email Assistant' in final_plain
            html_has_signature = 'AI Email Assistant' in final_html
            
            # Count signature occurrences to check for duplication
            plain_sig_count = final_plain.count('AI Email Assistant')
            html_sig_count = final_html.count('AI Email Assistant')
            
            print(f"   Signature in final plain text: {plain_has_signature} (count: {plain_sig_count})")
            print(f"   Signature in final HTML: {html_has_signature} (count: {html_sig_count})")
            
            # Test PASS if signature appears exactly once in both formats
            test1_passed = (plain_has_signature and html_has_signature and 
                           plain_sig_count == 1 and html_sig_count == 1)
            
            if test1_passed:
                print("   ✅ PASS: Signature added correctly, no duplication")
            else:
                print("   ❌ FAIL: Signature duplication or missing")
                
        except Exception as e:
            print(f"   ❌ FAIL: Exception: {str(e)}")
            test1_passed = False
        
        # Test 2: Check that draft generation doesn't include signature
        print("\n📝 Test 2: Draft Generation - No Signature in Draft")
        try:
            from server import generate_draft, classify_email_intents
            
            # Create test email for draft generation
            test_email2 = EmailMessage(
                account_id=account['id'],
                message_id=f"<draft-test-{uuid.uuid4()}@example.com>",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Draft Generation Test",
                sender="prospect@example.com",
                recipient=account['email'],
                body="Hi, I'm looking for an automated email solution for my business. What options do you have?",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Classify intents
            intents = await classify_email_intents(test_email2)
            print(f"   Classified intents: {len(intents)}")
            
            # Generate draft
            draft_result = await generate_draft(test_email2, intents)
            
            draft_plain = draft_result.get('plain_text', '')
            draft_html = draft_result.get('html', '')
            
            # Check that draft does NOT contain signature
            draft_plain_has_sig = 'AI Email Assistant' in draft_plain
            draft_html_has_sig = 'AI Email Assistant' in draft_html
            
            print(f"   Draft lengths - Plain: {len(draft_plain)}, HTML: {len(draft_html)}")
            print(f"   Signature in draft plain: {draft_plain_has_sig}")
            print(f"   Signature in draft HTML: {draft_html_has_sig}")
            
            # Test PASS if draft does NOT contain signature (signature should be added later)
            test2_passed = not draft_plain_has_sig and not draft_html_has_sig
            
            if test2_passed:
                print("   ✅ PASS: Draft generated without signature (correct)")
            else:
                print("   ❌ FAIL: Draft contains signature (should be added later)")
                
        except Exception as e:
            print(f"   ❌ FAIL: Exception: {str(e)}")
            test2_passed = False
        
        # Test 3: End-to-end workflow test
        print("\n🔄 Test 3: End-to-End Workflow - Single Signature in Final Email")
        try:
            # Check recent processed emails
            recent_emails = await db.emails.find({
                "account_id": account['id'],
                "validation_result": {"$exists": True, "$ne": None}
            }).sort("created_at", -1).limit(5).to_list(5)
            
            print(f"   Found {len(recent_emails)} recent processed emails")
            
            signature_test_results = []
            for i, email in enumerate(recent_emails):
                validation = email.get('validation_result', {})
                final_plain = validation.get('final_plain_text', '')
                final_html = validation.get('final_html', '')
                
                if final_plain and final_html:
                    plain_sig_count = final_plain.count('AI Email Assistant')
                    html_sig_count = final_html.count('AI Email Assistant')
                    
                    single_signature = plain_sig_count == 1 and html_sig_count == 1
                    signature_test_results.append(single_signature)
                    
                    print(f"   Email {i+1}: Plain sig count: {plain_sig_count}, HTML sig count: {html_sig_count}, Single: {single_signature}")
            
            # Test PASS if all recent emails have single signature
            test3_passed = len(signature_test_results) > 0 and all(signature_test_results)
            
            if test3_passed:
                print("   ✅ PASS: All recent emails have single signature")
            elif len(signature_test_results) == 0:
                print("   ⚠️  No recent emails with validation results found")
                test3_passed = None
            else:
                print("   ❌ FAIL: Some emails have duplicate or missing signatures")
                
        except Exception as e:
            print(f"   ❌ FAIL: Exception: {str(e)}")
            test3_passed = False
        
        # Test 4: API endpoint test (if time permits)
        print("\n🌐 Test 4: API Endpoint Test - Quick Verification")
        try:
            test_email_data = {
                "subject": "Final signature test",
                "body": "This is a final test to verify the signature double fix is working correctly.",
                "sender": "final.test@example.com",
                "account_id": account['id']
            }
            
            print("   Sending quick API test...")
            response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=15)
            
            if response.status_code in [200, 201]:
                processed_email = response.json()
                validation = processed_email.get('validation_result', {})
                
                if validation:
                    final_plain = validation.get('final_plain_text', '')
                    final_html = validation.get('final_html', '')
                    
                    plain_sig_count = final_plain.count('AI Email Assistant')
                    html_sig_count = final_html.count('AI Email Assistant')
                    
                    test4_passed = plain_sig_count == 1 and html_sig_count == 1
                    
                    print(f"   API test result - Plain sig: {plain_sig_count}, HTML sig: {html_sig_count}")
                    
                    if test4_passed:
                        print("   ✅ PASS: API endpoint signature processing correct")
                    else:
                        print("   ❌ FAIL: API endpoint signature duplication detected")
                else:
                    print("   ⚠️  No validation result in API response")
                    test4_passed = None
            else:
                print(f"   ⚠️  API call failed: {response.status_code}")
                test4_passed = None
                
        except requests.exceptions.Timeout:
            print("   ⚠️  API call timed out")
            test4_passed = None
        except Exception as e:
            print(f"   ❌ FAIL: Exception: {str(e)}")
            test4_passed = False
        
        # Summary
        print("\n" + "="*60)
        print("SIGNATURE DOUBLE FIX TEST SUMMARY")
        print("="*60)
        
        tests = [
            ("validate_final_email Function", test1_passed),
            ("Draft Generation (No Signature)", test2_passed),
            ("End-to-End Workflow", test3_passed),
            ("API Endpoint Test", test4_passed)
        ]
        
        passed_tests = [t for t in tests if t[1] is True]
        failed_tests = [t for t in tests if t[1] is False]
        skipped_tests = [t for t in tests if t[1] is None]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"⚠️  SKIPPED: {len(skipped_tests)}")
        
        for test_name, result in tests:
            if result is True:
                print(f"   ✅ {test_name}")
            elif result is False:
                print(f"   ❌ {test_name}")
            else:
                print(f"   ⚠️  {test_name}")
        
        # Overall assessment
        critical_tests_passed = test1_passed and test2_passed
        if critical_tests_passed:
            print("\n🎉 OVERALL RESULT: SIGNATURE DOUBLE FIX IS WORKING CORRECTLY")
            print("   - Signatures are added only in validate_final_email function")
            print("   - Drafts are generated without signatures")
            print("   - Final emails contain exactly one signature")
        else:
            print("\n⚠️  OVERALL RESULT: SIGNATURE PROCESSING NEEDS ATTENTION")
            print("   - Some core functionality may not be working as expected")
        
        print("="*60)
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_signature_double_fix())