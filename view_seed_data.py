#!/usr/bin/env python3
"""
View current seed data for amits.joys@gmail.com
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def view_data():
    """View current intents and knowledge base"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get user ID
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    if not user:
        print("❌ User not found")
        return
    
    user_id = user['id']
    
    # Get intents
    intents = await db.intents.find({"user_id": user_id}).to_list(length=100)
    print(f"\n📋 INTENTS ({len(intents)}):")
    print("=" * 80)
    for i, intent in enumerate(intents, 1):
        print(f"\n{i}. {intent['name']}")
        print(f"   Description: {intent['description']}")
        print(f"   Confidence Threshold: {intent['confidence_threshold']}")
        print(f"   Follow-up Hours: {intent['follow_up_hours']}")
        print(f"   Meeting Related: {intent['is_meeting_related']}")
        print(f"   Examples: {len(intent.get('examples', []))} provided")
        print(f"   Has Embedding: {'✅' if intent.get('embedding') else '❌'}")
    
    # Get knowledge base
    kb_entries = await db.knowledge_base.find({"user_id": user_id}).to_list(length=100)
    print(f"\n\n📚 KNOWLEDGE BASE ({len(kb_entries)}):")
    print("=" * 80)
    for i, kb in enumerate(kb_entries, 1):
        print(f"\n{i}. {kb['title']}")
        print(f"   Tags: {', '.join(kb.get('tags', []))}")
        print(f"   Content Length: {len(kb['content'])} characters")
        print(f"   Has Embedding: {'✅' if kb.get('embedding') else '❌'}")
        print(f"   Preview: {kb['content'][:100]}...")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(view_data())
