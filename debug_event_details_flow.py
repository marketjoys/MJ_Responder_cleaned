#!/usr/bin/env python3
"""
Debug test to trace event details flow
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import uuid

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def debug_event_details():
    """Debug the event details flow"""
    print("=" * 70)
    print("DEBUG: EVENT DETAILS FLOW TRACING")
    print("=" * 70)
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Get a user with calendar provider
        user = await db.users.find_one({"email": "amits.joys@gmail.com"})
        if not user:
            print("❌ User not found")
            return
        
        user_id = user['id']
        print(f"\n✅ User: {user['email']} (ID: {user_id})")
        
        # Check calendar providers
        providers = await db.calendar_providers.find({"user_id": user_id}).to_list(10)
        print(f"\n📅 Calendar Providers: {len(providers)}")
        for provider in providers:
            print(f"   - {provider.get('provider_name')} (ID: {provider['id']})")
        
        # Check recent meeting intents
        print(f"\n📋 Recent Meeting Intents:")
        intents = await db.meeting_intents.find({"user_id": user_id}).sort("created_at", -1).limit(5).to_list(5)
        for intent in intents:
            print(f"\n   Intent ID: {intent['id']}")
            print(f"   Status: {intent.get('status', 'unknown')}")
            print(f"   Title: {intent.get('detected_title', 'N/A')}")
            print(f"   DateTime: {intent.get('detected_datetime', 'N/A')}")
            print(f"   Created Event ID: {intent.get('created_event_id', 'N/A')}")
            
            # If event was created, check if it exists
            if intent.get('created_event_id'):
                event = await db.calendar_events.find_one({
                    "external_event_id": intent['created_event_id'],
                    "user_id": user_id
                })
                if event:
                    print(f"   ✅ Calendar event found in DB")
                    print(f"      DB ID: {event['id']}")
                    print(f"      Title: {event['title']}")
                    print(f"      Start: {event['start_time']}")
                else:
                    print(f"   ❌ Calendar event NOT found in DB")
        
        # Check recent calendar events
        print(f"\n📆 Recent Calendar Events:")
        events = await db.calendar_events.find({"user_id": user_id}).sort("created_at", -1).limit(5).to_list(5)
        print(f"   Total events: {len(events)}")
        for event in events:
            print(f"\n   Event DB ID: {event['id']}")
            print(f"   External ID: {event['external_event_id']}")
            print(f"   Title: {event['title']}")
            print(f"   Start: {event['start_time']}")
            print(f"   End: {event['end_time']}")
            print(f"   Location: {event.get('location', 'N/A')}")
            print(f"   Reminders: {event.get('reminders', [])}")
        
        # Check recent emails with meeting detection
        print(f"\n📧 Recent Emails with Meeting Detection:")
        emails = await db.emails.find({
            "user_id": user_id,
            "meeting_detected": True
        }).sort("created_at", -1).limit(3).to_list(3)
        
        for email in emails:
            print(f"\n   Email ID: {email['id']}")
            print(f"   Subject: {email['subject']}")
            print(f"   Meeting Detected: {email.get('meeting_detected', False)}")
            print(f"   Meeting Confidence: {email.get('meeting_confidence', 0):.2f}")
            print(f"   Calendar Action: {email.get('calendar_action', 'N/A')}")
            print(f"   Status: {email.get('status', 'unknown')}")
            
            # Check if draft includes event details
            draft = email.get('draft', '')
            if draft:
                has_date = any(word in draft.lower() for word in ['october', 'november', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
                has_time = any(word in draft.lower() for word in ['am', 'pm', ':00', 'o\'clock'])
                has_confirmation = any(word in draft.lower() for word in ['scheduled', 'confirmed', 'calendar', 'event'])
                
                print(f"\n   Draft Analysis:")
                print(f"   - Length: {len(draft)} chars")
                print(f"   - Has date: {'✅' if has_date else '❌'}")
                print(f"   - Has time: {'✅' if has_time else '❌'}")
                print(f"   - Has confirmation: {'✅' if has_confirmation else '❌'}")
                
                if not (has_date and has_time):
                    print(f"\n   ⚠️  ISSUE: Draft missing specific event details")
                    print(f"   Draft preview (first 300 chars):")
                    print(f"   ---")
                    print(f"   {draft[:300]}")
                    print(f"   ---")
        
        # Test the lookup logic manually
        print(f"\n\n🔍 TESTING LOOKUP LOGIC:")
        
        # Get the most recent calendar action
        recent_email = await db.emails.find_one({
            "user_id": user_id,
            "calendar_action": {"$exists": True, "$ne": None}
        }, sort=[("created_at", -1)])
        
        if recent_email:
            calendar_action = recent_email['calendar_action']
            print(f"\n   Testing with calendar_action: {calendar_action}")
            
            # Try event lookup
            event = await db.calendar_events.find_one({
                "external_event_id": calendar_action,
                "user_id": user_id
            })
            print(f"   Event lookup by external_event_id: {'✅ FOUND' if event else '❌ NOT FOUND'}")
            
            if event:
                print(f"   Event title: {event['title']}")
                print(f"   Event start: {event['start_time']}")
            
            # Try intent lookup
            intent = await db.meeting_intents.find_one({
                "id": calendar_action,
                "user_id": user_id
            })
            print(f"   Intent lookup by id: {'✅ FOUND' if intent else '❌ NOT FOUND'}")
            
            if intent:
                print(f"   Intent title: {intent.get('detected_title', 'N/A')}")
                print(f"   Intent datetime: {intent.get('detected_datetime', 'N/A')}")
                print(f"   Intent status: {intent.get('status', 'N/A')}")
                print(f"   Intent created_event_id: {intent.get('created_event_id', 'N/A')}")
            
            # If calendar_action is intent id with created_event_id, try lookup
            if intent and intent.get('created_event_id'):
                event2 = await db.calendar_events.find_one({
                    "external_event_id": intent['created_event_id'],
                    "user_id": user_id
                })
                print(f"   Event lookup via intent.created_event_id: {'✅ FOUND' if event2 else '❌ NOT FOUND'}")
                
                if event2:
                    print(f"   Event title: {event2['title']}")
        else:
            print(f"   ❌ No recent emails with calendar_action found")
        
        print(f"\n" + "=" * 70)
        print("DEBUG COMPLETE")
        print("=" * 70)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_event_details())
