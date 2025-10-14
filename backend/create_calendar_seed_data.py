#!/usr/bin/env python3
"""
Create seed data for calendar agent testing
"""
import os
import sys
from datetime import datetime, timezone, timedelta
import pymongo
import uuid

sys.path.append('/app/backend')

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

client = pymongo.MongoClient(MONGO_URL)
db = client[DB_NAME]

# User details
USER_ID = 'dbd3d0ea-e7b7-4183-b902-af84f2a1661b'
USER_EMAIL = 'amits.joys@gmail.com'

# Get email account
email_account = db.email_accounts.find_one({"user_id": USER_ID})
if not email_account:
    print("❌ No email account found for user")
    sys.exit(1)

ACCOUNT_ID = email_account['id']
print(f"✅ Found email account: {ACCOUNT_ID}")

# Current time
now = datetime.now(timezone.utc)

# Create meeting request emails
meeting_emails = [
    {
        "id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "account_id": ACCOUNT_ID,
        "thread_id": str(uuid.uuid4()),
        "sender": "john.doe@techcorp.com",
        "sender_name": "John Doe",
        "recipients": [USER_EMAIL],
        "subject": "Product Demo Meeting Request",
        "body": f"""Hi Amit,

I hope this email finds you well. I'd like to schedule a product demo to show you our new AI-powered analytics platform.

Would you be available for a 30-minute call tomorrow at 2:00 PM EST? We can discuss how our solution can help streamline your data workflows.

Looking forward to hearing from you!

Best regards,
John Doe
Senior Sales Manager
TechCorp Solutions""",
        "received_at": now - timedelta(minutes=10),
        "status": "new",
        "is_read": False,
        "has_attachments": False,
        "importance": "normal",
        "labels": ["INBOX"],
        "processed": False
    },
    {
        "id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "account_id": ACCOUNT_ID,
        "thread_id": str(uuid.uuid4()),
        "sender": "sarah.johnson@consulting.com",
        "sender_name": "Sarah Johnson",
        "recipients": [USER_EMAIL],
        "subject": "Quick sync on Q4 strategy",
        "body": f"""Hey Amit,

Can we have a quick 15-minute call this Friday at 10:30 AM to discuss the Q4 strategy? I want to get your input on the new initiatives we're planning.

Let me know if that works for you, or suggest another time that's better.

Thanks!
Sarah""",
        "received_at": now - timedelta(minutes=30),
        "status": "new",
        "is_read": False,
        "has_attachments": False,
        "importance": "normal",
        "labels": ["INBOX"],
        "processed": False
    },
    {
        "id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "account_id": ACCOUNT_ID,
        "thread_id": str(uuid.uuid4()),
        "sender": "mike.chen@startupxyz.io",
        "sender_name": "Mike Chen",
        "recipients": [USER_EMAIL],
        "subject": "Interview Invitation - Senior Engineer Position",
        "body": f"""Dear Amit,

Thank you for your application for the Senior Engineer position at StartupXYZ. We're impressed with your background and would like to invite you for an interview.

Are you available for a 1-hour technical interview next Tuesday, October 18th at 3:00 PM? The interview will be conducted via Google Meet.

Please confirm your availability at your earliest convenience.

Best regards,
Mike Chen
Head of Engineering
StartupXYZ""",
        "received_at": now - timedelta(hours=1),
        "status": "new",
        "is_read": False,
        "has_attachments": False,
        "importance": "high",
        "labels": ["INBOX", "IMPORTANT"],
        "processed": False
    },
    {
        "id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "account_id": ACCOUNT_ID,
        "thread_id": str(uuid.uuid4()),
        "sender": "emma.wilson@webagency.com",
        "sender_name": "Emma Wilson",
        "recipients": [USER_EMAIL],
        "subject": "Website redesign consultation",
        "body": f"""Hi Amit,

I'd love to schedule a consultation call to discuss your website redesign project. Based on our initial conversation, I think we can create something amazing for you.

How does next Wednesday at 4:00 PM sound for a 45-minute call? We'll go over design concepts, timeline, and pricing.

Let me know!

Emma Wilson
Creative Director
WebAgency Pro""",
        "received_at": now - timedelta(hours=2),
        "status": "new",
        "is_read": False,
        "has_attachments": False,
        "importance": "normal",
        "labels": ["INBOX"],
        "processed": False
    },
    {
        "id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "account_id": ACCOUNT_ID,
        "thread_id": str(uuid.uuid4()),
        "sender": "info@conference.com",
        "sender_name": "Conference Team",
        "recipients": [USER_EMAIL],
        "subject": "Thank you for subscribing to our newsletter",
        "body": """Dear Subscriber,

Thank you for subscribing to our newsletter. You'll now receive weekly updates about upcoming tech conferences and events.

Stay tuned for exciting news!

Best regards,
Conference Team""",
        "received_at": now - timedelta(hours=3),
        "status": "new",
        "is_read": False,
        "has_attachments": False,
        "importance": "normal",
        "labels": ["INBOX"],
        "processed": False
    }
]

# Insert emails
print(f"\n📧 Creating {len(meeting_emails)} seed emails...")
result = db.emails.insert_many(meeting_emails)
print(f"✅ Created {len(result.inserted_ids)} emails")

# Print email IDs for testing
print("\n📋 Email IDs created:")
for i, email in enumerate(meeting_emails, 1):
    print(f"{i}. {email['subject'][:50]}... (ID: {email['id']})")
    print(f"   Sender: {email['sender']}")
    print(f"   Meeting indicators: {'Yes' if any(word in email['body'].lower() for word in ['meeting', 'call', 'interview', 'schedule']) else 'No'}")
    print()

print("✅ Seed data creation complete!")
print("\n🔄 Next steps:")
print("1. Process emails through AI workflow")
print("2. Verify meeting detection")
print("3. Check calendar events creation")
print("4. Verify reminders scheduling")
