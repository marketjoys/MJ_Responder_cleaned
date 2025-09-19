#!/usr/bin/env python3
"""
Manual Response Detection Test
Tests the response detection functionality directly
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def test_response_detection():
    """Test response detection functionality directly"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        print("🔍 Testing Response Detection Functionality...")
        
        # Import the response detection function
        from server import detect_and_handle_responses, cancel_follow_ups_for_thread
        
        # Create test thread
        thread_id = f"response-test-{uuid.uuid4()}"
        
        # Create original email
        original_email = {
            "id": str(uuid.uuid4()),
            "account_id": "test-account",
            "message_id": f"<original@example.com>",
            "thread_id": thread_id,
            "subject": "Test Response Detection",
            "sender": "customer@example.com",
            "recipient": "support@company.com",
            "body": "This is the original email",
            "received_at": datetime.utcnow() - timedelta(hours=1),
            "status": "processed",
            "created_at": datetime.utcnow() - timedelta(hours=1)
        }
        
        await db.emails.insert_one(original_email)
        print(f"✅ Created original email: {original_email['id']}")
        
        # Create follow-up emails
        follow_ups = []
        for i in range(3):
            follow_up = {
                "id": str(uuid.uuid4()),
                "original_email_id": original_email["id"],
                "account_id": "test-account",
                "user_id": "test-user",
                "thread_id": thread_id,
                "recipient_email": "customer@example.com",
                "subject": f"Re: Test Response Detection - Follow-up #{i+1}",
                "status": "pending",
                "follow_up_number": i+1,
                "scheduled_time": datetime.utcnow() + timedelta(hours=24*(i+1)),
                "draft_content": f"This is follow-up #{i+1}",
                "created_at": datetime.utcnow()
            }
            follow_ups.append(follow_up)
            await db.follow_up_emails.insert_one(follow_up)
        
        print(f"✅ Created {len(follow_ups)} follow-up emails")
        
        # Check initial state - should have pending follow-ups
        pending_count = await db.follow_up_emails.count_documents({
            "thread_id": thread_id,
            "status": "pending"
        })
        print(f"📊 Initial pending follow-ups: {pending_count}")
        
        # Run response detection - should find no responses yet
        print("🔍 Running initial response detection...")
        await detect_and_handle_responses()
        
        # Check if follow-ups are still pending
        pending_after_initial = await db.follow_up_emails.count_documents({
            "thread_id": thread_id,
            "status": "pending"
        })
        print(f"📊 Pending follow-ups after initial detection: {pending_after_initial}")
        
        # Now add a response email
        response_email = {
            "id": str(uuid.uuid4()),
            "account_id": "test-account",
            "message_id": f"<response@example.com>",
            "thread_id": thread_id,
            "subject": "Re: Test Response Detection",
            "sender": "support@company.com",  # Different sender
            "recipient": "customer@example.com",
            "body": "This is a response to the original email",
            "received_at": datetime.utcnow(),
            "status": "processed",
            "created_at": datetime.utcnow()
        }
        
        await db.emails.insert_one(response_email)
        print(f"✅ Created response email: {response_email['id']}")
        
        # Run response detection again - should detect response and cancel follow-ups
        print("🔍 Running response detection after adding response...")
        await detect_and_handle_responses()
        
        # Check if follow-ups were cancelled
        pending_after_response = await db.follow_up_emails.count_documents({
            "thread_id": thread_id,
            "status": "pending"
        })
        cancelled_count = await db.follow_up_emails.count_documents({
            "thread_id": thread_id,
            "status": "cancelled"
        })
        
        print(f"📊 Pending follow-ups after response detection: {pending_after_response}")
        print(f"📊 Cancelled follow-ups: {cancelled_count}")
        
        # Test results
        detection_working = (pending_after_initial == 3 and pending_after_response == 0 and cancelled_count == 3)
        
        if detection_working:
            print("✅ Response detection is working correctly!")
        else:
            print("❌ Response detection has issues")
            print(f"   Expected: 3 pending initially, 0 pending after response, 3 cancelled")
            print(f"   Actual: {pending_after_initial} pending initially, {pending_after_response} pending after response, {cancelled_count} cancelled")
        
        # Test manual cancellation function
        print("\n🧪 Testing manual follow-up cancellation...")
        
        # Create another test thread
        thread_id_2 = f"manual-test-{uuid.uuid4()}"
        
        # Create follow-ups for manual test
        manual_follow_ups = []
        for i in range(2):
            follow_up = {
                "id": str(uuid.uuid4()),
                "original_email_id": "manual-test-email",
                "account_id": "test-account",
                "user_id": "test-user",
                "thread_id": thread_id_2,
                "recipient_email": "test@example.com",
                "subject": f"Manual Test Follow-up #{i+1}",
                "status": "pending",
                "follow_up_number": i+1,
                "scheduled_time": datetime.utcnow() + timedelta(hours=24*(i+1)),
                "draft_content": f"Manual test follow-up #{i+1}",
                "created_at": datetime.utcnow()
            }
            manual_follow_ups.append(follow_up)
            await db.follow_up_emails.insert_one(follow_up)
        
        # Test manual cancellation
        cancelled_manual = await cancel_follow_ups_for_thread(thread_id_2, "Manual test cancellation")
        
        manual_cancelled_count = await db.follow_up_emails.count_documents({
            "thread_id": thread_id_2,
            "status": "cancelled"
        })
        
        manual_working = (cancelled_manual == 2 and manual_cancelled_count == 2)
        
        if manual_working:
            print("✅ Manual follow-up cancellation is working correctly!")
        else:
            print("❌ Manual follow-up cancellation has issues")
            print(f"   Expected: 2 cancelled, Actual: {cancelled_manual} returned, {manual_cancelled_count} in DB")
        
        # Cleanup
        await db.emails.delete_many({"thread_id": {"$in": [thread_id, thread_id_2]}})
        await db.follow_up_emails.delete_many({"thread_id": {"$in": [thread_id, thread_id_2]}})
        print("🧹 Cleaned up test data")
        
        return detection_working and manual_working
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        client.close()

if __name__ == "__main__":
    result = asyncio.run(test_response_detection())
    if result:
        print("\n✅ All response detection tests passed!")
    else:
        print("\n❌ Some response detection tests failed!")