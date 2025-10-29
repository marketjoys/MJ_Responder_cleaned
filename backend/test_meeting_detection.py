#!/usr/bin/env python3
"""
Test meeting detection manually for the email
"""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from calendar_agent import CalendarAgent
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

async def test_meeting_detection():
    """Test meeting detection for the specific email"""
    
    # Get the email
    client = MongoClient(os.getenv("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.getenv("DB_NAME", "test_database")]
    
    email = db.emails.find_one({"id": "cd07f01c-1551-4d89-ac73-b4872fdd360b"})
    
    print("="*70)
    print("🔍 TESTING MEETING DETECTION")
    print("="*70)
    print()
    print(f"Subject: {email['subject']}")
    print(f"Sender: {email['sender']}")
    print(f"Body: {email['body']}")
    print()
    
    # Initialize calendar agent
    calendar_agent = CalendarAgent()
    
    # Test meeting detection
    print("Running meeting detection...")
    result = await calendar_agent.analyze_email_for_meetings(
        email_content=email['body'],
        subject=email['subject'],
        sender=email['sender'],
        user_timezone="Asia/Kolkata",
        thread_context=[]
    )
    
    print()
    print("="*70)
    print("📊 DETECTION RESULTS")
    print("="*70)
    print(f"Meeting Detected: {result.meeting_detected}")
    print(f"Confidence Score: {result.confidence_score}")
    print(f"Detected DateTime: {result.detected_datetime}")
    print(f"Detected Timezone: {result.detected_timezone}")
    print(f"Detected Title: {result.detected_title}")
    print(f"Detected Location: {result.detected_location}")
    print(f"Detected Attendees: {result.detected_attendees}")
    print(f"Suggested Duration: {result.suggested_duration}")
    print(f"Needs Confirmation: {result.needs_confirmation}")
    print()
    
    if result.confidence_score < 0.6:
        print("❌ Confidence too low! Minimum required: 0.6")
        print("   This is why no calendar event was created.")
    elif not result.detected_datetime:
        print("❌ No datetime detected!")
        print("   Calendar events require a specific date/time.")
    else:
        print("✅ Meeting should have been detected and calendar event created!")
        print("   Something else prevented the calendar event creation.")
    
    print()
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_meeting_detection())
