#!/usr/bin/env python3
"""Debug Groq API responses directly"""

import asyncio
import httpx
import os
import sys

# Add backend to path for imports
sys.path.append('/app/backend')
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

async def test_groq_directly():
    """Test Groq API directly to see if responses are complete"""
    
    system_prompt = """You are Agent A - an email draft generator. Generate ONLY the email body content for a professional reply.

ACCOUNT PERSONA: Professional and helpful

EMAIL CONTEXT:
- Original Subject: Test Email
- From: test@example.com
- Body: Hello, can you tell me about your pricing?

CRITICAL INSTRUCTIONS:
1. MUST start with the salutation: "Dear Test,"
2. Generate ONLY the email body content - no subject lines, NO SIGNATURES, no placeholders
3. Keep response comprehensive but professional (200-400 words when detailed info is needed)
4. Address the pricing inquiry directly
5. Include actionable next steps where appropriate
6. DO NOT include any signatures, closing remarks like "Best regards", "Sincerely", etc.

Generate the email body content now:"""

    messages = [
        {"role": "user", "content": "Generate a comprehensive email body response for: Hello, can you tell me about your pricing?"}
    ]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": [{"role": "system", "content": system_prompt}] + messages,
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.6,
                    "max_completion_tokens": 4096,
                    "top_p": 0.95,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"✅ Success! Response length: {len(content)}")
                print(f"First 200 chars: {content[:200]}...")
                print(f"Last 200 chars: ...{content[-200:]}")
                return True
            else:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_groq_directly())
    sys.exit(0 if success else 1)