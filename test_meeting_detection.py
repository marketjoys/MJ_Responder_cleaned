#!/usr/bin/env python3
"""
Test meeting detection with actual email content
"""
import asyncio
import sys
sys.path.append('/app/backend')

from calendar_agent import calendar_agent

async def test_detection():
    """Test meeting detection"""
    
    # Test email content
    email_body = "Let set up a demo call tomorrow 8.30pm IST?"
    subject = "Hi team"
    sender = "ronsmith.joys@gmail.com"
    timezone = "Asia/Kolkata"  # IST
    
    print("="*80)
    print("🧪 Testing Meeting Detection")
    print("="*80)
    print(f"Subject: {subject}")
    print(f"Body: {email_body}")
    print(f"Sender: {sender}")
    print(f"Timezone: {timezone}")
    print("="*80)
    
    # Run detection
    try:
        result = await calendar_agent.analyze_email_for_meetings(
            email_body,
            subject,
            sender,
            timezone,
            thread_context=None
        )
        
        print(f"\n✅ Detection Result:")
        print(f"   Meeting Detected: {result.meeting_detected}")
        print(f"   Confidence Score: {result.confidence_score}")
        print(f"   Detected DateTime: {result.detected_datetime}")
        print(f"   Detected Timezone: {result.detected_timezone}")
        print(f"   Detected Title: {result.detected_title}")
        print(f"   Detected Location: {result.detected_location}")
        print(f"   Detected Attendees: {result.detected_attendees}")
        print(f"   Suggested Duration: {result.suggested_duration}")
        print(f"   Needs Confirmation: {result.needs_confirmation}")
        
    except Exception as e:
        print(f"\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_detection())
