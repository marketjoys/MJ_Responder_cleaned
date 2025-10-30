#!/usr/bin/env python3
"""
Investigate calendar event creation issue
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def investigate():
    """Investigate calendar event creation"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    if not user:
        print("❌ User not found")
        return
    
    user_id = user['id']
    print(f"✅ User: {user['email']} (ID: {user_id})")
    
    # Check for meeting intents in intents collection
    meeting_intents = await db.intents.find({
        "user_id": user_id,
        "is_meeting_related": True
    }).to_list(length=100)
    
    print(f"\n📋 Meeting-related Intents: {len(meeting_intents)}")
    for intent in meeting_intents:
        print(f"   - {intent['name']} (ID: {intent['id']})")
    
    # Check for meeting_intents collection (detected meetings from emails)
    meeting_detections = await db.meeting_intents.find({"user_id": user_id}).to_list(length=100)
    
    print(f"\n🔍 Meeting Detections: {len(meeting_detections)}")
    for detection in meeting_detections:
        print(f"\n   Meeting Detection ID: {detection.get('id')}")
        print(f"   Email ID: {detection.get('email_id')}")
        print(f"   Confidence: {detection.get('confidence', 'N/A')}")
        print(f"   Proposed Time: {detection.get('proposed_time', 'N/A')}")
        print(f"   Duration: {detection.get('duration_minutes', 'N/A')} minutes")
        print(f"   Created At: {detection.get('created_at', 'N/A')}")
        print(f"   Calendar Event ID: {detection.get('calendar_event_id', 'Not created')}")
    
    # Check calendar_events collection
    calendar_events = await db.calendar_events.find({"user_id": user_id}).to_list(length=100)
    
    print(f"\n📅 Calendar Events Created: {len(calendar_events)}")
    for event in calendar_events:
        print(f"\n   Event ID: {event.get('id')}")
        print(f"   Title: {event.get('title')}")
        print(f"   Start: {event.get('start_time')}")
        print(f"   End: {event.get('end_time')}")
        print(f"   External Event ID: {event.get('external_event_id', 'N/A')}")
        print(f"   Meeting Intent ID: {event.get('meeting_intent_id', 'N/A')}")
    
    # Check emails with meeting-related processing
    emails = await db.emails.find({
        "user_id": user_id,
        "calendar_action": {"$exists": True, "$ne": None}
    }).to_list(length=100)
    
    print(f"\n✉️ Emails with Calendar Action: {len(emails)}")
    for email in emails:
        print(f"\n   Email ID: {email.get('id')}")
        print(f"   Subject: {email.get('subject', 'N/A')}")
        print(f"   Status: {email.get('status', 'N/A')}")
        print(f"   Calendar Action: {email.get('calendar_action', 'N/A')}")
        print(f"   Classified Intent: {email.get('classified_intent', 'N/A')}")
        print(f"   Meeting Detected: {email.get('meeting_detected', False)}")
        print(f"   Meeting Confidence: {email.get('meeting_confidence', 'N/A')}")
    
    # Check calendar providers
    calendar_providers = await db.calendar_providers.find({"user_id": user_id}).to_list(length=100)
    
    print(f"\n🗓️ Calendar Providers: {len(calendar_providers)}")
    for provider in calendar_providers:
        print(f"\n   Provider ID: {provider.get('id')}")
        print(f"   Type: {provider.get('provider_type')}")
        print(f"   Use OAuth: {provider.get('use_oauth', False)}")
        print(f"   OAuth Email: {provider.get('oauth_email', 'N/A')}")
        print(f"   Active: {provider.get('is_active', False)}")
    
    # Check OAuth tokens
    oauth_tokens = await db.oauth_tokens.find({"user_id": user_id}).to_list(length=100)
    
    print(f"\n🔐 OAuth Tokens: {len(oauth_tokens)}")
    for token in oauth_tokens:
        print(f"\n   Provider: {token.get('provider')}")
        print(f"   Email: {token.get('email')}")
        print(f"   Has Access Token: {'✅' if token.get('access_token') else '❌'}")
        print(f"   Has Refresh Token: {'✅' if token.get('refresh_token') else '❌'}")
        print(f"   Scopes: {', '.join(token.get('scopes', []))}")
        print(f"   Expires At: {token.get('expires_at')}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Meeting-related Intents Configured: {len(meeting_intents)}")
    print(f"Meeting Detections in Database: {len(meeting_detections)}")
    print(f"Calendar Events Created: {len(calendar_events)}")
    print(f"Emails with Calendar Action: {len(emails)}")
    print(f"Calendar Providers Configured: {len(calendar_providers)}")
    print(f"OAuth Tokens Available: {len(oauth_tokens)}")
    
    # Diagnosis
    print("\n🔍 DIAGNOSIS:")
    if len(meeting_intents) == 0:
        print("   ❌ No meeting-related intents configured")
    else:
        print(f"   ✅ {len(meeting_intents)} meeting-related intents configured")
    
    if len(meeting_detections) == 0:
        print("   ⚠️ No meeting detections found - calendar agent may not be detecting meetings")
    else:
        print(f"   ✅ {len(meeting_detections)} meeting detections found")
        
        if len(calendar_events) == 0:
            print("   ❌ ISSUE: Meeting detected but NO calendar events created")
        else:
            print(f"   ✅ {len(calendar_events)} calendar events created")
    
    if len(calendar_providers) == 0:
        print("   ❌ No calendar providers configured - cannot create events")
    else:
        print(f"   ✅ {len(calendar_providers)} calendar provider(s) configured")
    
    if len(oauth_tokens) == 0:
        print("   ❌ No OAuth tokens - calendar API access not available")
    else:
        print(f"   ✅ {len(oauth_tokens)} OAuth token(s) available")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(investigate())
