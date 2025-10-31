"""
Google OAuth 2.0 Integration for Email and Calendar Access
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

class GoogleOAuthConfig:
    """Google OAuth configuration"""
    
    def __init__(self):
        # These should be set in environment variables
        self.client_id = os.environ.get('GOOGLE_CLIENT_ID')
        self.client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:3000/oauth/google/callback')
        
        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth credentials not found in environment variables")
        
        # OAuth endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        # OAuth scopes - unified flow for both email and calendar
        self.scopes = [
            # Gmail API scopes
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send", 
            "https://www.googleapis.com/auth/gmail.modify",
            # Calendar API scopes
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            # User info scopes
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ]

class GoogleOAuthState(BaseModel):
    """OAuth state model for database storage"""
    id: str = None
    user_id: str
    state: str
    requested_services: List[str]  # ['email', 'calendar']
    created_at: datetime
    expires_at: datetime
    used: bool = False

class GoogleOAuthTokens(BaseModel):
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

class GoogleOAuthService:
    """Google OAuth service for unified email and calendar access"""
    
    def __init__(self):
        self.config = GoogleOAuthConfig()
        
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
                detail="Google OAuth not configured"
            )
        
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        
        # Store state in database with expiration
        oauth_state = GoogleOAuthState(
            id=str(uuid.uuid4()),
            user_id=user_id,
            state=state,
            requested_services=requested_services,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            used=False
        )
        
        await db.oauth_states.insert_one(oauth_state.dict())
        
        # Build authorization URL
        params = {
            'client_id': self.config.client_id,
            'redirect_uri': self.config.redirect_uri,
            'scope': ' '.join(self.config.scopes),
            'response_type': 'code',
            'access_type': 'offline',  # Request refresh token
            'prompt': 'consent',  # Force consent to get refresh token
            'state': state,
            'include_granted_scopes': 'true'
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
            code: Authorization code from Google
            state: State parameter to validate
            
        Returns:
            Dict with user info and tokens
        """
        # Validate state parameter
        oauth_state = await db.oauth_states.find_one({
            'state': state,
            'expires_at': {'$gt': datetime.now(timezone.utc)}
        })
        
        if not oauth_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state"
            )
        
        # Check if state was already used (duplicate callback)
        if oauth_state.get('used'):
            logger.warning(f"⚠️ OAuth state already used for user {oauth_state['user_id']}")
            # Check if user already has a recent valid OAuth token
            recent_token = await db.oauth_tokens.find_one({
                'user_id': oauth_state['user_id'],
                'created_at': {'$gte': datetime.now(timezone.utc) - timedelta(minutes=5)}
            })
            
            if recent_token:
                # Return success response since authorization was already successful
                logger.info(f"✅ Returning existing OAuth result for duplicate callback (user {oauth_state['user_id']})")
                user_info = {
                    'email': recent_token.get('user_email', ''),
                    'name': recent_token.get('user_name', ''),
                    'id': recent_token.get('user_email', '').split('@')[0]
                }
                return {
                    'user_id': oauth_state['user_id'],
                    'authorized_services': recent_token.get('authorized_services', []),
                    'requested_services': oauth_state.get('requested_services', []),
                    'user_info': user_info
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OAuth state already used. Please start a new authorization."
                )
        
        # Mark state as used
        await db.oauth_states.update_one(
            {'_id': oauth_state['_id']},
            {'$set': {'used': True}}
        )
        
        # Check if this authorization code has been used before
        existing_code_usage = await db.oauth_code_usage.find_one({'code': code})
        if existing_code_usage:
            logger.warning(f"⚠️ OAuth authorization code reuse attempt for user {oauth_state['user_id']}")
            # Check if user already has a valid OAuth token from this recent authorization
            recent_token = await db.oauth_tokens.find_one({
                'user_id': oauth_state['user_id'],
                'created_at': {'$gte': existing_code_usage['used_at'] - timedelta(minutes=5)}
            })
            
            if recent_token:
                # Return success response since authorization was already successful
                logger.info(f"✅ Returning existing successful OAuth result for user {oauth_state['user_id']}")
                user_info = {
                    'email': recent_token.get('user_email', ''),
                    'name': recent_token.get('user_name', ''),
                    'id': recent_token.get('user_email', '').split('@')[0]
                }
                return {
                    'user_id': oauth_state['user_id'],
                    'authorized_services': recent_token.get('authorized_services', []),
                    'requested_services': oauth_state.get('requested_services', []),
                    'user_info': user_info
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OAuth authorization was already completed. Please try again if needed."
                )
        
        # Mark authorization code as used
        await db.oauth_code_usage.insert_one({
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
            
            # Check if Gmail scopes are present
            gmail_scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
            if any(scope in granted_scopes for scope in gmail_scopes):
                authorized_services.append('email')
            
            # Check if Calendar scopes are present
            calendar_scopes = [
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/calendar.events'
            ]
            if any(scope in granted_scopes for scope in calendar_scopes):
                authorized_services.append('calendar')
            
            # Store tokens in database
            oauth_email = user_info.get('email', '')
            
            oauth_tokens = GoogleOAuthTokens(
                id=str(uuid.uuid4()),
                user_id=oauth_state['user_id'],
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600)),
                scope=token_data.get('scope', ''),
                authorized_services=authorized_services,
                user_email=oauth_email,
                user_name=user_info.get('name', ''),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Check if token already exists for this user + email combination
            existing_token = await db.oauth_tokens.find_one({
                'user_id': oauth_state['user_id'],
                'user_email': oauth_email
            })
            
            if existing_token:
                # Update existing token
                await db.oauth_tokens.update_one(
                    {
                        'user_id': oauth_state['user_id'],
                        'user_email': oauth_email
                    },
                    {
                        '$set': {
                            'access_token': token_data['access_token'],
                            'refresh_token': token_data.get('refresh_token') or existing_token.get('refresh_token'),
                            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600)),
                            'scope': token_data.get('scope', ''),
                            'authorized_services': authorized_services,
                            'user_name': user_info.get('name', ''),
                            'updated_at': datetime.now(timezone.utc)
                        }
                    }
                )
                logger.info(f"✅ Updated Google OAuth token for {oauth_email}")
            else:
                # Insert new token (allows multiple accounts)
                await db.oauth_tokens.insert_one(oauth_tokens.dict())
                logger.info(f"✅ Created new Google OAuth token for {oauth_email}")
            
            return {
                'user_id': oauth_state['user_id'],
                'user_info': user_info,
                'authorized_services': authorized_services,
                'requested_services': oauth_state['requested_services'],
                'tokens_stored': True
            }
            
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth callback failed: {str(e)}"
            )
    
    async def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        
        token_data = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.config.redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data=token_data,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {response.text}"
                )
            
            return response.json()
    
    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information using access token"""
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get user info: {response.text}"
                )
            
            return response.json()
    
    async def refresh_access_token(self, user_id: str, oauth_email: Optional[str] = None) -> Optional[str]:
        """Refresh access token using refresh token for specific email or first available"""
        
        # Get stored tokens - prioritize specific email if provided
        if oauth_email:
            oauth_tokens = await db.oauth_tokens.find_one({
                'user_id': user_id,
                'user_email': oauth_email
            })
        else:
            # Fallback to any token for this user (backward compatibility)
            oauth_tokens = await db.oauth_tokens.find_one({'user_id': user_id})
            
        if not oauth_tokens or not oauth_tokens.get('refresh_token'):
            return None
        
        # Check if token needs refresh (expires in next 5 minutes) - safe datetime comparison
        expires_at = oauth_tokens['expires_at']
        current_time = datetime.now(timezone.utc)
        
        # Ensure both datetimes are timezone-aware for comparison
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except:
                logger.warning(f"Invalid expires_at format: {expires_at}, forcing refresh")
                expires_at = current_time  # Force refresh on invalid format
        elif isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at > current_time + timedelta(minutes=5):
            return oauth_tokens['access_token']  # Token still valid
        
        try:
            refresh_data = {
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'refresh_token': oauth_tokens['refresh_token'], 
                'grant_type': 'refresh_token'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.token_url,
                    data=refresh_data,
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code != 200:
                    logger.error(f"Token refresh failed: {response.text}")
                    return None
                
                token_data = response.json()
                
                # Update stored tokens - use email if available
                update_filter = {'user_id': user_id}
                if oauth_email:
                    update_filter['user_email'] = oauth_email
                elif oauth_tokens.get('user_email'):
                    update_filter['user_email'] = oauth_tokens['user_email']
                    
                await db.oauth_tokens.update_one(
                    update_filter,
                    {
                        '$set': {
                            'access_token': token_data['access_token'],
                            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600)),
                            'updated_at': datetime.now(timezone.utc)
                        }
                    }
                )
                
                return token_data['access_token']
                
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return None
    
    async def get_valid_token(self, user_id: str, service: str = None, oauth_email: Optional[str] = None) -> Optional[str]:
        """
        Get valid access token for user, refreshing if necessary
        
        Args:
            user_id: User ID
            service: Optional service filter ('email' or 'calendar')
            oauth_email: Optional specific email to get token for
            
        Returns:
            Valid access token or None
        """
        # Try to find token for specific email first
        if oauth_email:
            oauth_tokens = await db.oauth_tokens.find_one({
                'user_id': user_id,
                'user_email': oauth_email
            })
        else:
            # Fallback to any token for this user (backward compatibility)
            oauth_tokens = await db.oauth_tokens.find_one({'user_id': user_id})
            
        if not oauth_tokens:
            return None
        
        # Check if service is authorized
        if service and service not in oauth_tokens.get('authorized_services', []):
            return None
        
        # Try to refresh token if needed
        return await self.refresh_access_token(user_id, oauth_email or oauth_tokens.get('user_email'))
    
    async def revoke_tokens(self, user_id: str, oauth_email: Optional[str] = None) -> bool:
        """Revoke OAuth tokens and remove from database - supports specific email"""
        
        if oauth_email:
            # Revoke specific OAuth account
            oauth_tokens = await db.oauth_tokens.find_one({
                'user_id': user_id,
                'user_email': oauth_email
            })
            
            if not oauth_tokens:
                return True
            
            try:
                # Revoke token with Google
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        'https://oauth2.googleapis.com/revoke',
                        data={'token': oauth_tokens['access_token']},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )
                
                # Remove specific token from database
                await db.oauth_tokens.delete_one({
                    'user_id': user_id,
                    'user_email': oauth_email
                })
                logger.info(f"OAuth tokens revoked for user {user_id}, email {oauth_email}")
                return True
                
            except Exception as e:
                logger.error(f"Error revoking tokens for {oauth_email}: {str(e)}")
                # Still remove from database
                await db.oauth_tokens.delete_one({
                    'user_id': user_id,
                    'user_email': oauth_email
                })
                return False
        else:
            # Revoke all tokens for user (existing behavior)
            all_tokens = await db.oauth_tokens.find({'user_id': user_id}).to_list(length=100)
            
            if not all_tokens:
                return True
            
            success_count = 0
            for token in all_tokens:
                try:
                    # Revoke token with Google
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            'https://oauth2.googleapis.com/revoke',
                            data={'token': token['access_token']},
                            headers={'Content-Type': 'application/x-www-form-urlencoded'}
                        )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error revoking token for {token.get('user_email')}: {str(e)}")
            
            # Remove all tokens from database
            await db.oauth_tokens.delete_many({'user_id': user_id})
            logger.info(f"OAuth tokens revoked for user {user_id} ({success_count}/{len(all_tokens)} successful)")
            return success_count == len(all_tokens)
    
    async def get_oauth_status(self, user_id: str, oauth_email: Optional[str] = None) -> Dict[str, Any]:
        """Get OAuth authorization status for user - supports multiple accounts"""
        
        def _safe_date_check(expires_at) -> bool:
            """Safely check if token needs refresh, handling malformed dates"""
            try:
                if not expires_at:
                    return True  # No expiry means needs refresh
                
                # Handle string dates (corrupted data)
                if isinstance(expires_at, str):
                    try:
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    except:
                        logger.warning(f"Corrupted expires_at date format: {expires_at}")
                        return True  # Treat corrupted dates as expired
                
                # Handle datetime objects
                if isinstance(expires_at, datetime):
                    # Ensure timezone aware
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    return expires_at < datetime.now(timezone.utc) + timedelta(minutes=5)
                
                return True  # Unknown format, assume needs refresh
            except Exception as e:
                logger.warning(f"Error checking token expiry: {str(e)}")
                return True
        
        if oauth_email:
            # Get status for specific email
            oauth_tokens = await db.oauth_tokens.find_one({
                'user_id': user_id,
                'user_email': oauth_email
            })
            if not oauth_tokens:
                return {
                    'is_authorized': False,
                    'authorized_services': [],
                    'user_email': None,
                    'expires_at': None
                }
            
            return {
                'is_authorized': True,
                'authorized_services': oauth_tokens.get('authorized_services', []),
                'user_email': oauth_tokens.get('user_email'),
                'user_name': oauth_tokens.get('user_name'),
                'expires_at': oauth_tokens.get('expires_at'),
                'needs_refresh': _safe_date_check(oauth_tokens.get('expires_at'))
            }
        else:
            # Get all authorized accounts for this user
            all_tokens = await db.oauth_tokens.find({'user_id': user_id}).to_list(length=100)
            
            if not all_tokens:
                return {
                    'is_authorized': False,
                    'authorized_services': [],
                    'authorized_accounts': [],
                    'user_email': None,
                    'expires_at': None
                }
            
            # Return info about all accounts
            authorized_accounts = []
            for token in all_tokens:
                authorized_accounts.append({
                    'user_email': token.get('user_email'),
                    'user_name': token.get('user_name'),
                    'authorized_services': token.get('authorized_services', []),
                    'expires_at': token.get('expires_at'),
                    'needs_refresh': _safe_date_check(token.get('expires_at'))
                })
            
            # For backward compatibility, return first account as primary
            primary = all_tokens[0]
            return {
                'is_authorized': True,
                'authorized_services': primary.get('authorized_services', []),
                'user_email': primary.get('user_email'),
                'user_name': primary.get('user_name'),
                'expires_at': primary.get('expires_at'),
                'needs_refresh': _safe_date_check(primary.get('expires_at')),
                'authorized_accounts': authorized_accounts,
                'total_accounts': len(all_tokens)
            }

# Global OAuth service instance
google_oauth_service = GoogleOAuthService()