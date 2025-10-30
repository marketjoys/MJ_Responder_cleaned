#!/usr/bin/env python3
"""
Test script to verify reminders are being stored correctly in calendar events
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import httpx
import uuid

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

# Get backend URL from environment
backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

async def test_reminders():
    """Test that reminders are being stored correctly"""
    print("=" * 60)
    print("REMINDERS STORAGE TEST")
    print("=" * 60)
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Step 1: Login and get token
        print("\n🔐 Step 1: Authenticating user...")
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            login_response = await http_client.post(
                f"{backend_url}/api/auth/login",
                json={
                    "email": "amits.joys@gmail.com",
                    "password": "ij@123"
                }
            )
            
            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.status_code}")
                print(f"   Response: {login_response.text}")
                return
            
            token = login_response.json()['access_token']
            user_id = login_response.json()['user_id']
            print(f"✅ Logged in successfully (User ID: {user_id})")
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 2: Check if user has calendar provider
            print("\n📅 Step 2: Checking calendar providers...")
            providers_response = await http_client.get(
                f"{backend_url}/api/calendar/providers",
                headers=headers
            )
            
            if providers_response.status_code != 200:
                print(f"❌ Failed to get providers: {providers_response.status_code}")
                return
            
            providers = providers_response.json()
            if not providers:
                print("⚠️  No calendar providers found for user")
                print("   Please set up OAuth calendar integration first")
                return
            
            provider = providers[0]
            print(f"✅ Found calendar provider: {provider['provider_name']} (ID: {provider['id']})")
            
            # Step 3: Get calendars
            print("\n📆 Step 3: Fetching calendars...")
            calendars_response = await http_client.get(
                f"{backend_url}/api/calendar/calendars",
                headers=headers
            )
            
            if calendars_response.status_code != 200:
                print(f"❌ Failed to get calendars: {calendars_response.status_code}")
                return
            
            calendars_data = calendars_response.json()
            if not calendars_data or not calendars_data.get(provider['provider_name']):
                print("⚠️  No calendars found for provider")
                return
            
            calendars = calendars_data[provider['provider_name']]
            primary_calendar = next((cal for cal in calendars if cal.get('is_primary')), calendars[0] if calendars else None)
            
            if not primary_calendar:
                print("⚠️  No primary calendar found")
                return
            
            print(f"✅ Found primary calendar: {primary_calendar['name']} (ID: {primary_calendar['id']})")
            
            # Step 4: Create test event with reminders
            print("\n🎯 Step 4: Creating test event with reminders...")
            
            start_time = datetime.now(timezone.utc) + timedelta(hours=24)
            end_time = start_time + timedelta(hours=1)
            
            event_data = {
                "title": "Test Event - Reminders Check",
                "description": "This is a test event to verify reminders are stored correctly",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "timezone": "UTC",
                "location": "Virtual Meeting",
                "attendees": ["test@example.com"],
                "reminders": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                    {"method": "email", "minutes": 1440}  # 24 hours
                ]
            }
            
            print(f"   Event: {event_data['title']}")
            print(f"   Start: {start_time}")
            print(f"   Reminders: {event_data['reminders']}")
            
            create_response = await http_client.post(
                f"{backend_url}/api/calendar/providers/{provider['id']}/calendars/{primary_calendar['id']}/events",
                headers=headers,
                json=event_data
            )
            
            if create_response.status_code != 200:
                print(f"❌ Failed to create event: {create_response.status_code}")
                print(f"   Response: {create_response.text}")
                return
            
            created_event = create_response.json()
            print(f"✅ Event created successfully!")
            print(f"   Event ID: {created_event['id']}")
            print(f"   Title: {created_event['title']}")
            
            # Step 5: Verify reminders in API response
            print("\n🔍 Step 5: Verifying reminders in API response...")
            if 'reminders' in created_event and created_event['reminders']:
                print(f"✅ Reminders found in API response:")
                for reminder in created_event['reminders']:
                    print(f"   - {reminder['method']}: {reminder['minutes']} minutes before")
            else:
                print(f"⚠️  No reminders in API response")
                print(f"   Response data: {created_event}")
            
            # Step 6: Verify reminders in database
            print("\n💾 Step 6: Verifying reminders in database...")
            stored_event = await db.calendar_events.find_one({
                "external_event_id": created_event['id'],
                "user_id": user_id
            })
            
            if not stored_event:
                print(f"⚠️  Event not found in database")
                print(f"   Looking for external_event_id: {created_event['id']}")
                
                # Try to find any recent events
                recent_events = await db.calendar_events.find({
                    "user_id": user_id
                }).sort("created_at", -1).limit(5).to_list(5)
                
                print(f"\n   Found {len(recent_events)} recent events in database:")
                for evt in recent_events:
                    print(f"   - {evt.get('title')} (ID: {evt.get('external_event_id')})")
                    print(f"     Reminders: {evt.get('reminders', 'NOT SET')}")
            else:
                print(f"✅ Event found in database!")
                print(f"   Database ID: {stored_event['id']}")
                print(f"   Title: {stored_event['title']}")
                print(f"   External Event ID: {stored_event['external_event_id']}")
                
                if 'reminders' in stored_event and stored_event['reminders']:
                    print(f"\n✅ REMINDERS STORED SUCCESSFULLY:")
                    for reminder in stored_event['reminders']:
                        print(f"   - {reminder['method']}: {reminder['minutes']} minutes before")
                    print(f"\n✅ FIX VERIFIED: Reminders are now being stored in the database!")
                else:
                    print(f"\n⚠️  ISSUE: Reminders field missing or empty in database")
                    print(f"   Stored event data: {stored_event}")
            
            # Step 7: Summary
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            
            # Count total events with reminders
            events_with_reminders = await db.calendar_events.count_documents({
                "user_id": user_id,
                "reminders": {"$exists": True, "$ne": []}
            })
            
            total_events = await db.calendar_events.count_documents({"user_id": user_id})
            
            print(f"\n📊 Calendar Events Summary:")
            print(f"   Total events: {total_events}")
            print(f"   Events with reminders: {events_with_reminders}")
            
            if stored_event and stored_event.get('reminders'):
                print(f"\n✅ REMINDERS FIX SUCCESSFUL!")
                print(f"   - CalendarEvent model updated with reminders field")
                print(f"   - calendar_services.py now stores reminders from event_data")
                print(f"   - Detailed logging added to calendar_agent.py")
                print(f"   - Events are being created with reminder configurations")
            else:
                print(f"\n⚠️  REMINDERS FIX NEEDS ATTENTION")
                print(f"   Please check the backend logs for more details")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_reminders())
