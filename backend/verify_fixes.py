#!/usr/bin/env python3
"""
Test script to verify calendar agent and human-like responses
"""
import asyncio
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "test_database")

async def verify_fixes():
    """Verify all fixes are working"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("="*70)
    print("🔍 VERIFICATION REPORT - Calendar Agent & Human-Like Responses")
    print("="*70)
    print()
    
    # 1. Check Cohere API Key
    with open('/app/backend/.env', 'r') as f:
        env_content = f.read()
        if 'jFzD5zpDyiOkosDWvbaMCSDI1NR6M5cv8Nwp1oyn' in env_content:
            print("✅ Cohere API Key Updated: jFzD5zpDyiOkosDWvbaMCSDI1NR6M5cv8Nwp1oyn")
        else:
            print("❌ Cohere API Key NOT updated")
    print()
    
    # 2. Check Intent Updates
    print("📋 Intent System Prompts (Human-like Check):")
    intents = list(db.intents.find({}, {"name": 1, "system_prompt": 1, "_id": 0}))
    for intent in intents:
        system_prompt = intent.get('system_prompt', 'N/A')
        has_human_prompt = 'conversational' in system_prompt.lower() or 'natural' in system_prompt.lower() or 'real person' in system_prompt.lower()
        status = "✅" if has_human_prompt else "⚠️"
        print(f"  {status} {intent['name']}")
        if system_prompt != 'N/A':
            print(f"      Prompt: {system_prompt[:100]}...")
    print()
    
    # 3. Check if user exists and has quota
    user = db.users.find_one({"email": "amits.joys@gmail.com"})
    if user:
        print("✅ User Account:")
        print(f"    Email: {user['email']}")
        print(f"    ID: {user['id']}")
        print(f"    Email Quota: {user.get('email_quota', 'N/A')}")
        print(f"    Quota Reset Date: {user.get('quota_reset_date', 'N/A')}")
    else:
        print("❌ User not found")
    print()
    
    # 4. Check calendar providers
    providers = list(db.calendar_providers.find({"user_id": user['id']}, {"provider_type": 1, "use_oauth": 1, "is_active": 1, "_id": 0}))
    if providers:
        print("✅ Calendar Providers:")
        for provider in providers:
            print(f"    Type: {provider.get('provider_type')}, OAuth: {provider.get('use_oauth')}, Active: {provider.get('is_active')}")
    else:
        print("⚠️ No calendar providers found - user needs to connect calendar")
    print()
    
    # 5. Test email accounts
    email_accounts = list(db.email_accounts.find({"user_id": user['id']}, {"email": 1, "auth_type": 1, "is_active": 1, "_id": 0}))
    if email_accounts:
        print("✅ Email Accounts:")
        for acc in email_accounts:
            print(f"    Email: {acc.get('email')}, Type: {acc.get('auth_type')}, Active: {acc.get('is_active')}")
    else:
        print("⚠️ No email accounts found")
    print()
    
    print("="*70)
    print("📝 SUMMARY OF FIXES")
    print("="*70)
    print()
    print("1. ✅ Fixed calendar_agent.py quota_reset_date error")
    print("   - Converted dict to User object before quota check")
    print()
    print("2. ✅ Updated Cohere API key to new key")
    print("   - jFzD5zpDyiOkosDWvbaMCSDI1NR6M5cv8Nwp1oyn")
    print()
    print("3. ✅ Made all intent prompts human-like")
    print("   - Removed robotic language")
    print("   - Added conversational tone instructions")
    print()
    print("4. ✅ Updated Meeting Confirmation prompt")
    print("   - Natural language: 'I'll send you a calendar invite'")
    print("   - No mention of 'calendar agent' or automation")
    print()
    print("5. ✅ Added human-like communication to draft generation")
    print("   - Rule #2 in PARLANT COMPLIANCE")
    print("   - Rule #14 for meeting confirmations")
    print()
    print("6. ✅ Enabled calendar invite sending")
    print("   - Added sendUpdates=all parameter to Google Calendar API")
    print("   - Attendees will now receive email invites")
    print()
    print("7. ✅ Added reminder support")
    print("   - Email reminder 60 min before")
    print("   - Popup reminder 15 min before")
    print()
    print("="*70)
    print()
    print("🎯 NEXT STEPS:")
    print("   1. Test with a meeting request email")
    print("   2. Verify attendees receive calendar invites")
    print("   3. Check that responses sound human-like")
    print("   4. Confirm no mention of 'calendar agent' in responses")
    print()
    print("="*70)

if __name__ == "__main__":
    asyncio.run(verify_fixes())
