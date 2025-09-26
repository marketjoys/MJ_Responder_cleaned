#!/usr/bin/env python3
"""
Debug Signature Test - Check exact draft content
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

async def debug_draft_generation():
    """Debug what's actually in the draft"""
    print("🔍 DEBUG: Draft Generation Content Analysis")
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
        
        print(f"Account signature: {repr(account.get('signature', ''))}")
        
        # Import functions
        from server import generate_draft, classify_email_intents, EmailMessage
        
        # Create test email
        test_email = EmailMessage(
            account_id=account['id'],
            message_id=f"<debug-{uuid.uuid4()}@example.com>",
            thread_id=f"thread-{uuid.uuid4()}",
            subject="Debug Draft Test",
            sender="debug@example.com",
            recipient=account['email'],
            body="I need help with your AI email assistant. Can you provide pricing?",
            received_at=datetime.utcnow(),
            status="new"
        )
        
        # Classify intents
        intents = await classify_email_intents(test_email)
        print(f"Intents found: {len(intents)}")
        
        # Generate draft
        draft_result = await generate_draft(test_email, intents)
        
        plain_text = draft_result.get('plain_text', '')
        html_text = draft_result.get('html', '')
        
        print(f"\nDraft Plain Text ({len(plain_text)} chars):")
        print("-" * 40)
        print(repr(plain_text))
        print("-" * 40)
        print(plain_text)
        print("-" * 40)
        
        print(f"\nDraft HTML ({len(html_text)} chars):")
        print("-" * 40)
        print(repr(html_text))
        print("-" * 40)
        
        # Check for signature components
        signature_parts = ['Best regards', 'AI Email Assistant', 'Technology Solutions Team']
        
        print(f"\nSignature Analysis:")
        for part in signature_parts:
            plain_count = plain_text.count(part)
            html_count = html_text.count(part)
            print(f"  '{part}': Plain={plain_count}, HTML={html_count}")
        
        # Check if signature is at the end
        if 'AI Email Assistant' in plain_text:
            ai_pos = plain_text.rfind('AI Email Assistant')
            text_after_sig = plain_text[ai_pos + len('AI Email Assistant'):].strip()
            print(f"\nText after 'AI Email Assistant': {repr(text_after_sig)}")
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_draft_generation())