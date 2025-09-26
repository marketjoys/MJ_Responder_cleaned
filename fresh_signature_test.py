#!/usr/bin/env python3
"""
Fresh Signature Test - Test with completely new data
"""
import asyncio
import sys
import os
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def fresh_signature_test():
    """Test signature processing with fresh data"""
    print("🧪 FRESH SIGNATURE PROCESSING TEST")
    print("="*50)
    
    # Setup database connection
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get the main account
        account = await db.email_accounts.find_one({
            "email": "rohushanshinde@gmail.com"
        })
        
        if not account:
            print("❌ Account not found")
            return
        
        print(f"✅ Account: {account['email']}")
        signature = account.get('signature', '')
        print(f"   Signature: {repr(signature)}")
        
        # Import functions
        from server import generate_draft, classify_email_intents, EmailMessage, validate_final_email
        
        # Test 1: Fresh draft generation
        print(f"\n🔍 Test 1: Fresh Draft Generation")
        test_email1 = EmailMessage(
            account_id=account['id'],
            message_id=f"<fresh-draft-{uuid.uuid4()}@example.com>",
            thread_id=f"thread-{uuid.uuid4()}",
            subject="Fresh Draft Test",
            sender="fresh.test@example.com",
            recipient=account['email'],
            body="I'm interested in your AI email automation solution. What are the key benefits and pricing options?",
            received_at=datetime.utcnow(),
            status="new"
        )
        
        # Generate fresh draft
        intents1 = await classify_email_intents(test_email1)
        draft1 = await generate_draft(test_email1, intents1)
        
        plain1 = draft1.get('plain_text', '')
        html1 = draft1.get('html', '')
        
        # Check for signature in draft
        plain_has_sig = 'AI Email Assistant' in plain1
        html_has_sig = 'AI Email Assistant' in html1
        
        print(f"   Draft lengths: Plain={len(plain1)}, HTML={len(html1)}")
        print(f"   Signature in draft: Plain={plain_has_sig}, HTML={html_has_sig}")
        
        if not plain_has_sig and not html_has_sig:
            print("   ✅ PASS: Draft generated without signature")
            draft_test_passed = True
        else:
            print("   ❌ FAIL: Draft contains signature")
            draft_test_passed = False
        
        # Test 2: Validation adds signature
        print(f"\n🔍 Test 2: Validation Adds Signature")
        validation_result = await validate_final_email(test_email1, draft1, intents1, account)
        
        final_plain = validation_result.get('final_plain_text', '')
        final_html = validation_result.get('final_html', '')
        
        # Check signature in final content
        final_plain_has_sig = 'AI Email Assistant' in final_plain
        final_html_has_sig = 'AI Email Assistant' in final_html
        
        # Count occurrences
        plain_sig_count = final_plain.count('AI Email Assistant')
        html_sig_count = final_html.count('AI Email Assistant')
        
        print(f"   Final lengths: Plain={len(final_plain)}, HTML={len(final_html)}")
        print(f"   Signature in final: Plain={final_plain_has_sig} (count={plain_sig_count}), HTML={final_html_has_sig} (count={html_sig_count})")
        
        if final_plain_has_sig and final_html_has_sig and plain_sig_count == 1 and html_sig_count == 1:
            print("   ✅ PASS: Validation adds signature exactly once")
            validation_test_passed = True
        else:
            print("   ❌ FAIL: Signature not added correctly or duplicated")
            validation_test_passed = False
        
        # Test 3: Check signature content
        print(f"\n🔍 Test 3: Signature Content Verification")
        if final_plain_has_sig:
            # Find signature position
            sig_pos = final_plain.find('AI Email Assistant')
            signature_section = final_plain[sig_pos-20:sig_pos+100]  # Context around signature
            print(f"   Signature context: {repr(signature_section)}")
            
            # Check if it matches expected signature
            expected_parts = ['Best regards', 'AI Email Assistant', 'Technology Solutions Team']
            all_parts_present = all(part in final_plain for part in expected_parts)
            
            if all_parts_present:
                print("   ✅ PASS: All signature parts present")
                content_test_passed = True
            else:
                print("   ❌ FAIL: Missing signature parts")
                content_test_passed = False
        else:
            print("   ❌ FAIL: No signature found")
            content_test_passed = False
        
        # Summary
        print(f"\n" + "="*50)
        print("FRESH SIGNATURE TEST RESULTS")
        print("="*50)
        
        tests = [
            ("Draft Generation (No Signature)", draft_test_passed),
            ("Validation Adds Signature", validation_test_passed),
            ("Signature Content Correct", content_test_passed)
        ]
        
        passed = sum(1 for _, result in tests if result)
        total = len(tests)
        
        print(f"Passed: {passed}/{total}")
        
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        if passed == total:
            print(f"\n🎉 ALL TESTS PASSED: Signature double fix is working correctly!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
        
        print("="*50)
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fresh_signature_test())