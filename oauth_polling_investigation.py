#!/usr/bin/env python3
"""
OAuth Polling Investigation for Email Assistant System
Investigates why email polling is not starting for newly added Outlook OAuth account
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from email_services import EmailPollingService, EmailConnection
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://auth-calendar-fix.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class OAuthPollingInvestigator:
    def __init__(self):
        self.client = None
        self.db = None
        self.investigation_results = []
        self.polling_service = None
        
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
        if self.polling_service:
            self.polling_service.stop_polling()
        if self.client:
            self.client.close()
    
    def log_investigation_result(self, test_name: str, status: str, details: str = ""):
        """Log investigation result"""
        result = {
            "investigation": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.investigation_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    async def investigate_oauth_account_creation(self):
        """1. Verify OAuth Account Creation - Check if Outlook account was properly created"""
        print("\n🔍 INVESTIGATION 1: OAuth Account Creation")
        
        try:
            # Search for the specific Outlook OAuth account
            target_email = "amits.joys@outlook.com"
            authenticating_user = "amits.joys@gmail.com"
            
            # Check email_accounts collection
            oauth_account = await self.db.email_accounts.find_one({
                "email": target_email,
                "auth_type": "oauth"
            })
            
            if oauth_account:
                self.log_investigation_result(
                    "OAuth Account Found in Database", 
                    "✅ SUCCESS",
                    f"Account ID: {oauth_account['id']}, OAuth Email: {oauth_account.get('oauth_email')}, "
                    f"Use OAuth: {oauth_account.get('use_oauth')}, Token ID: {oauth_account.get('oauth_token_id')}, "
                    f"Active: {oauth_account.get('is_active')}, Provider: {oauth_account.get('provider')}"
                )
                
                # Check OAuth token details
                if oauth_account.get('oauth_token_id'):
                    oauth_token = await self.db.oauth_tokens.find_one({
                        "id": oauth_account['oauth_token_id']
                    })
                    
                    if oauth_token:
                        self.log_investigation_result(
                            "OAuth Token Found",
                            "✅ SUCCESS", 
                            f"Provider: {oauth_token.get('provider')}, Email: {oauth_token.get('email')}, "
                            f"Expires: {oauth_token.get('expires_at')}, Scope: {oauth_token.get('scope')}"
                        )
                    else:
                        self.log_investigation_result(
                            "OAuth Token Missing",
                            "❌ CRITICAL ISSUE",
                            f"Token ID {oauth_account['oauth_token_id']} not found in oauth_tokens collection"
                        )
                else:
                    self.log_investigation_result(
                        "OAuth Token ID Missing",
                        "❌ CRITICAL ISSUE",
                        "Account has no oauth_token_id field"
                    )
                
                return oauth_account
            else:
                # Check if account exists with different auth_type
                any_account = await self.db.email_accounts.find_one({"email": target_email})
                if any_account:
                    self.log_investigation_result(
                        "Account Found with Wrong Auth Type",
                        "⚠️ WARNING",
                        f"Account exists but auth_type is '{any_account.get('auth_type')}', not 'oauth'"
                    )
                else:
                    self.log_investigation_result(
                        "OAuth Account Not Found",
                        "❌ CRITICAL ISSUE",
                        f"No account found for {target_email} in email_accounts collection"
                    )
                return None
                
        except Exception as e:
            self.log_investigation_result(
                "OAuth Account Creation Check",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
            return None
    
    async def investigate_polling_service_status(self):
        """2. Check Polling Service Status - Verify if polling service is running"""
        print("\n📡 INVESTIGATION 2: Polling Service Status")
        
        try:
            # Check API endpoint
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                if response.status_code == 200:
                    status_data = response.json()
                    self.log_investigation_result(
                        "Polling Service API Status",
                        "✅ SUCCESS",
                        f"Status: {status_data.get('status')}, Active Connections: {status_data.get('active_connections', 0)}"
                    )
                else:
                    self.log_investigation_result(
                        "Polling Service API Status",
                        "❌ ISSUE",
                        f"HTTP {response.status_code}: {response.text}"
                    )
            except Exception as e:
                self.log_investigation_result(
                    "Polling Service API Status",
                    "❌ ERROR",
                    f"API call failed: {str(e)}"
                )
            
            # Check all accounts polling status
            try:
                response = requests.get(f"{API_BASE}/polling/accounts-status", timeout=10)
                if response.status_code == 200:
                    accounts_status = response.json()
                    polling_service_running = accounts_status.get('polling_service_running', False)
                    accounts = accounts_status.get('accounts', [])
                    
                    self.log_investigation_result(
                        "All Accounts Polling Status",
                        "✅ SUCCESS" if polling_service_running else "⚠️ WARNING",
                        f"Service Running: {polling_service_running}, Total Accounts: {len(accounts)}"
                    )
                    
                    # Check specifically for OAuth accounts
                    oauth_accounts = [acc for acc in accounts if 'oauth' in acc.get('name', '').lower() or 'outlook' in acc.get('email', '').lower()]
                    if oauth_accounts:
                        for acc in oauth_accounts:
                            self.log_investigation_result(
                                f"OAuth Account Polling Status",
                                "✅ FOUND" if acc.get('polling_active') else "❌ INACTIVE",
                                f"Email: {acc.get('email')}, Active: {acc.get('polling_active')}, "
                                f"Has Connection: {acc.get('has_connection')}, Last Polled: {acc.get('last_polled')}"
                            )
                    else:
                        self.log_investigation_result(
                            "OAuth Accounts in Polling Status",
                            "❌ NOT FOUND",
                            "No OAuth or Outlook accounts found in polling status"
                        )
                        
                else:
                    self.log_investigation_result(
                        "All Accounts Polling Status",
                        "❌ ISSUE",
                        f"HTTP {response.status_code}: {response.text}"
                    )
            except Exception as e:
                self.log_investigation_result(
                    "All Accounts Polling Status",
                    "❌ ERROR",
                    f"API call failed: {str(e)}"
                )
            
            # Initialize direct polling service for deeper investigation
            try:
                self.polling_service = EmailPollingService(MONGO_URL, DB_NAME)
                self.log_investigation_result(
                    "Direct Polling Service Initialization",
                    "✅ SUCCESS",
                    f"Service initialized, Running: {self.polling_service.is_running}"
                )
            except Exception as e:
                self.log_investigation_result(
                    "Direct Polling Service Initialization",
                    "❌ ERROR",
                    f"Failed to initialize: {str(e)}"
                )
                
        except Exception as e:
            self.log_investigation_result(
                "Polling Service Status Investigation",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
    
    async def investigate_oauth_token_validation(self, oauth_account):
        """3. OAuth Token Validation - Test if Microsoft OAuth tokens are valid"""
        print("\n🔐 INVESTIGATION 3: OAuth Token Validation")
        
        if not oauth_account:
            self.log_investigation_result(
                "OAuth Token Validation",
                "❌ SKIPPED",
                "No OAuth account found to validate"
            )
            return
        
        try:
            # Get OAuth token from database
            oauth_token_id = oauth_account.get('oauth_token_id')
            if not oauth_token_id:
                self.log_investigation_result(
                    "OAuth Token Validation",
                    "❌ CRITICAL ISSUE",
                    "Account has no oauth_token_id"
                )
                return
            
            oauth_token = await self.db.oauth_tokens.find_one({"id": oauth_token_id})
            if not oauth_token:
                self.log_investigation_result(
                    "OAuth Token Validation",
                    "❌ CRITICAL ISSUE",
                    f"OAuth token {oauth_token_id} not found in database"
                )
                return
            
            # Check token expiration
            expires_at = oauth_token.get('expires_at')
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo if expires_at.tzinfo else None)
                if expires_at < now:
                    self.log_investigation_result(
                        "OAuth Token Expiration Check",
                        "❌ CRITICAL ISSUE",
                        f"Token expired at {expires_at}, current time: {now}"
                    )
                else:
                    self.log_investigation_result(
                        "OAuth Token Expiration Check",
                        "✅ SUCCESS",
                        f"Token valid until {expires_at}, current time: {now}"
                    )
            else:
                self.log_investigation_result(
                    "OAuth Token Expiration Check",
                    "⚠️ WARNING",
                    "No expiration date found in token"
                )
            
            # Test Microsoft Graph API access
            try:
                access_token = oauth_token.get('access_token')
                if access_token:
                    # Test basic Graph API call
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    # Test user profile access
                    response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10)
                    if response.status_code == 200:
                        user_data = response.json()
                        self.log_investigation_result(
                            "Microsoft Graph API Access Test",
                            "✅ SUCCESS",
                            f"User: {user_data.get('displayName')}, Email: {user_data.get('mail') or user_data.get('userPrincipalName')}"
                        )
                        
                        # Test mail access
                        mail_response = requests.get('https://graph.microsoft.com/v1.0/me/messages?$top=1', headers=headers, timeout=10)
                        if mail_response.status_code == 200:
                            self.log_investigation_result(
                                "Microsoft Graph Mail API Access Test",
                                "✅ SUCCESS",
                                f"Mail API accessible, response: {len(mail_response.json().get('value', []))} messages"
                            )
                        else:
                            self.log_investigation_result(
                                "Microsoft Graph Mail API Access Test",
                                "❌ ISSUE",
                                f"HTTP {mail_response.status_code}: {mail_response.text[:200]}"
                            )
                    else:
                        self.log_investigation_result(
                            "Microsoft Graph API Access Test",
                            "❌ CRITICAL ISSUE",
                            f"HTTP {response.status_code}: {response.text[:200]}"
                        )
                else:
                    self.log_investigation_result(
                        "Microsoft Graph API Access Test",
                        "❌ CRITICAL ISSUE",
                        "No access_token found in OAuth token"
                    )
                    
            except Exception as e:
                self.log_investigation_result(
                    "Microsoft Graph API Access Test",
                    "❌ ERROR",
                    f"API test failed: {str(e)}"
                )
                
        except Exception as e:
            self.log_investigation_result(
                "OAuth Token Validation",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
    
    async def investigate_polling_logic_oauth_support(self, oauth_account):
        """4. Polling Logic for OAuth - Check if polling logic handles OAuth accounts"""
        print("\n🔄 INVESTIGATION 4: Polling Logic OAuth Support")
        
        if not oauth_account:
            self.log_investigation_result(
                "Polling Logic OAuth Support",
                "❌ SKIPPED",
                "No OAuth account found to test"
            )
            return
        
        try:
            # Test if polling service can handle OAuth account
            if self.polling_service:
                try:
                    # Attempt to poll the OAuth account
                    await self.polling_service._poll_account(oauth_account)
                    
                    # Check if connection was created
                    account_id = oauth_account['id']
                    has_connection = account_id in self.polling_service.connections
                    
                    self.log_investigation_result(
                        "OAuth Account Polling Test",
                        "✅ SUCCESS" if has_connection else "❌ FAILED",
                        f"Connection created: {has_connection}, Account ID: {account_id}"
                    )
                    
                    if has_connection:
                        connection = self.polling_service.connections[account_id]
                        # Check connection type and OAuth support
                        is_oauth_connection = hasattr(connection, 'use_oauth') and connection.use_oauth
                        self.log_investigation_result(
                            "OAuth Connection Type Check",
                            "✅ SUCCESS" if is_oauth_connection else "⚠️ WARNING",
                            f"Connection uses OAuth: {is_oauth_connection}, Connection type: {type(connection).__name__}"
                        )
                    
                except Exception as e:
                    self.log_investigation_result(
                        "OAuth Account Polling Test",
                        "❌ CRITICAL ISSUE",
                        f"Polling failed: {str(e)}"
                    )
            else:
                self.log_investigation_result(
                    "OAuth Account Polling Test",
                    "❌ SKIPPED",
                    "Polling service not initialized"
                )
            
            # Check EmailConnection OAuth support
            try:
                connection = EmailConnection(oauth_account)
                oauth_supported = hasattr(connection, 'use_oauth') and connection.use_oauth
                
                self.log_investigation_result(
                    "EmailConnection OAuth Support",
                    "✅ SUCCESS" if oauth_supported else "❌ CRITICAL ISSUE",
                    f"OAuth support: {oauth_supported}, Use OAuth: {getattr(connection, 'use_oauth', False)}"
                )
                
                # Test OAuth connection method
                if oauth_supported:
                    try:
                        # This might fail but we want to see how it fails
                        connect_result = connection.connect_imap()
                        self.log_investigation_result(
                            "OAuth IMAP Connection Test",
                            "✅ SUCCESS" if connect_result else "❌ FAILED",
                            f"Connection result: {connect_result}"
                        )
                    except Exception as e:
                        self.log_investigation_result(
                            "OAuth IMAP Connection Test",
                            "❌ ERROR",
                            f"Connection error: {str(e)}"
                        )
                
            except Exception as e:
                self.log_investigation_result(
                    "EmailConnection OAuth Support",
                    "❌ ERROR",
                    f"Exception: {str(e)}"
                )
                
        except Exception as e:
            self.log_investigation_result(
                "Polling Logic OAuth Support",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
    
    async def investigate_oauth_email_service_integration(self, oauth_account):
        """5. OAuth Email Service Integration - Test Microsoft email service"""
        print("\n📧 INVESTIGATION 5: OAuth Email Service Integration")
        
        if not oauth_account:
            self.log_investigation_result(
                "OAuth Email Service Integration",
                "❌ SKIPPED",
                "No OAuth account found to test"
            )
            return
        
        try:
            # Test Microsoft Mail Service integration
            try:
                from microsoft_services import MicrosoftMailService
                
                # Get OAuth token
                oauth_token_id = oauth_account.get('oauth_token_id')
                if oauth_token_id:
                    oauth_token = await self.db.oauth_tokens.find_one({"id": oauth_token_id})
                    if oauth_token:
                        # Initialize Microsoft Mail Service
                        mail_service = MicrosoftMailService(oauth_token)
                        
                        self.log_investigation_result(
                            "Microsoft Mail Service Initialization",
                            "✅ SUCCESS",
                            f"Service initialized for token: {oauth_token_id}"
                        )
                        
                        # Test email retrieval
                        try:
                            messages = await mail_service.get_messages(max_results=1)
                            self.log_investigation_result(
                                "Microsoft Mail Service Email Retrieval",
                                "✅ SUCCESS",
                                f"Retrieved {len(messages)} messages"
                            )
                        except Exception as e:
                            self.log_investigation_result(
                                "Microsoft Mail Service Email Retrieval",
                                "❌ CRITICAL ISSUE",
                                f"Email retrieval failed: {str(e)}"
                            )
                    else:
                        self.log_investigation_result(
                            "Microsoft Mail Service Integration",
                            "❌ CRITICAL ISSUE",
                            f"OAuth token {oauth_token_id} not found"
                        )
                else:
                    self.log_investigation_result(
                        "Microsoft Mail Service Integration",
                        "❌ CRITICAL ISSUE",
                        "No oauth_token_id in account"
                    )
                    
            except ImportError as e:
                self.log_investigation_result(
                    "Microsoft Mail Service Integration",
                    "❌ CRITICAL ISSUE",
                    f"Microsoft services not available: {str(e)}"
                )
            except Exception as e:
                self.log_investigation_result(
                    "Microsoft Mail Service Integration",
                    "❌ ERROR",
                    f"Service integration error: {str(e)}"
                )
                
        except Exception as e:
            self.log_investigation_result(
                "OAuth Email Service Integration",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
    
    async def investigate_background_service_logs(self):
        """6. Background Service Logs - Check for errors in background services"""
        print("\n📋 INVESTIGATION 6: Background Service Logs")
        
        try:
            # Check recent emails for processing status
            recent_emails = await self.db.emails.find().sort("created_at", -1).limit(10).to_list(10)
            
            self.log_investigation_result(
                "Recent Email Processing Status",
                "✅ INFO",
                f"Found {len(recent_emails)} recent emails"
            )
            
            # Analyze email statuses
            status_counts = {}
            oauth_emails = []
            
            for email in recent_emails:
                status = email.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Check if this is from an OAuth account
                account_id = email.get('account_id')
                if account_id:
                    account = await self.db.email_accounts.find_one({"id": account_id})
                    if account and account.get('auth_type') == 'oauth':
                        oauth_emails.append(email)
            
            self.log_investigation_result(
                "Email Status Distribution",
                "✅ INFO",
                f"Status counts: {status_counts}"
            )
            
            self.log_investigation_result(
                "OAuth Account Emails",
                "✅ INFO" if oauth_emails else "⚠️ WARNING",
                f"Found {len(oauth_emails)} emails from OAuth accounts"
            )
            
            # Check for stuck or failed emails
            stuck_statuses = ['classifying', 'generating_draft', 'validating', 'error']
            stuck_emails = [e for e in recent_emails if e.get('status') in stuck_statuses]
            
            if stuck_emails:
                for email in stuck_emails:
                    self.log_investigation_result(
                        f"Stuck Email Analysis",
                        "⚠️ WARNING",
                        f"Email ID: {email['id']}, Status: {email.get('status')}, "
                        f"Subject: {email.get('subject', 'N/A')[:50]}, "
                        f"Error: {email.get('error', 'None')}"
                    )
            else:
                self.log_investigation_result(
                    "Stuck Email Analysis",
                    "✅ SUCCESS",
                    "No stuck emails found"
                )
            
            # Check background task queues if RQ is available
            try:
                from tasks import get_queue_stats
                queue_stats = get_queue_stats()
                
                self.log_investigation_result(
                    "Background Queue Status",
                    "✅ SUCCESS",
                    f"Queue stats: {queue_stats}"
                )
            except Exception as e:
                self.log_investigation_result(
                    "Background Queue Status",
                    "⚠️ WARNING",
                    f"Queue stats unavailable: {str(e)}"
                )
                
        except Exception as e:
            self.log_investigation_result(
                "Background Service Logs",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
    
    async def investigate_account_active_status(self, oauth_account):
        """7. Account Status - Verify OAuth account is marked as active"""
        print("\n✅ INVESTIGATION 7: Account Active Status")
        
        if not oauth_account:
            self.log_investigation_result(
                "Account Active Status",
                "❌ SKIPPED",
                "No OAuth account found to check"
            )
            return
        
        try:
            account_id = oauth_account['id']
            is_active = oauth_account.get('is_active', False)
            
            self.log_investigation_result(
                "OAuth Account Active Status",
                "✅ SUCCESS" if is_active else "❌ CRITICAL ISSUE",
                f"Account ID: {account_id}, Active: {is_active}"
            )
            
            # Check last polling time
            last_polled = oauth_account.get('last_polled')
            last_oauth_sync = oauth_account.get('last_oauth_sync')
            
            self.log_investigation_result(
                "OAuth Account Polling History",
                "✅ INFO",
                f"Last Polled: {last_polled}, Last OAuth Sync: {last_oauth_sync}"
            )
            
            # Test account polling control
            try:
                # Test status check via API
                status_data = {"action": "status"}
                response = requests.post(f"{API_BASE}/email-accounts/{account_id}/polling", 
                                       json=status_data, timeout=10)
                
                if response.status_code == 200:
                    polling_status = response.json()
                    self.log_investigation_result(
                        "Account Polling Control API",
                        "✅ SUCCESS",
                        f"Polling Active: {polling_status.get('polling_active')}, "
                        f"Has Connection: {polling_status.get('has_connection')}"
                    )
                else:
                    self.log_investigation_result(
                        "Account Polling Control API",
                        "❌ ISSUE",
                        f"HTTP {response.status_code}: {response.text}"
                    )
                    
            except Exception as e:
                self.log_investigation_result(
                    "Account Polling Control API",
                    "❌ ERROR",
                    f"API call failed: {str(e)}"
                )
            
            # Check if account should be polled based on configuration
            should_be_polled = (
                is_active and 
                oauth_account.get('auth_type') == 'oauth' and
                oauth_account.get('use_oauth', False) and
                oauth_account.get('oauth_token_id')
            )
            
            self.log_investigation_result(
                "Account Should Be Polled Analysis",
                "✅ SUCCESS" if should_be_polled else "❌ CRITICAL ISSUE",
                f"Should be polled: {should_be_polled} (Active: {is_active}, "
                f"OAuth: {oauth_account.get('use_oauth')}, Token: {bool(oauth_account.get('oauth_token_id'))})"
            )
                
        except Exception as e:
            self.log_investigation_result(
                "Account Active Status",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
    
    async def investigate_oauth_email_service_connection(self, oauth_account):
        """8. OAuth Email Service Connection - Test direct connection and email retrieval"""
        print("\n🔌 INVESTIGATION 8: OAuth Email Service Connection")
        
        if not oauth_account:
            self.log_investigation_result(
                "OAuth Email Service Connection",
                "❌ SKIPPED",
                "No OAuth account found to test"
            )
            return
        
        try:
            # Test direct Microsoft Graph API connection
            oauth_token_id = oauth_account.get('oauth_token_id')
            if not oauth_token_id:
                self.log_investigation_result(
                    "OAuth Email Service Connection",
                    "❌ CRITICAL ISSUE",
                    "No OAuth token ID found"
                )
                return
            
            oauth_token = await self.db.oauth_tokens.find_one({"id": oauth_token_id})
            if not oauth_token:
                self.log_investigation_result(
                    "OAuth Email Service Connection",
                    "❌ CRITICAL ISSUE",
                    f"OAuth token {oauth_token_id} not found"
                )
                return
            
            access_token = oauth_token.get('access_token')
            if not access_token:
                self.log_investigation_result(
                    "OAuth Email Service Connection",
                    "❌ CRITICAL ISSUE",
                    "No access token found"
                )
                return
            
            # Test email retrieval via Graph API
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            try:
                # Get recent messages
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=id,subject,from,receivedDateTime,isRead',
                    headers=headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    messages_data = response.json()
                    messages = messages_data.get('value', [])
                    
                    self.log_investigation_result(
                        "Direct Email Retrieval Test",
                        "✅ SUCCESS",
                        f"Retrieved {len(messages)} messages successfully"
                    )
                    
                    # Show sample message info
                    if messages:
                        sample_msg = messages[0]
                        self.log_investigation_result(
                            "Sample Message Analysis",
                            "✅ INFO",
                            f"Subject: {sample_msg.get('subject', 'N/A')[:50]}, "
                            f"From: {sample_msg.get('from', {}).get('emailAddress', {}).get('address', 'N/A')}, "
                            f"Received: {sample_msg.get('receivedDateTime', 'N/A')}"
                        )
                    
                    # Test message content retrieval
                    if messages:
                        msg_id = messages[0]['id']
                        content_response = requests.get(
                            f'https://graph.microsoft.com/v1.0/me/messages/{msg_id}?$select=body,bodyPreview',
                            headers=headers,
                            timeout=10
                        )
                        
                        if content_response.status_code == 200:
                            self.log_investigation_result(
                                "Message Content Retrieval Test",
                                "✅ SUCCESS",
                                f"Content retrieved for message {msg_id[:8]}..."
                            )
                        else:
                            self.log_investigation_result(
                                "Message Content Retrieval Test",
                                "❌ ISSUE",
                                f"HTTP {content_response.status_code}: {content_response.text[:100]}"
                            )
                
                else:
                    self.log_investigation_result(
                        "Direct Email Retrieval Test",
                        "❌ CRITICAL ISSUE",
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )
                    
            except Exception as e:
                self.log_investigation_result(
                    "Direct Email Retrieval Test",
                    "❌ ERROR",
                    f"Email retrieval failed: {str(e)}"
                )
            
            # Test folder access (Inbox)
            try:
                folders_response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/mailFolders?$select=id,displayName,totalItemCount,unreadItemCount',
                    headers=headers,
                    timeout=10
                )
                
                if folders_response.status_code == 200:
                    folders_data = folders_response.json()
                    folders = folders_data.get('value', [])
                    
                    inbox_folder = next((f for f in folders if f.get('displayName', '').lower() == 'inbox'), None)
                    
                    if inbox_folder:
                        self.log_investigation_result(
                            "Inbox Folder Access Test",
                            "✅ SUCCESS",
                            f"Inbox found - Total: {inbox_folder.get('totalItemCount')}, "
                            f"Unread: {inbox_folder.get('unreadItemCount')}"
                        )
                    else:
                        self.log_investigation_result(
                            "Inbox Folder Access Test",
                            "⚠️ WARNING",
                            f"Inbox not found in {len(folders)} folders"
                        )
                else:
                    self.log_investigation_result(
                        "Inbox Folder Access Test",
                        "❌ ISSUE",
                        f"HTTP {folders_response.status_code}: {folders_response.text[:100]}"
                    )
                    
            except Exception as e:
                self.log_investigation_result(
                    "Inbox Folder Access Test",
                    "❌ ERROR",
                    f"Folder access failed: {str(e)}"
                )
                
        except Exception as e:
            self.log_investigation_result(
                "OAuth Email Service Connection",
                "❌ ERROR",
                f"Exception: {str(e)}"
            )
    
    def print_investigation_summary(self):
        """Print comprehensive investigation summary"""
        print("\n" + "="*80)
        print("🔍 OAUTH POLLING INVESTIGATION SUMMARY")
        print("="*80)
        
        # Count results by status
        success_count = len([r for r in self.investigation_results if "✅" in r['status']])
        warning_count = len([r for r in self.investigation_results if "⚠️" in r['status']])
        error_count = len([r for r in self.investigation_results if "❌" in r['status']])
        
        print(f"Total Investigations: {len(self.investigation_results)}")
        print(f"✅ Success: {success_count}")
        print(f"⚠️ Warnings: {warning_count}")
        print(f"❌ Issues/Errors: {error_count}")
        print()
        
        # Group by investigation type
        critical_issues = []
        warnings = []
        successes = []
        
        for result in self.investigation_results:
            if "❌ CRITICAL ISSUE" in result['status']:
                critical_issues.append(result)
            elif "❌" in result['status']:
                warnings.append(result)
            elif "⚠️" in result['status']:
                warnings.append(result)
            else:
                successes.append(result)
        
        if critical_issues:
            print("🚨 CRITICAL ISSUES FOUND:")
            for issue in critical_issues:
                print(f"   • {issue['investigation']}: {issue['details']}")
            print()
        
        if warnings:
            print("⚠️ WARNINGS:")
            for warning in warnings:
                print(f"   • {warning['investigation']}: {warning['details']}")
            print()
        
        print("✅ SUCCESSFUL CHECKS:")
        for success in successes[-5:]:  # Show last 5 successes
            print(f"   • {success['investigation']}: {success['details']}")
        
        print("\n" + "="*80)
        
        # Provide recommendations
        print("🎯 RECOMMENDATIONS:")
        
        if critical_issues:
            print("1. Address critical issues first:")
            for issue in critical_issues[:3]:  # Top 3 critical issues
                print(f"   - {issue['investigation']}")
        
        if any("OAuth Token" in r['investigation'] for r in critical_issues):
            print("2. OAuth token issues detected - check token refresh mechanism")
        
        if any("Polling" in r['investigation'] for r in critical_issues):
            print("3. Polling service issues detected - restart polling service")
        
        if any("Active" in r['investigation'] for r in critical_issues):
            print("4. Account activation issues - verify account configuration")
        
        print("="*80)

async def main():
    """Main investigation function"""
    print("🔍 Starting OAuth Polling Investigation for amits.joys@outlook.com")
    print("="*80)
    
    investigator = OAuthPollingInvestigator()
    
    try:
        # Setup
        if not await investigator.setup():
            print("❌ Failed to setup investigation environment")
            return
        
        # Run investigations
        oauth_account = await investigator.investigate_oauth_account_creation()
        await investigator.investigate_polling_service_status()
        await investigator.investigate_oauth_token_validation(oauth_account)
        await investigator.investigate_polling_logic_oauth_support(oauth_account)
        await investigator.investigate_oauth_email_service_integration(oauth_account)
        await investigator.investigate_background_service_logs()
        await investigator.investigate_account_active_status(oauth_account)
        await investigator.investigate_oauth_email_service_connection(oauth_account)
        
        # Print summary
        investigator.print_investigation_summary()
        
    except Exception as e:
        print(f"❌ Investigation failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await investigator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())