#!/usr/bin/env python3
"""
Detailed OAuth Multi-Account Testing with Authentication
"""

import asyncio
import httpx
import json
import os
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://agent-sync-workflow.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

async def test_oauth_endpoints():
    """Test OAuth endpoints with proper authentication"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🔐 Testing OAuth Multi-Account Implementation")
        print("=" * 50)
        
        # Step 1: Authenticate
        print("1. Authenticating...")
        
        # Try to register a test user
        register_data = {
            "email": "oauth_detailed_test@example.com",
            "password": "testpass123",
            "full_name": "OAuth Detailed Test User"
        }
        
        response = await client.post(f"{API_BASE}/auth/register", json=register_data)
        
        if response.status_code == 400:
            # User exists, try login
            login_data = {
                "email": "oauth_detailed_test@example.com",
                "password": "testpass123"
            }
            response = await client.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code != 200:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return
        
        auth_data = response.json()
        token = auth_data['access_token']
        user_id = auth_data['user']['id']
        
        # Set authorization header
        client.headers.update({"Authorization": f"Bearer {token}"})
        print(f"✅ Authenticated as user: {user_id}")
        
        # Step 2: Test OAuth Status Endpoint
        print("\n2. Testing OAuth Status Endpoint...")
        response = await client.get(f"{API_BASE}/oauth/google/status")
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"✅ OAuth Status Response: {json.dumps(status_data, indent=2)}")
            
            # Check for multi-account fields
            multi_account_fields = ['authorized_accounts', 'total_accounts']
            backward_compat_fields = ['user_email', 'user_name', 'expires_at', 'needs_refresh']
            
            print(f"Multi-account fields present: {all(f in status_data for f in multi_account_fields)}")
            print(f"Backward compatibility fields present: {all(f in status_data for f in backward_compat_fields)}")
        else:
            print(f"❌ OAuth Status failed: {response.status_code} - {response.text}")
        
        # Step 3: Test OAuth Account Creation Endpoint
        print("\n3. Testing OAuth Account Creation Endpoint...")
        
        oauth_account_data = {
            "name": "Test OAuth Account",
            "email": "test@gmail.com",
            "provider": "gmail",
            "auth_type": "oauth",
            "oauth_email": "test@gmail.com",
            "use_oauth": True,
            "signature": "Test Signature",
            "persona": "Professional"
        }
        
        response = await client.post(f"{API_BASE}/email-accounts/oauth", json=oauth_account_data)
        print(f"OAuth Account Creation Response: {response.status_code}")
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
        else:
            account_data = response.json()
            print(f"✅ Account created: {json.dumps(account_data, indent=2)}")
        
        # Step 4: Test Token Revocation Endpoints
        print("\n4. Testing Token Revocation Endpoints...")
        
        # Full revocation
        response = await client.post(f"{API_BASE}/oauth/google/revoke")
        print(f"Full revocation response: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        
        # Specific account revocation
        response = await client.post(f"{API_BASE}/oauth/google/revoke/test@example.com")
        print(f"Specific revocation response: {response.status_code}")
        if response.status_code in [200, 404]:
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response text: {response.text}")
        
        # Step 5: Test Email Account Structure
        print("\n5. Testing Email Account Structure...")
        response = await client.get(f"{API_BASE}/email-accounts")
        
        if response.status_code == 200:
            accounts = response.json()
            print(f"Found {len(accounts)} email accounts")
            
            for i, account in enumerate(accounts[:3]):  # Show first 3 accounts
                print(f"Account {i+1}:")
                print(f"  - auth_type: {account.get('auth_type')}")
                print(f"  - oauth_token_id: {account.get('oauth_token_id')}")
                print(f"  - oauth_email: {account.get('oauth_email')}")
                print(f"  - use_oauth: {account.get('use_oauth')}")
        else:
            print(f"❌ Failed to get accounts: {response.status_code}")
        
        # Step 6: Test Manual Account Creation (Backward Compatibility)
        print("\n6. Testing Manual Account Creation...")
        
        manual_account_data = {
            "name": "Test Manual Account",
            "email": "manual_test@example.com",
            "provider": "gmail",
            "username": "manual_test@example.com",
            "password": "testpass123",
            "signature": "Manual Test Signature"
        }
        
        response = await client.post(f"{API_BASE}/email-accounts", json=manual_account_data)
        print(f"Manual account creation response: {response.status_code}")
        
        if response.status_code == 200:
            account = response.json()
            print("✅ Manual account created successfully")
            print(f"  - auth_type: {account.get('auth_type')}")
            print(f"  - oauth_token_id: {account.get('oauth_token_id')}")
            print(f"  - oauth_email: {account.get('oauth_email')}")
        else:
            try:
                error_data = response.json()
                print(f"Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_oauth_endpoints())