#!/usr/bin/env python3
"""
Add seed data for knowledge base and intents for amits.joys@gmail.com
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime
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

async def add_seed_data():
    """Add seed data for knowledge base and intents"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user ID for amits.joys@gmail.com
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    if not user:
        print("❌ Error: User amits.joys@gmail.com not found")
        return
    
    user_id = user['id']
    print(f"✅ Found user: {user['email']} (ID: {user_id})")
    
    # Check existing data
    existing_intents = await db.intents.count_documents({"user_id": user_id})
    existing_kb = await db.knowledge_base.count_documents({"user_id": user_id})
    
    print(f"\n📊 Current data:")
    print(f"   - Intents: {existing_intents}")
    print(f"   - Knowledge Base entries: {existing_kb}")
    
    # Seed Intents
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
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
        }
    ]
    
    # Knowledge Base entries
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
            "embedding": None,  # Will be generated
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
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
            "created_at": datetime.utcnow()
        }
    ]
    
    print("\n📝 Adding intents...")
    for intent in intents_data:
        # Check if intent with same name exists
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
    
    print("\n📚 Adding knowledge base entries...")
    for kb in knowledge_base_data:
        # Check if KB entry with same title exists
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
    
    # Final count
    final_intents = await db.intents.count_documents({"user_id": user_id})
    final_kb = await db.knowledge_base.count_documents({"user_id": user_id})
    
    print(f"\n📊 Final data:")
    print(f"   - Intents: {final_intents}")
    print(f"   - Knowledge Base entries: {final_kb}")
    print(f"\n✅ Seed data added successfully!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(add_seed_data())
