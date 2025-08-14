#!/usr/bin/env python3
"""
FOCUSED AUTO-SEND TEST
Quick test of the auto-send functionality after fixing SMTP credentials
"""
import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-detect-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def test_auto_send():
    print("🧪 Testing Auto-Send Functionality...")
    
    # Get account ID
    accounts_response = requests.get(f"{API_BASE}/email-accounts", timeout=10)
    if accounts_response.status_code != 200:
        print("❌ Failed to get accounts")
        return False
    
    accounts = accounts_response.json()
    if not accounts:
        print("❌ No accounts found")
        return False
    
    account_id = accounts[0]['id']
    print(f"✅ Using account: {accounts[0]['email']}")
    
    # Test email data
    test_data = {
        "subject": "FOCUSED AUTO-SEND TEST: Quick Response Needed",
        "body": "Hello! I need immediate information about your AI Email Assistant pricing. Can you please send me a quote right away? This is urgent and I need to make a decision today. Thank you!",
        "sender": "focused.test@urgent.com",
        "account_id": account_id
    }
    
    print("📧 Creating test email...")
    response = requests.post(f"{API_BASE}/emails/test", json=test_data, timeout=30)
    
    if response.status_code not in [200, 201]:
        print(f"❌ Email creation failed: {response.status_code}")
        return False
    
    email = response.json()
    email_id = email.get('id')
    initial_status = email.get('status')
    
    print(f"✅ Email created - ID: {email_id}")
    print(f"📊 Initial status: {initial_status}")
    print(f"🎯 Intents found: {len(email.get('intents', []))}")
    print(f"📝 Draft length: {len(email.get('draft', ''))}")
    
    # Check if auto-sent immediately
    if initial_status == 'sent':
        print("🚀 Email was auto-sent immediately!")
        return True
    
    # Wait and check again
    print("⏳ Waiting 5 seconds for auto-send...")
    time.sleep(5)
    
    check_response = requests.get(f"{API_BASE}/emails/{email_id}", timeout=10)
    if check_response.status_code != 200:
        print("❌ Failed to check email status")
        return False
    
    updated_email = check_response.json()
    final_status = updated_email.get('status')
    sent_at = updated_email.get('sent_at')
    error = updated_email.get('error')
    
    print(f"📊 Final status: {final_status}")
    if sent_at:
        print(f"📅 Sent at: {sent_at}")
    if error:
        print(f"❌ Error: {error}")
    
    # Test manual send if auto-send didn't work
    if final_status == 'ready_to_send':
        print("🔧 Attempting manual send...")
        send_request = {"email_id": email_id, "manual_override": False}
        send_response = requests.post(f"{API_BASE}/emails/{email_id}/send", 
                                    json=send_request, timeout=15)
        
        if send_response.status_code == 200:
            print("✅ Manual send successful!")
            return True
        else:
            print(f"❌ Manual send failed: {send_response.status_code}")
            if send_response.text:
                print(f"   Error: {send_response.text}")
    
    return final_status == 'sent'

if __name__ == "__main__":
    success = test_auto_send()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Auto-send test {'passed' if success else 'failed'}")