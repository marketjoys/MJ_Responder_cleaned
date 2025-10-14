#!/usr/bin/env python3
"""
Test complete calendar agent workflow
"""
import os
import sys
import asyncio
from datetime import datetime, timezone

sys.path.append('/app/backend')

# Set environment variables
os.environ['MONGO_URL'] = 'mongodb://localhost:27017'
os.environ['DB_NAME'] = 'test_database'

from motor.motor_asyncio import AsyncIOMotorClient
from server import process_email_workflow

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def test_workflow():
    """Test the complete calendar workflow"""
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("🔍 Testing Calendar Agent Workflow")
    print("=" * 60)
    
    # Get unprocessed emails
    emails = await db.emails.find({
        "user_id": "dbd3d0ea-e7b7-4183-b902-af84f2a1661b",
        "processed": False
    }).to_list(10)
    
    print(f"\n📧 Found {len(emails)} unprocessed emails")
    
    results = []
    for i, email in enumerate(emails, 1):
        print(f"\n{'=' * 60}")
        print(f"📨 Processing Email {i}/{len(emails)}")
        print(f"Subject: {email['subject']}")
        print(f"From: {email['sender']}")
        print(f"Email ID: {email['id']}")
        print("-" * 60)
        
        try:
            # Process through AI workflow
            result = await process_email_workflow(email['id'])
            
            # Check if meeting was detected
            updated_email = await db.emails.find_one({"id": email['id']})
            
            print(f"\n✅ Processing Result:")
            print(f"   Status: {updated_email.get('status', 'unknown')}")
            print(f"   Draft Generated: {'Yes' if updated_email.get('draft') else 'No'}")
            
            # Check for meeting intent
            meeting_intent = await db.meeting_intents.find_one({
                "email_id": email['id']
            })
            
            if meeting_intent:
                print(f"\n📅 Meeting Detected:")
                print(f"   Confidence: {meeting_intent.get('confidence_score', 0):.2f}")
                print(f"   Title: {meeting_intent.get('detected_title', 'N/A')}")
                print(f"   DateTime: {meeting_intent.get('detected_datetime', 'N/A')}")
                print(f"   Status: {meeting_intent.get('status', 'N/A')}")
                
                # Check if calendar event was created
                if meeting_intent.get('created_event_id'):
                    event_id = meeting_intent['created_event_id']
                    calendar_event = await db.calendar_events.find_one({
                        "external_event_id": event_id
                    })
                    
                    if calendar_event:
                        print(f"\n🎉 Calendar Event Created:")
                        print(f"   Event ID: {event_id}")
                        print(f"   Title: {calendar_event.get('title', 'N/A')}")
                        print(f"   Start: {calendar_event.get('start_time', 'N/A')}")
                        print(f"   End: {calendar_event.get('end_time', 'N/A')}")
                        print(f"   Location: {calendar_event.get('location', 'None')}")
                        
                        results.append({
                            'email': email['subject'],
                            'meeting_detected': True,
                            'event_created': True,
                            'event_id': event_id
                        })
                    else:
                        print(f"\n⚠️  Event ID recorded but not found in calendar_events collection")
                        results.append({
                            'email': email['subject'],
                            'meeting_detected': True,
                            'event_created': False,
                            'issue': 'Event not stored in DB'
                        })
                else:
                    print(f"\n⚠️  Meeting detected but no event created (confidence too low or error)")
                    results.append({
                        'email': email['subject'],
                        'meeting_detected': True,
                        'event_created': False,
                        'issue': 'Low confidence or error'
                    })
            else:
                print(f"\n❌ No Meeting Detected")
                results.append({
                    'email': email['subject'],
                    'meeting_detected': False,
                    'event_created': False
                })
            
        except Exception as e:
            print(f"\n❌ Error processing email: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                'email': email['subject'],
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'=' * 60}")
    print("📊 WORKFLOW TEST SUMMARY")
    print("=" * 60)
    
    total = len(results)
    meetings_detected = sum(1 for r in results if r.get('meeting_detected'))
    events_created = sum(1 for r in results if r.get('event_created'))
    errors = sum(1 for r in results if 'error' in r)
    
    print(f"\n📧 Total Emails Processed: {total}")
    print(f"📅 Meetings Detected: {meetings_detected}/{total}")
    print(f"✅ Calendar Events Created: {events_created}/{meetings_detected if meetings_detected > 0 else total}")
    print(f"❌ Errors: {errors}/{total}")
    
    # Check calendar_events collection
    total_events = await db.calendar_events.count_documents({})
    print(f"\n📋 Total Calendar Events in DB: {total_events}")
    
    # Check reminders
    events_with_reminders = await db.calendar_events.count_documents({
        "reminder_sent": {"$exists": True}
    })
    print(f"🔔 Events with Reminder Tracking: {events_with_reminders}")
    
    if events_created > 0:
        print(f"\n✅ SUCCESS: Automated calendar workflow is working!")
    else:
        print(f"\n⚠️  WARNING: No calendar events were created automatically")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_workflow())
