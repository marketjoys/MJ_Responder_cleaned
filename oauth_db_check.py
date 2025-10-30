#!/usr/bin/env python3
"""
Database Check for OAuth Data
"""
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def check_oauth_data():
    """Check OAuth data in database"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        print("🔍 Checking OAuth Data in Database...")
        
        # Check users
        users = await db.users.find().to_list(100)
        print(f"\n👥 Users ({len(users)}):")
        for user in users:
            print(f"   • {user.get('email')} (ID: {user.get('id')[:8]}...)")
        
        # Check oauth_tokens
        oauth_tokens = await db.oauth_tokens.find().to_list(100)
        print(f"\n🔐 OAuth Tokens ({len(oauth_tokens)}):")
        for token in oauth_tokens:
            print(f"   • User: {token.get('user_id', 'N/A')[:8]}..., Provider: {token.get('provider')}, Email: {token.get('email')}")
        
        # Check email_accounts
        email_accounts = await db.email_accounts.find().to_list(100)
        print(f"\n📧 Email Accounts ({len(email_accounts)}):")
        for account in email_accounts:
            print(f"   • {account.get('email')} (Auth: {account.get('auth_type')}, OAuth: {account.get('use_oauth')}, User: {account.get('user_id', 'N/A')[:8]}...)")
        
        # Check calendar_providers
        calendar_providers = await db.calendar_providers.find().to_list(100)
        print(f"\n📅 Calendar Providers ({len(calendar_providers)}):")
        for provider in calendar_providers:
            print(f"   • Type: {provider.get('provider_type')}, OAuth: {provider.get('use_oauth')}, Email: {provider.get('oauth_email')}, User: {provider.get('user_id', 'N/A')[:8]}...")
        
        # Check calendar_events
        calendar_events = await db.calendar_events.find().to_list(100)
        print(f"\n🗓️ Calendar Events ({len(calendar_events)}):")
        for event in calendar_events[:5]:  # Show first 5
            print(f"   • {event.get('title')} (User: {event.get('user_id', 'N/A')[:8]}...)")
        
        # Check meeting_intents
        meeting_intents = await db.meeting_intents.find().to_list(100)
        print(f"\n🤝 Meeting Intents ({len(meeting_intents)}):")
        for intent in meeting_intents[:5]:  # Show first 5
            print(f"   • Status: {intent.get('status')}, User: {intent.get('user_id', 'N/A')[:8]}...")
        
        # Find the OAuth user specifically
        oauth_user = None
        for user in users:
            user_id = user.get('id')
            user_tokens = [t for t in oauth_tokens if t.get('user_id') == user_id]
            user_accounts = [a for a in email_accounts if a.get('user_id') == user_id and a.get('auth_type') == 'oauth']
            user_providers = [p for p in calendar_providers if p.get('user_id') == user_id and p.get('use_oauth')]
            
            if user_tokens or user_accounts or user_providers:
                oauth_user = user
                print(f"\n🎯 OAuth User Found: {user.get('email')}")
                print(f"   • User ID: {user_id}")
                print(f"   • OAuth Tokens: {len(user_tokens)}")
                print(f"   • OAuth Email Accounts: {len(user_accounts)}")
                print(f"   • OAuth Calendar Providers: {len(user_providers)}")
                break
        
        if not oauth_user:
            print("\n⚠️ No OAuth user found with tokens, accounts, or providers")
        
        return oauth_user
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_oauth_data())