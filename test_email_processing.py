#!/usr/bin/env python3
"""
Test script to simulate email processing workflow
"""
import asyncio
import sys
import os
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from email_services import EmailPollingService, EmailMessage
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

async def test_email_workflow():
    """Test the email processing workflow by inserting a test email"""
    
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    try:
        print("🧪 Testing email processing workflow...")
        
        # Get the first email account
        account = await db.email_accounts.find_one({"is_active": True})
        if not account:
            print("❌ No active email accounts found")
            return False
        
        print(f"📧 Using account: {account['email']}")
        
        # Create a test email
        test_email = EmailMessage(
            account_id=account['id'],
            message_id=f"<test-{uuid.uuid4()}@gmail.com>",
            thread_id=f"thread-{uuid.uuid4()}",
            subject="Test Email - Need Help with Product",
            sender="test.sender@example.com",
            recipient=account['email'],
            body="Hello, I need help with your product. Can you please provide more information about pricing and features? Thank you!",
            body_html="<p>Hello, I need help with your product. Can you please provide more information about pricing and features? Thank you!</p>",
            received_at=datetime.utcnow(),
            status="new"
        )
        
        # Insert test email into database
        await db.emails.insert_one(test_email.dict())
        print(f"✅ Inserted test email: {test_email.subject}")
        print(f"📄 Email ID: {test_email.id}")
        
        # Create polling service and test AI workflow
        polling_service = EmailPollingService(mongo_url, os.environ['DB_NAME'])
        
        print("🤖 Processing email through AI workflow...")
        await polling_service._process_email_ai_workflow(test_email.id)
        
        # Check the result
        processed_email = await db.emails.find_one({"id": test_email.id})
        if processed_email:
            print(f"📊 Final status: {processed_email['status']}")
            if processed_email.get('intents'):
                print(f"🎯 Classified intents: {processed_email['intents']}")
            if processed_email.get('draft'):
                print(f"✏️  Generated draft: {processed_email['draft'][:100]}...")
            if processed_email.get('validation_result'):
                print(f"✔️  Validation result: {processed_email['validation_result']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()

if __name__ == "__main__":
    success = asyncio.run(test_email_workflow())
    if success:
        print("✅ Email processing workflow test completed!")
    else:
        print("❌ Email processing workflow test failed!")