#!/usr/bin/env python3
"""
Comprehensive seed data script for amits.joys@gmail.com
Includes: User creation, Intents, Knowledge Base, Email Accounts, Calendar Providers
"""
import asyncio
import os
import sys
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import uuid
import httpx

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
COHERE_API_KEY = os.environ.get('COHERE_API_KEY')

async def generate_embedding(text: str) -> list:
    """Generate embedding using Cohere API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.cohere.ai/v1/embed",
                headers={
                    "Authorization": f"Bearer {COHERE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "texts": [text],
                    "model": "embed-english-v3.0",
                    "input_type": "search_document"
                }
            )
            if response.status_code == 200:
                result = response.json()
                return result['embeddings'][0]
            else:
                print(f"⚠️ Warning: Cohere API returned {response.status_code}")
                return None
    except Exception as e:
        print(f"⚠️ Warning: Failed to generate embedding: {e}")
        return None

async def create_user(db, email: str, password: str, full_name: str):
    """Create or update user"""
    user = await db.users.find_one({"email": email})
    
    if user:
        print(f"✅ User already exists: {email} (ID: {user['id']})")
        return user['id']
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_id = str(uuid.uuid4())
    user_data = {
        "id": user_id,
        "email": email,
        "password_hash": password_hash,
        "full_name": full_name,
        "timezone": "America/Los_Angeles",
        "email_quota": 10000,
        "emails_used": 0,
        "quota_reset_date": datetime.now(timezone.utc) + timedelta(days=30),
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.users.insert_one(user_data)
    print(f"✅ Created user: {email} (ID: {user_id})")
    return user_id

async def add_intents(db, user_id: str):
    """Add intent data"""
    intents_data = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Sales Inquiry",
            "description": "Customer asking about products, pricing, or making a purchase inquiry",
            "examples": [
                "I'm interested in your product offerings",
                "What are your pricing plans?",
                "Can you send me a quote for your services?",
                "I'd like to know more about your enterprise solution"
            ],
            "system_prompt": "You are a professional sales representative. Be helpful, enthusiastic, and provide clear information about products and pricing. Always aim to move the conversation forward towards a demo or purchase.",
            "confidence_threshold": 0.65,
            "follow_up_hours": 24,
            "is_meeting_related": False,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Support Request",
            "description": "Customer needs technical support or has a problem with a product/service",
            "examples": [
                "I'm having trouble with my account",
                "The feature isn't working as expected",
                "Can you help me troubleshoot this issue?",
                "I need assistance with setup"
            ],
            "system_prompt": "You are a helpful technical support specialist. Be patient, empathetic, and provide clear step-by-step solutions. If the issue is complex, offer to escalate or schedule a call.",
            "confidence_threshold": 0.65,
            "follow_up_hours": 12,
            "is_meeting_related": False,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Meeting Request",
            "description": "Someone wants to schedule a meeting, call, or demo",
            "examples": [
                "Can we schedule a call to discuss this?",
                "I'd like to book a demo",
                "Are you available for a meeting next week?",
                "Let's set up a time to talk about this"
            ],
            "system_prompt": "You are a professional scheduler. Be accommodating and propose specific time slots. Always aim to lock in a meeting time and send calendar invites.",
            "confidence_threshold": 0.6,
            "follow_up_hours": 48,
            "is_meeting_related": True,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Partnership Inquiry",
            "description": "Business partnership, collaboration, or integration opportunities",
            "examples": [
                "We'd like to explore a partnership opportunity",
                "Can we integrate our platforms?",
                "Interested in collaboration opportunities",
                "Would you be open to a strategic partnership?"
            ],
            "system_prompt": "You are a business development professional. Be open and enthusiastic about partnerships while being professional. Gather information about their company and proposal.",
            "confidence_threshold": 0.65,
            "follow_up_hours": 48,
            "is_meeting_related": False,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "General Inquiry",
            "description": "General questions, information requests, or unclear intent",
            "examples": [
                "I have a question about your company",
                "Can you tell me more about what you do?",
                "I came across your website",
                "Just wanted to reach out"
            ],
            "system_prompt": "You are a friendly and professional representative. Provide helpful information and try to understand the sender's specific needs to route them appropriately.",
            "confidence_threshold": 0.5,
            "follow_up_hours": 48,
            "is_meeting_related": False,
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    print("\n📝 Adding intents...")
    added = 0
    for intent in intents_data:
        existing = await db.intents.find_one({
            "user_id": user_id,
            "name": intent["name"]
        })
        
        if existing:
            print(f"   ⏭️  Skipping '{intent['name']}' - already exists")
        else:
            # Generate embedding for intent
            embedding_text = f"{intent['name']} {intent['description']} {' '.join(intent['examples'])}"
            embedding = await generate_embedding(embedding_text)
            if embedding:
                intent["embedding"] = embedding
            
            await db.intents.insert_one(intent)
            print(f"   ✅ Added intent: {intent['name']}")
            added += 1
    
    return added

async def add_knowledge_base(db, user_id: str):
    """Add knowledge base entries"""
    knowledge_base_data = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Company Overview",
            "content": """We are an AI-powered email automation platform that helps businesses manage their email communications efficiently. 

Our key features include:
- Intelligent email classification and routing
- Automated response generation using advanced AI
- Meeting detection and calendar integration
- Multi-account email management with OAuth support
- Custom knowledge base for contextual responses
- Follow-up automation and tracking

Founded in 2024, we serve businesses of all sizes looking to streamline their email workflows and improve response times.""",
            "tags": ["company", "overview", "about"],
            "embedding": None,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Pricing Information",
            "content": """Our pricing is flexible and designed to scale with your business:

Starter Plan - $29/month
- 1 email account
- 1,000 emails processed per month
- Basic AI responses
- Email support

Professional Plan - $99/month
- 5 email accounts
- 10,000 emails processed per month
- Advanced AI with custom training
- Calendar integration
- Priority support

Enterprise Plan - Custom pricing
- Unlimited email accounts
- Unlimited email processing
- Dedicated AI model
- Advanced integrations
- 24/7 premium support
- Custom SLAs

All plans include a 14-day free trial. No credit card required to start.""",
            "tags": ["pricing", "plans", "cost", "subscription"],
            "embedding": None,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Support Channels",
            "content": """We offer multiple support channels to help you succeed:

Email Support: support@company.com
- Response time: Within 24 hours (Starter)
- Response time: Within 4 hours (Professional)
- Response time: Within 1 hour (Enterprise)

Live Chat: Available on our dashboard
- Available: 9 AM - 6 PM EST, Monday-Friday

Phone Support: Available for Professional and Enterprise plans
- Schedule a callback through your dashboard

Documentation: docs.company.com
- Comprehensive guides and tutorials
- API documentation
- Video tutorials

Community Forum: community.company.com
- Connect with other users
- Share best practices
- Get tips from experts""",
            "tags": ["support", "help", "contact", "documentation"],
            "embedding": None,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "OAuth Integration Setup",
            "content": """Setting up OAuth integration for Gmail and Outlook:

For Gmail:
1. Go to Account Settings in your dashboard
2. Click 'Add Email Account'
3. Select 'Connect with Google'
4. Authorize the necessary permissions (Gmail and Calendar access)
5. Your account will be automatically configured

For Outlook/Microsoft:
1. Go to Account Settings in your dashboard
2. Click 'Add Email Account'
3. Select 'Connect with Microsoft'
4. Authorize the necessary permissions
5. Your account will be automatically configured

Benefits of OAuth:
- No need to generate app passwords
- More secure authentication
- Automatic token refresh
- Calendar integration included
- Multi-account support

Troubleshooting:
- Make sure pop-ups are enabled in your browser
- Check that you're granting all requested permissions
- If authorization fails, try logging out and back in
- Contact support if issues persist""",
            "tags": ["oauth", "gmail", "outlook", "setup", "integration"],
            "embedding": None,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "AI Features and Capabilities",
            "content": """Our AI-powered email assistant provides intelligent automation:

Intelligent Classification:
- Automatically categorizes incoming emails by intent
- Learns from your corrections and feedback
- Handles multiple languages
- Identifies meeting requests automatically

Smart Response Generation:
- Creates contextual responses based on your knowledge base
- Maintains your brand voice and tone
- Includes relevant information from your company data
- Generates follow-up emails automatically

Meeting Detection:
- Identifies meeting requests in emails
- Extracts date, time, and duration
- Creates calendar events automatically
- Sends meeting confirmations

Personalization:
- Custom signatures per email account
- Persona-based responses
- Knowledge base integration
- Learning from past conversations

Security & Privacy:
- End-to-end encryption for credentials
- OAuth secure authentication
- No data sharing with third parties
- GDPR compliant""",
            "tags": ["ai", "features", "automation", "capabilities"],
            "embedding": None,
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    print("\n📚 Adding knowledge base entries...")
    added = 0
    for kb in knowledge_base_data:
        existing = await db.knowledge_base.find_one({
            "user_id": user_id,
            "title": kb["title"]
        })
        
        if existing:
            print(f"   ⏭️  Skipping '{kb['title']}' - already exists")
        else:
            # Generate embedding for knowledge base
            embedding_text = f"{kb['title']} {kb['content']}"
            embedding = await generate_embedding(embedding_text)
            if embedding:
                kb["embedding"] = embedding
            
            await db.knowledge_base.insert_one(kb)
            print(f"   ✅ Added KB entry: {kb['title']}")
            added += 1
    
    return added

async def add_sample_emails(db, user_id: str):
    """Add sample test emails with meeting requests"""
    sample_emails = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "account_id": "sample_account",
            "thread_id": str(uuid.uuid4()),
            "message_id": f"<{uuid.uuid4()}@mail.gmail.com>",
            "sender": "john.doe@example.com",
            "sender_name": "John Doe",
            "recipient": "amits.joys@gmail.com",
            "subject": "Meeting Request - Product Demo",
            "body": "Hi Amit,\n\nI hope this email finds you well. I'm interested in learning more about your AI email automation platform.\n\nWould you be available for a 30-minute demo call on November 5th at 2:00 PM PST?\n\nLooking forward to hearing from you.\n\nBest regards,\nJohn Doe",
            "received_at": datetime.now(timezone.utc) - timedelta(hours=2),
            "status": "unread",
            "is_read": False,
            "has_attachments": False,
            "labels": ["INBOX"],
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "account_id": "sample_account",
            "thread_id": str(uuid.uuid4()),
            "message_id": f"<{uuid.uuid4()}@mail.gmail.com>",
            "sender": "sarah.smith@company.com",
            "sender_name": "Sarah Smith",
            "recipient": "amits.joys@gmail.com",
            "subject": "Quick Question About Pricing",
            "body": "Hello,\n\nI came across your platform and I'm very interested in the Professional plan.\n\nCould you provide more details about the features included and if there's any discount for annual billing?\n\nThank you!\n\nSarah Smith\nMarketing Manager",
            "received_at": datetime.now(timezone.utc) - timedelta(hours=5),
            "status": "unread",
            "is_read": False,
            "has_attachments": False,
            "labels": ["INBOX"],
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "account_id": "sample_account",
            "thread_id": str(uuid.uuid4()),
            "message_id": f"<{uuid.uuid4()}@mail.gmail.com>",
            "sender": "mike.johnson@tech.io",
            "sender_name": "Mike Johnson",
            "recipient": "amits.joys@gmail.com",
            "subject": "Partnership Opportunity",
            "body": "Hi Amit,\n\nWe're building an integration platform and we think your email automation solution would be a great fit.\n\nCan we set up a call next week to discuss potential partnership opportunities? I'm flexible on timing.\n\nBest,\nMike Johnson\nCEO, Tech.io",
            "received_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "status": "unread",
            "is_read": False,
            "has_attachments": False,
            "labels": ["INBOX"],
            "created_at": datetime.now(timezone.utc)
        }
    ]
    
    print("\n📧 Adding sample emails...")
    added = 0
    for email in sample_emails:
        existing = await db.emails.find_one({
            "user_id": user_id,
            "message_id": email["message_id"]
        })
        
        if not existing:
            await db.emails.insert_one(email)
            print(f"   ✅ Added email from: {email['sender_name']}")
            added += 1
        else:
            print(f"   ⏭️  Skipping email from: {email['sender_name']} - already exists")
    
    return added

async def main():
    """Main seed data function"""
    print("=" * 60)
    print("COMPREHENSIVE SEED DATA SCRIPT")
    print("=" * 60)
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Step 1: Create/Get User
        print("\n🔐 Step 1: User Creation")
        user_id = await create_user(db, "amits.joys@gmail.com", "ij@123", "Amit Joys")
        
        # Step 2: Add Intents
        print("\n🎯 Step 2: Intent Setup")
        intents_added = await add_intents(db, user_id)
        
        # Step 3: Add Knowledge Base
        print("\n📚 Step 3: Knowledge Base Setup")
        kb_added = await add_knowledge_base(db, user_id)
        
        # Step 4: Add Sample Emails
        print("\n📧 Step 4: Sample Emails Setup")
        emails_added = await add_sample_emails(db, user_id)
        
        # Final Summary
        print("\n" + "=" * 60)
        print("SEED DATA SUMMARY")
        print("=" * 60)
        
        total_intents = await db.intents.count_documents({"user_id": user_id})
        total_kb = await db.knowledge_base.count_documents({"user_id": user_id})
        total_emails = await db.emails.count_documents({"user_id": user_id})
        
        print(f"\n✅ User: amits.joys@gmail.com (ID: {user_id})")
        print(f"   Password: ij@123")
        print(f"\n📊 Data Summary:")
        print(f"   - Total Intents: {total_intents} (Added: {intents_added})")
        print(f"   - Total KB Entries: {total_kb} (Added: {kb_added})")
        print(f"   - Total Sample Emails: {total_emails} (Added: {emails_added})")
        
        print("\n✅ Seed data setup completed successfully!")
        print("\n🔑 Login Credentials:")
        print(f"   Email: amits.joys@gmail.com")
        print(f"   Password: ij@123")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
