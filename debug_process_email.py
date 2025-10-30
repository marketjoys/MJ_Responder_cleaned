import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from datetime import datetime
import uuid

client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def test():
    # Get first email
    email = await db.emails.find_one({"status": "new"})
    if not email:
        print("No email found")
        return
    
    email_id = str(email["_id"])
    print(f"Email document fields: {list(email.keys())}")
    print(f"\nTrying to find with id field...")
    
    # Try both queries
    by_id = await db.emails.find_one({"id": email_id})
    by_id_result = "FOUND" if by_id else "NOT FOUND"
    print(f"Query {{\"id\": \"{email_id}\"}}: {by_id_result}")
    
    by_underscore_id = await db.emails.find_one({"_id": email_id})
    by_underscore_id_result = "FOUND" if by_underscore_id else "NOT FOUND"
    print(f"Query {{\"_id\": \"{email_id}\"}}: {by_underscore_id_result}")
    
    if by_id:
        print(f"\nEmail found with 'id' field!")
        print(f"Fields: {list(by_id.keys())}")
    else:
        print("\n❌ Email NOT found with 'id' field - this is the problem!")

asyncio.run(test())
