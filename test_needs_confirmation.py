#!/usr/bin/env python3
"""
Test meeting detection to see needs_confirmation value
"""
import asyncio
import sys
sys.path.append('/app/backend')

from calendar_agent import calendar_agent

async def test():
    """Test meeting detection"""
    
    # Test email content from the recent email
    email_body = "Can we meet tomorrow at 3 PM to discuss the project?"
    subject = "Meeting Request"
    sender = "test@example.com"
    timezone = "UTC"
    
    print("Testing Meeting Detection...")
    print(f"Subject: {subject}")
    print(f"Body: {email_body}")
    print(f"Timezone: {timezone}\n")
    
    # Run detection
    result = await calendar_agent.analyze_email_for_meetings(
        email_body,
        subject,
        sender,
        timezone,
        thread_context=None
    )
    
    print("✅ Detection Result:")
    print(f"   Meeting Detected: {result.meeting_detected}")
    print(f"   Confidence Score: {result.confidence_score}")
    print(f"   Detected DateTime: {result.detected_datetime}")
    print(f"   Detected Timezone: {result.detected_timezone}")
    print(f"   Detected Title: {result.detected_title}")
    print(f"   Suggested Duration: {result.suggested_duration}")
    print(f"   Needs Confirmation: {result.needs_confirmation}")  # KEY CHECK
    print()
    
    # Check the condition
    print("📊 Condition Check:")
    print(f"   confidence_score >= 0.4: {result.confidence_score >= 0.4}")
    print(f"   not needs_confirmation: {not result.needs_confirmation}")
    print(f"   BOTH conditions met: {result.confidence_score >= 0.4 and not result.needs_confirmation}")
    print()
    
    if result.confidence_score >= 0.4 and not result.needs_confirmation:
        print("✅ Should CREATE calendar event automatically")
    elif result.confidence_score >= 0.4:
        print("⚠️ Should create meeting intent but NEEDS CONFIRMATION")
    else:
        print("❌ Should NOT process (confidence too low)")

if __name__ == "__main__":
    asyncio.run(test())
