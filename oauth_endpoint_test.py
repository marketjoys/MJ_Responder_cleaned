#!/usr/bin/env python3
"""
OAuth Endpoint Testing - Test OAuth endpoints directly
"""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://worker-restart-hub.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def test_oauth_endpoints():
    """Test OAuth endpoints"""
    print("🔍 Testing OAuth Endpoints...")
    print(f"Backend URL: {BACKEND_URL}")
    
    # Test 1: OAuth Google Status (without auth)
    print("\n1. Testing OAuth Google Status (no auth)...")
    try:
        response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {str(e)}")
    
    # Test 2: OAuth Google Auth URL
    print("\n2. Testing OAuth Google Auth URL...")
    try:
        response = requests.get(f"{API_BASE}/oauth/google/auth", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            auth_data = response.json()
            print(f"   Auth URL exists: {'auth_url' in auth_data}")
            if 'auth_url' in auth_data:
                print(f"   Auth URL: {auth_data['auth_url'][:100]}...")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {str(e)}")
    
    # Test 3: OAuth Microsoft Status
    print("\n3. Testing OAuth Microsoft Status...")
    try:
        response = requests.get(f"{API_BASE}/oauth/microsoft/status", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {str(e)}")
    
    # Test 4: OAuth Microsoft Auth URL
    print("\n4. Testing OAuth Microsoft Auth URL...")
    try:
        response = requests.get(f"{API_BASE}/oauth/microsoft/auth", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            auth_data = response.json()
            print(f"   Auth URL exists: {'auth_url' in auth_data}")
            if 'auth_url' in auth_data:
                print(f"   Auth URL: {auth_data['auth_url'][:100]}...")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {str(e)}")
    
    # Test 5: Check if OAuth routes exist in server
    print("\n5. Testing OAuth route existence...")
    oauth_routes = [
        "/oauth/google/auth",
        "/oauth/google/callback", 
        "/oauth/google/status",
        "/oauth/microsoft/auth",
        "/oauth/microsoft/callback",
        "/oauth/microsoft/status"
    ]
    
    for route in oauth_routes:
        try:
            response = requests.get(f"{API_BASE}{route}", timeout=5)
            status_ok = response.status_code in [200, 302, 400, 401]  # Not 404
            print(f"   {route}: {'✅' if status_ok else '❌'} ({response.status_code})")
        except Exception as e:
            print(f"   {route}: ❌ (Exception: {str(e)})")
    
    # Test 6: Check email accounts OAuth endpoint
    print("\n6. Testing Email Accounts OAuth endpoint...")
    try:
        # This should require auth, so we expect 401
        response = requests.post(f"{API_BASE}/email-accounts/oauth", json={}, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Endpoint exists (requires auth)")
        elif response.status_code == 422:
            print("   ✅ Endpoint exists (validation error)")
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {str(e)}")

if __name__ == "__main__":
    test_oauth_endpoints()