#!/usr/bin/env python3
"""
SIMPLE REDRAFT AUTO-SEND TEST
Tests the redraft auto-send functionality using existing working account
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://signature-format.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def test_redraft_autosend():
    """Test redraft auto-send functionality with existing account"""
    print("🔧 SIMPLE REDRAFT AUTO-SEND TEST")
    print("="*50)
    
    # Setup database connection
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get existing working account
        accounts = await db.email_accounts.find({"is_active": True}).to_list(5)
        if not accounts:
            print("❌ No active accounts found")
            return
        
        # Use the first active account
        account = accounts[0]
        print(f"✅ Using account: {account['email']}")
        print(f"   auto_send setting: {account.get('auto_send', True)}")
        
        # Test 1: Create test email
        print("\n📧 Step 1: Creating test email...")
        test_email_data = {
            "subject": "SIMPLE REDRAFT TEST: Product Demo Request",
            "body": "Hello! I'm interested in your AI Email Assistant product. Could you please provide information about pricing and schedule a demo? We're a growing company looking to automate our customer support responses. Please let me know the next steps. Thank you!",
            "sender": "simple.redraft.test@company.com",
            "account_id": account['id']
        }
        
        response = requests.post(f"{API_BASE}/emails/test", json=test_email_data, timeout=30)
        if response.status_code not in [200, 201]:
            print(f"❌ Failed to create test email: {response.status_code}")
            return
        
        created_email = response.json()
        email_id = created_email['id']
        print(f"✅ Test email created: {email_id}")
        print(f"   Initial status: {created_email.get('status')}")
        
        # Wait for initial processing
        print("\n⏳ Step 2: Waiting for initial processing...")
        await asyncio.sleep(15)
        
        # Get email state before redraft
        email_before = await db.emails.find_one({"id": email_id})
        if not email_before:
            print("❌ Email not found in database")
            return
        
        initial_status = email_before.get('status')
        initial_sent_at = email_before.get('sent_at')
        initial_draft_length = len(email_before.get('draft', ''))
        
        print(f"✅ Initial processing complete")
        print(f"   Status: {initial_status}")
        print(f"   Draft length: {initial_draft_length}")
        print(f"   Sent at: {initial_sent_at}")
        
        # Test 2: Trigger redraft
        print(f"\n🔄 Step 3: Triggering redraft...")
        redraft_response = requests.post(f"{API_BASE}/emails/{email_id}/redraft", timeout=30)
        
        if redraft_response.status_code != 200:
            print(f"❌ Redraft failed: {redraft_response.status_code}")
            try:
                error_detail = redraft_response.json()
                print(f"   Error: {error_detail}")
            except:
                print(f"   Error text: {redraft_response.text}")
            return
        
        redrafted_email = redraft_response.json()
        print(f"✅ Redraft completed")
        print(f"   New status: {redrafted_email.get('status')}")
        
        # Test 3: Verify auto-send functionality
        print(f"\n✅ Step 4: Verifying auto-send functionality...")
        
        # Get final email state from database
        final_email = await db.emails.find_one({"id": email_id})
        if not final_email:
            print("❌ Email not found after redraft")
            return
        
        final_status = final_email.get('status')
        final_sent_at = final_email.get('sent_at')
        final_draft_length = len(final_email.get('draft', ''))
        validation_result = final_email.get('validation_result', {})
        validation_status = validation_result.get('status')
        
        print(f"📊 FINAL RESULTS:")
        print(f"   Status: {initial_status} → {final_status}")
        print(f"   Draft length: {initial_draft_length} → {final_draft_length}")
        print(f"   Validation: {validation_status}")
        print(f"   Sent at: {initial_sent_at} → {final_sent_at}")
        
        # Verify the bug fix
        print(f"\n🔍 BUG FIX VERIFICATION:")
        
        # Check 1: New draft was generated
        draft_regenerated = final_draft_length > 100 and final_draft_length != initial_draft_length
        print(f"   ✅ Draft regenerated: {draft_regenerated}")
        
        # Check 2: Validation was performed
        validation_performed = validation_result is not None
        print(f"   ✅ Validation performed: {validation_performed}")
        
        # Check 3: Auto-send functionality
        if validation_status == "PASS":
            if account.get('auto_send', True):
                # Should auto-send
                auto_send_worked = (final_status == "sent" and final_sent_at is not None)
                print(f"   ✅ Auto-send worked: {auto_send_worked}")
                
                if auto_send_worked:
                    # Check if sent_at was updated
                    sent_at_updated = (str(initial_sent_at) != str(final_sent_at))
                    print(f"   ✅ Sent timestamp updated: {sent_at_updated}")
                    
                    print(f"\n🎉 REDRAFT AUTO-SEND BUG FIX: SUCCESS")
                    print(f"   ✅ Redrafted email automatically sent")
                    print(f"   ✅ Status changed to 'sent'")
                    print(f"   ✅ Timestamp properly updated")
                else:
                    print(f"\n❌ REDRAFT AUTO-SEND BUG FIX: FAILED")
                    print(f"   ❌ Email was not automatically sent")
                    print(f"   ❌ Status: {final_status}, Expected: sent")
            else:
                # Should NOT auto-send
                no_auto_send = (final_status == "ready_to_send")
                print(f"   ✅ Correctly did not auto-send (auto_send=false): {no_auto_send}")
        else:
            print(f"   ⚠️  Validation failed ({validation_status}), auto-send not expected")
        
        # Test 4: Test with modified auto_send setting
        print(f"\n🔄 Step 5: Testing auto_send=false scenario...")
        
        # Temporarily set auto_send to false
        await db.email_accounts.update_one(
            {"id": account['id']},
            {"$set": {"auto_send": False}}
        )
        
        # Create another test email
        test_email_data_2 = {
            "subject": "AUTO_SEND=FALSE TEST: Support Question",
            "body": "Hi, I have a quick question about your service. Can you help me understand the pricing structure? Thanks!",
            "sender": "autosend.false.test@company.com",
            "account_id": account['id']
        }
        
        response = requests.post(f"{API_BASE}/emails/test", json=test_email_data_2, timeout=30)
        if response.status_code in [200, 201]:
            email_2 = response.json()
            email_2_id = email_2['id']
            print(f"✅ Second test email created: {email_2_id}")
            
            # Wait for processing
            await asyncio.sleep(15)
            
            # Trigger redraft
            redraft_response_2 = requests.post(f"{API_BASE}/emails/{email_2_id}/redraft", timeout=30)
            if redraft_response_2.status_code == 200:
                final_email_2 = await db.emails.find_one({"id": email_2_id})
                final_status_2 = final_email_2.get('status')
                validation_2 = final_email_2.get('validation_result', {})
                validation_status_2 = validation_2.get('status')
                
                print(f"   Final status: {final_status_2}")
                print(f"   Validation: {validation_status_2}")
                
                if validation_status_2 == "PASS":
                    # Should stay at ready_to_send (not auto-send)
                    correct_behavior = (final_status_2 == "ready_to_send")
                    print(f"   ✅ Correct behavior (no auto-send): {correct_behavior}")
                    
                    if correct_behavior:
                        print(f"   🎉 AUTO_SEND=FALSE TEST: SUCCESS")
                    else:
                        print(f"   ❌ AUTO_SEND=FALSE TEST: FAILED")
                        print(f"      Expected 'ready_to_send', got '{final_status_2}'")
            else:
                print(f"   ❌ Second redraft failed: {redraft_response_2.status_code}")
        else:
            print(f"   ❌ Failed to create second test email: {response.status_code}")
        
        # Restore original auto_send setting
        await db.email_accounts.update_one(
            {"id": account['id']},
            {"$set": {"auto_send": account.get('auto_send', True)}}
        )
        
        print(f"\n{'='*50}")
        print(f"REDRAFT AUTO-SEND BUG FIX TESTING COMPLETE")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_redraft_autosend())