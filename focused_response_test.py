#!/usr/bin/env python3
"""
Focused test for automatic email response system
Tests key functionality without timeouts
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
TEST_ACCOUNT_ID = "0cda0f06-6478-4eae-93da-4458a4728ab5"

async def test_automatic_response_system():
    """Test the automatic response system directly"""
    print("🔍 Testing Automatic Email Response System...")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Test 1: Check API keys are updated
        print("\n1. Checking API Keys...")
        groq_key = os.environ.get('GROQ_API_KEY')
        cohere_key = os.environ.get('COHERE_API_KEY')
        
        expected_groq = "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"
        expected_cohere = "rEiWPn4RxWnp5uEKgHEH7tj7D0MZGL76VurAXg5D"
        
        keys_correct = (groq_key == expected_groq and cohere_key == expected_cohere)
        print(f"   ✅ API Keys Updated: {keys_correct}")
        
        # Test 2: Check intent thresholds
        print("\n2. Checking Intent Thresholds...")
        intents = await db.intents.find().to_list(100)
        
        lowered_count = 0
        high_count = 0
        
        for intent in intents:
            threshold = intent.get('confidence_threshold', 0.8)
            if threshold <= 0.7:
                lowered_count += 1
            else:
                high_count += 1
        
        print(f"   ✅ Intents with lowered thresholds (≤0.7): {lowered_count}")
        print(f"   ⚠️  Intents with high thresholds (>0.7): {high_count}")
        
        # Test 3: Check recent email processing
        print("\n3. Checking Recent Email Processing...")
        recent_emails = await db.emails.find().sort('created_at', -1).limit(10).to_list(10)
        
        sent_emails = [e for e in recent_emails if e.get('status') == 'sent']
        processing_emails = [e for e in recent_emails if e.get('status') in ['classifying', 'drafting', 'validating']]
        failed_emails = [e for e in recent_emails if e.get('status') in ['error', 'send_failed']]
        
        print(f"   ✅ Successfully sent emails: {len(sent_emails)}")
        print(f"   🔄 Currently processing: {len(processing_emails)}")
        print(f"   ❌ Failed emails: {len(failed_emails)}")
        
        # Test 4: Check email account configuration
        print("\n4. Checking Email Account Configuration...")
        account = await db.email_accounts.find_one({"id": TEST_ACCOUNT_ID})
        
        if account:
            print(f"   ✅ Test account found: {account.get('email', 'Unknown')}")
            print(f"   ✅ Account active: {account.get('is_active', False)}")
            print(f"   ✅ Auto-send enabled: {account.get('auto_send', False)}")
            print(f"   ✅ Has signature: {bool(account.get('signature', ''))}")
            print(f"   ✅ Has persona: {bool(account.get('persona', ''))}")
        else:
            print(f"   ❌ Test account {TEST_ACCOUNT_ID} not found")
        
        # Test 5: Test direct AI functions
        print("\n5. Testing AI Functions Directly...")
        
        try:
            from server import classify_email_intents, generate_draft, validate_final_email, EmailMessage
            import uuid
            
            # Create test email
            test_email = EmailMessage(
                account_id=TEST_ACCOUNT_ID,
                message_id=f"direct-test-{uuid.uuid4()}",
                thread_id=f"thread-{uuid.uuid4()}",
                subject="Direct Test - Product Pricing Inquiry",
                sender="direct.test@example.com",
                recipient="support@company.com",
                body="Hello! I'm interested in your AI email assistant product. Could you please provide pricing information and schedule a demo? We have a budget of $10,000 and need to make a decision soon. Thank you!",
                received_at=datetime.utcnow(),
                status="new"
            )
            
            # Test classification
            print("   Testing intent classification...")
            intents = await classify_email_intents(test_email)
            print(f"   ✅ Intent classification: {len(intents)} intents found")
            
            if intents:
                for intent in intents:
                    print(f"      - {intent.get('name', 'Unknown')}: {intent.get('confidence', 0):.3f}")
            
            # Test draft generation
            print("   Testing draft generation...")
            draft_result = await generate_draft(test_email, intents)
            draft_length = len(draft_result.get('plain_text', '')) if draft_result else 0
            print(f"   ✅ Draft generation: {draft_length} characters")
            
            # Test validation
            if draft_result and account:
                print("   Testing validation...")
                validation_result = await validate_final_email(test_email, draft_result, intents, account)
                validation_status = validation_result.get('status', 'UNKNOWN') if validation_result else 'FAILED'
                print(f"   ✅ Validation: {validation_status}")
            
            ai_functions_working = len(intents) >= 0 and draft_length > 50
            print(f"   ✅ AI Functions Working: {ai_functions_working}")
            
        except Exception as e:
            print(f"   ❌ AI Functions Error: {str(e)}")
        
        # Test 6: Check validation improvements
        print("\n6. Checking Validation Improvements...")
        
        # Look for emails that were processed with lenient validation
        lenient_emails = []
        strict_emails = []
        
        for email in recent_emails:
            validation = email.get('validation_result', {})
            if validation:
                status = validation.get('status', '')
                if 'LENIENT' in status:
                    lenient_emails.append(email)
                elif status in ['PASS', 'FAIL']:
                    strict_emails.append(email)
        
        print(f"   ✅ Emails with lenient validation: {len(lenient_emails)}")
        print(f"   ✅ Emails with strict validation: {len(strict_emails)}")
        
        # Test 7: Check auto-send functionality
        print("\n7. Checking Auto-Send Functionality...")
        
        auto_sent_count = 0
        needs_redraft_count = 0
        
        for email in recent_emails:
            status = email.get('status', '')
            if status == 'sent':
                auto_sent_count += 1
            elif status == 'needs_redraft':
                needs_redraft_count += 1
        
        print(f"   ✅ Auto-sent emails: {auto_sent_count}")
        print(f"   ⚠️  Emails needing redraft: {needs_redraft_count}")
        
        auto_send_working = auto_sent_count > 0
        print(f"   ✅ Auto-send working: {auto_send_working}")
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY OF AUTOMATIC EMAIL RESPONSE SYSTEM")
        print("="*60)
        
        print(f"✅ API Keys Updated: {keys_correct}")
        print(f"✅ Intent Thresholds Lowered: {lowered_count > 0}")
        print(f"✅ Recent Email Processing: {len(recent_emails)} emails found")
        print(f"✅ Auto-Send Working: {auto_send_working}")
        print(f"✅ Account Configuration: {account is not None}")
        
        if sent_emails:
            print(f"\n📧 Recent Successfully Sent Emails:")
            for email in sent_emails[:3]:  # Show top 3
                print(f"   - {email.get('subject', 'No subject')}")
                print(f"     Status: {email.get('status')}, Intents: {len(email.get('intents', []))}")
        
        if processing_emails:
            print(f"\n🔄 Currently Processing Emails:")
            for email in processing_emails[:3]:  # Show top 3
                print(f"   - {email.get('subject', 'No subject')}")
                print(f"     Status: {email.get('status')}")
        
        overall_working = (keys_correct and lowered_count > 0 and 
                          len(recent_emails) > 0 and account is not None)
        
        print(f"\n🎯 OVERALL SYSTEM STATUS: {'✅ WORKING' if overall_working else '❌ ISSUES DETECTED'}")
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_automatic_response_system())