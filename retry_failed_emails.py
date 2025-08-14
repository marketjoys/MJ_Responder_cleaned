#!/usr/bin/env python3
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv('/app/backend/.env')

async def retry_samhere_emails():
    """Retry processing emails from samhere.joy@gmail.com that are in error status"""
    
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    try:
        print("🔄 Finding failed emails from samhere.joy@gmail.com...")
        
        # Find emails from samhere that are in error status
        failed_emails = await db.emails.find({
            "sender": {"$regex": "samhere", "$options": "i"},
            "status": "error"
        }).to_list(100)
        
        print(f"📧 Found {len(failed_emails)} failed emails from samhere")
        
        # Reset their status to 'new' so they get reprocessed
        for email in failed_emails:
            print(f"   🔄 Resetting email: {email['subject']} (ID: {email['id'][:8]}...)")
            
            # Reset email to reprocess
            await db.emails.update_one(
                {"id": email["id"]},
                {"$set": {
                    "status": "new",
                    "processed_at": None,
                    "intents": [],
                    "draft": None,
                    "draft_html": None,
                    "validation_result": None,
                    "error": None
                }}
            )
        
        if failed_emails:
            print(f"✅ Reset {len(failed_emails)} emails to 'new' status for reprocessing")
            print("⏳ The email polling service will automatically reprocess these emails")
            print("💡 Wait 1-2 minutes for the rate limit to reset and processing to complete")
        else:
            print("ℹ️  No failed emails found from samhere.joy@gmail.com")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        client.close()

async def check_groq_rate_limit():
    """Check if Groq API is available"""
    try:
        print("🔍 Testing Groq API availability...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": [{"role": "user", "content": "test"}],
                    "model": "deepseek-r1-distill-llama-70b",
                    "max_completion_tokens": 10
                }
            )
            
            if response.status_code == 200:
                print("✅ Groq API is available - rate limit has reset")
                return True
            elif response.status_code == 429:
                print("⏳ Groq API still rate limited - please wait a few more minutes")
                return False
            else:
                print(f"⚠️  Groq API returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing Groq API: {str(e)}")
        return False

async def main():
    print("🚀 Starting email retry process for samhere.joy@gmail.com emails...")
    
    # First check if API rate limit has reset
    api_available = await check_groq_rate_limit()
    
    if api_available:
        # Reset failed emails for reprocessing
        await retry_samhere_emails()
    else:
        print("⚠️  Groq API is still rate limited. Please wait and try again in a few minutes.")
        print("💡 You can run this script again when the rate limit resets.")

if __name__ == "__main__":
    asyncio.run(main())