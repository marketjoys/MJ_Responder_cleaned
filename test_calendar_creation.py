#!/usr/bin/env python3
"""
Test calendar event creation directly
"""
import asyncio
import sys
import os
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
from calendar_models import MeetingIntent
import uuid

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def test_calendar_event_creation():
    """Test creating a calendar event"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    user_id = user['id']
    
    print(f"✅ User: {user['email']}")
    print(f"   User ID: {user_id}\n")
    
    # Check calendar provider
    provider = await db.calendar_providers.find_one({"user_id": user_id, "is_active": True})
    
    if not provider:
        print("❌ No calendar provider found!")
        return
    
    print(f"✅ Calendar Provider:")
    print(f"   ID: {provider['id']}")
    print(f"   Type: {provider['provider_type']}")
    print(f"   OAuth Email: {provider.get('oauth_email')}\n")
    
    # Try to get calendar service
    try:
        from calendar_services import calendar_service
        
        print("🔄 Getting calendar service...")
        service = await calendar_service.get_service(provider["id"], user_id)
        print(f"✅ Service obtained: {type(service).__name__}\n")
        
        print("🔄 Getting calendars...")
        calendars = await service.get_calendars()
        print(f"✅ Found {len(calendars)} calendar(s):")
        for cal in calendars[:3]:
            print(f"   - {cal.get('title', 'Unknown')} (ID: {cal.get('id')}) [Primary: {cal.get('is_primary', False)}]")
        print()
        
        if not calendars:
            print("❌ No calendars found!")
            return
        
        # Get default calendar
        default_calendar = next((cal for cal in calendars if cal.get('is_primary')), calendars[0])
        print(f"✅ Using calendar: {default_calendar.get('title')}\n")
        
        # Create test meeting intent
        print("🔄 Creating test calendar event...")
        now = datetime.utcnow()
        start_time = now + timedelta(days=1)  # Tomorrow
        end_time = start_time + timedelta(minutes=30)
        
        event_data = {
            'title': "Test Meeting - Calendar Agent",
            'description': "This is a test meeting created by the calendar agent investigation.",
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'timezone': 'UTC',
            'location': '',
            'attendees': ['test@example.com'],
            'meeting_intent_id': str(uuid.uuid4()),
            'reminders': [
                {'method': 'email', 'minutes': 60},
                {'method': 'popup', 'minutes': 15}
            ]
        }
        
        print(f"   Title: {event_data['title']}")
        print(f"   Start: {event_data['start_time']}")
        print(f"   End: {event_data['end_time']}")
        print(f"   Reminders: {len(event_data['reminders'])}\n")
        
        # Create the event
        event_response = await calendar_service.create_event(
            provider["id"],
            default_calendar['id'],
            event_data,
            user_id
        )
        
        print(f"✅ Calendar event created successfully!")
        print(f"   Event ID: {event_response.id}")
        print(f"   External Event ID: {event_response.external_event_id}")
        print()
        
        # Check if event was stored in database
        stored_event = await db.calendar_events.find_one({"id": event_response.id})
        if stored_event:
            print(f"✅ Event stored in database:")
            print(f"   ID: {stored_event['id']}")
            print(f"   Title: {stored_event.get('title')}")
            print(f"   Reminders: {stored_event.get('reminders', 'N/A')}")
            print(f"   Reminder Sent: {stored_event.get('reminder_sent', False)}")
        else:
            print(f"❌ Event NOT found in database!")
        
        # Clean up - delete test event
        print(f"\n🧹 Cleaning up test event...")
        await calendar_service.delete_event(provider["id"], default_calendar['id'], event_response.id, user_id)
        print(f"✅ Test event deleted")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_calendar_event_creation())
