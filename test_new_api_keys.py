#!/usr/bin/env python3
"""
Test new Groq and Cohere API keys
"""
import os
import sys
import requests
import json

# Load environment variables
sys.path.append('/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
COHERE_API_KEY = os.environ.get('COHERE_API_KEY')

def test_groq_api():
    """Test Groq API with the new key"""
    print("\n🔍 Testing Groq API...")
    print(f"   API Key: {GROQ_API_KEY[:20]}...")
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'Hello World' in exactly 2 words."}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Groq API WORKING")
            print(f"   Response: {content}")
            return True
        else:
            print(f"❌ Groq API FAILED: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Groq API ERROR: {str(e)}")
        return False

def test_cohere_api():
    """Test Cohere API with the new key"""
    print("\n🔍 Testing Cohere API...")
    print(f"   API Key: {COHERE_API_KEY[:20]}...")
    
    try:
        response = requests.post(
            "https://api.cohere.com/v1/embed",
            headers={
                "Authorization": f"Bearer {COHERE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "texts": ["Hello World"],
                "model": "embed-english-v3.0",
                "input_type": "search_document"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            embeddings = result.get('embeddings', [])
            print(f"✅ Cohere API WORKING")
            print(f"   Embeddings generated: {len(embeddings)} vectors")
            if embeddings:
                print(f"   Vector dimension: {len(embeddings[0])}")
            return True
        else:
            print(f"❌ Cohere API FAILED: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Cohere API ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing New API Keys")
    print("=" * 60)
    
    groq_ok = test_groq_api()
    cohere_ok = test_cohere_api()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Groq API:   {'✅ WORKING' if groq_ok else '❌ FAILED'}")
    print(f"Cohere API: {'✅ WORKING' if cohere_ok else '❌ FAILED'}")
    
    if groq_ok and cohere_ok:
        print("\n🎉 All API keys are working correctly!")
        sys.exit(0)
    else:
        print("\n⚠️  Some API keys are not working")
        sys.exit(1)
