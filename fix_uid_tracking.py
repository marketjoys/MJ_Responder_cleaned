#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

async def fix_uid_tracking():
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    try:
        print("🔧 Fixing UID tracking for rohushanshinde@gmail.com...")
        
        # Reset the UID to current latest UID (487) so it will start monitoring from there
        result = await db.email_accounts.update_one(
            {"email": "rohushanshinde@gmail.com"},
            {"$set": {
                "last_uid": 487,  # Set to current latest UID
                "uidvalidity": None,  # Reset UIDVALIDITY to force refresh
                "last_polled": None
            }}
        )
        
        if result.modified_count > 0:
            print("✅ Successfully reset UID tracking!")
            print("   - last_uid reset to 487")
            print("   - uidvalidity reset to None")
            print("   - System will now monitor for emails newer than UID 487")
        else:
            print("❌ No account found to update")
            
        # Also check and fix kasargovinda account if needed
        kasar_account = await db.email_accounts.find_one({"email": "kasargovinda@gmail.com"})
        if kasar_account:
            print(f"\n🔍 Checking kasargovinda@gmail.com - current last_uid: {kasar_account.get('last_uid', 0)}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_uid_tracking())