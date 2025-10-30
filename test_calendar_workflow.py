#!/usr/bin/env python3
"""
Test complete meeting detection and calendar event creation workflow
"""
import asyncio
import sys
import os
import httpx
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import uuid

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def test_workflow():
    """Test the complete workflow"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    if not user:
        print("❌ User not found")
        return
    
    user_id = user['id']
    print(f"✅ User: {user['email']} (ID: {user_id})")
    
    # Get email account
    account = await db.email_accounts.find_one({"user_id": user_id})
    if not account:
        print("❌ No email account found")
        return
    
    print(f"✅ Email Account: {account['email']}")
    
    # Create a test email in the database
    test_email_id = str(uuid.uuid4())
    test_thread_id = str(uuid.uuid4())
    
    test_email = {
        "id": test_email_id,
        "thread_id": test_thread_id,
        "user_id": user_id,
        "account_id": account['id'],
        "sender": "testuser@example.com",
        "subject": "Meeting Request - Project Discussion",
        "body": "Hi, can we schedule a call tomorrow at 3:00 PM IST to discuss the project roadmap and next steps?",
        "received_at": datetime.utcnow(),
        "status": "received",
        "is_read": False
    }
    
    print(f"\n📧 Created Test Email:")
    print(f"   ID: {test_email_id}")
    print(f"   Subject: {test_email['subject']}")
    print(f"   Body: {test_email['body']}")
    
    # Insert test email
    await db.emails.insert_one(test_email)
    
    # Now trigger email processing via API
    print(f"\n🔄 Processing email via backend API...")
    
    # Get auth token first
    async with httpx.AsyncClient() as http_client:
        # Login
        login_response = await http_client.post(
            "http://localhost:8001/api/login",
            json={"email": "amits.joys@gmail.com", "password": "ij@123"}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return
        
        token = login_response.json()['access_token']
        print(f"✅ Authenticated successfully")
        
        # Process the email
        headers = {"Authorization": f"Bearer {token}"}
        
        # Wait a moment for any background processing
        await asyncio.sleep(2)
        
        # Check if email was processed (it should be auto-processed by the system)
        email_check = await db.emails.find_one({"id": test_email_id})
        
        print(f"\n📧 Email Status After Processing:")
        print(f"   Status: {email_check.get('status', 'N/A')}")
        print(f"   Meeting Detected: {email_check.get('meeting_detected', 'N/A')}")
        print(f"   Meeting Confidence: {email_check.get('meeting_confidence', 'N/A')}")
        print(f"   Meeting DateTime: {email_check.get('meeting_datetime', 'N/A')}")
        print(f"   Calendar Action: {email_check.get('calendar_action', 'N/A')}")
        print(f"   Draft: {email_check.get('draft', 'N/A')[:100] if email_check.get('draft') else 'N/A'}...")
        
        # Check for meeting intents
        meeting_intents = await db.meeting_intents.find({"email_id": test_email_id}).to_list(10)
        print(f"\n📋 Meeting Intents Created: {len(meeting_intents)}")
        
        for intent in meeting_intents:
            print(f"\n   Meeting Intent:")
            print(f"      ID: {intent.get('id')}")
            print(f"      Status: {intent.get('status')}")
            print(f"      Confidence: {intent.get('confidence_score')}")
            print(f"      DateTime: {intent.get('detected_datetime')}")
            print(f"      Title: {intent.get('detected_title')}")
            print(f"      Created Event ID: {intent.get('created_event_id', 'Not created')}")
        
        # Check for calendar events
        calendar_events = await db.calendar_events.find({"user_id": user_id}).to_list(10)
        print(f"\n📅 Calendar Events Created: {len(calendar_events)}")
        
        for event in calendar_events:
            print(f"\n   Calendar Event:")
            print(f"      ID: {event.get('id')}")
            print(f"      Title: {event.get('title')}")
            print(f"      Start: {event.get('start_time')}")
            print(f"      End: {event.get('end_time')}")
            print(f"      External Event ID: {event.get('external_event_id')}")
            print(f"      Meeting Intent ID: {event.get('meeting_intent_id')}")
    
    # Cleanup - delete test email
    print(f"\n🧹 Cleaning up test email...")
    await db.emails.delete_one({"id": test_email_id})
    print(f"✅ Test email deleted")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_workflow())
