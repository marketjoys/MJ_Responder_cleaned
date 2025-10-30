import sys
sys.path.insert(0, '/app/backend')

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import cohere

# Setup Cohere
cohere_api_key = "ACor25P7eXjbEsfGvtfkdCpKOhnouLUzmyFIXg0E"
co = cohere.Client(cohere_api_key)

client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def fix_embeddings():
    print("=" * 80)
    print("FIXING EMBEDDINGS WITH PROPER INPUT TYPE")
    print("=" * 80)
    
    user = await db.users.find_one({"email": "amits.joys@gmail.com"})
    user_id = str(user["_id"])
    
    # Lower the confidence threshold for all intents
    await db.intents.update_many(
        {"user_id": user_id},
        {"$set": {"confidence_threshold": 0.15}}  # Much lower threshold
    )
    print("\n✅ Updated confidence thresholds to 0.15")
    
    # Test with a sample email
    sample_email_text = "Hi, I'm interested in your Professional Plan for my team of 5 people. Can you provide more details about the features and any discounts for annual billing?"
    
    print(f"\n📧 Testing with email: '{sample_email_text[:80]}...'")
    
    # Get embedding for the email
    response = co.embed(
        texts=[sample_email_text],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    email_embedding = response.embeddings[0]
    
    # Compare with intents
    intents = await db.intents.find({"user_id": user_id}).to_list(100)
    
    print("\n📊 Similarity scores:")
    for intent in intents:
        if "embedding" in intent:
            # Calculate cosine similarity
            intent_emb = intent["embedding"]
            dot_product = sum(a * b for a, b in zip(email_embedding, intent_emb))
            norm_a = sum(a * a for a in email_embedding) ** 0.5
            norm_b = sum(b * b for b in intent_emb) ** 0.5
            similarity = dot_product / (norm_a * norm_b)
            
            print(f"  {intent['name']}: {similarity:.4f}")

asyncio.run(fix_embeddings())
