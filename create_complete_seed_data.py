import pymongo
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
import json

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

print("=" * 80)
print("CREATING COMPLETE SEED DATA FOR amits.joys@gmail.com")
print("=" * 80)

# 1. Create/Update User
user_id = str(uuid.uuid4())
hashed_password = pwd_context.hash("ij@123")

user_data = {
    "_id": user_id,
    "email": "amits.joys@gmail.com",
    "full_name": "Amit S Joys",
    "hashed_password": hashed_password,
    "is_active": True,
    "created_at": datetime.utcnow(),
    "quota_reset_date": datetime.utcnow() + timedelta(days=30)
}

# Check if user exists
existing_user = db.users.find_one({"email": "amits.joys@gmail.com"})
if existing_user:
    user_id = str(existing_user["_id"])
    db.users.update_one(
        {"email": "amits.joys@gmail.com"},
        {"$set": {"hashed_password": hashed_password, "quota_reset_date": datetime.utcnow() + timedelta(days=30)}}
    )
    print(f"✅ User updated: {user_id}")
else:
    db.users.insert_one(user_data)
    print(f"✅ User created: {user_id}")

# 2. Create OAuth Token
oauth_token_id = str(uuid.uuid4())
oauth_token_data = {
    "_id": oauth_token_id,
    "user_id": user_id,
    "oauth_email": "amits.joys@gmail.com",
    "provider": "google",
    "access_token": "ya29.a0AfH6SMBxxx_sample_access_token_xxx",
    "refresh_token": "1//0xxx_sample_refresh_token_xxx",
    "token_type": "Bearer",
    "expires_at": datetime.utcnow() + timedelta(days=60),
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly", 
               "https://www.googleapis.com/auth/gmail.send",
               "https://www.googleapis.com/auth/calendar"],
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

# Check if token exists
existing_token = db.oauth_tokens.find_one({"user_id": user_id, "oauth_email": "amits.joys@gmail.com"})
if existing_token:
    oauth_token_id = str(existing_token["_id"])
    print(f"✅ OAuth token exists: {oauth_token_id}")
else:
    db.oauth_tokens.insert_one(oauth_token_data)
    print(f"✅ OAuth token created: {oauth_token_id}")

# 3. Create Email Account
email_account_id = str(uuid.uuid4())
email_account_data = {
    "_id": email_account_id,
    "user_id": user_id,
    "email": "amits.joys@gmail.com",
    "oauth_email": "amits.joys@gmail.com",
    "auth_type": "oauth",
    "provider": "google",
    "oauth_token_id": oauth_token_id,
    "is_active": True,
    "auto_send": True,
    "enable_follow_ups": True,
    "last_oauth_sync": datetime.utcnow(),
    "created_at": datetime.utcnow(),
    "signature": "Best regards,\nAmit S Joys\nEmail Assistant",
    "persona": "Professional and helpful business assistant"
}

existing_account = db.email_accounts.find_one({"user_id": user_id, "email": "amits.joys@gmail.com"})
if existing_account:
    email_account_id = str(existing_account["_id"])
    db.email_accounts.update_one(
        {"_id": email_account_id},
        {"$set": {"oauth_token_id": oauth_token_id, "is_active": True, "auto_send": True}}
    )
    print(f"✅ Email account updated: {email_account_id}")
else:
    db.email_accounts.insert_one(email_account_data)
    print(f"✅ Email account created: {email_account_id}")

# 4. Create Calendar Provider
calendar_provider_id = str(uuid.uuid4())
calendar_provider_data = {
    "_id": calendar_provider_id,
    "user_id": user_id,
    "provider_type": "google",
    "oauth_email": "amits.joys@gmail.com",
    "use_oauth": True,
    "is_active": True,
    "created_at": datetime.utcnow()
}

existing_provider = db.calendar_providers.find_one({"user_id": user_id, "oauth_email": "amits.joys@gmail.com"})
if existing_provider:
    calendar_provider_id = str(existing_provider["_id"])
    print(f"✅ Calendar provider exists: {calendar_provider_id}")
else:
    db.calendar_providers.insert_one(calendar_provider_data)
    print(f"✅ Calendar provider created: {calendar_provider_id}")

# 5. Create Intents with proper embeddings (dummy embeddings for now)
dummy_embedding = [0.1] * 1536  # Standard OpenAI embedding dimension

intents_data = [
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": "Sales Inquiry",
        "description": "Customer asking about products, pricing, or purchasing",
        "prompt": "You are responding to a sales inquiry. Provide helpful product information, pricing details, and encourage them to make a purchase. Be enthusiastic and persuasive while remaining professional.",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": "Support Request",
        "description": "Customer needs help with an existing product or service",
        "prompt": "You are responding to a support request. Be empathetic, provide clear troubleshooting steps, and offer to escalate if needed. Maintain a helpful and patient tone.",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": "Meeting Request",
        "description": "Someone wants to schedule a meeting or call",
        "prompt": "You are responding to a meeting request. Acknowledge the request, provide available time slots, and use a professional but friendly tone. Confirm the meeting purpose and any preparation needed.",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": "General Inquiry",
        "description": "General questions or information requests",
        "prompt": "You are responding to a general inquiry. Be informative, friendly, and direct. Provide relevant information and offer additional assistance if needed.",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": "Partnership Opportunity",
        "description": "Business partnership or collaboration proposals",
        "prompt": "You are responding to a partnership opportunity. Show interest and professionalism, request more details about the proposal, and suggest next steps for discussion.",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
]

# Delete existing intents and insert new ones
db.intents.delete_many({"user_id": user_id})
db.intents.insert_many(intents_data)
print(f"✅ Created {len(intents_data)} intents with embeddings")

# 6. Create Knowledge Base entries
kb_data = [
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "Company Overview",
        "content": """We are a leading technology solutions provider specializing in AI-powered business automation. 
        Our flagship product is an intelligent email response system that uses advanced AI to automatically classify, 
        draft, and send email responses. We serve businesses of all sizes, from startups to enterprises.""",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "Pricing and Plans",
        "content": """Our pricing structure:
        - Starter Plan: $49/month - Up to 1,000 emails, 2 email accounts, Basic AI features
        - Professional Plan: $149/month - Up to 10,000 emails, 10 email accounts, Advanced AI, Calendar integration
        - Enterprise Plan: Custom pricing - Unlimited emails, Unlimited accounts, Custom AI training, Priority support
        All plans include 14-day free trial, no credit card required.""",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "Support and Onboarding",
        "content": """We provide comprehensive support:
        - 24/7 email support for all customers
        - Live chat support during business hours (9 AM - 6 PM EST)
        - Dedicated account manager for Enterprise plans
        - Free onboarding and training sessions
        - Extensive documentation and video tutorials
        - Regular product updates and improvements""",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": "Meeting and Calendar Integration",
        "content": """Our calendar integration features:
        - Automatic meeting detection from emails
        - Smart scheduling with Google Calendar and Outlook
        - Automatic calendar event creation
        - Meeting reminders via email
        - Rescheduling and cancellation handling
        - Time zone support
        - Meeting participant management""",
        "embedding": dummy_embedding,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
]

db.knowledge_base.delete_many({"user_id": user_id})
db.knowledge_base.insert_many(kb_data)
print(f"✅ Created {len(kb_data)} knowledge base entries with embeddings")

# 7. Create sample emails for testing
sample_emails = [
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "email_account_id": email_account_id,
        "sender_email": "customer1@example.com",
        "sender_name": "John Smith",
        "subject": "Interested in your Professional Plan",
        "body": "Hi, I'm interested in your Professional Plan for my team of 5 people. Can you provide more details about the features and any discounts for annual billing?",
        "received_at": datetime.utcnow() - timedelta(hours=2),
        "status": "new",
        "is_read": False,
        "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
        "message_id": f"msg_{uuid.uuid4().hex}"
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "email_account_id": email_account_id,
        "sender_email": "partner@techcorp.com",
        "sender_name": "Sarah Johnson",
        "subject": "Partnership Opportunity - AI Integration",
        "body": "Hello, I represent TechCorp and we're interested in integrating your AI email system into our platform. Would you be available for a call next week to discuss this partnership opportunity?",
        "received_at": datetime.utcnow() - timedelta(hours=5),
        "status": "new",
        "is_read": False,
        "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
        "message_id": f"msg_{uuid.uuid4().hex}"
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "email_account_id": email_account_id,
        "sender_email": "support_needed@company.com",
        "sender_name": "Mike Davis",
        "subject": "Issue with email classification",
        "body": "I'm having trouble with the email classification feature. Some of my sales emails are being classified as general inquiries. Can you help me fix this?",
        "received_at": datetime.utcnow() - timedelta(hours=1),
        "status": "new",
        "is_read": False,
        "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
        "message_id": f"msg_{uuid.uuid4().hex}"
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "email_account_id": email_account_id,
        "sender_email": "meeting@client.com",
        "sender_name": "Emily Chen",
        "subject": "Schedule Demo Meeting",
        "body": "Hi Amit, I'd like to schedule a product demo for our team. Would you be available for a 30-minute call on Thursday, November 2nd at 2:00 PM EST? Please let me know if this works for you.",
        "received_at": datetime.utcnow() - timedelta(minutes=30),
        "status": "new",
        "is_read": False,
        "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
        "message_id": f"msg_{uuid.uuid4().hex}"
    },
    {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "email_account_id": email_account_id,
        "sender_email": "info@newstartup.io",
        "sender_name": "David Wilson",
        "subject": "Quick question about your Enterprise plan",
        "body": "Hello, we're a startup with about 50 employees. What kind of custom features can we get with the Enterprise plan? Also, is there any startup discount available?",
        "received_at": datetime.utcnow() - timedelta(minutes=15),
        "status": "new",
        "is_read": False,
        "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
        "message_id": f"msg_{uuid.uuid4().hex}"
    }
]

db.emails.delete_many({"user_id": user_id})
db.emails.insert_many(sample_emails)
print(f"✅ Created {len(sample_emails)} sample emails")

print("\n" + "=" * 80)
print("SEED DATA CREATION COMPLETE!")
print("=" * 80)
print(f"\nUser ID: {user_id}")
print(f"Email: amits.joys@gmail.com")
print(f"Password: ij@123")
print(f"OAuth Token ID: {oauth_token_id}")
print(f"Email Account ID: {email_account_id}")
print(f"Calendar Provider ID: {calendar_provider_id}")
print(f"\nCreated:")
print(f"  - 5 Intents with embeddings")
print(f"  - 4 Knowledge Base entries with embeddings")
print(f"  - 5 Sample emails ready for processing")

