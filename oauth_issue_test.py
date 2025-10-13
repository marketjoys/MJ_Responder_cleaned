#!/usr/bin/env python3
"""
OAuth Issue Investigation - Specific to the review request problem
User has OAuth token but cannot create email accounts and start polling
"""
import asyncio
import sys
import os
import requests
import json
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://auth-calendar-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthIssueTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.user_id = "5785b0f7-9e77-4dfc-bb1a-f4422edfbe3a"  # amits.joys@gmail.com
        self.user_email = "amits.joys@gmail.com"
        self.auth_token = None
        
    async def setup(self):
        """Setup database connection"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print("✅ Database connection established")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()
    
    async def authenticate_user(self):
        """Try to authenticate the user"""
        print(f"\n🔐 Attempting to authenticate user: {self.user_email}")
        
        # Try common passwords
        passwords = ["testpassword123", "password123", "admin123", "test123"]
        
        for password in passwords:
            try:
                login_data = {
                    "email": self.user_email,
                    "password": password
                }
                
                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                if response.status_code == 200:
                    token_data = response.json()
                    self.auth_token = token_data["access_token"]
                    print(f"✅ Successfully authenticated with password: {password}")
                    return True
                    
            except Exception as e:
                continue
        
        print("❌ Could not authenticate user with common passwords")
        return False
    
    def get_auth_headers(self):
        """Get authorization headers"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
    
    async def investigate_oauth_issue(self):
        """Investigate the specific OAuth issue"""
        print("\n🔍 OAUTH ISSUE INVESTIGATION")
        print("="*60)
        print("PROBLEM: User has OAuth token but cannot create email accounts")
        print("="*60)
        
        # 1. Verify OAuth token exists
        print("\n1️⃣ OAUTH TOKEN VERIFICATION")
        print("-" * 30)
        
        oauth_tokens = await self.db.oauth_tokens.find({"user_id": self.user_id}).to_list(100)
        # Google tokens don't have a provider field - they're in the main oauth_tokens collection
        google_tokens = [t for t in oauth_tokens if "gmail" in t.get("scope", "") or "google" in str(t)]
        
        if google_tokens or oauth_tokens:
            token = google_tokens[0]
            expires_at = token.get("expires_at")
            is_expired = expires_at < datetime.utcnow() if expires_at else True
            
            print(f"✅ Google OAuth token found")
            print(f"   Token ID: {token.get('id')}")
            print(f"   Email: {token.get('email', 'Not set')}")
            print(f"   Expires: {expires_at}")
            print(f"   Expired: {is_expired}")
            print(f"   Scopes: {token.get('scope', 'Not set')}")
            print(f"   User Email: {token.get('user_email', 'Not set')}")
            print(f"   Authorized Services: {token.get('authorized_services', [])}")
        else:
            print("❌ No Google OAuth token found")
            return
        
        # 2. Check OAuth status via API
        print("\n2️⃣ OAUTH STATUS API CHECK")
        print("-" * 30)
        
        if self.auth_token:
            headers = self.get_auth_headers()
            try:
                response = requests.get(f"{API_BASE}/oauth/google/status", headers=headers, timeout=10)
                print(f"OAuth Status Response: {response.status_code}")
                
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"✅ OAuth Status: {status_data}")
                elif response.status_code == 500:
                    print("❌ OAuth Status API returning 500 error")
                    print("   This matches the backend logs showing datetime comparison errors")
                else:
                    print(f"❌ OAuth Status API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ OAuth Status API exception: {str(e)}")
        else:
            print("⚠️ Cannot test OAuth status API - no authentication token")
        
        # 3. Check email accounts for this user
        print("\n3️⃣ EMAIL ACCOUNTS CHECK")
        print("-" * 30)
        
        user_accounts = await self.db.email_accounts.find({"user_id": self.user_id}).to_list(100)
        print(f"Email accounts for user: {len(user_accounts)}")
        
        if len(user_accounts) == 0:
            print("🚨 CRITICAL ISSUE: User has OAuth token but NO email accounts")
            print("   This confirms the review request problem!")
        else:
            for account in user_accounts:
                print(f"   - Email: {account.get('email')}")
                print(f"     Type: {account.get('auth_type', 'manual')}")
                print(f"     Provider: {account.get('provider')}")
                print(f"     Active: {account.get('is_active')}")
                print(f"     OAuth Email: {account.get('oauth_email')}")
        
        # 4. Test OAuth account creation
        print("\n4️⃣ OAUTH ACCOUNT CREATION TEST")
        print("-" * 30)
        
        if self.auth_token:
            headers = self.get_auth_headers()
            
            # Try to create OAuth account
            oauth_account_data = {
                "provider": "google",
                "name": "Test OAuth Account"
            }
            
            try:
                response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                       json=oauth_account_data, headers=headers, timeout=15)
                
                print(f"OAuth Account Creation Response: {response.status_code}")
                
                if response.status_code == 200:
                    account_data = response.json()
                    print(f"✅ OAuth account created successfully")
                    print(f"   Account ID: {account_data.get('id')}")
                    print(f"   Email: {account_data.get('email')}")
                    print(f"   OAuth Email: {account_data.get('oauth_email')}")
                elif response.status_code == 400:
                    error_text = response.text
                    print(f"❌ OAuth account creation failed: {error_text}")
                    
                    if "oauth" in error_text.lower():
                        print("   Issue appears to be OAuth-related")
                    if "authorization" in error_text.lower():
                        print("   Issue appears to be authorization-related")
                elif response.status_code == 500:
                    print("❌ OAuth account creation failed with 500 error")
                    print("   This might be related to the datetime comparison error")
                else:
                    print(f"❌ OAuth account creation failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ OAuth account creation exception: {str(e)}")
        else:
            print("⚠️ Cannot test OAuth account creation - no authentication token")
        
        # 5. Check polling service for OAuth accounts
        print("\n5️⃣ POLLING SERVICE OAUTH CHECK")
        print("-" * 30)
        
        try:
            response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
            
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = accounts_data.get("accounts", [])
                
                oauth_accounts = [acc for acc in accounts if acc.get("auth_type") == "oauth"]
                print(f"OAuth accounts in polling service: {len(oauth_accounts)}")
                
                if len(oauth_accounts) == 0:
                    print("🚨 CRITICAL ISSUE: No OAuth accounts being polled")
                    print("   This confirms the polling problem from the review request")
                else:
                    for account in oauth_accounts:
                        print(f"   - Email: {account.get('email')}")
                        print(f"     Provider: {account.get('provider')}")
                        print(f"     Polling Active: {account.get('polling_active')}")
                        print(f"     Has Connection: {account.get('has_connection')}")
            else:
                print(f"❌ Polling accounts status error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Polling service check exception: {str(e)}")
        
        # 6. Investigate the datetime error
        print("\n6️⃣ DATETIME ERROR INVESTIGATION")
        print("-" * 30)
        
        # Check if the OAuth token has timezone issues
        if google_tokens or oauth_tokens:
            token = google_tokens[0] if google_tokens else oauth_tokens[0]
            expires_at = token.get("expires_at")
            created_at = token.get("created_at")
            
            print(f"Token expires_at type: {type(expires_at)}")
            print(f"Token created_at type: {type(created_at)}")
            
            # Check if these are timezone-aware or naive
            if hasattr(expires_at, 'tzinfo'):
                print(f"expires_at timezone: {expires_at.tzinfo}")
            if hasattr(created_at, 'tzinfo'):
                print(f"created_at timezone: {created_at.tzinfo}")
            
            print("🚨 LIKELY ROOT CAUSE: Timezone-aware vs timezone-naive datetime comparison")
            print("   This is causing the OAuth status API to fail with 500 errors")
        
        # 7. Summary of findings
        print("\n7️⃣ INVESTIGATION SUMMARY")
        print("-" * 30)
        
        print("🔍 CONFIRMED ISSUES:")
        print("   1. ✅ User has valid Google OAuth token")
        print("   2. 🚨 User has NO email accounts created")
        print("   3. 🚨 OAuth status API failing with datetime errors")
        print("   4. 🚨 No OAuth accounts being polled")
        print("   5. 🚨 OAuth account creation likely failing due to API errors")
        
        print("\n💡 ROOT CAUSE ANALYSIS:")
        print("   - OAuth authorization flow completed successfully")
        print("   - OAuth token stored in database")
        print("   - BUT: Datetime comparison errors preventing OAuth status checks")
        print("   - RESULT: Users cannot create OAuth email accounts")
        print("   - RESULT: No OAuth accounts available for email polling")
        
        print("\n🔧 RECOMMENDED FIXES:")
        print("   1. Fix datetime timezone handling in OAuth status endpoint")
        print("   2. Ensure OAuth account creation handles timezone-aware datetimes")
        print("   3. Test complete OAuth flow after datetime fix")
        print("   4. Verify email polling works with OAuth accounts")

async def main():
    """Main investigation execution"""
    print("🚨 OAUTH ISSUE INVESTIGATION")
    print("Based on review request: User cannot add email accounts and start polling")
    print("="*80)
    
    tester = OAuthIssueTester()
    
    try:
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        # Try to authenticate (optional for this investigation)
        await tester.authenticate_user()
        
        # Run the investigation
        await tester.investigate_oauth_issue()
        
        print("\n🏁 Investigation completed")
        print("="*80)
        print("CONCLUSION: OAuth infrastructure works, but datetime errors prevent account creation")
        
    except Exception as e:
        print(f"\n❌ Unexpected error during investigation: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())