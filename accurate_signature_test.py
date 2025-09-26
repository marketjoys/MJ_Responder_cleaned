#!/usr/bin/env python3
"""
Accurate Signature Test - Distinguish between product mentions and actual signatures
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

async def accurate_signature_test():
    """Test signature processing accurately"""
    print("🧪 ACCURATE SIGNATURE PROCESSING TEST")
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
        
        # Test 1: Check if draft has signature BLOCK (not just product mentions)
        print(f"\n🔍 Test 1: Draft Generation - Check for Signature Block")
        test_email1 = EmailMessage(
            account_id=account['id'],
            message_id=f"<accurate-draft-{uuid.uuid4()}@example.com>",
            thread_id=f"thread-{uuid.uuid4()}",
            subject="Accurate Draft Test",
            sender="accurate.test@example.com",
            recipient=account['email'],
            body="I need information about your services. Can you help me?",
            received_at=datetime.utcnow(),
            status="new"
        )
        
        # Generate draft
        intents1 = await classify_email_intents(test_email1)
        draft1 = await generate_draft(test_email1, intents1)
        
        plain1 = draft1.get('plain_text', '')
        html1 = draft1.get('html', '')
        
        print(f"   Draft lengths: Plain={len(plain1)}, HTML={len(html1)}")
        
        # Check for actual signature block (Best regards + AI Email Assistant + Technology Solutions Team)
        has_signature_block_plain = ('Best regards' in plain1 and 
                                    'AI Email Assistant' in plain1 and 
                                    'Technology Solutions Team' in plain1)
        
        has_signature_block_html = ('Best regards' in html1 and 
                                   'AI Email Assistant' in html1 and 
                                   'Technology Solutions Team' in html1)
        
        # Check for product mentions (legitimate content)
        has_product_mention_plain = 'AI Email Assistant' in plain1
        has_product_mention_html = 'AI Email Assistant' in html1
        
        print(f"   Signature block in draft: Plain={has_signature_block_plain}, HTML={has_signature_block_html}")
        print(f"   Product mentions in draft: Plain={has_product_mention_plain}, HTML={has_product_mention_html}")
        
        if not has_signature_block_plain and not has_signature_block_html:
            print("   ✅ PASS: No signature block in draft (product mentions are OK)")
            draft_test_passed = True
        else:
            print("   ❌ FAIL: Signature block found in draft")
            draft_test_passed = False
        
        # Test 2: Validation adds signature block
        print(f"\n🔍 Test 2: Validation Adds Signature Block")
        validation_result = await validate_final_email(test_email1, draft1, intents1, account)
        
        final_plain = validation_result.get('final_plain_text', '')
        final_html = validation_result.get('final_html', '')
        
        print(f"   Final lengths: Plain={len(final_plain)}, HTML={len(final_html)}")
        
        # Check that signature block is added
        final_has_signature_block_plain = ('Best regards' in final_plain and 
                                          'AI Email Assistant' in final_plain and 
                                          'Technology Solutions Team' in final_plain)
        
        final_has_signature_block_html = ('Best regards' in final_html and 
                                         'AI Email Assistant' in final_html and 
                                         'Technology Solutions Team' in final_html)
        
        # Count signature blocks (should be exactly 1)
        # Look for the pattern: Best regards followed by AI Email Assistant followed by Technology Solutions Team
        import re
        signature_pattern = r'Best regards.*?AI Email Assistant.*?Technology Solutions Team'
        plain_sig_blocks = len(re.findall(signature_pattern, final_plain, re.DOTALL))
        html_sig_blocks = len(re.findall(signature_pattern, final_html, re.DOTALL))
        
        print(f"   Signature block in final: Plain={final_has_signature_block_plain}, HTML={final_has_signature_block_html}")
        print(f"   Signature block count: Plain={plain_sig_blocks}, HTML={html_sig_blocks}")
        
        if (final_has_signature_block_plain and final_has_signature_block_html and 
            plain_sig_blocks == 1 and html_sig_blocks == 1):
            print("   ✅ PASS: Signature block added exactly once")
            validation_test_passed = True
        else:
            print("   ❌ FAIL: Signature block not added correctly or duplicated")
            validation_test_passed = False
        
        # Test 3: Check signature position (should be at the end)
        print(f"\n🔍 Test 3: Signature Position Verification")
        if final_has_signature_block_plain:
            # Find the last occurrence of "Best regards"
            best_regards_pos = final_plain.rfind('Best regards')
            text_after_signature = final_plain[best_regards_pos:].strip()
            
            # Check if signature is at the end
            signature_at_end = text_after_signature.endswith('Technology Solutions Team')
            
            print(f"   Signature at end: {signature_at_end}")
            print(f"   Text after 'Best regards': {repr(text_after_signature[:100])}")
            
            if signature_at_end:
                print("   ✅ PASS: Signature positioned at end of email")
                position_test_passed = True
            else:
                print("   ❌ FAIL: Signature not at end of email")
                position_test_passed = False
        else:
            print("   ❌ FAIL: No signature found")
            position_test_passed = False
        
        # Summary
        print(f"\n" + "="*50)
        print("ACCURATE SIGNATURE TEST RESULTS")
        print("="*50)
        
        tests = [
            ("Draft Generation (No Signature Block)", draft_test_passed),
            ("Validation Adds Signature Block", validation_test_passed),
            ("Signature Position Correct", position_test_passed)
        ]
        
        passed = sum(1 for _, result in tests if result)
        total = len(tests)
        
        print(f"Passed: {passed}/{total}")
        
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        if passed == total:
            print(f"\n🎉 ALL TESTS PASSED: Signature processing is working correctly!")
            print("   - Drafts contain product mentions but no signature blocks")
            print("   - Validation adds signature block exactly once")
            print("   - Signature is positioned at the end of emails")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
        
        print("="*50)
        
        return passed == total
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(accurate_signature_test())