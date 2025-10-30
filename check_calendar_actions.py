#!/usr/bin/env python3
"""
Check if calendar_action IDs are meeting intents
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def check_calendar_actions():
    """Check calendar actions"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    user_id = user['id']
    
    # Get emails with calendar_action
    emails = await db.emails.find({
        "user_id": user_id,
        "calendar_action": {"$exists": True, "$ne": None}
    }).to_list(length=10)
    
    print(f"📧 Emails with calendar_action: {len(emails)}\n")
    
    for email in emails:
        calendar_action_id = email.get('calendar_action')
        email_id = email.get('id')
        subject = email.get('subject')
        
        print(f"Email: {subject}")
        print(f"   Email ID: {email_id}")
        print(f"   Calendar Action ID: {calendar_action_id}")
        
        # Check if this ID exists in meeting_intents
        meeting_intent = await db.meeting_intents.find_one({"id": calendar_action_id})
        
        if meeting_intent:
            print(f"   ✅ Meeting Intent Found:")
            print(f"      Status: {meeting_intent.get('status')}")
            print(f"      Confidence: {meeting_intent.get('confidence_score')}")
            print(f"      DateTime: {meeting_intent.get('detected_datetime')}")
            print(f"      Created Event ID: {meeting_intent.get('created_event_id', 'None')}")
        else:
            print(f"   ❌ Meeting Intent NOT FOUND in database")
            print(f"      This is the issue! Meeting intent should have been created.")
        
        print()
    
    # Check if there are ANY meeting intents
    all_intents = await db.meeting_intents.find({"user_id": user_id}).to_list(length=100)
    print(f"\n📋 Total Meeting Intents in DB: {len(all_intents)}")
    
    if all_intents:
        print("\nExisting Meeting Intents:")
        for intent in all_intents:
            print(f"   - ID: {intent.get('id')}")
            print(f"     Email ID: {intent.get('email_id')}")
            print(f"     Status: {intent.get('status')}")
            print(f"     Created: {intent.get('created_at')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_calendar_actions())
