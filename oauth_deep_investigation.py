#!/usr/bin/env python3
"""
Deep OAuth Investigation - Find all OAuth accounts and tokens
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

async def deep_oauth_investigation():
    """Deep investigation of all OAuth accounts and tokens"""
    print("🔍 DEEP OAUTH INVESTIGATION")
    print("="*80)
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # 1. Find all email accounts
        print("\n📧 ALL EMAIL ACCOUNTS:")
        all_accounts = await db.email_accounts.find().to_list(100)
        
        for i, account in enumerate(all_accounts, 1):
            print(f"\n{i}. Account ID: {account['id']}")
            print(f"   Email: {account['email']}")
            print(f"   Name: {account.get('name', 'N/A')}")
            print(f"   Provider: {account.get('provider', 'N/A')}")
            print(f"   Auth Type: {account.get('auth_type', 'N/A')}")
            print(f"   Use OAuth: {account.get('use_oauth', False)}")
            print(f"   OAuth Email: {account.get('oauth_email', 'N/A')}")
            print(f"   OAuth Token ID: {account.get('oauth_token_id', 'N/A')}")
            print(f"   Active: {account.get('is_active', False)}")
            print(f"   Last Polled: {account.get('last_polled', 'Never')}")
            print(f"   Last OAuth Sync: {account.get('last_oauth_sync', 'Never')}")
            print(f"   User ID: {account.get('user_id', 'N/A')}")
        
        # 2. Find all OAuth tokens
        print(f"\n🔐 ALL OAUTH TOKENS:")
        all_tokens = await db.oauth_tokens.find().to_list(100)
        
        for i, token in enumerate(all_tokens, 1):
            print(f"\n{i}. Token ID: {token['id']}")
            print(f"   Provider: {token.get('provider', 'N/A')}")
            print(f"   Email: {token.get('email', 'N/A')}")
            print(f"   User ID: {token.get('user_id', 'N/A')}")
            print(f"   Scope: {token.get('scope', 'N/A')}")
            print(f"   Created: {token.get('created_at', 'N/A')}")
            print(f"   Expires: {token.get('expires_at', 'N/A')}")
            print(f"   Has Access Token: {bool(token.get('access_token'))}")
            print(f"   Has Refresh Token: {bool(token.get('refresh_token'))}")
        
        # 3. Find OAuth accounts specifically
        print(f"\n🔗 OAUTH ACCOUNTS ONLY:")
        oauth_accounts = await db.email_accounts.find({"auth_type": "oauth"}).to_list(100)
        
        for i, account in enumerate(oauth_accounts, 1):
            print(f"\n{i}. OAuth Account:")
            print(f"   ID: {account['id']}")
            print(f"   Email: {account['email']}")
            print(f"   OAuth Email: {account.get('oauth_email', 'N/A')}")
            print(f"   Token ID: {account.get('oauth_token_id', 'N/A')}")
            print(f"   Active: {account.get('is_active', False)}")
            
            # Find matching token
            token_id = account.get('oauth_token_id')
            if token_id:
                token = await db.oauth_tokens.find_one({"id": token_id})
                if token:
                    print(f"   Token Found: ✅")
                    print(f"   Token Email: {token.get('email', 'N/A')}")
                    print(f"   Token Provider: {token.get('provider', 'N/A')}")
                    
                    # Check expiration
                    expires_at = token.get('expires_at')
                    if expires_at:
                        if isinstance(expires_at, str):
                            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo if expires_at.tzinfo else None)
                        expired = expires_at < now
                        print(f"   Token Expired: {'❌ YES' if expired else '✅ NO'}")
                        print(f"   Expires At: {expires_at}")
                    else:
                        print(f"   Token Expired: ⚠️ NO EXPIRATION")
                else:
                    print(f"   Token Found: ❌ NOT FOUND")
            else:
                print(f"   Token ID: ❌ MISSING")
        
        # 4. Search for accounts related to amits.joys
        print(f"\n🔍 ACCOUNTS RELATED TO 'amits.joys':")
        related_accounts = await db.email_accounts.find({
            "$or": [
                {"email": {"$regex": "amits.joys", "$options": "i"}},
                {"oauth_email": {"$regex": "amits.joys", "$options": "i"}},
                {"name": {"$regex": "amits.joys", "$options": "i"}}
            ]
        }).to_list(100)
        
        for account in related_accounts:
            print(f"\n   Account: {account['email']}")
            print(f"   OAuth Email: {account.get('oauth_email', 'N/A')}")
            print(f"   Auth Type: {account.get('auth_type', 'N/A')}")
            print(f"   Active: {account.get('is_active', False)}")
        
        # 5. Search for tokens related to amits.joys
        print(f"\n🔍 TOKENS RELATED TO 'amits.joys':")
        related_tokens = await db.oauth_tokens.find({
            "$or": [
                {"email": {"$regex": "amits.joys", "$options": "i"}},
                {"user_email": {"$regex": "amits.joys", "$options": "i"}}
            ]
        }).to_list(100)
        
        for token in related_tokens:
            print(f"\n   Token Email: {token.get('email', 'N/A')}")
            print(f"   Provider: {token.get('provider', 'N/A')}")
            print(f"   User ID: {token.get('user_id', 'N/A')}")
            print(f"   Created: {token.get('created_at', 'N/A')}")
        
        # 6. Check users collection
        print(f"\n👤 USERS:")
        users = await db.users.find().to_list(100)
        
        for user in users:
            print(f"\n   User ID: {user['id']}")
            print(f"   Email: {user['email']}")
            print(f"   Name: {user.get('full_name', 'N/A')}")
            print(f"   Active: {user.get('is_active', False)}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Investigation failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(deep_oauth_investigation())