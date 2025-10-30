import sys
sys.path.insert(0, '/app/backend')

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from server import EmailMessage

client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def test():
    email = await db.emails.find_one({"status": "new"})
    if not email:
        print("No email found")
        return
    
    print("Email document:")
    for key, value in email.items():
        print(f"  {key}: {type(value).__name__}")
    
    print("\n\nTrying to create EmailMessage object...")
    try:
        email_msg = EmailMessage(**email)
        print("✅ EmailMessage created successfully!")
        print(f"  ID: {email_msg.id}")
        print(f"  Subject: {email_msg.subject}")
        print(f"  Sender: {email_msg.sender}")
    except Exception as e:
        print(f"❌ Error creating EmailMessage: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
