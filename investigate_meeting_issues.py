#!/usr/bin/env python3
"""
Investigate meeting request response and reminder issues
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

async def investigate_meeting_workflow():
    """Investigate meeting workflow issues"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    if not user:
        print("❌ User not found")
        return
    
    user_id = user['id']
    print(f"✅ User: {user['email']} (ID: {user_id})")
    print("="*100)
    
    # Check recent emails with meeting detection
    emails = await db.emails.find({
        "user_id": user_id
    }).sort("received_at", -1).limit(10).to_list(length=10)
    
    print(f"\n📧 Recent Emails: {len(emails)}")
    print("="*100)
    
    for email in emails:
        email_id = email.get('id')
        subject = email.get('subject', 'N/A')
        
        print(f"\n📨 Email: {subject}")
        print(f"   ID: {email_id}")
        print(f"   Status: {email.get('status')}")
        print(f"   Meeting Detected: {email.get('meeting_detected', False)}")
        print(f"   Meeting Confidence: {email.get('meeting_confidence', 'N/A')}")
        print(f"   Meeting DateTime: {email.get('meeting_datetime', 'N/A')}")
        print(f"   Calendar Action: {email.get('calendar_action', 'N/A')}")
        
        # Check draft content
        draft = email.get('draft', '')
        if draft:
            print(f"\n   📝 Draft Preview:")
            print(f"   {draft[:300]}...")
            
            # Check if draft mentions meeting details
            meeting_keywords = ['meeting', 'calendar', 'schedule', 'time', 'date', 'invite']
            has_meeting_details = any(keyword in draft.lower() for keyword in meeting_keywords)
            print(f"\n   Has Meeting Details in Draft: {'✅' if has_meeting_details else '❌'}")
    
    # Check meeting intents
    print("\n" + "="*100)
    print("📋 Meeting Intents")
    print("="*100)
    
    meeting_intents = await db.meeting_intents.find({
        "user_id": user_id
    }).sort("created_at", -1).limit(10).to_list(length=10)
    
    print(f"\nFound: {len(meeting_intents)} meeting intents")
    
    for intent in meeting_intents:
        print(f"\n   Meeting Intent:")
        print(f"      ID: {intent.get('id')}")
        print(f"      Email ID: {intent.get('email_id')}")
        print(f"      Status: {intent.get('status')}")
        print(f"      Confidence: {intent.get('confidence_score')}")
        print(f"      DateTime: {intent.get('detected_datetime')}")
        print(f"      Title: {intent.get('detected_title')}")
        print(f"      Location: {intent.get('detected_location', 'N/A')}")
        print(f"      Created Event ID: {intent.get('created_event_id', 'Not created')}")
        print(f"      Processed At: {intent.get('processed_at', 'Not processed')}")
    
    # Check calendar events
    print("\n" + "="*100)
    print("📅 Calendar Events")
    print("="*100)
    
    calendar_events = await db.calendar_events.find({
        "user_id": user_id
    }).sort("created_at", -1).limit(10).to_list(length=10)
    
    print(f"\nFound: {len(calendar_events)} calendar events")
    
    for event in calendar_events:
        print(f"\n   Calendar Event:")
        print(f"      ID: {event.get('id')}")
        print(f"      Title: {event.get('title')}")
        print(f"      Start: {event.get('start_time')}")
        print(f"      End: {event.get('end_time')}")
        print(f"      External Event ID: {event.get('external_event_id')}")
        print(f"      Meeting Intent ID: {event.get('meeting_intent_id')}")
        print(f"      Reminder Sent: {event.get('reminder_sent', False)}")
        print(f"      Reminders: {event.get('reminders', 'N/A')}")
    
    # Check if calendar reminder service is running
    print("\n" + "="*100)
    print("🔔 Reminder Service Check")
    print("="*100)
    
    # Check if there are any scheduled reminders
    # This would be in a separate collection or as part of calendar events
    
    # Look for upcoming events that need reminders
    now = datetime.utcnow()
    upcoming_events = await db.calendar_events.find({
        "user_id": user_id,
        "start_time": {"$gte": now.isoformat()},
        "reminder_sent": {"$ne": True}
    }).to_list(length=10)
    
    print(f"\n📆 Upcoming Events Needing Reminders: {len(upcoming_events)}")
    for event in upcoming_events:
        print(f"   - {event.get('title')} at {event.get('start_time')}")
    
    # Check calendar providers
    print("\n" + "="*100)
    print("🗓️ Calendar Providers")
    print("="*100)
    
    providers = await db.calendar_providers.find({
        "user_id": user_id
    }).to_list(length=10)
    
    for provider in providers:
        print(f"\n   Provider:")
        print(f"      ID: {provider.get('id')}")
        print(f"      Type: {provider.get('provider_type')}")
        print(f"      OAuth Email: {provider.get('oauth_email')}")
        print(f"      Active: {provider.get('is_active')}")
    
    # Diagnosis
    print("\n" + "="*100)
    print("🔍 DIAGNOSIS")
    print("="*100)
    
    issues = []
    
    # Issue 1: Check if meeting details are in draft responses
    emails_with_meetings = [e for e in emails if e.get('meeting_detected')]
    if emails_with_meetings:
        drafts_missing_details = []
        for e in emails_with_meetings:
            draft = e.get('draft', '').lower()
            if not any(keyword in draft for keyword in ['calendar', 'schedule', 'invite', 'meeting']):
                drafts_missing_details.append(e.get('subject', 'Unknown'))
        
        if drafts_missing_details:
            issues.append(f"❌ {len(drafts_missing_details)} meeting emails missing details in draft")
            print(f"\n❌ Issue 1: Meeting details NOT included in email responses")
            print(f"   Affected emails: {', '.join(drafts_missing_details)}")
        else:
            print(f"\n✅ Meeting details ARE included in email responses")
    
    # Issue 2: Check if calendar events are being created
    if meeting_intents and not calendar_events:
        issues.append("❌ Meeting intents exist but NO calendar events created")
        print(f"\n❌ Issue 2: Meeting intents created but calendar events NOT created")
        print(f"   {len(meeting_intents)} meeting intents, but 0 calendar events")
    elif meeting_intents and calendar_events:
        print(f"\n✅ Calendar events ARE being created")
        print(f"   {len(meeting_intents)} meeting intents, {len(calendar_events)} calendar events")
    
    # Issue 3: Check if reminders are configured
    if calendar_events:
        events_without_reminders = [e for e in calendar_events if not e.get('reminders')]
        if events_without_reminders:
            issues.append(f"❌ {len(events_without_reminders)} calendar events missing reminder configuration")
            print(f"\n❌ Issue 3: Calendar events created WITHOUT reminders")
            print(f"   {len(events_without_reminders)}/{len(calendar_events)} events missing reminders")
        else:
            print(f"\n✅ Calendar events have reminder configurations")
        
        # Check if reminders are being sent
        events_needing_reminders = [e for e in calendar_events if not e.get('reminder_sent')]
        if events_needing_reminders:
            print(f"\n⚠️ Reminder Status: {len(events_needing_reminders)} events have NOT sent reminders yet")
            print(f"   (This may be normal if events are in the future)")
    
    # Summary
    print("\n" + "="*100)
    print("📊 SUMMARY")
    print("="*100)
    print(f"Total Emails: {len(emails)}")
    print(f"Emails with Meeting Detection: {len([e for e in emails if e.get('meeting_detected')])}")
    print(f"Meeting Intents: {len(meeting_intents)}")
    print(f"Calendar Events: {len(calendar_events)}")
    print(f"Calendar Providers: {len(providers)}")
    print(f"Issues Found: {len(issues)}")
    
    if issues:
        print("\n🚨 ISSUES:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ No critical issues found")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(investigate_meeting_workflow())
