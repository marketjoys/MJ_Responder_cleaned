#!/usr/bin/env python3
"""
Manual test of the email polling system
"""
import asyncio
import sys
import os
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from email_services import EmailPollingService
from dotenv import load_dotenv
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/app/backend/.env')

async def test_manual_poll():
    """Manually trigger a polling cycle to debug the issue"""
    
    try:
        print("🔍 Testing manual email polling...")
        
        # Create polling service
        mongo_url = os.environ['MONGO_URL']
        db_name = os.environ['DB_NAME']
        polling_service = EmailPollingService(mongo_url, db_name)
        
        # Get account info first
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        account = await db.email_accounts.find_one({"is_active": True})
        if not account:
            print("❌ No active accounts found")
            return
        
        print(f"📧 Account: {account['email']}")
        print(f"🔢 Current last_uid in DB: {account.get('last_uid', 0)}")
        print(f"🔑 UIDVALIDITY: {account.get('uidvalidity', 'None')}")
        
        # Manually poll this account
        print("\n🔄 Manually polling account...")
        await polling_service._poll_account(account)
        
        # Check updated account state
        updated_account = await db.email_accounts.find_one({"id": account['id']})
        print(f"\n📊 After polling:")
        print(f"🔢 Updated last_uid: {updated_account.get('last_uid', 0)}")
        print(f"📅 Last polled: {updated_account.get('last_polled', 'Never')}")
        
        # Check for any new emails in database
        new_emails = await db.emails.find({"account_id": account['id']}).sort("received_at", -1).limit(3).to_list(3)
        print(f"\n📧 Latest emails in database:")
        for email in new_emails:
            print(f"  📍 {email['subject']} - Status: {email['status']} - Received: {email['received_at']}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error in manual poll test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_manual_poll())