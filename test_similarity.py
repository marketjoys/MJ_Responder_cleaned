import sys
sys.path.insert(0, '/app/backend')

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from server import EmailMessage, get_cohere_embedding, cosine_similarity

client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["email_response_system"]

async def test():
    # Get email
    email = await db.emails.find_one({"status": "new"})
    email_msg = EmailMessage(**email)
    
    print(f"Email: {email_msg.subject}")
    print(f"Body: {email_msg.body[:100]}...")
    
    # Get email embedding
    email_embedding = await get_cohere_embedding(email_msg.body)
    print(f"\nEmail embedding dimension: {len(email_embedding)}")
    
    # Get intents
    intents = await db.intents.find({"user_id": email_msg.user_id}).to_list(100)
    print(f"\nComparing against {len(intents)} intents:")
    
    for intent in intents:
        if "embedding" in intent:
            intent_embedding = intent["embedding"]
            print(f"\n  Intent: {intent['name']}")
            print(f"  Intent embedding dimension: {len(intent_embedding)}")
            
            similarity = cosine_similarity(email_embedding, intent_embedding)
            threshold = intent.get("confidence_threshold", 0.7)
            print(f"  Similarity: {similarity:.4f} (threshold: {threshold})")
            print(f"  Match: {'✅' if similarity >= threshold else '❌'}")

asyncio.run(test())
