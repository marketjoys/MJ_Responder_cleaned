"""
Microsoft OAuth 2.0 Integration for Email and Calendar Access
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
import secrets
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException, status
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

class MicrosoftOAuthConfig:
    """Microsoft OAuth configuration"""
    
    def __init__(self):
        # These should be set in environment variables
        self.client_id = os.environ.get('MICROSOFT_CLIENT_ID')
        self.client_secret = os.environ.get('MICROSOFT_CLIENT_SECRET')
        self.tenant_id = os.environ.get('MICROSOFT_TENANT_ID', 'common')
        self.redirect_uri = os.environ.get('MICROSOFT_REDIRECT_URI', 'http://localhost:3000/oauth/microsoft/callback')
        
        if not self.client_id or not self.client_secret:
            logger.warning("Microsoft OAuth credentials not found in environment variables")
        
        # OAuth endpoints
        self.auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.userinfo_url = "https://graph.microsoft.com/v1.0/me"
        
        # OAuth scopes - unified flow for both email and calendar
        self.scopes = [
            # Mail API scopes
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/Mail.Send",
            "https://graph.microsoft.com/Mail.ReadWrite",
            # Calendar API scopes
            "https://graph.microsoft.com/Calendars.Read",
            "https://graph.microsoft.com/Calendars.ReadWrite",
            # User info scopes
            "https://graph.microsoft.com/User.Read",
            # Offline access for refresh token
            "offline_access"
        ]

class MicrosoftOAuthState(BaseModel):
    """OAuth state model for database storage"""
    id: str = None
    user_id: str
    state: str
    requested_services: List[str]  # ['email', 'calendar']
    created_at: datetime
    expires_at: datetime
    used: bool = False

class MicrosoftOAuthTokens(BaseModel):
    """OAuth tokens model"""  
    id: str = None
    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: datetime
    scope: str
    authorized_services: List[str]  # ['email', 'calendar'] 
    user_email: str
    user_name: str
    created_at: datetime
    updated_at: datetime

class MicrosoftOAuthService:
    """Microsoft OAuth service for unified email and calendar access"""
    
    def __init__(self):
        self.config = MicrosoftOAuthConfig()
        
    async def generate_auth_url(self, user_id: str, requested_services: List[str]) -> Dict[str, str]:
        """
        Generate OAuth authorization URL with state parameter
        
        Args:
            user_id: Current user ID
            requested_services: List of services user wants to authorize ['email', 'calendar']
        
        Returns:
            Dict with auth_url and state
        """
        if not self.config.client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Microsoft OAuth not configured"
            )
        
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        
        # Store state in database with expiration
        oauth_state = MicrosoftOAuthState(
            id=str(uuid.uuid4()),
            user_id=user_id,
            state=state,
            requested_services=requested_services,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            used=False
        )
        
        await db.oauth_states_microsoft.insert_one(oauth_state.dict())
        
        # Build authorization URL
        params = {
            'client_id': self.config.client_id,
            'redirect_uri': self.config.redirect_uri,
            'scope': ' '.join(self.config.scopes),
            'response_type': 'code',
            'response_mode': 'query',
            'state': state,
            'prompt': 'consent'  # Force consent to get refresh token
        }
        
        auth_url = f"{self.config.auth_url}?{urlencode(params)}"
        
        return {
            'auth_url': auth_url,
            'state': state
        }
    
    async def handle_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for tokens
        
        Args:  
            code: Authorization code from Microsoft
            state: State parameter to validate
            
        Returns:
            Dict with user info and tokens
        """
        # Validate state parameter
        oauth_state = await db.oauth_states_microsoft.find_one({
            'state': state,
            'used': False,
            'expires_at': {'$gt': datetime.now(timezone.utc)}
        })
        
        if not oauth_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state"
            )
        
        # Mark state as used
        await db.oauth_states_microsoft.update_one(
            {'_id': oauth_state['_id']},
            {'$set': {'used': True}}
        )
        
        # Check if this authorization code has been used before
        existing_code_usage = await db.oauth_code_usage_microsoft.find_one({'code': code})
        if existing_code_usage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code has already been used"
            )
        
        # Mark authorization code as used
        await db.oauth_code_usage_microsoft.insert_one({
            'code': code,
            'user_id': oauth_state['user_id'],
            'used_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)  # Cleanup after 1 hour
        })
        
        try:
            # Exchange code for tokens
            token_data = await self._exchange_code_for_tokens(code)
            
            # Get user info
            user_info = await self._get_user_info(token_data['access_token'])
            
            # Determine which services were actually authorized
            granted_scopes = token_data.get('scope', '').split()
            authorized_services = []
            
            # Check if Mail scopes are present
            mail_scopes = [
                'Mail.Read',
                'Mail.Send',
                'Mail.ReadWrite'
            ]
            if any(scope in granted_scopes or f'https://graph.microsoft.com/{scope}' in granted_scopes for scope in mail_scopes):
                authorized_services.append('email')
            
            # Check if Calendar scopes are present
            calendar_scopes = [
                'Calendars.Read',
                'Calendars.ReadWrite'
            ]
            if any(scope in granted_scopes or f'https://graph.microsoft.com/{scope}' in granted_scopes for scope in calendar_scopes):
                authorized_services.append('calendar')
            
            # Calculate token expiration
            expires_in = token_data.get('expires_in', 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            # Store or update tokens in database (support multiple accounts)
            oauth_email = user_info.get('mail') or user_info.get('userPrincipalName', '')
            
            oauth_tokens = MicrosoftOAuthTokens(
                id=str(uuid.uuid4()),
                user_id=oauth_state['user_id'],
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_type=token_data.get('token_type', 'Bearer'),
                expires_at=expires_at,
                scope=token_data.get('scope', ''),
                authorized_services=authorized_services,
                user_email=oauth_email,
                user_name=user_info.get('displayName', ''),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Check if token already exists for this user + email combination
            existing_token = await db.oauth_tokens_microsoft.find_one({
                'user_id': oauth_state['user_id'],
                'user_email': oauth_email
            })
            
            if existing_token:
                # Update existing token
                await db.oauth_tokens_microsoft.update_one(
                    {
                        'user_id': oauth_state['user_id'],
                        'user_email': oauth_email
                    },
                    {
                        '$set': {
                            'access_token': token_data['access_token'],
                            'refresh_token': token_data.get('refresh_token') or existing_token.get('refresh_token'),
                            'expires_at': expires_at,
                            'scope': token_data.get('scope', ''),
                            'authorized_services': authorized_services,
                            'user_name': user_info.get('displayName', ''),
                            'updated_at': datetime.now(timezone.utc)
                        }
                    }
                )
                logger.info(f"✅ Updated Microsoft OAuth token for {oauth_email}")
            else:
                # Insert new token (allows multiple accounts)
                await db.oauth_tokens_microsoft.insert_one(oauth_tokens.dict())
                logger.info(f"✅ Created new Microsoft OAuth token for {oauth_email}")
            
            return {
                'user_id': oauth_state['user_id'],
                'user_email': oauth_tokens.user_email,
                'user_name': oauth_tokens.user_name,
                'authorized_services': authorized_services,
                'requested_services': oauth_state['requested_services']
            }
            
        except Exception as e:
            logger.error(f"Error handling Microsoft OAuth callback: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete OAuth flow: {str(e)}"
            )
    
    async def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    'client_id': self.config.client_id,
                    'client_secret': self.config.client_secret,
                    'code': code,
                    'redirect_uri': self.config.redirect_uri,
                    'grant_type': 'authorization_code'
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for tokens: {response.text}"
                )
            
            return response.json()
    
    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft Graph API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user information"
                )
            
            return response.json()
    
    async def get_valid_token(self, user_id: str, service: str = 'email', oauth_email: Optional[str] = None) -> str:
        """
        Get a valid access token for the user, refreshing if necessary (supports multiple accounts)
        
        Args:
            user_id: User ID
            service: Service type ('email' or 'calendar')
            oauth_email: Optional specific email to get token for
            
        Returns:
            Valid access token
        """
        # Try to find token for specific email first
        if oauth_email:
            logger.info(f"🔍 Looking for Microsoft token - user_id: {user_id}, oauth_email: {oauth_email}")
            tokens = await db.oauth_tokens_microsoft.find_one({
                'user_id': user_id,
                'user_email': oauth_email
            })
        else:
            logger.info(f"🔍 Looking for Microsoft token - user_id: {user_id} (any email)")
            # Fallback to any token for this user (backward compatibility)
            tokens = await db.oauth_tokens_microsoft.find_one({'user_id': user_id})
        
        if not tokens:
            logger.error(f"❌ No Microsoft OAuth token found for user_id: {user_id}, oauth_email: {oauth_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Microsoft OAuth not authorized"
            )
        else:
            logger.info(f"✅ Found Microsoft token for {tokens.get('user_email', 'unknown email')}")
            logger.info(f"🔐 Token expires at: {tokens.get('expires_at')}")
            logger.info(f"🔧 Authorized services: {tokens.get('authorized_services')}")
        
        # Check if service is authorized
        if service not in tokens.get('authorized_services', []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Microsoft {service} access not authorized"
            )
        
        # Check if token is expired or will expire in next 5 minutes
        expires_at = tokens['expires_at']
        # Ensure expires_at has timezone info for comparison
        if not hasattr(expires_at, 'tzinfo') or expires_at.tzinfo is None:
            # If naive datetime, assume UTC
            from datetime import timezone as dt_timezone
            expires_at = expires_at.replace(tzinfo=dt_timezone.utc)
        
        current_time = datetime.now(timezone.utc)
        time_until_expiry = expires_at - current_time
        logger.info(f"⏰ Token check: Current time: {current_time}, Expires: {expires_at}, Time until expiry: {time_until_expiry}")
        
        if current_time >= expires_at - timedelta(minutes=5):
            # Refresh token
            logger.info("🔄 Token needs refresh (expires within 5 minutes)")
            if not tokens.get('refresh_token'):
                logger.error("❌ No refresh token available")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token not available, please re-authorize"
                )
            
            new_tokens = await self._refresh_access_token(tokens['refresh_token'])
            
            # Update tokens in database - use email to identify which token
            expires_in = new_tokens.get('expires_in', 3600)
            new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            update_filter = {'user_id': user_id}
            if oauth_email:
                update_filter['user_email'] = oauth_email
            elif tokens.get('user_email'):
                update_filter['user_email'] = tokens['user_email']
            
            await db.oauth_tokens_microsoft.update_one(
                update_filter,
                {
                    '$set': {
                        'access_token': new_tokens['access_token'],
                        'expires_at': new_expires_at,
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            logger.info("✅ Token refreshed successfully")
            access_token = new_tokens['access_token']
        else:
            logger.info("✅ Using existing token (not expired)")
            access_token = tokens['access_token']
        
        # Debug: Show partial token for verification
        if access_token:
            token_preview = f"{access_token[:10]}...{access_token[-10:]}" if len(access_token) > 20 else "short_token"
            logger.info(f"🔑 Returning access token: {token_preview}")
        else:
            logger.error("❌ No access token available!")
            
        return access_token
    
    async def _refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    'client_id': self.config.client_id,
                    'client_secret': self.config.client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token'
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to refresh access token, please re-authorize"
                )
            
            return response.json()
    
    async def get_oauth_status(self, user_id: str, oauth_email: Optional[str] = None) -> Dict[str, Any]:
        """Get current OAuth authorization status for a user (supports multiple accounts)"""
        
        if oauth_email:
            # Get status for specific email
            tokens = await db.oauth_tokens_microsoft.find_one({
                'user_id': user_id,
                'user_email': oauth_email
            })
            
            if not tokens:
                return {
                    'is_authorized': False,
                    'authorized_services': [],
                    'user_email': None,
                    'user_name': None,
                    'expires_at': None
                }
            
            return {
                'is_authorized': True,
                'authorized_services': tokens.get('authorized_services', []),
                'user_email': tokens.get('user_email'),
                'user_name': tokens.get('user_name'),
                'expires_at': tokens.get('expires_at')
            }
        else:
            # Get all authorized accounts for this user
            all_tokens = await db.oauth_tokens_microsoft.find({'user_id': user_id}).to_list(length=100)
            
            if not all_tokens:
                return {
                    'is_authorized': False,
                    'authorized_services': [],
                    'authorized_accounts': [],
                    'user_email': None,
                    'user_name': None,
                    'expires_at': None
                }
            
            # Return info about all accounts
            authorized_accounts = []
            for token in all_tokens:
                authorized_accounts.append({
                    'user_email': token.get('user_email'),
                    'user_name': token.get('user_name'),
                    'authorized_services': token.get('authorized_services', []),
                    'expires_at': token.get('expires_at')
                })
            
            # For backward compatibility, return first account as primary
            primary = all_tokens[0]
            return {
                'is_authorized': True,
                'authorized_services': primary.get('authorized_services', []),
                'user_email': primary.get('user_email'),
                'user_name': primary.get('user_name'),
                'expires_at': primary.get('expires_at'),
                'authorized_accounts': authorized_accounts,
                'total_accounts': len(all_tokens)
            }
    
    async def revoke_access(self, user_id: str, oauth_email: Optional[str] = None) -> bool:
        """Revoke OAuth access for a user (supports specific email or all accounts)"""
        
        if oauth_email:
            # Revoke specific OAuth account
            logger.info(f"🗑️ Revoking Microsoft OAuth for user {user_id}, email {oauth_email}")
            result = await db.oauth_tokens_microsoft.delete_one({
                'user_id': user_id,
                'user_email': oauth_email
            })
            return result.deleted_count > 0
        else:
            # Revoke all tokens for user (existing behavior)
            logger.info(f"🗑️ Revoking ALL Microsoft OAuth tokens for user {user_id}")
            result = await db.oauth_tokens_microsoft.delete_many({'user_id': user_id})
            return result.deleted_count > 0

# Global service instance
microsoft_oauth_service = MicrosoftOAuthService()
