#!/usr/bin/env python3
"""
Database Migration: Add quota_reset_date to existing users
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def migrate_users():
    """Add quota_reset_date to users missing this field"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        print("🔧 Starting User Migration...")
        
        # Find users without quota_reset_date
        users_to_update = await db.users.find({"quota_reset_date": {"$exists": False}}).to_list(1000)
        
        print(f"📊 Found {len(users_to_update)} users without quota_reset_date")
        
        if not users_to_update:
            print("✅ All users already have quota_reset_date")
            return
        
        # Calculate next month for quota reset
        next_month = datetime.utcnow() + timedelta(days=30)
        
        # Update each user
        updated_count = 0
        for user in users_to_update:
            result = await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"quota_reset_date": next_month}}
            )
            if result.modified_count > 0:
                updated_count += 1
                print(f"   ✅ Updated user: {user.get('email', 'N/A')}")
        
        print(f"\n🎉 Migration Complete!")
        print(f"   Updated: {updated_count} users")
        print(f"   Quota reset date set to: {next_month.isoformat()}")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(migrate_users())
