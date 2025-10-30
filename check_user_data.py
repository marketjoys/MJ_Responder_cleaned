import pymongo
from bson import ObjectId
import json
from datetime import datetime

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

print("=" * 80)
print("DATABASE STATE FOR amits.joys@gmail.com")
print("=" * 80)

# Find user
user = db.users.find_one({"email": "amits.joys@gmail.com"})
if user:
    user_id = str(user["_id"])
    print(f"\n✅ User Found: {user['email']}")
    print(f"   User ID: {user_id}")
    print(f"   Name: {user.get('full_name', 'N/A')}")
else:
    print("❌ User not found!")
    exit(1)

# Check OAuth tokens
print("\n" + "=" * 80)
print("OAUTH TOKENS")
print("=" * 80)
oauth_tokens = list(db.oauth_tokens.find({"user_id": user_id}))
if oauth_tokens:
    for idx, token in enumerate(oauth_tokens, 1):
        print(f"\n{idx}. Token ID: {token['_id']}")
        print(f"   OAuth Email: {token.get('oauth_email', 'N/A')}")
        print(f"   Provider: {token.get('provider', 'N/A')}")
        print(f"   Scopes: {token.get('scopes', [])}")
        print(f"   Has Access Token: {'✅' if token.get('access_token') else '❌'}")
        print(f"   Has Refresh Token: {'✅' if token.get('refresh_token') else '❌'}")
        expires = token.get('expires_at')
        if expires:
            print(f"   Expires: {expires}")
else:
    print("❌ No OAuth tokens found!")

# Check email accounts
print("\n" + "=" * 80)
print("EMAIL ACCOUNTS")
print("=" * 80)
email_accounts = list(db.email_accounts.find({"user_id": user_id}))
if email_accounts:
    for idx, account in enumerate(email_accounts, 1):
        print(f"\n{idx}. Account ID: {account['_id']}")
        print(f"   Email: {account.get('email', 'N/A')}")
        print(f"   Auth Type: {account.get('auth_type', 'N/A')}")
        print(f"   OAuth Email: {account.get('oauth_email', 'N/A')}")
        print(f"   Provider: {account.get('provider', 'N/A')}")
        print(f"   OAuth Token ID: {account.get('oauth_token_id', 'N/A')}")
        print(f"   Active: {'✅' if account.get('is_active') else '❌'}")
        print(f"   Last Sync: {account.get('last_oauth_sync', 'N/A')}")
else:
    print("❌ No email accounts found!")

# Check calendar providers
print("\n" + "=" * 80)
print("CALENDAR PROVIDERS")
print("=" * 80)
calendar_providers = list(db.calendar_providers.find({"user_id": user_id}))
if calendar_providers:
    for idx, provider in enumerate(calendar_providers, 1):
        print(f"\n{idx}. Provider ID: {provider['_id']}")
        print(f"   Type: {provider.get('provider_type', 'N/A')}")
        print(f"   OAuth Email: {provider.get('oauth_email', 'N/A')}")
        print(f"   Use OAuth: {'✅' if provider.get('use_oauth') else '❌'}")
        print(f"   Active: {'✅' if provider.get('is_active') else '❌'}")
else:
    print("❌ No calendar providers found!")

# Check intents
print("\n" + "=" * 80)
print("INTENTS")
print("=" * 80)
intents = list(db.intents.find({"user_id": user_id}))
print(f"Total Intents: {len(intents)}")
for intent in intents:
    print(f"  - {intent.get('name', 'N/A')} (has_embedding: {'✅' if intent.get('embedding') else '❌'})")

# Check knowledge base
print("\n" + "=" * 80)
print("KNOWLEDGE BASE")
print("=" * 80)
kb_entries = list(db.knowledge_base.find({"user_id": user_id}))
print(f"Total KB Entries: {len(kb_entries)}")
for kb in kb_entries:
    print(f"  - {kb.get('title', 'N/A')} (has_embedding: {'✅' if kb.get('embedding') else '❌'})")

# Check emails
print("\n" + "=" * 80)
print("EMAILS (Recent 5)")
print("=" * 80)
emails = list(db.emails.find({"user_id": user_id}).sort("received_at", -1).limit(5))
print(f"Total Emails: {db.emails.count_documents({'user_id': user_id})}")
for idx, email in enumerate(emails, 1):
    print(f"\n{idx}. Email ID: {email['_id']}")
    print(f"   From: {email.get('sender_email', 'N/A')}")
    print(f"   Subject: {email.get('subject', 'N/A')[:50]}")
    print(f"   Status: {email.get('status', 'N/A')}")
    print(f"   Intent: {email.get('classified_intent', 'N/A')}")
    print(f"   Draft Length: {len(email.get('generated_draft', ''))}")

print("\n" + "=" * 80)
