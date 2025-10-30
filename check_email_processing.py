#!/usr/bin/env python3
"""
Check email processing for meeting detection
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

async def check_emails():
    """Check emails for meeting detection"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    if not user:
        print("❌ User not found")
        return
    
    user_id = user['id']
    print(f"✅ User: {user['email']} (ID: {user_id})")
    
    # Get all emails for this user
    emails = await db.emails.find({"user_id": user_id}).sort("received_at", -1).to_list(length=50)
    
    print(f"\n📧 Total Emails: {len(emails)}")
    print("="*100)
    
    # Group emails by status
    by_status = {}
    for email in emails:
        status = email.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1
    
    print("\n📊 Emails by Status:")
    for status, count in by_status.items():
        print(f"   {status}: {count}")
    
    # Check for emails with meeting keywords
    meeting_keywords = ['meeting', 'schedule', 'call', 'discuss', 'demo', 'interview', 'appointment']
    
    print(f"\n🔍 Checking recent emails for meeting keywords...")
    print("="*100)
    
    meeting_related_emails = []
    for email in emails[:20]:  # Check last 20 emails
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        has_keyword = any(keyword in subject or keyword in body for keyword in meeting_keywords)
        
        if has_keyword:
            meeting_related_emails.append(email)
            print(f"\n📧 Email ID: {email.get('id')}")
            print(f"   Subject: {email.get('subject', 'N/A')}")
            print(f"   Sender: {email.get('sender', 'N/A')}")
            print(f"   Status: {email.get('status', 'N/A')}")
            print(f"   Received: {email.get('received_at', 'N/A')}")
            print(f"   Meeting Detected: {email.get('meeting_detected', 'Not checked')}")
            print(f"   Meeting Confidence: {email.get('meeting_confidence', 'N/A')}")
            print(f"   Calendar Action: {email.get('calendar_action', 'None')}")
            print(f"   Classified Intent: {email.get('classified_intent', 'Not classified')}")
            print(f"   Body Preview: {email.get('body', '')[:150]}...")
    
    print(f"\n📊 Found {len(meeting_related_emails)} emails with meeting-related keywords")
    
    # Check if any emails have been processed but didn't create calendar events
    processed_emails = await db.emails.find({
        "user_id": user_id,
        "status": {"$in": ["processed", "ready_to_send", "sent"]}
    }).to_list(length=100)
    
    print(f"\n✅ Processed Emails: {len(processed_emails)}")
    print("="*100)
    
    for email in processed_emails[:10]:  # Show last 10 processed
        print(f"\n📧 Email ID: {email.get('id')}")
        print(f"   Subject: {email.get('subject', 'N/A')}")
        print(f"   Status: {email.get('status')}")
        print(f"   Meeting Detected: {email.get('meeting_detected', False)}")
        print(f"   Meeting Confidence: {email.get('meeting_confidence', 'N/A')}")
        print(f"   Calendar Action: {email.get('calendar_action', 'None')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_emails())
