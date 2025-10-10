#!/usr/bin/env python3
"""
Focused Google OAuth Investigation for user amits.joys@gmail.com
Based on the review request findings
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
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-sync-fix-2.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class FocusedOAuthTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.user_id = "5785b0f7-9e77-4dfc-bb1a-f4422edfbe3a"  # amits.joys@gmail.com
        self.user_email = "amits.joys@gmail.com"
        
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
    
    def log_result(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
    
    async def investigate_oauth_flow(self):
        """Comprehensive OAuth Flow Investigation"""
        print("\n🔍 COMPREHENSIVE GOOGLE OAUTH FLOW INVESTIGATION")
        print("="*60)
        print(f"Target User: {self.user_email} (ID: {self.user_id})")
        print("="*60)
        
        # 1. OAuth Initiation Test
        print("\n1️⃣ OAUTH INITIATION TEST")
        print("-" * 30)
        
        try:
            # Test without authentication first (should fail)
            response = requests.post(f"{API_BASE}/oauth/google/authorize", 
                                   json={"scopes": ["email", "calendar"]}, timeout=10)
            
            if response.status_code == 403:
                self.log_result("OAuth Initiation (Unauthenticated)", "✅ EXPECTED", 
                              f"Status: {response.status_code} - Authentication required")
            else:
                self.log_result("OAuth Initiation (Unauthenticated)", "❌ UNEXPECTED", 
                              f"Status: {response.status_code} - Should require auth")
            
            # Check if endpoint exists
            endpoint_exists = response.status_code != 404
            self.log_result("OAuth Endpoint Exists", "✅ PASS" if endpoint_exists else "❌ FAIL",
                          f"Endpoint accessible: {endpoint_exists}")
            
        except Exception as e:
            self.log_result("OAuth Initiation Test", "❌ ERROR", f"Exception: {str(e)}")
        
        # 2. OAuth Status Check
        print("\n2️⃣ OAUTH STATUS CHECK")
        print("-" * 30)
        
        try:
            response = requests.get(f"{API_BASE}/oauth/google/status", timeout=10)
            
            if response.status_code == 403:
                self.log_result("OAuth Status (Unauthenticated)", "✅ EXPECTED",
                              f"Status: {response.status_code} - Authentication required")
            else:
                self.log_result("OAuth Status (Unauthenticated)", "❌ UNEXPECTED",
                              f"Status: {response.status_code} - Should require auth")
                
        except Exception as e:
            self.log_result("OAuth Status Check", "❌ ERROR", f"Exception: {str(e)}")
        
        # 3. Database State Investigation
        print("\n3️⃣ DATABASE STATE INVESTIGATION")
        print("-" * 30)
        
        try:
            # Check user exists
            user_doc = await self.db.users.find_one({"id": self.user_id})
            user_exists = user_doc is not None
            self.log_result("Target User Exists", "✅ PASS" if user_exists else "❌ FAIL",
                          f"User {self.user_email}: {user_exists}")
            
            # Check OAuth tokens for this user
            oauth_tokens = await self.db.oauth_tokens.find({"user_id": self.user_id}).to_list(100)
            google_tokens = [t for t in oauth_tokens if t.get("provider") == "google"]
            
            self.log_result("Google OAuth Tokens", "ℹ️ INFO",
                          f"Found {len(google_tokens)} Google OAuth tokens for user")
            
            # Check Microsoft OAuth tokens (mentioned in review request)
            microsoft_tokens = await self.db.oauth_tokens_microsoft.find({"user_id": self.user_id}).to_list(100)
            self.log_result("Microsoft OAuth Tokens", "ℹ️ INFO",
                          f"Found {len(microsoft_tokens)} Microsoft OAuth tokens for user")
            
            # Check email accounts for this user
            email_accounts = await self.db.email_accounts.find({"user_id": self.user_id}).to_list(100)
            oauth_accounts = [acc for acc in email_accounts if acc.get("auth_type") == "oauth"]
            
            self.log_result("User Email Accounts", "ℹ️ INFO",
                          f"Total: {len(email_accounts)}, OAuth: {len(oauth_accounts)}")
            
            # Detailed account analysis
            for i, account in enumerate(email_accounts):
                account_type = account.get("auth_type", "manual")
                provider = account.get("provider", "unknown")
                email = account.get("email", "unknown")
                is_active = account.get("is_active", False)
                oauth_email = account.get("oauth_email", "N/A")
                
                self.log_result(f"Account {i+1} Details", "ℹ️ INFO",
                              f"Email: {email}, Type: {account_type}, Provider: {provider}, "
                              f"Active: {is_active}, OAuth Email: {oauth_email}")
            
            # Check OAuth states
            oauth_states = await self.db.oauth_states.find({"user_id": self.user_id}).to_list(100)
            self.log_result("OAuth States", "ℹ️ INFO",
                          f"Found {len(oauth_states)} OAuth states for user")
            
        except Exception as e:
            self.log_result("Database Investigation", "❌ ERROR", f"Exception: {str(e)}")
        
        # 4. OAuth Callback Investigation
        print("\n4️⃣ OAUTH CALLBACK INVESTIGATION")
        print("-" * 30)
        
        try:
            # Test callback endpoint accessibility
            callback_url = f"{API_BASE}/oauth/google/callback"
            
            # Test with no parameters
            response = requests.get(callback_url, timeout=10)
            callback_accessible = response.status_code != 404
            
            self.log_result("OAuth Callback Endpoint", "✅ PASS" if callback_accessible else "❌ FAIL",
                          f"Endpoint accessible: {callback_accessible}, Status: {response.status_code}")
            
            # Test with error parameter (simulating OAuth error)
            response = requests.get(f"{callback_url}?error=access_denied", timeout=10)
            error_handled = response.status_code in [400, 401, 422]
            
            self.log_result("OAuth Error Handling", "✅ PASS" if error_handled else "❌ FAIL",
                          f"Error parameter handled: {error_handled}, Status: {response.status_code}")
            
        except Exception as e:
            self.log_result("OAuth Callback Investigation", "❌ ERROR", f"Exception: {str(e)}")
        
        # 5. Account Creation Investigation
        print("\n5️⃣ ACCOUNT CREATION INVESTIGATION")
        print("-" * 30)
        
        try:
            # Test OAuth account creation endpoint
            response = requests.post(f"{API_BASE}/email-accounts/oauth", 
                                   json={"provider": "google"}, timeout=10)
            
            if response.status_code == 403:
                self.log_result("OAuth Account Creation", "✅ EXPECTED",
                              f"Status: {response.status_code} - Authentication required")
            else:
                self.log_result("OAuth Account Creation", "ℹ️ INFO",
                              f"Status: {response.status_code}, Response: {response.text[:100]}")
            
            # Check account limits function
            try:
                from server import validate_account_limits
                self.log_result("Account Limits Function", "✅ PASS", "Function exists and importable")
            except ImportError:
                self.log_result("Account Limits Function", "❌ FAIL", "Function not found")
            
        except Exception as e:
            self.log_result("Account Creation Investigation", "❌ ERROR", f"Exception: {str(e)}")
        
        # 6. Email Polling Investigation
        print("\n6️⃣ EMAIL POLLING INVESTIGATION")
        print("-" * 30)
        
        try:
            # Check polling service status
            response = requests.get(f"{API_BASE}/polling/status", timeout=10)
            
            if response.status_code == 200:
                polling_data = response.json()
                service_running = polling_data.get("status") == "running"
                active_connections = polling_data.get("active_connections", 0)
                
                self.log_result("Polling Service Status", "✅ PASS" if service_running else "❌ FAIL",
                              f"Running: {service_running}, Connections: {active_connections}")
            else:
                self.log_result("Polling Service Status", "❌ FAIL",
                              f"Status: {response.status_code}")
            
            # Check accounts polling status
            response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
            
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = accounts_data.get("accounts", [])
                
                # Look for OAuth routing issues (key finding from review request)
                oauth_routing_issues = []
                
                for account in accounts:
                    email = account.get("email", "")
                    auth_type = account.get("auth_type", "manual")
                    provider = account.get("provider", "")
                    
                    # Check for Microsoft accounts that might be routed to Google
                    if auth_type == "oauth":
                        if ("outlook" in email.lower() or "hotmail" in email.lower() or 
                            "live.com" in email.lower() or "onmicrosoft.com" in email.lower()):
                            if provider.lower() not in ["microsoft", "outlook"]:
                                oauth_routing_issues.append(f"{email} -> {provider}")
                
                self.log_result("OAuth Routing Analysis", 
                              "🚨 ISSUE" if oauth_routing_issues else "✅ PASS",
                              f"Routing issues found: {len(oauth_routing_issues)}")
                
                if oauth_routing_issues:
                    for issue in oauth_routing_issues:
                        print(f"   🚨 Routing Issue: {issue}")
                
            else:
                self.log_result("Accounts Polling Status", "❌ FAIL",
                              f"Status: {response.status_code}")
            
        except Exception as e:
            self.log_result("Email Polling Investigation", "❌ ERROR", f"Exception: {str(e)}")
        
        # 7. Configuration Verification
        print("\n7️⃣ CONFIGURATION VERIFICATION")
        print("-" * 30)
        
        try:
            # Check Google OAuth configuration
            google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
            google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
            google_redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')
            
            config_complete = all([google_client_id, google_client_secret, google_redirect_uri])
            
            self.log_result("Google OAuth Config", "✅ PASS" if config_complete else "❌ FAIL",
                          f"Client ID: {bool(google_client_id)}, Secret: {bool(google_client_secret)}, "
                          f"Redirect URI: {bool(google_redirect_uri)}")
            
            # Verify redirect URI format
            expected_callback = "/oauth/google/callback"
            expected_domain = "google-sync-app.preview.emergentagent.com"
            
            if google_redirect_uri:
                correct_format = (expected_callback in google_redirect_uri and 
                                expected_domain in google_redirect_uri)
                self.log_result("Redirect URI Format", "✅ PASS" if correct_format else "❌ FAIL",
                              f"URI: {google_redirect_uri}")
            
            # Check Microsoft OAuth configuration (for comparison)
            microsoft_client_id = os.environ.get('MICROSOFT_CLIENT_ID')
            microsoft_client_secret = os.environ.get('MICROSOFT_CLIENT_SECRET')
            
            self.log_result("Microsoft OAuth Config", "ℹ️ INFO",
                          f"Client ID: {bool(microsoft_client_id)}, Secret: {bool(microsoft_client_secret)}")
            
        except Exception as e:
            self.log_result("Configuration Verification", "❌ ERROR", f"Exception: {str(e)}")
    
    def print_investigation_summary(self):
        """Print investigation summary"""
        print("\n" + "="*80)
        print("🔍 GOOGLE OAUTH INVESTIGATION SUMMARY")
        print("="*80)
        
        # Categorize results
        passes = [r for r in self.test_results if "✅ PASS" in r["status"]]
        fails = [r for r in self.test_results if "❌ FAIL" in r["status"]]
        errors = [r for r in self.test_results if "❌ ERROR" in r["status"]]
        issues = [r for r in self.test_results if "🚨 ISSUE" in r["status"]]
        info = [r for r in self.test_results if "ℹ️ INFO" in r["status"]]
        expected = [r for r in self.test_results if "✅ EXPECTED" in r["status"]]
        
        print(f"📊 RESULTS BREAKDOWN:")
        print(f"   ✅ Passes: {len(passes)}")
        print(f"   ❌ Failures: {len(fails)}")
        print(f"   ❌ Errors: {len(errors)}")
        print(f"   🚨 Issues: {len(issues)}")
        print(f"   ✅ Expected: {len(expected)}")
        print(f"   ℹ️ Info: {len(info)}")
        
        print(f"\n🎯 KEY FINDINGS:")
        
        # Critical issues
        if issues:
            print("   🚨 CRITICAL ISSUES FOUND:")
            for issue in issues:
                print(f"      - {issue['test']}: {issue['details']}")
        
        # Authentication requirements
        auth_required = len([r for r in expected if "Authentication required" in r["details"]])
        if auth_required > 0:
            print(f"   🔐 OAuth endpoints properly require authentication ({auth_required} endpoints)")
        
        # Configuration status
        config_passes = len([r for r in passes if "Config" in r["test"]])
        if config_passes > 0:
            print(f"   ⚙️ OAuth configuration appears correct ({config_passes} checks passed)")
        
        # Database state
        db_info = len([r for r in info if "Database" in r["test"] or "Account" in r["test"]])
        if db_info > 0:
            print(f"   🗄️ Database state analyzed ({db_info} items checked)")
        
        print(f"\n💡 INVESTIGATION CONCLUSIONS:")
        
        if issues:
            print("   🚨 OAuth routing issues detected - matches review request findings")
            print("   📋 Recommendation: Fix OAuth provider routing logic")
        
        if len(fails) == 0 and len(errors) == 0:
            print("   ✅ No critical failures detected in OAuth infrastructure")
        
        if len(expected) > 0:
            print("   🔐 OAuth security properly implemented (authentication required)")
        
        print(f"\n🔗 NEXT STEPS:")
        print("   1. Review OAuth routing logic for Microsoft vs Google accounts")
        print("   2. Test complete OAuth flow with authenticated user")
        print("   3. Verify email polling service handles OAuth accounts correctly")
        print("   4. Check backend logs for specific OAuth errors")
        
        return len(passes), len(fails) + len(errors) + len(issues)

async def main():
    """Main investigation execution"""
    print("🔍 FOCUSED GOOGLE OAUTH INVESTIGATION")
    print("Based on review request: 'User has added redirect URL and scopes to Google Cloud Console but still cannot add email accounts and start polling'")
    print("="*80)
    
    tester = FocusedOAuthTester()
    
    try:
        if not await tester.setup():
            print("❌ Setup failed, exiting...")
            return
        
        await tester.investigate_oauth_flow()
        
        passes, issues = tester.print_investigation_summary()
        
        exit_code = 0 if issues == 0 else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Investigation interrupted by user")
        exit_code = 130
    except Exception as e:
        print(f"\n❌ Unexpected error during investigation: {str(e)}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        await tester.cleanup()
    
    print(f"\n🏁 OAuth Investigation completed with exit code: {exit_code}")
    return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)