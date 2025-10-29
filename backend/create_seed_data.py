#!/usr/bin/env python3
"""
Script to create seed data for Knowledge Base and Intents
"""
import os
import uuid
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import requests

load_dotenv()

# Get environment variables
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "test_database")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

def get_embedding(text: str):
    """Get embedding from Cohere API"""
    if not COHERE_API_KEY:
        print("⚠️ Warning: No COHERE_API_KEY found, skipping embeddings")
        return None
    
    try:
        response = requests.post(
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
            return response.json()["embeddings"][0]
        else:
            print(f"⚠️ Embedding API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Error getting embedding: {e}")
        return None

def create_seed_data(user_id: str):
    """Create seed data for Knowledge Base and Intents"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("📚 Creating Knowledge Base entries...")
    
    # Knowledge Base entries
    kb_entries = [
        {
            "kb_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Company Services Overview",
            "content": "We provide comprehensive email automation services including AI-powered email responses, calendar integration, meeting scheduling, and follow-up management. Our platform supports OAuth integration with Gmail and Outlook for seamless email and calendar synchronization.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "kb_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Pricing Information",
            "content": "Our pricing starts at $29/month for the basic plan which includes up to 500 automated emails per month. The professional plan is $99/month with unlimited emails and advanced AI features. Enterprise plans are available starting at $299/month with custom integrations and dedicated support.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "kb_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Support Channels",
            "content": "For technical support, please email support@emailautomation.com or use our live chat available 24/7. We also offer phone support Monday-Friday 9am-5pm EST at 1-800-EMAIL-AI. Premium customers have access to priority support with guaranteed 1-hour response time.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "kb_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "API Documentation",
            "content": "Our REST API allows you to integrate email automation into your applications. Access the full documentation at https://docs.emailautomation.com/api. Authentication is via API keys which can be generated from your account dashboard. Rate limits are 1000 requests per hour for basic plans.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "kb_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Meeting Scheduling Features",
            "content": "Our calendar agent automatically detects meeting requests in emails and creates calendar events. It supports Google Calendar and Outlook Calendar. Features include automatic rescheduling, conflict detection, reminder sending, and timezone handling. Meeting details are extracted using AI with 90%+ accuracy.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Add embeddings to KB entries
    for entry in kb_entries:
        embedding_text = f"{entry['title']} {entry['content']}"
        embedding = get_embedding(embedding_text)
        if embedding:
            entry["embedding"] = embedding
            entry["embedding_model"] = "cohere-embed-english-v3.0"
        
        # Check if entry already exists
        existing = db.knowledge_base.find_one({"user_id": user_id, "title": entry["title"]})
        if not existing:
            db.knowledge_base.insert_one(entry)
            print(f"✅ Created KB entry: {entry['title']}")
        else:
            print(f"⏭️  KB entry already exists: {entry['title']}")
    
    print("\n🎯 Creating Intent entries...")
    
    # Intent entries
    intents = [
        {
            "intent_id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Sales Inquiry",
            "description": "Customer is interested in purchasing or learning about our products/services",
            "example_phrases": [
                "I'm interested in your services",
                "Can you send me pricing information?",
                "I'd like to schedule a demo",
                "What packages do you offer?",
                "Tell me more about your product"
            ],
            "response_template": "Thank you for your interest in our services! I'd be happy to provide you with detailed information about our offerings and pricing. [CONTEXT_FROM_KB]",
            "auto_send": True,
            "priority": "high",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "intent_id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Support Request",
            "description": "Customer needs technical support or has a problem",
            "example_phrases": [
                "I'm having trouble with",
                "This isn't working",
                "Can you help me with",
                "I need technical support",
                "How do I fix"
            ],
            "response_template": "Thank you for reaching out. I understand you're experiencing an issue. [CONTEXT_FROM_KB] Our support team will investigate this and get back to you within 24 hours.",
            "auto_send": False,
            "priority": "high",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "intent_id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Meeting Request",
            "description": "Customer wants to schedule a meeting or call",
            "example_phrases": [
                "Can we schedule a meeting?",
                "Let's set up a call",
                "When are you available?",
                "I'd like to discuss this over a meeting",
                "Can we meet next week?"
            ],
            "response_template": "I'd be happy to schedule a meeting with you. [MEETING_DETECTION_WILL_CREATE_EVENT] I'll send you a calendar invitation shortly.",
            "auto_send": True,
            "priority": "medium",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "intent_id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "General Inquiry",
            "description": "General questions or information requests",
            "example_phrases": [
                "I have a question",
                "Can you tell me about",
                "I'm curious about",
                "What is",
                "How does this work"
            ],
            "response_template": "Thank you for your inquiry. [CONTEXT_FROM_KB] Please let me know if you need any additional information.",
            "auto_send": True,
            "priority": "low",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "intent_id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Feedback",
            "description": "Customer providing feedback, testimonial, or review",
            "example_phrases": [
                "I wanted to share my experience",
                "Great service!",
                "This has been very helpful",
                "I'd like to provide feedback",
                "Thank you for"
            ],
            "response_template": "Thank you so much for your valuable feedback! We truly appreciate you taking the time to share your experience with us. Your input helps us continue to improve our services.",
            "auto_send": True,
            "priority": "low",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Add embeddings to intents
    for intent in intents:
        embedding_text = f"{intent['name']} {intent['description']} {' '.join(intent['example_phrases'])}"
        embedding = get_embedding(embedding_text)
        if embedding:
            intent["embedding"] = embedding
            intent["embedding_model"] = "cohere-embed-english-v3.0"
        
        # Check if intent already exists
        existing = db.intents.find_one({"user_id": user_id, "name": intent["name"]})
        if not existing:
            db.intents.insert_one(intent)
            print(f"✅ Created intent: {intent['name']}")
        else:
            print(f"⏭️  Intent already exists: {intent['name']}")
    
    # Print summary
    kb_count = db.knowledge_base.count_documents({"user_id": user_id})
    intent_count = db.intents.count_documents({"user_id": user_id})
    
    print(f"\n✅ Seed data creation complete!")
    print(f"   📚 Total Knowledge Base entries: {kb_count}")
    print(f"   🎯 Total Intents: {intent_count}")

if __name__ == "__main__":
    # Get user
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    user = db.users.find_one({"email": "amits.joys@gmail.com"})
    
    if not user:
        print("❌ Error: User amits.joys@gmail.com not found!")
        print("   Please create the user first using create_user.py")
        exit(1)
    
    user_id = user["user_id"]
    print(f"👤 Found user: {user['email']} (ID: {user_id})")
    print()
    
    create_seed_data(user_id)
