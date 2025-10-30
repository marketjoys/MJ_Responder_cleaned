import pymongo
from datetime import datetime

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

user = db.users.find_one({"email": "amits.joys@gmail.com"})
user_id = str(user["_id"])

print("=" * 80)
print("CALENDAR INTEGRATION STATUS")
print("=" * 80)

# Check meeting intents
meeting_intents = list(db.meeting_intents.find({"user_id": user_id}))
print(f"\n📅 Meeting Intents Created: {len(meeting_intents)}")
for mi in meeting_intents:
    print(f"\n  Title: {mi.get('detected_title')}")
    print(f"  DateTime: {mi.get('detected_datetime')}")
    print(f"  Confidence: {mi.get('confidence_score')}")
    print(f"  Email ID: {mi.get('email_id')}")
    print(f"  Created Event ID: {mi.get('created_event_id', 'N/A')}")

# Check calendar events
calendar_events = list(db.calendar_events.find({"user_id": user_id}))
print(f"\n📆 Calendar Events Created: {len(calendar_events)}")
for event in calendar_events:
    print(f"\n  Title: {event.get('title')}")
    print(f"  Start: {event.get('start_time')}")
    print(f"  End: {event.get('end_time')}")
    print(f"  Location: {event.get('location', 'N/A')}")
    print(f"  External Event ID: {event.get('external_event_id', 'N/A')}")

# Check emails with meeting detection
meeting_emails = list(db.emails.find({
    "user_id": user_id,
    "meeting_detected": True
}))
print(f"\n✉️  Emails with Meeting Detection: {len(meeting_emails)}")
for email in meeting_emails:
    print(f"\n  Subject: {email.get('subject')}")
    print(f"  Meeting Confidence: {email.get('meeting_confidence')}")
    print(f"  Calendar Action: {email.get('calendar_action')}")
    
    # Check if draft includes event details
    draft = email.get('draft', '')
    has_details = 'CALENDAR EVENT CREATED' in draft.upper() or 'MEETING DETECTED' in draft.upper()
    print(f"  Event Details in Draft: {'✅' if has_details else '❌'}")

