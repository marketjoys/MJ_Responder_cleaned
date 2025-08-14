#!/usr/bin/env python3
"""
Manually process the new email through AI workflow
"""
import asyncio
import sys
import os
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from email_services import EmailPollingService
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

async def process_new_email():
    """Find and process the new email through AI workflow"""
    
    try:
        print("🤖 Processing new email through AI workflow...")
        
        # Connect to database
        mongo_url = os.environ['MONGO_URL']
        db_name = os.environ['DB_NAME']
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Find emails with status "new"
        new_emails = await db.emails.find({"status": "new"}).to_list(10)
        print(f"📧 Found {len(new_emails)} emails with status 'new'")
        
        if new_emails:
            # Process the most recent "new" email
            email = new_emails[-1]  # Get the latest one
            print(f"📍 Processing email: {email['subject']} from {email['sender']}")
            print(f"📄 Email ID: {email['id']}")
            print(f"🕒 Received: {email['received_at']}")
            
            # Create polling service and run AI workflow
            polling_service = EmailPollingService(mongo_url, db_name)
            
            print("🔄 Starting AI workflow...")
            await polling_service._process_email_ai_workflow(email['id'])
            
            # Check the result
            processed_email = await db.emails.find_one({"id": email['id']})
            if processed_email:
                print(f"\n📊 Processing complete!")
                print(f"   Status: {processed_email['status']}")
                if processed_email.get('intents'):
                    print(f"   Intents: {len(processed_email['intents'])} classified")
                if processed_email.get('draft'):
                    print(f"   Draft: {processed_email['draft'][:100]}...")
                if processed_email.get('validation_result'):
                    print(f"   Validation: {processed_email['validation_result'].get('status', 'N/A')}")
                if processed_email.get('sent_at'):
                    print(f"   ✅ Reply sent at: {processed_email['sent_at']}")
                elif processed_email.get('error'):
                    print(f"   ❌ Error: {processed_email['error']}")
        else:
            print("ℹ️  No emails with status 'new' found")
            
            # Check emails with other statuses
            all_emails = await db.emails.find({}).sort("received_at", -1).limit(5).to_list(5)
            print(f"\n📧 Latest 5 emails in database:")
            for email in all_emails:
                print(f"  📍 {email['subject']} - Status: {email['status']} - From: {email['sender']}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error processing email: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(process_new_email())