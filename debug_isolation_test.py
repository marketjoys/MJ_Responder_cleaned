#!/usr/bin/env python3
"""
Debug User Isolation Issues
"""
import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-codebase-debug.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def create_test_users():
    """Create two test users"""
    user1_data = {
        "email": f"debug1.{int(time.time())}@example.com",
        "password": "testpassword123",
        "full_name": "Debug User One"
    }
    
    user2_data = {
        "email": f"debug2.{int(time.time())}@example.com",
        "password": "testpassword123",
        "full_name": "Debug User Two"
    }
    
    # Create users
    response1 = requests.post(f"{API_BASE}/auth/register", json=user1_data, timeout=15)
    response2 = requests.post(f"{API_BASE}/auth/register", json=user2_data, timeout=15)
    
    if response1.status_code in [200, 201] and response2.status_code in [200, 201]:
        user1_token = response1.json().get('access_token')
        user2_token = response2.json().get('access_token')
        user1_id = response1.json().get('user', {}).get('id')
        user2_id = response2.json().get('user', {}).get('id')
        
        print(f"User 1: {user1_data['email']} (ID: {user1_id})")
        print(f"User 2: {user2_data['email']} (ID: {user2_id})")
        
        return user1_token, user2_token, user1_id, user2_id
    else:
        print(f"User creation failed: {response1.status_code}, {response2.status_code}")
        return None, None, None, None

def debug_intent_isolation():
    """Debug intent isolation issue"""
    print("\n🔍 Debugging Intent Isolation...")
    
    user1_token, user2_token, user1_id, user2_id = create_test_users()
    if not user1_token or not user2_token:
        print("❌ Failed to create users")
        return
    
    headers1 = {"Authorization": f"Bearer {user1_token}"}
    headers2 = {"Authorization": f"Bearer {user2_token}"}
    
    # User 1 creates an intent
    intent1_data = {
        "name": "Debug User 1 Intent",
        "description": "This intent belongs to user 1",
        "examples": ["user 1 example"],
        "confidence_threshold": 0.7
    }
    
    response = requests.post(f"{API_BASE}/intents", json=intent1_data, headers=headers1, timeout=15)
    print(f"User 1 create intent: {response.status_code}")
    if response.status_code in [200, 201]:
        intent1_id = response.json().get('id')
        print(f"Intent 1 ID: {intent1_id}")
    else:
        print(f"Create failed: {response.text}")
        return
    
    # User 2 creates an intent
    intent2_data = {
        "name": "Debug User 2 Intent",
        "description": "This intent belongs to user 2",
        "examples": ["user 2 example"],
        "confidence_threshold": 0.7
    }
    
    response = requests.post(f"{API_BASE}/intents", json=intent2_data, headers=headers2, timeout=15)
    print(f"User 2 create intent: {response.status_code}")
    if response.status_code in [200, 201]:
        intent2_id = response.json().get('id')
        print(f"Intent 2 ID: {intent2_id}")
    else:
        print(f"Create failed: {response.text}")
        return
    
    # Test: User 1 tries to update User 2's intent
    print(f"\n🧪 User 1 trying to update User 2's intent ({intent2_id})...")
    update_data = {"name": "Hacked Intent", "description": "Hacked by user 1"}
    response = requests.put(f"{API_BASE}/intents/{intent2_id}", json=update_data, headers=headers1, timeout=15)
    print(f"Update attempt status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Verify the intent wasn't actually updated
    response = requests.get(f"{API_BASE}/intents/{intent2_id}", headers=headers2, timeout=10)
    if response.status_code == 200:
        intent_data = response.json()
        print(f"Intent name after update attempt: {intent_data.get('name')}")
        print(f"Intent description after update attempt: {intent_data.get('description')}")
    
    # Test: User 1 tries to delete User 2's intent
    print(f"\n🧪 User 1 trying to delete User 2's intent ({intent2_id})...")
    response = requests.delete(f"{API_BASE}/intents/{intent2_id}", headers=headers1, timeout=10)
    print(f"Delete attempt status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Verify the intent still exists
    response = requests.get(f"{API_BASE}/intents/{intent2_id}", headers=headers2, timeout=10)
    print(f"Intent still exists check: {response.status_code}")
    
    # Cleanup
    requests.delete(f"{API_BASE}/intents/{intent1_id}", headers=headers1, timeout=10)
    requests.delete(f"{API_BASE}/intents/{intent2_id}", headers=headers2, timeout=10)

if __name__ == "__main__":
    debug_intent_isolation()