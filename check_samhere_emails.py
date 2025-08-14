#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

async def check_latest_emails():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    
    try:
        # Check account status
        account = await db.email_accounts.find_one({'email': 'rohushanshinde@gmail.com'})
        print(f'🔢 Account last_uid: {account.get("last_uid", 0)}')
        print(f'📅 Last polled: {account.get("last_polled", "Never")}')
        
        # Check latest emails from samhere
        cursor = db.emails.find({'sender': {'$regex': 'samhere', '$options': 'i'}})
        emails = await cursor.sort('received_at', -1).limit(5).to_list(5)
        
        print(f'\n📧 Latest {len(emails)} emails from samhere:')
        for email in emails:
            print(f'  📍 ID: {email["id"][:8]}...')
            print(f'      Subject: {email["subject"]}')
            print(f'      Status: {email["status"]}')
            print(f'      Received: {email["received_at"]}')
            if email.get('sent_at'):
                print(f'      ✅ Sent Reply: {email["sent_at"]}')
            if email.get('draft'):
                print(f'      📝 Draft: {email["draft"][:50]}...')
            print()
        
        # Check total email count
        total_emails = await db.emails.count_documents({})
        sent_emails = await db.emails.count_documents({"status": "sent"})
        print(f'📊 Total emails in database: {total_emails}')
        print(f'📤 Successfully sent emails: {sent_emails}')
        
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_latest_emails())