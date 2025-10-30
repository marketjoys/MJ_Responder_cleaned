import sys
sys.path.insert(0, '/app/backend')

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from server import EmailMessage, classify_email_intents

client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def test():
    # Get email
    email = await db.emails.find_one({"status": "new"})
    if not email:
        print("No email found")
        return
    
    email_msg = EmailMessage(**email)
    print(f"Classifying: {email_msg.subject}")
    print(f"User ID: {email_msg.user_id}")
    
    # Check if user has intents
    intents_count = await db.intents.count_documents({"user_id": email_msg.user_id})
    print(f"User has {intents_count} intents")
    
    # Try to classify
    try:
        intents = await classify_email_intents(email_msg)
        print(f"✅ Classification result: {len(intents)} intents")
        for intent in intents:
            print(f"  - {intent.get('name')}: {intent.get('confidence', 0):.2f}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
