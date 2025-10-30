import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from server import process_email_async
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def test():
    # Get first email
    email = await db.emails.find_one({"status": "new"})
    if not email:
        print("No email found")
        return
    
    email_id = str(email["_id"])
    print(f"Processing email: {email_id}")
    print(f"Subject: {email.get('subject')}")
    print(f"From: {email.get('sender_email')}")
    
    try:
        await process_email_async(email_id)
        print("✅ Processing completed")
        
        # Check result
        processed = await db.emails.find_one({"_id": email_id})
        print(f"\nResult:")
        print(f"  Status: {processed.get('status')}")
        print(f"  Intents: {len(processed.get('intents', []))}")
        print(f"  Draft: {len(processed.get('draft', ''))} chars")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
