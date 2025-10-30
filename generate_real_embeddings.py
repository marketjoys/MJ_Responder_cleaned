import sys
sys.path.insert(0, '/app/backend')

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import cohere

# Setup Cohere
cohere_api_key = os.getenv("COHERE_API_KEY", "ACor25P7eXjbEsfGvtfkdCpKOhnouLUzmyFIXg0E")
co = cohere.Client(cohere_api_key)

client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def generate_embeddings():
    print("=" * 80)
    print("GENERATING REAL EMBEDDINGS")
    print("=" * 80)
    
    # Get user
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    user_id = str(user["_id"])
    
    # Generate embeddings for intents
    print("\n📊 Generating Intent Embeddings...")
    intents = await db.intents.find({"user_id": user_id}).to_list(100)
    
    intent_texts = []
    for intent in intents:
        text = f"{intent['name']}: {intent['description']}"
        intent_texts.append(text)
    
    if intent_texts:
        response = co.embed(
            texts=intent_texts,
            model="embed-english-v3.0",
            input_type="search_document"
        )
        
        for idx, intent in enumerate(intents):
            embedding = response.embeddings[idx]
            await db.intents.update_one(
                {"_id": intent["_id"]},
                {"$set": {"embedding": embedding}}
            )
            print(f"  ✅ {intent['name']} (embedding dim: {len(embedding)})")
    
    # Generate embeddings for knowledge base
    print("\n📚 Generating Knowledge Base Embeddings...")
    kb_entries = await db.knowledge_base.find({"user_id": user_id}).to_list(100)
    
    kb_texts = []
    for kb in kb_entries:
        text = f"{kb['title']}: {kb['content']}"
        kb_texts.append(text)
    
    if kb_texts:
        response = co.embed(
            texts=kb_texts,
            model="embed-english-v3.0",
            input_type="search_document"
        )
        
        for idx, kb in enumerate(kb_entries):
            embedding = response.embeddings[idx]
            await db.knowledge_base.update_one(
                {"_id": kb["_id"]},
                {"$set": {"embedding": embedding}}
            )
            print(f"  ✅ {kb['title']} (embedding dim: {len(embedding)})")
    
    print("\n✅ All embeddings generated successfully!")

asyncio.run(generate_embeddings())
