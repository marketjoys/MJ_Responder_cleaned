#!/usr/bin/env python3
"""
Test to verify calendar event details are included in email draft responses
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import httpx
import uuid

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

async def test_event_details_in_response():
    """Test that calendar event details are included in email drafts"""
    print("=" * 70)
    print("CALENDAR EVENT DETAILS IN EMAIL DRAFT TEST")
    print("=" * 70)
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Step 1: Login
        print("\n🔐 Step 1: Authentication...")
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            login_response = await http_client.post(
                f"{backend_url}/api/auth/login",
                json={"email": "amits.joys@gmail.com", "password": "ij@123"}
            )
            
            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.status_code}")
                return
            
            login_data = login_response.json()
            token = login_data['access_token']
            user_id = login_data['user']['id']
            print(f"✅ Authenticated as: {login_data['user']['email']}")
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 2: Get user's email account
            print("\n📧 Step 2: Getting email account...")
            accounts_response = await http_client.get(
                f"{backend_url}/api/email-accounts",
                headers=headers
            )
            
            if accounts_response.status_code != 200 or not accounts_response.json():
                print("⚠️  No email accounts found")
                print("   Creating a test email account...")
                # You might need to create one or use the sample account
                account_id = "test_account_id"
            else:
                accounts = accounts_response.json()
                account_id = accounts[0]['id']
                print(f"✅ Using email account: {account_id}")
            
            # Step 3: Create a test email with meeting request
            print("\n📨 Step 3: Creating test email with meeting request...")
            
            email_id = str(uuid.uuid4())
            thread_id = str(uuid.uuid4())
            
            test_email = {
                "id": email_id,
                "user_id": user_id,
                "account_id": account_id,
                "thread_id": thread_id,
                "message_id": f"<{uuid.uuid4()}@mail.gmail.com>",
                "sender": "john.doe@example.com",
                "sender_name": "John Doe",
                "recipient": "amits.joys@gmail.com",
                "subject": "Let's Schedule a Product Demo",
                "body": """Hi Amit,

I hope this email finds you well. I've been following your AI email automation platform and I'm very impressed with the features.

I would like to schedule a 45-minute product demo to understand how it can help our team. Would tomorrow (October 31st) at 3:00 PM PST work for you?

Looking forward to learning more about your solution.

Best regards,
John Doe
Head of Operations
Tech Solutions Inc.""",
                "received_at": datetime.now(timezone.utc),
                "status": "unread",
                "is_read": False,
                "has_attachments": False,
                "labels": ["INBOX"],
                "created_at": datetime.now(timezone.utc)
            }
            
            await db.emails.insert_one(test_email)
            print(f"✅ Test email created")
            print(f"   From: {test_email['sender_name']}")
            print(f"   Subject: {test_email['subject']}")
            
            # Step 4: Manually trigger email processing
            print("\n⚙️  Step 4: Processing email (simulating email workflow)...")
            
            # Import the process_email_workflow function
            import sys
            sys.path.append('/app/backend')
            from server import process_email_workflow
            
            # Process the email
            print("   Processing email with calendar agent...")
            await process_email_workflow(email_id)
            
            # Wait a moment for processing
            await asyncio.sleep(2)
            
            # Step 5: Check email for draft and calendar details
            print("\n📋 Step 5: Checking email draft...")
            
            processed_email = await db.emails.find_one({"id": email_id})
            
            if not processed_email:
                print("❌ Email not found after processing")
                return
            
            print(f"✅ Email processed")
            print(f"   Status: {processed_email.get('status', 'unknown')}")
            
            # Check meeting detection
            if processed_email.get('meeting_detected'):
                print(f"\n✅ Meeting Detected:")
                print(f"   Confidence: {processed_email.get('meeting_confidence', 0):.2f}")
                print(f"   Title: {processed_email.get('meeting_title', 'N/A')}")
                print(f"   DateTime: {processed_email.get('meeting_datetime', 'N/A')}")
                print(f"   Location: {processed_email.get('meeting_location', 'N/A')}")
                print(f"   Duration: {processed_email.get('meeting_duration', 30)} minutes")
            else:
                print(f"\n⚠️  Meeting not detected")
                print(f"   This might affect the test results")
            
            # Check calendar action
            calendar_action = processed_email.get('calendar_action')
            if calendar_action:
                print(f"\n✅ Calendar Action Created: {calendar_action}")
                
                # Check if it's an event ID or meeting intent ID
                created_event = await db.calendar_events.find_one({
                    "external_event_id": calendar_action,
                    "user_id": user_id
                })
                
                if created_event:
                    print(f"\n✅ Calendar Event Created in Database:")
                    print(f"   Event ID: {created_event['id']}")
                    print(f"   Title: {created_event['title']}")
                    print(f"   Start: {created_event['start_time']}")
                    print(f"   End: {created_event['end_time']}")
                    print(f"   Location: {created_event.get('location', 'Not specified')}")
                    print(f"   Reminders: {len(created_event.get('reminders', []))} configured")
                else:
                    meeting_intent = await db.meeting_intents.find_one({
                        "id": calendar_action,
                        "user_id": user_id
                    })
                    
                    if meeting_intent:
                        print(f"\n✅ Meeting Intent Created:")
                        print(f"   Intent ID: {meeting_intent['id']}")
                        print(f"   Status: {meeting_intent.get('status', 'unknown')}")
                        print(f"   Confidence: {meeting_intent.get('confidence_score', 0):.2f}")
            else:
                print(f"\n⚠️  No calendar action created")
            
            # Check draft content
            draft = processed_email.get('draft', '')
            if draft:
                print(f"\n📝 Draft Generated:")
                print(f"   Length: {len(draft)} characters")
                print(f"\n--- DRAFT CONTENT ---")
                print(draft)
                print("--- END DRAFT ---\n")
                
                # Check if draft includes event details
                has_date = any(keyword in draft.lower() for keyword in ['october', 'november', '31', 'tomorrow', 'scheduled', 'meeting'])
                has_time = any(keyword in draft.lower() for keyword in ['3:00', '3 pm', '15:00', 'time'])
                has_confirmation = any(keyword in draft.lower() for keyword in ['confirmed', 'scheduled', 'calendar', 'event created', 'booked'])
                
                print("✅ Event Details Analysis:")
                print(f"   Contains date reference: {'✅ YES' if has_date else '❌ NO'}")
                print(f"   Contains time reference: {'✅ YES' if has_time else '❌ NO'}")
                print(f"   Contains confirmation: {'✅ YES' if has_confirmation else '❌ NO'}")
                
                if has_date and has_time and has_confirmation:
                    print(f"\n✅ SUCCESS: Draft includes calendar event details!")
                elif has_date or has_time:
                    print(f"\n⚠️  PARTIAL: Draft includes some event details but may be incomplete")
                else:
                    print(f"\n❌ ISSUE: Draft does NOT include event details")
                    print(f"   The meeting detection/calendar event info is not being communicated to user")
            else:
                print(f"\n❌ No draft generated")
            
            # Step 6: Summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            
            meeting_detected = processed_email.get('meeting_detected', False)
            calendar_created = bool(calendar_action)
            draft_has_details = bool(draft and has_date and has_time and has_confirmation if draft else False)
            
            print(f"\n📊 Test Results:")
            print(f"   ✅ Meeting Detection: {'PASSED' if meeting_detected else 'FAILED'}")
            print(f"   ✅ Calendar Event/Intent Created: {'PASSED' if calendar_created else 'FAILED'}")
            print(f"   {'✅' if draft_has_details else '❌'} Event Details in Draft: {'PASSED' if draft_has_details else 'FAILED'}")
            
            if meeting_detected and calendar_created and draft_has_details:
                print(f"\n✅ ALL TESTS PASSED!")
                print(f"   Event details are being communicated to users in email responses")
            else:
                print(f"\n⚠️  SOME TESTS FAILED")
                if not draft_has_details:
                    print(f"   Event details may not be fully communicated in email responses")
                    print(f"   Check the system prompt and intent generation logic")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_event_details_in_response())
