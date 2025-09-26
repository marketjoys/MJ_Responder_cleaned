#!/usr/bin/env python3
"""
Focused Follow-up Cancellation Issue Analysis
Identifies the specific problem with follow-up cancellation logic
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def analyze_followup_issue():
    """Analyze the specific issue with follow-up cancellation"""
    print("🔍 Analyzing Follow-up Cancellation Issue...")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get an active email account
        account = await db.email_accounts.find_one({"is_active": True})
        if not account:
            print("❌ No active email accounts found")
            return
        
        print(f"✅ Using account: {account['email']}")
        
        # Create a realistic test scenario
        test_thread_id = f"test-thread-{uuid.uuid4()}"
        customer_email = "customer@example.com"
        business_email = account['email']
        
        # 1. Customer sends initial inquiry
        original_email = {
            "id": str(uuid.uuid4()),
            "account_id": account['id'],
            "message_id": f"<original-{uuid.uuid4()}@example.com>",
            "thread_id": test_thread_id,
            "subject": "Pricing Inquiry",
            "sender": customer_email,  # Customer is the sender
            "recipient": business_email,  # Business receives the inquiry
            "body": "I need pricing information for your services.",
            "received_at": datetime.utcnow() - timedelta(hours=2),
            "status": "sent",
            "created_at": datetime.utcnow() - timedelta(hours=2)
        }
        
        await db.emails.insert_one(original_email)
        print(f"✅ Created original email from customer: {customer_email}")
        
        # 2. Business sends automated response
        business_response = {
            "id": str(uuid.uuid4()),
            "account_id": account['id'],
            "message_id": f"<business-response-{uuid.uuid4()}@{business_email.split('@')[1]}>",
            "thread_id": test_thread_id,
            "subject": "Re: Pricing Inquiry",
            "sender": business_email,  # Business is the sender
            "recipient": customer_email,  # Customer receives the response
            "body": "Thank you for your inquiry. Here's our pricing information...",
            "received_at": datetime.utcnow() - timedelta(hours=1),
            "status": "sent",
            "created_at": datetime.utcnow() - timedelta(hours=1)
        }
        
        await db.emails.insert_one(business_response)
        print(f"✅ Created business response to customer")
        
        # 3. Create follow-up scheduled for the customer (who hasn't replied yet)
        follow_up = {
            "id": str(uuid.uuid4()),
            "original_email_id": original_email['id'],
            "account_id": account['id'],
            "user_id": "test-user-id",
            "thread_id": test_thread_id,
            "recipient_email": customer_email,  # Follow-up will be sent TO the customer
            "subject": "Re: Pricing Inquiry - Follow-up",
            "status": "pending",
            "follow_up_number": 1,
            "scheduled_time": datetime.utcnow() + timedelta(hours=24),
            "draft_content": "Following up on your pricing inquiry...",
            "response_received": False,
            "created_at": datetime.utcnow() - timedelta(minutes=30),
            "updated_at": datetime.utcnow() - timedelta(minutes=30)
        }
        
        await db.follow_up_emails.insert_one(follow_up)
        print(f"✅ Created pending follow-up for customer: {customer_email}")
        
        # 4. Now customer replies (this should cancel the follow-up)
        customer_reply = {
            "id": str(uuid.uuid4()),
            "account_id": account['id'],
            "message_id": f"<customer-reply-{uuid.uuid4()}@example.com>",
            "thread_id": test_thread_id,
            "subject": "Re: Pricing Inquiry",
            "sender": customer_email,  # Customer is replying
            "recipient": business_email,  # Business receives the reply
            "body": "Thanks for the pricing info. I'm interested in the premium package.",
            "received_at": datetime.utcnow(),
            "in_reply_to": business_response['message_id'],
            "references": f"{original_email['message_id']} {business_response['message_id']}",
            "status": "new",
            "created_at": datetime.utcnow()
        }
        
        await db.emails.insert_one(customer_reply)
        print(f"✅ Created customer reply: {customer_email}")
        
        # 5. Analyze the current response detection logic
        print("\n🔍 Analyzing Response Detection Logic...")
        
        # Get all emails in thread
        thread_emails = await db.emails.find({
            "thread_id": test_thread_id
        }).sort("received_at", 1).to_list(100)
        
        print(f"Thread has {len(thread_emails)} emails:")
        for i, email in enumerate(thread_emails):
            print(f"  {i+1}. {email['sender']} -> {email['recipient']} at {email['received_at']}")
        
        # Current logic analysis
        print("\n🔍 Current Logic Analysis:")
        original_email_in_thread = thread_emails[0]
        original_sender = original_email_in_thread.get("sender", "")
        print(f"Original sender: {original_sender}")
        
        # Check what current logic would detect as responses
        responses = [
            email for email in thread_emails[1:]
            if (email.get("sender", "") != original_sender and 
                email.get("received_at", datetime.min) > original_email_in_thread.get("received_at", datetime.min))
        ]
        
        print(f"Current logic detects {len(responses)} responses:")
        for response in responses:
            print(f"  - {response['sender']} at {response['received_at']}")
        
        # The PROBLEM: Current logic looks for emails from different senders than original
        # But in this case:
        # - Original: customer@example.com -> business
        # - Business response: business -> customer (different sender, so detected as "response")
        # - Customer reply: customer@example.com -> business (same as original sender, so NOT detected)
        
        print("\n❌ PROBLEM IDENTIFIED:")
        print("Current logic incorrectly identifies business responses as 'responses' that should cancel follow-ups")
        print("But customer replies (which should actually cancel follow-ups) are not detected")
        print("because they have the same sender as the original email")
        
        # 6. Test the correct logic
        print("\n✅ CORRECT LOGIC:")
        print("Follow-ups should be cancelled when the RECIPIENT of the follow-up sends a reply")
        
        # Get pending follow-ups for this thread
        pending_follow_ups = await db.follow_up_emails.find({
            "thread_id": test_thread_id,
            "status": "pending"
        }).to_list(100)
        
        print(f"Found {len(pending_follow_ups)} pending follow-ups")
        
        for follow_up_item in pending_follow_ups:
            recipient_email = follow_up_item.get('recipient_email', '').lower()
            print(f"Follow-up recipient: {recipient_email}")
            
            # Check for emails FROM the follow-up recipient AFTER the follow-up was created
            follow_up_created = follow_up_item.get('created_at', datetime.utcnow())
            
            replies_from_recipient = [
                email for email in thread_emails
                if (email.get('sender', '').lower() == recipient_email and
                    email.get('received_at', datetime.min) > follow_up_created)
            ]
            
            print(f"Found {len(replies_from_recipient)} replies from follow-up recipient after follow-up was created")
            
            if replies_from_recipient:
                print("✅ This follow-up SHOULD be cancelled")
                for reply in replies_from_recipient:
                    print(f"  - Reply from {reply['sender']} at {reply['received_at']}")
            else:
                print("❌ No replies found - follow-up should remain pending")
        
        # 7. Test process_email_async logic
        print("\n🔍 Testing process_email_async logic...")
        
        # Import the function
        from server import process_email_async
        
        # Process the customer reply
        print(f"Processing customer reply email: {customer_reply['id']}")
        await process_email_async(customer_reply['id'])
        
        # Check if follow-up was cancelled
        updated_follow_up = await db.follow_up_emails.find_one({"id": follow_up['id']})
        
        if updated_follow_up:
            status = updated_follow_up.get('status')
            print(f"Follow-up status after processing: {status}")
            
            if status == 'cancelled':
                print("✅ SUCCESS: Follow-up was correctly cancelled")
            else:
                print("❌ FAILURE: Follow-up was not cancelled")
                
                # Analyze why it wasn't cancelled
                print("\nAnalyzing why cancellation failed...")
                
                # Check the logic in process_email_async
                original_in_process = thread_emails[0]
                original_sender_in_process = original_in_process.get("sender", "")
                current_sender = customer_reply['sender']
                
                print(f"Original sender: {original_sender_in_process}")
                print(f"Current sender: {current_sender}")
                print(f"Are they different? {current_sender != original_sender_in_process}")
                
                # The issue is here - customer reply has SAME sender as original
                # So the condition (current_sender != original_sender) is FALSE
                # Therefore no cancellation happens
                
                print("\n❌ ROOT CAUSE IDENTIFIED:")
                print("process_email_async checks if current_sender != original_sender")
                print("But in customer inquiry -> business response -> customer reply scenario:")
                print("- Original sender: customer")
                print("- Current sender: customer (reply)")
                print("- They are the SAME, so no cancellation occurs")
                print("\nThe logic should check if the sender is the RECIPIENT of pending follow-ups")
        
        # Cleanup
        await db.emails.delete_many({"thread_id": test_thread_id})
        await db.follow_up_emails.delete_many({"thread_id": test_thread_id})
        
        print("\n🔧 SOLUTION:")
        print("The response detection logic needs to be fixed to:")
        print("1. Check if the email sender matches any pending follow-up recipients")
        print("2. Not just check if sender is different from original thread starter")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(analyze_followup_issue())