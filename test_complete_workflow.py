"""
Complete workflow test for amits.joys@gmail.com
Tests the full email processing pipeline
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import uuid
from tasks import enqueue_email_processing
from server import process_email_async, redis_conn, RQ_ENABLED
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to MongoDB
client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def test_workflow():
    """Test complete email processing workflow"""
    
    print("=" * 80)
    print("TESTING COMPLETE EMAIL WORKFLOW")
    print("=" * 80)
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    if not user:
        print("❌ User not found!")
        return
    
    user_id = str(user["_id"])
    print(f"✅ User found: {user_id}")
    
    # Get email account
    account = await db.email_accounts.find_one({"user_id": user_id})
    if not account:
        print("❌ Email account not found!")
        return
    
    account_id = str(account["_id"])
    print(f"✅ Email account found: {account_id}")
    
    # Get all unprocessed emails
    emails = await db.emails.find({
        "user_id": user_id,
        "status": "new"
    }).to_list(100)
    
    print(f"\n📧 Found {len(emails)} unprocessed emails")
    
    if not emails:
        print("No emails to process")
        return
    
    # Process each email
    for idx, email in enumerate(emails, 1):
        email_id = str(email["_id"])
        print(f"\n{'=' * 80}")
        print(f"Processing Email {idx}/{len(emails)}")
        print(f"{'=' * 80}")
        print(f"Email ID: {email_id}")
        print(f"From: {email.get('sender_email')}")
        print(f"Subject: {email.get('subject')}")
        print(f"Status: {email.get('status')}")
        
        try:
            # Process through the complete workflow
            if RQ_ENABLED:
                print("📋 Enqueuing email processing via RQ...")
                job = enqueue_email_processing(email_id, delay=0)
                print(f"✅ Job enqueued: {job.id}")
                
                # Wait for job to complete
                print("⏳ Waiting for job to complete...")
                timeout = 60
                start_time = datetime.utcnow()
                while not job.is_finished and not job.is_failed:
                    await asyncio.sleep(1)
                    job.refresh()
                    if (datetime.utcnow() - start_time).seconds > timeout:
                        print("⏰ Job timeout!")
                        break
                
                if job.is_finished:
                    print(f"✅ Job completed successfully")
                elif job.is_failed:
                    print(f"❌ Job failed: {job.exc_info}")
            else:
                print("⚙️  Processing directly (RQ not enabled)...")
                await process_email_async(email_id)
                print("✅ Email processed")
            
            # Check the processed email
            processed_email = await db.emails.find_one({"_id": email_id})
            if processed_email:
                print(f"\n📊 PROCESSING RESULTS:")
                print(f"   Status: {processed_email.get('status')}")
                print(f"   Intents: {len(processed_email.get('intents', []))}")
                for intent in processed_email.get('intents', []):
                    print(f"     - {intent.get('name')} (confidence: {intent.get('confidence', 0):.2f})")
                print(f"   Draft Length: {len(processed_email.get('draft', ''))} chars")
                print(f"   Validation: {processed_email.get('validation_result', {}).get('status')}")
                print(f"   Meeting Detected: {processed_email.get('meeting_detected', False)}")
                print(f"   Calendar Action: {processed_email.get('calendar_action', 'None')}")
                
                # Check if draft includes event details for meeting emails
                if processed_email.get('meeting_detected'):
                    draft = processed_email.get('draft', '')
                    has_date = any(keyword in draft.lower() for keyword in ['date:', 'time:', 'meeting', 'scheduled'])
                    print(f"   Event Details in Draft: {'✅' if has_date else '❌'}")
                
        except Exception as e:
            print(f"❌ Error processing email: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("CHECKING POST-PROCESSING STATE")
    print(f"{'=' * 80}")
    
    # Check sent emails
    sent_emails = await db.emails.find({
        "user_id": user_id,
        "status": "sent"
    }).to_list(100)
    print(f"\n✉️  Sent Emails: {len(sent_emails)}")
    
    # Check ready to send emails
    ready_emails = await db.emails.find({
        "user_id": user_id,
        "status": "ready_to_send"
    }).to_list(100)
    print(f"📤 Ready to Send: {len(ready_emails)}")
    
    # Check follow-ups
    follow_ups = await db.follow_up_emails.find({
        "user_id": user_id
    }).to_list(100)
    print(f"📅 Follow-ups Created: {len(follow_ups)}")
    for fu in follow_ups[:3]:
        print(f"   - {fu.get('status')} | Scheduled: {fu.get('scheduled_for')} | Recipient: {fu.get('recipient_email')}")
    
    # Check calendar events
    calendar_events = await db.calendar_events.find({
        "user_id": user_id
    }).to_list(100)
    print(f"📆 Calendar Events Created: {len(calendar_events)}")
    for event in calendar_events:
        print(f"   - {event.get('title')} | {event.get('start_time')} | Location: {event.get('location', 'N/A')}")
    
    # Check meeting intents
    meeting_intents = await db.meeting_intents.find({
        "user_id": user_id
    }).to_list(100)
    print(f"🤝 Meeting Intents Created: {len(meeting_intents)}")
    for mi in meeting_intents:
        print(f"   - {mi.get('detected_title')} | {mi.get('detected_datetime')} | Confidence: {mi.get('confidence_score'):.2f}")
    
    print(f"\n{'=' * 80}")
    print("WORKFLOW TEST COMPLETE")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    asyncio.run(test_workflow())
