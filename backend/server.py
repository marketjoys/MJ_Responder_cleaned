from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends, status
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import uuid
from datetime import datetime, timedelta, timezone
import json
import asyncio
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import imaplib
import email
import re
from email.header import decode_header
import time
from collections import deque
import threading

# Import authentication and calendar modules
from auth import (
    User, UserCreate, UserLogin, Token, get_current_active_user, 
    authenticate_user, create_access_token, get_password_hash,
    get_user_by_email, check_email_quota, increment_email_usage,
    get_user_quota_info, update_user_quota
)
from calendar_models import (
    CalendarProviderCreate, CalendarProviderResponse, CalendarInfo,
    EventCreate, EventUpdate, EventResponse, MeetingDetectionRequest,
    MeetingDetectionResponse, QuotaInfo, UserProfile
)
from calendar_services import calendar_service, credential_manager
from calendar_agent import calendar_agent
from oauth_google import google_oauth_service
from google_services import get_google_gmail_service, get_google_calendar_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Automated Email Assistant API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# API Keys from environment
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
COHERE_API_KEY = os.environ.get('COHERE_API_KEY')

# Email provider configurations
EMAIL_PROVIDERS = {
    "gmail": {
        "name": "Gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "requires_app_password": True
    },
    "outlook": {
        "name": "Outlook/Hotmail",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp-mail.outlook.com",
        "smtp_port": 587,
        "requires_app_password": False
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "requires_app_password": True
    },
    "custom": {
        "name": "Custom IMAP/SMTP",
        "imap_server": "",
        "imap_port": 993,
        "smtp_server": "",
        "smtp_port": 587,
        "requires_app_password": False
    }
}

# Models
class Intent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    examples: List[str] = []
    system_prompt: str = ""
    confidence_threshold: float = 0.7
    follow_up_hours: int = 24
    is_meeting_related: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IntentCreate(BaseModel):
    name: str
    description: str
    examples: List[str] = []
    system_prompt: str = ""
    confidence_threshold: float = 0.7
    follow_up_hours: int = 24
    is_meeting_related: bool = False

class EmailAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    provider: str
    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int
    username: str
    password: str  # In production, this should be encrypted
    is_active: bool = True
    persona: str = ""
    signature: str = ""
    last_uid: int = 0
    uidvalidity: Optional[str] = None
    last_polled: Optional[datetime] = None
    auto_send: bool = True  # Auto-send approved replies
    # Follow-up configuration
    enable_follow_ups: bool = True
    follow_up_hours_override: Optional[int] = None  # Override global setting
    max_follow_ups_override: Optional[int] = None
    custom_follow_up_template: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EmailAccountCreate(BaseModel):
    name: str
    email: str
    provider: str
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    username: str
    password: str
    persona: str = ""
    signature: str = ""
    auto_send: bool = True
    # Follow-up configuration  
    enable_follow_ups: bool = True
    follow_up_hours_override: Optional[int] = None
    max_follow_ups_override: Optional[int] = None
    custom_follow_up_template: Optional[str] = None

class KnowledgeBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    tags: List[str] = []
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KnowledgeBaseCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = []

class EmailTestRequest(BaseModel):
    subject: str
    body: str
    sender: str
    account_id: str

class DraftRequest(BaseModel):
    email_id: str
    force_redraft: bool = False

class SendEmailRequest(BaseModel):
    email_id: str
    manual_override: bool = False

class PollingControlRequest(BaseModel):
    action: str  # start, stop, status

# Follow-up Configuration Models
class FollowUpConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Link to user who owns this config
    global_follow_up_hours: int = 24  # Default global follow-up time
    max_follow_ups: int = 3  # Maximum number of follow-ups per email
    follow_up_interval_hours: int = 48  # Time between follow-ups
    auto_follow_up: bool = True  # Enable automatic follow-ups
    business_hours_only: bool = False  # Only send follow-ups during business hours
    business_start_hour: int = 9  # 9 AM
    business_end_hour: int = 17  # 5 PM
    business_days: List[int] = [1, 2, 3, 4, 5]  # Monday=1 to Sunday=7
    exclude_weekends: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class FollowUpConfigCreate(BaseModel):
    global_follow_up_hours: int = 24
    max_follow_ups: int = 3
    follow_up_interval_hours: int = 48
    auto_follow_up: bool = True
    business_hours_only: bool = False
    business_start_hour: int = 9
    business_end_hour: int = 17
    business_days: List[int] = [1, 2, 3, 4, 5]
    exclude_weekends: bool = True

class FollowUpConfigUpdate(BaseModel):
    global_follow_up_hours: Optional[int] = None
    max_follow_ups: Optional[int] = None
    follow_up_interval_hours: Optional[int] = None
    auto_follow_up: Optional[bool] = None
    business_hours_only: Optional[bool] = None
    business_start_hour: Optional[int] = None
    business_end_hour: Optional[int] = None
    business_days: Optional[List[int]] = None
    exclude_weekends: Optional[bool] = None

# Enhanced Email Account with Follow-up Settings
class EmailAccountFollowUp(BaseModel):
    enable_follow_ups: bool = True
    follow_up_hours_override: Optional[int] = None  # Override global setting
    max_follow_ups_override: Optional[int] = None
    custom_follow_up_template: Optional[str] = None

# Follow-up Email Tracking Models
class FollowUpEmail(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_email_id: str  # Reference to the original email
    account_id: str  # Email account that will send the follow-up
    user_id: str  # User who owns this follow-up
    thread_id: str  # Email thread identifier
    recipient_email: str  # Who to send follow-up to
    subject: str  # Follow-up email subject
    status: str = "pending"  # pending, scheduled, sent, cancelled, failed
    follow_up_number: int = 1  # 1st, 2nd, 3rd follow-up etc.
    scheduled_time: datetime  # When to send this follow-up
    sent_time: Optional[datetime] = None
    draft_content: str = ""  # Generated follow-up content
    draft_html: str = ""
    error_message: Optional[str] = None
    response_received: bool = False  # Did we get a response after sending?
    last_response_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class FollowUpEmailCreate(BaseModel):
    original_email_id: str
    account_id: str
    recipient_email: str
    subject: str
    follow_up_number: int = 1
    scheduled_time: datetime
    draft_content: str = ""

class FollowUpEmailUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    draft_content: Optional[str] = None
    draft_html: Optional[str] = None
    response_received: Optional[bool] = None
    error_message: Optional[str] = None

class AccountPollingStatus(BaseModel):
    account_id: str
    email: str
    polling_active: bool
    has_connection: bool
    last_polled: Optional[str] = None
    last_uid: int = 0

# Thread conversation models
class EmailThread(BaseModel):
    thread_id: str
    subject: str
    participants: List[str]
    original_email: Dict[str, Any]  # The original email that started the thread
    follow_ups: List[Dict[str, Any]] = []  # Associated follow-ups
    responses: List[Dict[str, Any]] = []  # Response emails in the thread
    has_response: bool = False  # Whether thread received responses
    follow_ups_active: bool = True  # Whether follow-ups should continue
    last_activity: datetime
    created_at: datetime
    
class ThreadSummary(BaseModel):
    total_threads: int
    active_follow_ups: int
    threads_with_responses: int
    pending_follow_ups: int

# Define EmailMessage model here to avoid circular imports
class EmailMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    body: str
    body_html: str = ""
    received_at: datetime
    in_reply_to: str = ""
    references: str = ""
    status: str = "new"  # new, classifying, drafting, ready_to_send, sent, error
    intents: List[Dict[str, Any]] = []
    draft: str = ""
    draft_html: str = ""
    validation_result: Optional[Dict[str, Any]] = None
    processed_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Import email services and model
from email_services import get_polling_service, EmailConnection

# Rate limiter for Groq API
class TokenBucketRateLimiter:
    def __init__(self, max_tokens=5000, refill_rate=100):  # 5000 tokens with 100/minute refill
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per minute
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    async def acquire(self, tokens_needed=100):
        """Acquire tokens, wait if necessary"""
        while True:
            with self.lock:
                now = time.time()
                # Refill tokens based on time passed
                time_passed = now - self.last_refill
                tokens_to_add = (time_passed / 60) * self.refill_rate
                self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
                self.last_refill = now
                
                if self.tokens >= tokens_needed:
                    self.tokens -= tokens_needed
                    return True
            
            # Wait before retrying
            await asyncio.sleep(1)

# Global rate limiter instance
groq_rate_limiter = TokenBucketRateLimiter()

# Global polling service
polling_service = None

# Helper Functions
async def get_cohere_embedding(text: str) -> List[float]:
    """Get embedding from Cohere API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.cohere.com/v1/embed",
            headers={
                "Authorization": f"Bearer {COHERE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "embed-english-v3.0",
                "texts": [text],
                "input_type": "classification",
                "truncate": "NONE"
            }
        )
        if response.status_code == 200:
            result = response.json()
            return result["embeddings"][0]
        else:
            raise HTTPException(status_code=500, detail=f"Cohere API error: {response.text}")

async def groq_chat_completion(messages: List[Dict], system_prompt: str = "") -> str:
    """Get completion from Groq API with rate limiting and retry logic"""
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages
    
    # Calculate approximate tokens needed (rough estimate)
    total_text = " ".join([msg.get("content", "") for msg in messages])
    estimated_tokens = len(total_text) // 4  # Rough approximation: 4 chars per token
    
    # Acquire tokens from rate limiter
    await groq_rate_limiter.acquire(estimated_tokens)
    
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": messages,
                        "model": "llama-3.3-70b-versatile",
                        "temperature": 0.6,
                        "max_completion_tokens": 4096,  # Increased to ensure full responses
                        "top_p": 0.95,
                        "stream": False
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"🤖 Groq response received: '{content[:100]}...' (length: {len(content)})")
                    return content
                elif response.status_code == 429:  # Rate limit exceeded
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Groq rate limit hit, retrying in {delay}s (attempt {attempt + 1})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise HTTPException(status_code=429, detail="Groq API rate limit exceeded - please try again later")
                else:
                    raise HTTPException(status_code=500, detail=f"Groq API error: {response.text}")
                    
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                logger.warning(f"Groq API timeout, retrying (attempt {attempt + 1})")
                await asyncio.sleep(base_delay)
                continue
            else:
                raise HTTPException(status_code=500, detail="Groq API timeout")
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Groq API error: {str(e)}, retrying (attempt {attempt + 1})")
                await asyncio.sleep(base_delay)
                continue
            else:
                raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    import math
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    return dot_product / (magnitude_a * magnitude_b)

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    
    # Check if user already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    
    # Set quota reset date to next month
    next_month = datetime.utcnow().replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name or "",
        "hashed_password": hashed_password,
        "is_active": True,
        "email_quota": 100,  # Default monthly quota
        "emails_used": 0,
        "quota_reset_date": next_month,
        "timezone": "UTC",
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user_data.email}, expires_delta=access_token_expires
    )
    
    user_response = User(**new_user)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@api_router.post("/auth/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """Login user and return JWT token"""
    
    user = await authenticate_user(user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    user_response = User(**user)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@api_router.get("/auth/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user's profile"""
    
    quota_info = await get_user_quota_info(current_user.id)
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        timezone=current_user.timezone,
        email_quota=current_user.email_quota,
        emails_used=current_user.emails_used,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        quota_info=QuotaInfo(**quota_info)
    )

@api_router.put("/auth/quota/{user_id}")
async def upgrade_user_quota(user_id: str, new_quota: int, current_user: User = Depends(get_current_active_user)):
    """Upgrade user's email quota (admin function)"""
    
    # For now, allow users to upgrade their own quota
    # In production, this should be restricted to admin users
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify other user's quota"
        )
    
    await update_user_quota(user_id, new_quota)
    return {"message": f"Quota updated to {new_quota} emails per month"}

# Calendar Provider Routes
@api_router.post("/calendar/providers", response_model=CalendarProviderResponse)
async def create_calendar_provider(
    provider_data: CalendarProviderCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new calendar provider configuration"""
    
    try:
        # Encrypt credentials
        encrypted_credentials = credential_manager.encrypt_credentials(provider_data.credentials)
        
        # Create provider record
        provider_id = str(uuid.uuid4())
        provider_config = {
            "id": provider_id,
            "user_id": current_user.id,
            "provider_type": provider_data.provider_type.value,
            "provider_name": provider_data.provider_name,
            "encrypted_credentials": encrypted_credentials,
            "is_active": True,
            "timezone": provider_data.timezone,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.calendar_providers.insert_one(provider_config)
        
        # Test provider connection
        try:
            service = await calendar_service.get_service(provider_id, current_user.id)
            calendars = await service.get_calendars()
            calendar_count = len(calendars)
        except Exception as e:
            logger.warning(f"Provider connection test failed: {e}")
            calendar_count = 0
        
        return CalendarProviderResponse(
            id=provider_id,
            provider_type=provider_data.provider_type,
            provider_name=provider_data.provider_name,
            is_active=True,
            timezone=provider_data.timezone,
            calendar_count=calendar_count,
            created_at=provider_config["created_at"],
            updated_at=provider_config["updated_at"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create calendar provider: {str(e)}"
        )

@api_router.get("/calendar/providers", response_model=List[CalendarProviderResponse])
async def get_calendar_providers(current_user: User = Depends(get_current_active_user)):
    """Get all calendar providers for current user"""
    
    providers = await db.calendar_providers.find({
        "user_id": current_user.id,
        "is_active": True
    }).to_list(100)
    
    provider_responses = []
    for provider in providers:
        # Get calendar count
        try:
            service = await calendar_service.get_service(provider["id"], current_user.id)
            calendars = await service.get_calendars()
            calendar_count = len(calendars)
        except Exception:
            calendar_count = 0
        
        provider_responses.append(CalendarProviderResponse(
            id=provider["id"],
            provider_type=provider["provider_type"],
            provider_name=provider["provider_name"],
            is_active=provider["is_active"],
            timezone=provider["timezone"],
            calendar_count=calendar_count,
            created_at=provider["created_at"],
            updated_at=provider["updated_at"]
        ))
    
    return provider_responses

@api_router.delete("/calendar/providers/{provider_id}")
async def delete_calendar_provider(
    provider_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a calendar provider"""
    
    result = await db.calendar_providers.delete_one({
        "id": provider_id,
        "user_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Calendar provider not found")
    
    return {"message": "Calendar provider deleted successfully"}

@api_router.get("/calendar/calendars")
async def get_all_calendars(current_user: User = Depends(get_current_active_user)):
    """Get all calendars from all providers"""
    
    try:
        all_calendars = await calendar_service.get_all_calendars(current_user.id)
        return all_calendars
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to retrieve calendars: {str(e)}"
        )

@api_router.post("/calendar/providers/{provider_id}/calendars/{calendar_id}/events", response_model=EventResponse)
async def create_calendar_event(
    provider_id: str,
    calendar_id: str,
    event_data: EventCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new calendar event"""
    
    try:
        # Check user quota
        if not await check_email_quota(current_user):
            raise HTTPException(
                status_code=429,
                detail="Monthly email quota exceeded. Please upgrade your plan."
            )
        
        # Convert event data to dict
        event_dict = event_data.dict()
        event_dict['start_time'] = event_data.start_time.isoformat()
        event_dict['end_time'] = event_data.end_time.isoformat()
        
        # Create event
        event_response = await calendar_service.create_event(
            provider_id, calendar_id, event_dict, current_user.id
        )
        
        # Increment usage
        await increment_email_usage(current_user.id)
        
        return event_response
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create event: {str(e)}"
        )

@api_router.get("/calendar/providers/{provider_id}/calendars/{calendar_id}/events", response_model=List[EventResponse])
async def get_calendar_events(
    provider_id: str,
    calendar_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_results: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """Get calendar events"""
    
    try:
        events = await calendar_service.get_events(
            provider_id, calendar_id, start_time, end_time, max_results, current_user.id
        )
        return events
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to retrieve events: {str(e)}"
        )

@api_router.put("/calendar/providers/{provider_id}/calendars/{calendar_id}/events/{event_id}", response_model=EventResponse)
async def update_calendar_event(
    provider_id: str,
    calendar_id: str,
    event_id: str,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update a calendar event"""
    
    try:
        # Convert to dict excluding None values
        event_dict = event_data.dict(exclude_unset=True)
        
        # Convert datetime objects
        if event_data.start_time:
            event_dict['start_time'] = event_data.start_time.isoformat()
        if event_data.end_time:
            event_dict['end_time'] = event_data.end_time.isoformat()
        
        event_response = await calendar_service.update_event(
            provider_id, calendar_id, event_id, event_dict, current_user.id
        )
        
        return event_response
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update event: {str(e)}"
        )

@api_router.delete("/calendar/providers/{provider_id}/calendars/{calendar_id}/events/{event_id}")
async def delete_calendar_event(
    provider_id: str,
    calendar_id: str,
    event_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a calendar event"""
    
    try:
        success = await calendar_service.delete_event(
            provider_id, calendar_id, event_id, current_user.id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {"message": "Event deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete event: {str(e)}"
        )

# Meeting Detection and Calendar Agent Routes
@api_router.post("/calendar/detect-meeting", response_model=MeetingDetectionResponse)
async def detect_meeting_intent(
    request: MeetingDetectionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Analyze email content for meeting intents"""
    
    try:
        detection_response = await calendar_agent.analyze_email_for_meetings(
            request.email_content,
            "Manual Detection",
            request.sender,
            request.user_timezone or current_user.timezone
        )
        
        return detection_response
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to detect meeting intent: {str(e)}"
        )

@api_router.get("/calendar/meeting-intents")
async def get_meeting_intents(current_user: User = Depends(get_current_active_user)):
    """Get all meeting intents for current user"""
    
    intents = await db.meeting_intents.find({
        "user_id": current_user.id
    }).sort("created_at", -1).to_list(100)
    
    return intents

@api_router.post("/calendar/meeting-intents/{intent_id}/confirm")
async def confirm_meeting_intent(
    intent_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Confirm a meeting intent and create calendar event"""
    
    # Find the meeting intent
    intent = await db.meeting_intents.find_one({
        "id": intent_id,
        "user_id": current_user.id
    })
    
    if not intent:
        raise HTTPException(status_code=404, detail="Meeting intent not found")
    
    if intent["status"] != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Meeting intent cannot be confirmed")
    
    try:
        # Check quota
        if not await check_email_quota(current_user):
            raise HTTPException(
                status_code=429,
                detail="Monthly email quota exceeded"
            )
        
        # Create calendar event using the calendar agent
        event_id = await calendar_agent._create_calendar_event(intent, current_user.id)
        
        if event_id:
            # Update intent status
            await db.meeting_intents.update_one(
                {"id": intent_id},
                {
                    "$set": {
                        "status": "created",
                        "created_event_id": event_id,
                        "processed_at": datetime.utcnow()
                    }
                }
            )
            
            # Increment usage
            await increment_email_usage(current_user.id)
            
            return {"message": "Meeting confirmed and calendar event created", "event_id": event_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create calendar event")
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to confirm meeting: {str(e)}"
        )
@api_router.post("/intents", response_model=Intent)
async def create_intent(intent: IntentCreate):
    intent_dict = intent.dict()
    intent_obj = Intent(**intent_dict)
    
    # Create embedding for intent description + examples
    text_for_embedding = f"{intent_obj.description} {' '.join(intent_obj.examples)}"
    embedding = await get_cohere_embedding(text_for_embedding)
    
    # Store with embedding
    doc = intent_obj.dict()
    doc["embedding"] = embedding
    await db.intents.insert_one(doc)
    return intent_obj

@api_router.get("/intents", response_model=List[Intent])
async def get_intents():
    intents = await db.intents.find().to_list(1000)
    return [Intent(**intent) for intent in intents]

@api_router.get("/intents/{intent_id}", response_model=Intent)
async def get_intent(intent_id: str):
    intent_doc = await db.intents.find_one({"id": intent_id})
    if not intent_doc:
        raise HTTPException(status_code=404, detail="Intent not found")
    return Intent(**intent_doc)

@api_router.put("/intents/{intent_id}", response_model=Intent)
async def update_intent(intent_id: str, intent: IntentCreate):
    # Check if intent exists
    existing_intent = await db.intents.find_one({"id": intent_id})
    if not existing_intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    # Prepare update data
    update_data = intent.dict()
    update_data["updated_at"] = datetime.utcnow()
    
    # Regenerate embedding if description or examples changed
    old_text = f"{existing_intent.get('description', '')} {' '.join(existing_intent.get('examples', []))}"
    new_text = f"{intent.description} {' '.join(intent.examples)}"
    
    if old_text != new_text:
        update_data["embedding"] = await get_cohere_embedding(new_text)
    
    # Update in database
    await db.intents.update_one(
        {"id": intent_id},
        {"$set": update_data}
    )
    
    # Return updated intent
    updated_intent = await db.intents.find_one({"id": intent_id})
    return Intent(**updated_intent)

@api_router.delete("/intents/{intent_id}")
async def delete_intent(intent_id: str):
    result = await db.intents.delete_one({"id": intent_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Intent not found")
    return {"message": "Intent deleted successfully"}

# Email Account Management Routes
@api_router.get("/email-providers")
async def get_email_providers():
    return EMAIL_PROVIDERS

@api_router.post("/email-accounts", response_model=EmailAccount)
async def create_email_account(account: EmailAccountCreate):
    account_dict = account.dict()
    
    # Auto-fill provider settings if not custom
    if account.provider != "custom" and account.provider in EMAIL_PROVIDERS:
        provider_config = EMAIL_PROVIDERS[account.provider]
        account_dict["imap_server"] = provider_config["imap_server"]
        account_dict["imap_port"] = provider_config["imap_port"]
        account_dict["smtp_server"] = provider_config["smtp_server"]
        account_dict["smtp_port"] = provider_config["smtp_port"]
    
    account_obj = EmailAccount(**account_dict)
    await db.email_accounts.insert_one(account_obj.dict())
    return account_obj

@api_router.get("/email-accounts", response_model=List[EmailAccount])
async def get_email_accounts():
    accounts = await db.email_accounts.find().to_list(1000)
    # Don't return passwords in response
    for account in accounts:
        account["password"] = "***"
    return [EmailAccount(**account) for account in accounts]

@api_router.get("/email-accounts/{account_id}", response_model=EmailAccount)
async def get_email_account(account_id: str):
    account_doc = await db.email_accounts.find_one({"id": account_id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Email account not found")
    # Don't return password
    account_doc["password"] = "***"
    return EmailAccount(**account_doc)

@api_router.put("/email-accounts/{account_id}", response_model=EmailAccount)
async def update_email_account(account_id: str, account: EmailAccountCreate):
    # Check if account exists
    existing_account = await db.email_accounts.find_one({"id": account_id})
    if not existing_account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    # Prepare update data
    update_data = account.dict()
    update_data["updated_at"] = datetime.utcnow()
    
    # Auto-fill provider settings if not custom
    if account.provider != "custom" and account.provider in EMAIL_PROVIDERS:
        provider_config = EMAIL_PROVIDERS[account.provider]
        update_data["imap_server"] = provider_config["imap_server"]
        update_data["imap_port"] = provider_config["imap_port"]
        update_data["smtp_server"] = provider_config["smtp_server"]
        update_data["smtp_port"] = provider_config["smtp_port"]
    
    # If connection settings changed, remove existing connection to force reconnect
    connection_fields = ['imap_server', 'imap_port', 'smtp_server', 'smtp_port', 'username', 'password']
    connection_changed = any(existing_account.get(field) != update_data.get(field) for field in connection_fields)
    
    if connection_changed:
        global polling_service
        if polling_service and account_id in polling_service.connections:
            try:
                polling_service.connections[account_id].disconnect_imap()
                del polling_service.connections[account_id]
                logger.info(f"🔌 Removed connection for updated account: {account.email}")
            except Exception as e:
                logger.warning(f"⚠️  Error removing connection during update: {str(e)}")
    
    # Update in database
    await db.email_accounts.update_one(
        {"id": account_id},
        {"$set": update_data}
    )
    
    # Return updated account (without password)
    updated_account = await db.email_accounts.find_one({"id": account_id})
    updated_account["password"] = "***"
    return EmailAccount(**updated_account)

@api_router.delete("/email-accounts/{account_id}")
async def delete_email_account(account_id: str):
    # Remove connection if exists
    global polling_service
    if polling_service and account_id in polling_service.connections:
        try:
            polling_service.connections[account_id].disconnect_imap()
            del polling_service.connections[account_id]
            logger.info(f"🔌 Removed connection for deleted account")
        except Exception as e:
            logger.warning(f"⚠️  Error removing connection during delete: {str(e)}")
    
    result = await db.email_accounts.delete_one({"id": account_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Email account not found")
    return {"message": "Email account deleted successfully"}

@api_router.put("/email-accounts/{account_id}/toggle")
async def toggle_email_account(account_id: str):
    """Toggle email account active status"""
    account = await db.email_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    new_status = not account.get("is_active", True)
    await db.email_accounts.update_one(
        {"id": account_id},
        {"$set": {"is_active": new_status}}
    )
    
    # If deactivating, remove connection
    if not new_status:
        global polling_service
        if polling_service and account_id in polling_service.connections:
            try:
                polling_service.connections[account_id].disconnect_imap()
                del polling_service.connections[account_id]
                logger.info(f"🔌 Removed connection for deactivated account: {account.get('email')}")
            except Exception as e:
                logger.warning(f"⚠️  Error removing connection during deactivation: {str(e)}")
    
    return {"message": f"Account {'activated' if new_status else 'deactivated'} successfully"}

@api_router.post("/email-accounts/{account_id}/polling")
async def control_account_polling(account_id: str, request: PollingControlRequest):
    """Control polling for individual email account"""
    account = await db.email_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    global polling_service
    if not polling_service:
        raise HTTPException(status_code=500, detail="Polling service not initialized")
    
    if request.action == "start":
        # Activate account and add to polling
        await db.email_accounts.update_one(
            {"id": account_id},
            {"$set": {"is_active": True}}
        )
        
        # Force create new connection on next poll
        if account_id in polling_service.connections:
            try:
                polling_service.connections[account_id].disconnect_imap()
                del polling_service.connections[account_id]
            except Exception as e:
                logger.warning(f"⚠️  Error removing old connection: {str(e)}")
        
        return {"message": f"Polling started for account: {account['email']}"}
    
    elif request.action == "stop":
        # Deactivate account and remove from polling
        await db.email_accounts.update_one(
            {"id": account_id},
            {"$set": {"is_active": False}}
        )
        
        # Remove connection
        if account_id in polling_service.connections:
            try:
                polling_service.connections[account_id].disconnect_imap()
                del polling_service.connections[account_id]
                logger.info(f"🔌 Stopped polling for account: {account['email']}")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping polling: {str(e)}")
        
        return {"message": f"Polling stopped for account: {account['email']}"}
    
    elif request.action == "status":
        is_active = account.get("is_active", False)
        has_connection = account_id in polling_service.connections
        last_polled = account.get("last_polled")
        
        return {
            "account_id": account_id,
            "email": account["email"],
            "polling_active": is_active,
            "has_connection": has_connection,
            "last_polled": last_polled.isoformat() if last_polled else None,
            "last_uid": account.get("last_uid", 0)
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start', 'stop', or 'status'")

# Knowledge Base Routes
@api_router.post("/knowledge-base", response_model=KnowledgeBase)
async def create_knowledge_base(kb: KnowledgeBaseCreate):
    kb_dict = kb.dict()
    kb_obj = KnowledgeBase(**kb_dict)
    
    # Create embedding for content
    embedding = await get_cohere_embedding(kb_obj.content)
    
    # Store with embedding
    doc = kb_obj.dict()
    doc["embedding"] = embedding
    await db.knowledge_base.insert_one(doc)
    return kb_obj

@api_router.get("/knowledge-base", response_model=List[KnowledgeBase])
async def get_knowledge_base():
    kb_items = await db.knowledge_base.find().to_list(1000)
    return [KnowledgeBase(**kb) for kb in kb_items]

@api_router.get("/knowledge-base/{kb_id}", response_model=KnowledgeBase)
async def get_knowledge_base_item(kb_id: str):
    kb_doc = await db.knowledge_base.find_one({"id": kb_id})
    if not kb_doc:
        raise HTTPException(status_code=404, detail="Knowledge base item not found")
    return KnowledgeBase(**kb_doc)

@api_router.put("/knowledge-base/{kb_id}", response_model=KnowledgeBase)
async def update_knowledge_base(kb_id: str, kb: KnowledgeBaseCreate):
    # Check if KB item exists
    existing_kb = await db.knowledge_base.find_one({"id": kb_id})
    if not existing_kb:
        raise HTTPException(status_code=404, detail="Knowledge base item not found")
    
    # Prepare update data
    update_data = kb.dict()
    update_data["updated_at"] = datetime.utcnow()
    
    # Regenerate embedding if content changed
    if existing_kb.get('content', '') != kb.content:
        update_data["embedding"] = await get_cohere_embedding(kb.content)
    
    # Update in database
    await db.knowledge_base.update_one(
        {"id": kb_id},
        {"$set": update_data}
    )
    
    # Return updated KB item
    updated_kb = await db.knowledge_base.find_one({"id": kb_id})
    return KnowledgeBase(**updated_kb)

@api_router.delete("/knowledge-base/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    result = await db.knowledge_base.delete_one({"id": kb_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Knowledge base item not found")
    return {"message": "Knowledge base item deleted successfully"}

# Email Processing Routes
@api_router.post("/emails/test")
async def test_email_processing(request: EmailTestRequest):
    """Test email processing with manual input"""
    # Create a test email message
    email_obj = EmailMessage(
        account_id=request.account_id,
        message_id=f"test-{uuid.uuid4()}",
        thread_id=f"thread-{uuid.uuid4()}",
        subject=request.subject,
        sender=request.sender,
        recipient="test@example.com",
        body=request.body,
        received_at=datetime.utcnow(),
        status="processing"
    )
    
    # Store in database
    await db.emails.insert_one(email_obj.dict())
    
    # Process the email
    await process_email_async(email_obj.id)
    
    # Return processed email
    processed_email = await db.emails.find_one({"id": email_obj.id})
    return EmailMessage(**processed_email)

@api_router.post("/emails/{email_id}/send")
async def send_email_reply(email_id: str, request: SendEmailRequest):
    """Send email reply"""
    email_doc = await db.emails.find_one({"id": email_id})
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    if email_doc['status'] not in ['ready_to_send', 'needs_redraft'] and not request.manual_override:
        raise HTTPException(status_code=400, detail="Email not ready to send")
    
    # Get account
    account_doc = await db.email_accounts.find_one({"id": email_doc['account_id']})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    # Create connection and send
    connection = EmailConnection(account_doc)
    
    # Extract sender email
    sender_email = email_doc['sender']
    if '<' in sender_email:
        sender_email = sender_email.split('<')[1].split('>')[0]
    
    # Prepare reply subject
    subject = email_doc['subject']
    if not subject.lower().startswith('re:'):
        subject = f"Re: {subject}"
    
    # Send email
    success = connection.send_email(
        to_email=sender_email,
        subject=subject,
        body=email_doc['draft'],
        body_html=email_doc['draft_html'],
        message_id_to_reply=email_doc['message_id'],
        references=email_doc.get('references', '')
    )
    
    if success:
        # Update status to sent
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {
                "status": "sent",
                "sent_at": datetime.utcnow()
            }}
        )
        return {"message": "Email sent successfully"}
    else:
        # Mark as failed to send
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "send_failed"}}
        )
        raise HTTPException(status_code=500, detail="Failed to send email")

# Email Polling Control Routes
@api_router.post("/polling/control")
async def control_email_polling(request: PollingControlRequest):
    """Control email polling service"""
    global polling_service
    
    if request.action == "start":
        if polling_service and polling_service.is_running:
            return {"message": "Email polling is already running"}
        
        polling_service = get_polling_service(mongo_url, os.environ['DB_NAME'])
        # Start polling in background
        asyncio.create_task(polling_service.start_polling())
        return {"message": "Email polling started"}
    
    elif request.action == "stop":
        if polling_service:
            polling_service.stop_polling()
            return {"message": "Email polling stopped"}
        return {"message": "Email polling was not running"}
    
    elif request.action == "status":
        if polling_service and polling_service.is_running:
            return {
                "status": "running",
                "active_connections": len(polling_service.connections)
            }
        return {"status": "stopped"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start', 'stop', or 'status'")

@api_router.get("/polling/status")
async def get_polling_status():
    """Get polling service status"""
    global polling_service
    if polling_service and polling_service.is_running:
        return {
            "status": "running",
            "active_connections": len(polling_service.connections)
        }
    return {"status": "stopped"}

@api_router.get("/polling/accounts-status")
async def get_all_accounts_polling_status():
    """Get polling status for all accounts"""
    global polling_service
    
    accounts = await db.email_accounts.find().to_list(1000)
    account_statuses = []
    
    for account in accounts:
        account_id = account["id"]
        is_active = account.get("is_active", False)
        has_connection = polling_service and account_id in polling_service.connections if polling_service else False
        last_polled = account.get("last_polled")
        
        account_statuses.append({
            "account_id": account_id,
            "email": account["email"],
            "name": account.get("name", ""),
            "polling_active": is_active,
            "has_connection": has_connection,
            "last_polled": last_polled.isoformat() if last_polled else None,
            "last_uid": account.get("last_uid", 0)
        })
    
    return {
        "polling_service_running": polling_service.is_running if polling_service else False,
        "total_accounts": len(accounts),
        "active_accounts": len([a for a in account_statuses if a["polling_active"]]),
        "connected_accounts": len([a for a in account_statuses if a["has_connection"]]),
        "accounts": account_statuses
    }

def is_bounce_or_delivery_error(email_message: EmailMessage) -> bool:
    """Check if email is a bounce/delivery error notification that should be ignored"""
    
    # Check sender patterns for delivery errors
    sender_lower = email_message.sender.lower()
    delivery_error_senders = [
        'mailer-daemon', 'postmaster', 'mail delivery subsystem',
        'delivery-daemon', 'no-reply', 'noreply', 'bounce',
        'mail-daemon', 'mailerdaemon', 'delivery@', 'bounce@'
    ]
    
    for error_sender in delivery_error_senders:
        if error_sender in sender_lower:
            return True
    
    # Check subject patterns
    subject_lower = email_message.subject.lower()
    delivery_error_subjects = [
        'delivery status notification', 'undelivered mail returned',
        'mail delivery failed', 'delivery failure', 'message not delivered',
        'returned mail', 'undeliverable', 'bounce', 'mail system error',
        'delivery report', 'non-delivery report', 'message delivery failure',
        'mail could not be delivered', 'delivery notification'
    ]
    
    for error_subject in delivery_error_subjects:
        if error_subject in subject_lower:
            return True
    
    # Check body content for delivery error indicators
    body_lower = email_message.body.lower()
    delivery_error_body_patterns = [
        '550 5.1.1', '550 5.4.1', 'smtp error', 'delivery failed',
        'message was not delivered', 'user unknown', 'mailbox unavailable',
        'recipient address rejected', 'dns lookup failed'
    ]
    
    for error_pattern in delivery_error_body_patterns:
        if error_pattern in body_lower:
            return True
    
    return False

async def classify_email_intents(email_message: EmailMessage) -> List[Dict[str, Any]]:
    """Classify email intents using Cohere embeddings, skip delivery errors"""
    
    # Skip delivery error/bounce emails
    if is_bounce_or_delivery_error(email_message):
        logger.info(f"🚫 Skipping delivery error/bounce email: {email_message.subject}")
        return []
    
    # Get email embedding
    email_embedding = await get_cohere_embedding(email_message.body)
    
    # Get all intents with embeddings
    intents = await db.intents.find().to_list(1000)
    
    intent_scores = []
    for intent in intents:
        if "embedding" in intent:
            similarity = cosine_similarity(email_embedding, intent["embedding"])
            if similarity >= intent.get("confidence_threshold", 0.7):
                intent_scores.append({
                    "intent_id": intent["id"],
                    "name": intent["name"],
                    "description": intent["description"],
                    "system_prompt": intent.get("system_prompt", ""),
                    "confidence": similarity,
                    "is_meeting_related": intent.get("is_meeting_related", False)
                })
    
    # Return top 3 intents
    intent_scores.sort(key=lambda x: x["confidence"], reverse=True)
    return intent_scores[:3]

async def generate_draft(email_message: EmailMessage, intents: List[Dict[str, Any]]) -> Dict[str, str]:
    """Generate email draft using Agent A (Groq API) with enhanced KB usage and link insertion"""
    
    # Skip generating draft for delivery errors
    if is_bounce_or_delivery_error(email_message):
        logger.info(f"🚫 Skipping draft generation for delivery error: {email_message.subject}")
        return {
            "plain_text": "",
            "html": "",
            "reasoning": "Skipped - delivery error/bounce email detected"
        }
    
    # Get account info
    account = await db.email_accounts.find_one({"id": email_message.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    # Get enhanced knowledge base context with links
    kb_data = await get_enhanced_knowledge_context(email_message.body, intents)
    
    # Get thread history to avoid duplicates
    thread_history = await get_thread_history(email_message)
    
    # Build context
    intent_descriptions = []
    system_prompts = []
    all_links = kb_data.get("links", [])
    
    for intent in intents:
        intent_descriptions.append(f"- {intent['name']}: {intent['description']} (confidence: {intent['confidence']:.2f})")
        if intent.get('system_prompt'):
            system_prompts.append(intent['system_prompt'])
    
    # Prepare thread context
    thread_context = ""
    if thread_history:
        thread_context = "THREAD HISTORY (avoid repeating exact content):\n"
        for i, prev_email in enumerate(thread_history[:2]):  # Show last 2 emails
            thread_context += f"Previous response {i+1}: {prev_email['draft'][:100]}...\n"
        thread_context += "\nIMPORTANT: Provide fresh, varied content. Do not repeat previous responses exactly.\n"
    
    # Prepare links section
    links_section = ""
    if all_links:
        links_section = f"\nRELEVANT LINKS TO INCLUDE:\n"
        for link in all_links[:3]:  # Limit to 3 most relevant links
            links_section += f"- {link}\n"
        links_section += "IMPORTANT: Include relevant links naturally in your response when appropriate.\n"
    
    # Extract sender name for personalized salutation
    sender_name = email_message.sender
    if '<' in sender_name:
        # Extract name from "John Doe <john.doe@example.com>" format
        sender_name = sender_name.split('<')[0].strip()
    elif '@' in sender_name:
        # Extract name from email address
        sender_name = sender_name.split('@')[0].replace('.', ' ').title()
    else:
        # Use sender name as is
        sender_name = sender_name.strip()
    
    # Clean up sender name - if it's too long or has numbers, use "there" instead
    if len(sender_name) > 30 or any(char.isdigit() for char in sender_name) or not sender_name.replace(' ', '').replace('.', '').isalpha():
        salutation = "Hello,"
    else:
        salutation = f"Dear {sender_name},"

    system_prompt = f"""You are Agent A - an email draft generator. Generate ONLY the email body content for a professional reply.

ACCOUNT PERSONA: {account.get('persona', 'Professional and helpful')}

EMAIL CONTEXT:
- Original Subject: {email_message.subject}
- From: {email_message.sender}
- Body: {email_message.body}

IDENTIFIED INTENTS:
{chr(10).join(intent_descriptions) if intent_descriptions else "No specific intents identified"}

INTENT-SPECIFIC GUIDANCE:
{chr(10).join(system_prompts) if system_prompts else "No specific guidance provided"}

{kb_data.get("context", "")}

{thread_context}

{links_section}

CRITICAL INSTRUCTIONS:
1. MUST start with the salutation: "{salutation}"
2. Generate ONLY the email body content - no subject lines, NO SIGNATURES, no placeholders
3. Do not include any reasoning, thinking, or meta-content
4. MUST use information from the knowledge base when relevant - this is critical
5. Include relevant links naturally in the response when provided above
6. Keep response comprehensive but professional (200-400 words when detailed info is needed)
7. Address all identified intents directly using knowledge base information
8. Maintain a {account.get('persona', 'professional')} tone
9. Include actionable next steps where appropriate
10. If thread history exists, provide varied content - do not repeat previous responses exactly
11. When links are provided, integrate them naturally (e.g., "You can learn more at [link]" or "Please visit [link] for details")
12. DO NOT include any signatures, closing remarks like "Best regards", "Sincerely", etc. - these will be added automatically
13. End the email body with the main content, not with a signature block

Generate the email body content now, ensuring you start with "{salutation}" and use the knowledge base information:"""

    messages = [
        {"role": "user", "content": f"Generate a comprehensive email body response using the knowledge base information and including relevant links for: {email_message.body}"}
    ]
    
    response = await groq_chat_completion(messages, system_prompt)
    logger.info(f"📝 Raw Groq response length: {len(response)}")
    
    # Clean the response to remove any unwanted content
    clean_response = response.strip()
    logger.info(f"📝 After strip: {len(clean_response)}")
    
    # Remove any <think> tags or reasoning content
    import re
    clean_response = re.sub(r'<think>.*?</think>', '', clean_response, flags=re.DOTALL)
    clean_response = re.sub(r'PLAIN_TEXT:|HTML:|Subject:|Re:.*?\n', '', clean_response)
    clean_response = re.sub(r'^-+|^=+', '', clean_response, flags=re.MULTILINE)  # Remove separator lines
    logger.info(f"📝 After basic cleaning: {len(clean_response)}")
    
    # Enhanced signature removal to prevent duplication
    # Remove common signature patterns that AI might generate - FIXED to be less aggressive
    signature_patterns = [
        r'\n\n(Best regards|Sincerely|Kind regards|Warm regards|Regards)\s*,?\s*\n+.*$',  # More specific signature patterns
        r'\n\n---+.*$',  # Separator lines
        r'\n\n\*+.*$',   # Asterisk lines
        r'\n\nWith (best )?regards,?\s*\n+.*$',  # "With regards" patterns
    ]
    
    for i, pattern in enumerate(signature_patterns):
        before_len = len(clean_response)
        clean_response = re.sub(pattern, '', clean_response, flags=re.DOTALL | re.IGNORECASE)
        after_len = len(clean_response)
        if before_len != after_len:
            logger.warning(f"📝 Pattern {i+1} removed {before_len - after_len} characters")
    
    clean_response = clean_response.strip()
    logger.info(f"📝 Final cleaned response length: {len(clean_response)}")
    if len(clean_response) < 50:
        logger.error(f"📝 CRITICAL: Response too short! Content: '{clean_response}'")
    
    
    # Generate enhanced HTML version from plain text with proper link formatting
    html_version = clean_response.replace('\n\n', '</p><p>').replace('\n', '<br>')
    if html_version and not html_version.startswith('<p>'):
        html_version = f"<p>{html_version}</p>"
    
    # Make links clickable in HTML
    url_pattern = r'(https?://[^\s<>"{}|\\^`[\]]+)'
    html_version = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', html_version)
    
    return {
        "plain_text": clean_response,
        "html": html_version,
        "reasoning": f"Used KB items: {kb_data.get('items_count', 0)}, Links included: {len(all_links)}, Intents: {', '.join([i['name'] for i in intents])}"
    }

async def validate_final_email(email_message: EmailMessage, draft: Dict[str, str], intents: List[Dict[str, Any]], account_config: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced validation that checks the final email including signature"""
    
    # Skip validation for delivery errors
    if is_bounce_or_delivery_error(email_message):
        return {
            "status": "SKIP",
            "feedback": "Delivery error email - no response needed",
            "coverage_report": "Email identified as delivery error/bounce notification"
        }
    
    # Prepare final email content with signature
    final_plain_text = draft['plain_text']
    final_html = draft['html']
    
    signature = account_config.get('signature', '')
    if signature:
        final_plain_text += f"\n\n{signature}"
        # Convert signature to HTML properly
        import html
        html_signature = html.escape(signature).replace('\n', '<br>')
        # Convert email addresses to mailto links
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        html_signature = re.sub(email_pattern, r'<a href="mailto:\g<0>">\g<0></a>', html_signature)
        # Convert URLs to clickable links
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        html_signature = re.sub(url_pattern, r'<a href="\g<0>">\g<0></a>', html_signature)
        final_html += f"<br><br>{html_signature}"
    
    # Create final draft object for validation
    final_draft = {
        'plain_text': final_plain_text,
        'html': final_html
    }
    
    # Get enhanced KB context and links for validation
    kb_data = await get_enhanced_knowledge_context(email_message.body, intents)
    thread_history = await get_thread_history(email_message)
    
    intent_descriptions = [f"- {intent['name']}: {intent['description']}" for intent in intents]
    
    # Check for knowledge base usage
    kb_info_present = kb_data.get("has_relevant_info", False)
    kb_content_used = any(
        kb_item["title"].lower() in final_draft['plain_text'].lower() or 
        any(word in final_draft['plain_text'].lower() for word in kb_item["content"].lower().split()[:10])
        for kb_item in [{"title": "test", "content": kb_data.get("context", "")}]
    )
    
    # Check for links inclusion
    expected_links = kb_data.get("links", [])
    links_included = any(link in final_draft['plain_text'] for link in expected_links) if expected_links else True
    
    # Check for thread duplicate avoidance
    avoids_duplicates = True
    if thread_history:
        for prev_email in thread_history:
            prev_draft = prev_email.get('draft', '')
            if prev_draft and len(prev_draft) > 50:
                # Check if current draft is too similar to previous ones
                similarity_words = set(final_draft['plain_text'].lower().split()) & set(prev_draft.lower().split())
                if len(similarity_words) > len(final_draft['plain_text'].split()) * 0.6:  # More than 60% word overlap
                    avoids_duplicates = False
                    break
    
    system_prompt = f"""You are Agent B - an enhanced email validator. Check if the FINAL EMAIL (including signature) correctly addresses the email, uses knowledge base information, includes relevant links, and avoids duplicating previous responses.

ORIGINAL EMAIL:
Subject: {email_message.subject}
From: {email_message.sender}
Body: {email_message.body}

IDENTIFIED INTENTS TO ADDRESS:
{chr(10).join(intent_descriptions) if intent_descriptions else "No specific intents"}

AVAILABLE KNOWLEDGE BASE INFORMATION:
{kb_data.get("context", "No knowledge base information available")}

EXPECTED LINKS TO INCLUDE:
{chr(10).join(f"- {link}" for link in expected_links) if expected_links else "No specific links required"}

THREAD HISTORY:
{f"Previous responses exist - final email should provide varied content" if thread_history else "No previous responses in thread"}

ACCOUNT SIGNATURE:
{signature if signature else "No signature configured"}

FINAL EMAIL TO VALIDATE (INCLUDING SIGNATURE):
{final_draft['plain_text']}

VALIDATION CRITERIA:
1. Does the final email address each identified intent appropriately?
2. Is relevant knowledge base information incorporated into the response?
3. Are required links included naturally in the response?
4. Does the response avoid duplicating previous thread responses?
5. Is the tone appropriate and professional?
6. Are actionable next steps provided where needed?
7. Is the response length appropriate for the inquiry complexity?
8. CRITICAL: Does the final email contain any placeholders like [name], [insert link], {{company}}, <add here>, TODO, INSERT, etc.?
9. CRITICAL: Are all sentences complete without obvious gaps, underscores, or ellipses indicating missing content?
10. Is the signature properly formatted and professional?

AUTOMATED CHECK RESULTS:
- KB Information Available: {kb_info_present}
- Expected Links Count: {len(expected_links)}
- Thread History Present: {len(thread_history) > 0}
- Signature Included: {bool(signature)}

IMPORTANT: Start your response with either "PASS:" or "FAIL:" followed by detailed explanation.

For PASS: The final email must address intents, use available KB information, include relevant links, provide unique content, have proper signature, AND contain NO placeholders or incomplete sections.
For FAIL: Clearly state what's missing - KB usage, links, intent coverage, duplicate content issues, signature formatting issues, OR any placeholders/incomplete content that must be completed before sending.

CRITICAL: This final email (including signature) will be sent to the customer. Ensure it's complete, professional, and ready for delivery without any placeholders or missing information.

Validate the final email now:"""

    messages = [
        {"role": "user", "content": "Please validate this final email response (including signature) focusing on knowledge base usage, link inclusion, signature formatting, and thread uniqueness. Start with PASS: or FAIL:"}
    ]
    
    validation_response = await groq_chat_completion(messages, system_prompt)
    
    # Clean and properly parse the validation response
    validation_response = validation_response.strip()
    
    # Remove any thinking tags if present
    import re
    validation_response = re.sub(r'<think>.*?</think>', '', validation_response, flags=re.DOTALL).strip()
    
    # Determine if it's a pass or fail - check the entire response
    is_pass = "PASS:" in validation_response.upper() or validation_response.upper().startswith("PASS")
    
    # Additional automated checks including placeholder detection
    automated_issues = []
    
    # Check for placeholders in the final email
    placeholder_patterns = [
        r'\[.*?\]',  # [name], [insert link], [company name]
        r'\{.*?\}',  # {name}, {company}
        r'{{.*?}}',  # {{name}}, {{company}}
        r'<.*?>',    # <name>, <insert here>
        r'XXX.*?XXX',  # XXXNAMEXXXX
        r'TODO',     # TODO: add name
        r'INSERT',   # INSERT LINK HERE
        r'PLACEHOLDER', # PLACEHOLDER text
        r'your name here',  # common placeholder text
        r'company name',    # placeholder for company
    ]
    
    found_placeholders = []
    final_text = final_draft['plain_text'].lower()
    for pattern in placeholder_patterns:
        matches = re.findall(pattern, final_draft['plain_text'], re.IGNORECASE)
        if matches:
            found_placeholders.extend(matches)
    
    if found_placeholders:
        automated_issues.append(f"Final email contains placeholders that need to be replaced: {', '.join(found_placeholders[:3])}")
    
    # Check for incomplete sentences or obvious gaps
    incomplete_patterns = [
        r'\.\.\.+',  # Multiple dots indicating incomplete
        r'\s+_+\s+', # Underscores as placeholders
        r'TBD',      # To be determined
        r'TBA',      # To be announced  
    ]
    
    for pattern in incomplete_patterns:
        if re.search(pattern, final_draft['plain_text'], re.IGNORECASE):
            automated_issues.append(f"Final email appears to have incomplete content (pattern: {pattern})")
    
    # Override pass status if automated issues found
    if automated_issues:
        is_pass = False
        validation_response += f"\n\nAUTOMATED ISSUES DETECTED:\n" + "\n".join(automated_issues)
    
    # Create comprehensive validation report
    status = "PASS" if is_pass else "FAIL"
    
    return {
        "status": status,
        "feedback": validation_response,
        "automated_checks": {
            "kb_info_available": kb_info_present,
            "kb_content_used": kb_content_used,
            "links_expected": len(expected_links),
            "links_included": links_included,
            "avoids_duplicates": avoids_duplicates,
            "placeholders_found": found_placeholders,
            "signature_included": bool(signature)
        },
        "coverage_report": f"KB: {'✓' if kb_content_used else '✗'}, Links: {'✓' if links_included else '✗'}, Unique: {'✓' if avoids_duplicates else '✗'}, Signature: {'✓' if signature else '✗'}"
    }

async def validate_draft(email_message: EmailMessage, draft: Dict[str, str], intents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enhanced draft validation using Agent B - checks KB usage, links, and thread context"""
    
    # Skip validation for delivery errors
    if is_bounce_or_delivery_error(email_message):
        return {
            "status": "SKIP",
            "feedback": "Delivery error email - no response needed",
            "coverage_report": "Email identified as delivery error/bounce notification"
        }
    
    # Get enhanced KB context and links for validation
    kb_data = await get_enhanced_knowledge_context(email_message.body, intents)
    thread_history = await get_thread_history(email_message)
    
    intent_descriptions = [f"- {intent['name']}: {intent['description']}" for intent in intents]
    
    # Check for knowledge base usage
    kb_info_present = kb_data.get("has_relevant_info", False)
    kb_content_used = any(
        kb_item["title"].lower() in draft['plain_text'].lower() or 
        any(word in draft['plain_text'].lower() for word in kb_item["content"].lower().split()[:10])
        for kb_item in [{"title": "test", "content": kb_data.get("context", "")}]
    )
    
    # Check for links inclusion
    expected_links = kb_data.get("links", [])
    links_included = any(link in draft['plain_text'] for link in expected_links) if expected_links else True
    
    # Check for thread duplicate avoidance
    avoids_duplicates = True
    if thread_history:
        for prev_email in thread_history:
            prev_draft = prev_email.get('draft', '')
            if prev_draft and len(prev_draft) > 50:
                # Check if current draft is too similar to previous ones
                similarity_words = set(draft['plain_text'].lower().split()) & set(prev_draft.lower().split())
                if len(similarity_words) > len(draft['plain_text'].split()) * 0.6:  # More than 60% word overlap
                    avoids_duplicates = False
                    break
    
    system_prompt = f"""You are Agent B - an enhanced email draft validator. Check if the draft correctly addresses the email, uses knowledge base information, includes relevant links, and avoids duplicating previous responses.

ORIGINAL EMAIL:
Subject: {email_message.subject}
From: {email_message.sender}
Body: {email_message.body}

IDENTIFIED INTENTS TO ADDRESS:
{chr(10).join(intent_descriptions) if intent_descriptions else "No specific intents"}

AVAILABLE KNOWLEDGE BASE INFORMATION:
{kb_data.get("context", "No knowledge base information available")}

EXPECTED LINKS TO INCLUDE:
{chr(10).join(f"- {link}" for link in expected_links) if expected_links else "No specific links required"}

THREAD HISTORY:
{f"Previous responses exist - draft should provide varied content" if thread_history else "No previous responses in thread"}

DRAFT TO VALIDATE:
{draft['plain_text']}

VALIDATION CRITERIA:
1. Does the draft address each identified intent appropriately?
2. Is relevant knowledge base information incorporated into the response?
3. Are required links included naturally in the response?
4. Does the response avoid duplicating previous thread responses?
5. Is the tone appropriate and professional?
6. Are actionable next steps provided where needed?
7. Is the response length appropriate for the inquiry complexity?
8. CRITICAL: Does the draft contain any placeholders like [name], [insert link], {{company}}, <add here>, TODO, INSERT, etc.?
9. CRITICAL: Are all sentences complete without obvious gaps, underscores, or ellipses indicating missing content?

AUTOMATED CHECK RESULTS:
- KB Information Available: {kb_info_present}
- Expected Links Count: {len(expected_links)}
- Thread History Present: {len(thread_history) > 0}

IMPORTANT: Start your response with either "PASS:" or "FAIL:" followed by detailed explanation.

For PASS: The draft must address intents, use available KB information, include relevant links, provide unique content, AND contain NO placeholders or incomplete sections.
For FAIL: Clearly state what's missing - KB usage, links, intent coverage, duplicate content issues, OR any placeholders/incomplete content that must be completed before sending.

CRITICAL: This draft will be sent as the final email to the customer. Ensure it's complete, professional, and ready for delivery without any placeholders or missing information.

Validate the draft now:"""

    messages = [
        {"role": "user", "content": "Please validate this draft response focusing on knowledge base usage, link inclusion, and thread uniqueness. Start with PASS: or FAIL:"}
    ]
    
    validation_response = await groq_chat_completion(messages, system_prompt)
    
    # Clean and properly parse the validation response
    validation_response = validation_response.strip()
    
    # Remove any thinking tags if present
    import re
    validation_response = re.sub(r'<think>.*?</think>', '', validation_response, flags=re.DOTALL).strip()
    
    # Determine if it's a pass or fail - check the entire response
    is_pass = "PASS:" in validation_response.upper() or validation_response.upper().startswith("PASS")
    
    # Additional automated checks including placeholder detection
    automated_issues = []
    
    # Check for placeholders in the draft
    placeholder_patterns = [
        r'\[.*?\]',  # [name], [insert link], [company name]
        r'\{.*?\}',  # {name}, {company}
        r'{{.*?}}',  # {{name}}, {{company}}
        r'<.*?>',    # <name>, <insert here>
        r'XXX.*?XXX',  # XXXNAMEXXXX
        r'TODO',     # TODO: add name
        r'INSERT',   # INSERT LINK HERE
        r'PLACEHOLDER', # PLACEHOLDER text
        r'your name here',  # common placeholder text
        r'company name',    # placeholder for company
    ]
    
    found_placeholders = []
    draft_text = draft['plain_text'].lower()
    for pattern in placeholder_patterns:
        import re
        matches = re.findall(pattern, draft['plain_text'], re.IGNORECASE)
        if matches:
            found_placeholders.extend(matches)
    
    if found_placeholders:
        automated_issues.append(f"Draft contains placeholders that need to be replaced: {', '.join(found_placeholders[:3])}")
    
    # Check for incomplete sentences or obvious gaps
    incomplete_patterns = [
        r'\.\.\.+',  # Multiple dots indicating incomplete
        r'\s+_+\s+', # Underscores as placeholders
        r'TBD',      # To be determined
        r'TBA',      # To be announced  
    ]
    
    for pattern in incomplete_patterns:
        if re.search(pattern, draft['plain_text'], re.IGNORECASE):
            automated_issues.append("Draft contains incomplete sections or obvious gaps")
            break
    
    if kb_info_present and not any(word in draft['plain_text'].lower() for word in ["pricing", "feature", "product", "service", "support", "meeting", "demo", "consultation"]):
        automated_issues.append("Knowledge base information not effectively utilized")
    
    if expected_links and not links_included:
        automated_issues.append(f"Expected links not included: {', '.join(expected_links[:2])}")
    
    if not avoids_duplicates:
        automated_issues.append("Response too similar to previous thread responses")
    
    # Override to FAIL if automated checks find critical issues
    if automated_issues and is_pass:
        is_pass = False
        validation_response = f"FAIL: {validation_response[5:].strip()} Additionally: {'; '.join(automated_issues)}"
    
    # Extract just the feedback without the PASS:/FAIL: prefix
    feedback = validation_response
    if validation_response.startswith("PASS:"):
        feedback = validation_response[5:].strip()
    elif validation_response.startswith("FAIL:"):
        feedback = validation_response[5:].strip()
    
    return {
        "status": "PASS" if is_pass else "FAIL",
        "feedback": feedback,
        "coverage_report": validation_response,
        "kb_usage": kb_info_present,
        "links_included": len([link for link in expected_links if link in draft['plain_text']]),
        "avoids_duplicates": avoids_duplicates,
        "placeholder_check": {
            "has_placeholders": bool(found_placeholders),
            "placeholders_found": found_placeholders[:5] if found_placeholders else [],
            "is_complete": not bool(found_placeholders)
        }
    }

async def extract_links_from_knowledge_and_prompts(intents: List[Dict[str, Any]], kb_context: str) -> List[str]:
    """Extract URLs/links from knowledge base content and intent system prompts"""
    import re
    
    links = []
    
    # Extract links from knowledge base context
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    kb_links = re.findall(url_pattern, kb_context)
    links.extend(kb_links)
    
    # Extract links from intent system prompts
    for intent in intents:
        system_prompt = intent.get('system_prompt', '')
        prompt_links = re.findall(url_pattern, system_prompt)
        links.extend(prompt_links)
    
    # Remove duplicates while preserving order
    unique_links = []
    for link in links:
        if link not in unique_links:
            unique_links.append(link)
    
    return unique_links

async def get_thread_history(email_message: EmailMessage) -> List[Dict[str, Any]]:
    """Get previous emails in the same thread to avoid duplicate responses"""
    
    # Find emails in the same thread
    thread_emails = await db.emails.find({
        "thread_id": email_message.thread_id,
        "status": {"$in": ["sent", "ready_to_send"]},
        "id": {"$ne": email_message.id}  # Exclude current email
    }).sort("received_at", -1).limit(5).to_list(5)
    
    history = []
    for email in thread_emails:
        history.append({
            "subject": email.get("subject", ""),
            "draft": email.get("draft", ""),
            "intents": [intent.get("name") for intent in email.get("intents", [])],
            "sent_at": email.get("sent_at")
        })
    
    return history

async def get_enhanced_thread_context(email_message: EmailMessage) -> List[Dict[str, Any]]:
    """Get ALL emails in the same thread for comprehensive meeting detection analysis"""
    
    # Find ALL emails in the same thread regardless of status for meeting detection
    thread_emails = await db.emails.find({
        "thread_id": email_message.thread_id,
        "id": {"$ne": email_message.id}  # Exclude current email
    }).sort("received_at", -1).limit(10).to_list(10)  # Increased limit for better context
    
    context = []
    for email in thread_emails:
        # Include full email body for meeting analysis, not just drafts
        context.append({
            "subject": email.get("subject", ""),
            "body": email.get("body", ""),
            "sender": email.get("sender", ""),
            "received_at": email.get("received_at"),
            "status": email.get("status", ""),
            "intents": [intent.get("name") for intent in email.get("intents", [])],
        })
    
    return context

async def get_enhanced_knowledge_context(email_body: str, intents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enhanced knowledge base context with better retrieval and link extraction"""
    # Get email embedding
    email_embedding = await get_cohere_embedding(email_body)
    
    # Get all knowledge base items with embeddings
    kb_items = await db.knowledge_base.find({"embedding": {"$exists": True}}).to_list(1000)
    
    relevant_items = []
    for item in kb_items:
        if "embedding" in item:
            similarity = cosine_similarity(email_embedding, item["embedding"])
            if similarity >= 0.5:  # Lower threshold for better coverage
                relevant_items.append({
                    "title": item["title"],
                    "content": item["content"],
                    "tags": item.get("tags", []),
                    "similarity": similarity
                })
    
    # Also include items that match intent keywords
    intent_keywords = []
    for intent in intents:
        intent_keywords.extend([intent['name'].lower(), intent['description'].lower()])
    
    for item in kb_items:
        item_text = f"{item['title']} {item['content']}".lower()
        for keyword in intent_keywords:
            if keyword in item_text and not any(existing['title'] == item['title'] for existing in relevant_items):
                relevant_items.append({
                    "title": item["title"],
                    "content": item["content"],
                    "tags": item.get("tags", []),
                    "similarity": 0.6  # Assign moderate similarity for keyword matches
                })
                break
    
    # Sort by similarity and take top 5 for better coverage
    relevant_items.sort(key=lambda x: x["similarity"], reverse=True)
    relevant_items = relevant_items[:5]
    
    # Extract links from knowledge base
    all_kb_text = " ".join([item["content"] for item in relevant_items])
    links = await extract_links_from_knowledge_and_prompts(intents, all_kb_text)
    
    if relevant_items:
        context = "RELEVANT KNOWLEDGE BASE INFORMATION:\n"
        for item in relevant_items:
            context += f"- {item['title']}: {item['content']}\n"
        context += f"\nTags: {', '.join(set([tag for item in relevant_items for tag in item.get('tags', [])]))}\n"
        
        return {
            "context": context,
            "links": links,
            "items_count": len(relevant_items),
            "has_relevant_info": True
        }
    else:
        return {
            "context": "No highly relevant knowledge base items found. Use general professional tone.",
            "links": links,
            "items_count": 0,
            "has_relevant_info": False
        }

async def get_knowledge_context(email_body: str) -> str:
    """Legacy function for backward compatibility"""
    result = await get_enhanced_knowledge_context(email_body, [])
    return result["context"]

async def auto_send_email(email_id: str):
    """Auto-send approved email if account has auto_send enabled"""
    try:
        # Get email
        email_doc = await db.emails.find_one({"id": email_id})
        if not email_doc or email_doc['status'] != 'ready_to_send':
            return
        
        # Get account
        account_doc = await db.email_accounts.find_one({"id": email_doc['account_id']})
        if not account_doc or not account_doc.get('is_active') or not account_doc.get('auto_send', True):
            return
        
        # Create connection
        connection = EmailConnection(account_doc)
        
        # Extract sender email
        sender_email = email_doc['sender']
        if '<' in sender_email:
            sender_email = sender_email.split('<')[1].split('>')[0]
        
        # Prepare reply subject
        subject = email_doc['subject']
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
        
        # Send email
        success = connection.send_email(
            to_email=sender_email,
            subject=subject,
            body=email_doc['draft'],
            body_html=email_doc['draft_html'],
            message_id_to_reply=email_doc['message_id'],
            references=email_doc.get('references', '')
        )
        
        if success:
            # Update status to sent
            await db.emails.update_one(
                {"id": email_id},
                {"$set": {
                    "status": "sent",
                    "sent_at": datetime.utcnow()
                }}
            )
            logger.info(f"✅ Auto-sent reply for email: {email_doc['subject']}")
            
            # CREATE FOLLOW-UP EMAILS if enabled for this account
            if account_doc.get('enable_follow_ups', True):
                try:
                    # Get user ID (assuming we can derive it from account)
                    user_doc = await db.users.find_one({"email": account_doc.get("email")})
                    if user_doc:
                        await create_follow_up_for_email(
                            email_id, 
                            account_doc['id'], 
                            user_doc['id']
                        )
                        logger.info(f"📅 Created follow-up schedule for email: {email_doc['subject']}")
                except Exception as e:
                    logger.error(f"Error creating follow-up for email {email_id}: {str(e)}")
            
        else:
            # Mark as failed to send
            await db.emails.update_one(
                {"id": email_id},
                {"$set": {"status": "send_failed"}}
            )
            
    except Exception as e:
        logger.error(f"❌ Error auto-sending email {email_id}: {str(e)}")
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "send_failed", "error": str(e)}}
        )

async def process_email_async(email_id: str):
    """Background task to process email through AI workflow with calendar integration"""
    try:
        # Get email
        email_doc = await db.emails.find_one({"id": email_id})
        if not email_doc:
            return
        
        email_message = EmailMessage(**email_doc)
        
        # CRITICAL: Check if this email is a response to an existing thread - cancel follow-ups if so
        thread_id = email_message.thread_id
        if thread_id:
            # Look for other emails in this thread that might have pending follow-ups
            thread_emails = await db.emails.find({
                "thread_id": thread_id,
                "id": {"$ne": email_id}
            }).sort("received_at", 1).to_list(100)
            
            if thread_emails:
                # Check if this email is a response (from different sender than original)
                original_email = thread_emails[0]  # Earliest email in thread
                original_sender = original_email.get("sender", "")
                current_sender = email_message.sender
                
                if (current_sender != original_sender and 
                    email_message.received_at > original_email.get("received_at", datetime.min)):
                    # This is a response - cancel pending follow-ups for this thread
                    cancelled_count = await cancel_follow_ups_for_thread(
                        thread_id, 
                        f"Response received from {current_sender}"
                    )
                    if cancelled_count > 0:
                        logger.info(f"📧 Response detected in thread {thread_id}: Cancelled {cancelled_count} pending follow-ups")
        
        # Get account info to find user
        account_doc = await db.email_accounts.find_one({"id": email_message.account_id})
        if not account_doc:
            logger.error(f"Account not found for email {email_id}")
            return
        
        # Find user associated with this account (for now, create a default user)
        user_doc = await db.users.find_one({"email": account_doc["email"]})
        if not user_doc:
            # Create a default user for this email account
            user_id = str(uuid.uuid4())
            next_month = datetime.utcnow().replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            
            default_user = {
                "id": user_id,
                "email": account_doc["email"],
                "full_name": account_doc.get("name", ""),
                "hashed_password": "default",  # This should be set properly
                "is_active": True,
                "email_quota": 100,
                "emails_used": 0,
                "quota_reset_date": next_month,
                "timezone": "UTC",
                "created_at": datetime.utcnow()
            }
            
            await db.users.insert_one(default_user)
            user_doc = default_user
        
        # Step 1: Check if this is a delivery error - skip processing if so
        if is_bounce_or_delivery_error(email_message):
            await db.emails.update_one(
                {"id": email_id},
                {"$set": {
                    "status": "ignored", 
                    "processed_at": datetime.utcnow(),
                    "intents": [],
                    "draft": "",
                    "validation_result": {
                        "status": "SKIP",
                        "feedback": "Delivery error/bounce email - no response needed"
                    }
                }}
            )
            logger.info(f"🚫 Ignored delivery error email: {email_message.subject}")
            return
        
        # Check user quota before processing
        if not await check_email_quota(User(**user_doc)):
            await db.emails.update_one(
                {"id": email_id},
                {"$set": {
                    "status": "quota_exceeded",
                    "processed_at": datetime.utcnow(),
                    "error": "User email quota exceeded"
                }}
            )
            logger.warning(f"Email processing skipped - quota exceeded for user {user_doc['id']}")
            return
        
        # Step 2: Classify intents (now takes EmailMessage object)
        intents = await classify_email_intents(email_message)
        
        # Update email with intents
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"intents": intents, "status": "classifying"}}
        )
        
        # Step 2.5: Always check for meeting intents and calendar integration
        # This ensures meeting detection runs for ALL emails, not just those with existing meeting intents
        calendar_action = None
        
        try:
            # Get thread context for better meeting detection - collect ALL messages in thread
            thread_context = await get_enhanced_thread_context(email_message)
            
            # Always analyze for meeting intents using the calendar agent
            # Let the agent decide based on email content, not pre-existing intents
            meeting_detection = await calendar_agent.analyze_email_for_meetings(
                email_message.body,
                email_message.subject,
                email_message.sender,
                user_doc.get("timezone", "UTC"),
                thread_context
            )
            
            logger.info(f"🔍 Meeting detection result: detected={meeting_detection.meeting_detected}, confidence={meeting_detection.confidence_score}")
            
            if meeting_detection.meeting_detected and meeting_detection.confidence_score >= 0.6:
                # Process meeting intent and potentially create calendar event only with high confidence
                calendar_action = await calendar_agent.process_meeting_intent(
                    email_id,
                    user_doc["id"],
                    meeting_detection,
                    email_message.thread_id
                )
                
                if calendar_action:
                    logger.info(f"📅 Calendar action completed: {calendar_action}")
            elif meeting_detection.meeting_detected:
                logger.info(f"📅 Meeting detected but confidence too low ({meeting_detection.confidence_score}) - no action taken")
            else:
                # Check if this is an update to existing meeting
                calendar_action = await calendar_agent.update_meeting_from_email(
                    email_message.body,
                    email_message.thread_id,
                    user_doc["id"],
                    user_doc.get("timezone", "UTC")
                )
                
                if calendar_action:
                    logger.info(f"📅 Meeting update completed: {calendar_action}")
                    
        except Exception as e:
            logger.error(f"Calendar integration error: {e}")
            # Continue with normal email processing even if calendar fails
        
        # Step 3: Generate draft
        draft = await generate_draft(email_message, intents)
        
        # Step 4: Update email with draft
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {
                "draft": draft["plain_text"],
                "draft_html": draft["html"],
                "status": "drafting",
                "calendar_action": calendar_action  # Store calendar action info
            }}
        )
        
        # Step 5: Validate final email with signature
        validation = await validate_final_email(email_message, draft, intents, account_doc)
        
        # Step 6: Determine final status based on validation
        if validation["status"] == "SKIP":
            final_status = "ignored"
        elif validation["status"] == "PASS":
            final_status = "ready_to_send"
        else:
            final_status = "needs_redraft"
        
        # Update email with validation
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {
                "validation_result": validation,
                "status": final_status,
                "processed_at": datetime.utcnow()
            }}
        )
        
        # Step 7: Auto-send if validation passed and account has auto_send enabled
        if validation["status"] == "PASS":
            if account_doc and account_doc.get('auto_send', True) and account_doc.get('is_active', True):
                await auto_send_email(email_id)
                # Increment email usage after successful send
                await increment_email_usage(user_doc["id"])
        
    except Exception as e:
        # Update email with error status
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "error", "error": str(e)}}
        )
        logger.error(f"❌ Error processing email {email_id}: {str(e)}")

@api_router.post("/emails/{email_id}/redraft")
async def redraft_email(email_id: str):
    """Request a redraft of an email"""
    email_doc = await db.emails.find_one({"id": email_id})
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email_message = EmailMessage(**email_doc)
    
    # Get previous validation feedback for improvement
    previous_feedback = email_message.validation_result.get("feedback", "") if email_message.validation_result else ""
    
    # Re-generate draft with feedback
    intents = email_message.intents
    draft = await generate_draft(email_message, intents)
    
    # Add improvement instruction based on previous feedback
    if previous_feedback:
        improvement_prompt = f"Previous draft had these issues: {previous_feedback}. Please address these in the new draft."
        # Here you could enhance the draft generation with the feedback
    
    # Get account info for validation with signature
    account_doc = await db.email_accounts.find_one({"id": email_message.account_id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Validate new final email with signature
    validation = await validate_final_email(email_message, draft, intents, account_doc)
    
    # Update email
    final_status = "ready_to_send" if validation["status"] == "PASS" else "escalate"
    await db.emails.update_one(
        {"id": email_id},
        {"$set": {
            "draft": draft["plain_text"],
            "draft_html": draft["html"],
            "validation_result": validation,
            "status": final_status,
            "processed_at": datetime.utcnow()
        }}
    )
    
    # CRITICAL FIX: Auto-send if validation passed and account has auto_send enabled
    if validation["status"] == "PASS":
        if account_doc and account_doc.get('auto_send', True) and account_doc.get('is_active', True):
            await auto_send_email(email_id)
            # Also increment email usage for redrafted emails
            user_doc = await db.users.find_one({"email": account_doc["email"]})
            if user_doc:
                await increment_email_usage(user_doc["id"])
    
    updated_email = await db.emails.find_one({"id": email_id})
    return EmailMessage(**updated_email)

@api_router.get("/emails", response_model=List[EmailMessage])
async def get_emails():
    emails = await db.emails.find().sort("received_at", -1).to_list(100)
    return [EmailMessage(**email) for email in emails]

@api_router.get("/emails/threads")
async def get_email_threads():
    """Get all email threads with their follow-ups and responses"""
    try:
        # Get all emails grouped by thread_id
        pipeline = [
            {"$sort": {"received_at": -1}},
            {"$group": {
                "_id": "$thread_id",
                "emails": {"$push": "$$ROOT"},
                "subject": {"$first": "$subject"},
                "thread_id": {"$first": "$thread_id"},
                "last_activity": {"$max": "$received_at"},
                "created_at": {"$min": "$received_at"}
            }},
            {"$sort": {"last_activity": -1}}
        ]
        
        email_groups = await db.emails.aggregate(pipeline).to_list(100)
        threads = []
        
        for group in email_groups:
            thread_id = group["thread_id"]
            emails = group["emails"]
            
            # Convert ObjectIds to strings and clean up the data
            for email in emails:
                if "_id" in email:
                    del email["_id"]
                # Ensure datetime fields are properly serialized
                if "received_at" in email and isinstance(email["received_at"], datetime):
                    email["received_at"] = email["received_at"].isoformat()
                if "created_at" in email and isinstance(email["created_at"], datetime):
                    email["created_at"] = email["created_at"].isoformat()
                if "processed_at" in email and email["processed_at"] and isinstance(email["processed_at"], datetime):
                    email["processed_at"] = email["processed_at"].isoformat()
                if "sent_at" in email and email["sent_at"] and isinstance(email["sent_at"], datetime):
                    email["sent_at"] = email["sent_at"].isoformat()
            
            # Get follow-ups for this thread
            follow_ups_cursor = await db.follow_up_emails.find({"thread_id": thread_id}).to_list(100)
            follow_ups = []
            for follow_up in follow_ups_cursor:
                if "_id" in follow_up:
                    del follow_up["_id"]
                # Clean datetime fields
                if "created_at" in follow_up and isinstance(follow_up["created_at"], datetime):
                    follow_up["created_at"] = follow_up["created_at"].isoformat()
                if "updated_at" in follow_up and isinstance(follow_up["updated_at"], datetime):
                    follow_up["updated_at"] = follow_up["updated_at"].isoformat()
                if "scheduled_time" in follow_up and isinstance(follow_up["scheduled_time"], datetime):
                    follow_up["scheduled_time"] = follow_up["scheduled_time"].isoformat()
                if "sent_time" in follow_up and follow_up["sent_time"] and isinstance(follow_up["sent_time"], datetime):
                    follow_up["sent_time"] = follow_up["sent_time"].isoformat()
                if "last_response_time" in follow_up and follow_up["last_response_time"] and isinstance(follow_up["last_response_time"], datetime):
                    follow_up["last_response_time"] = follow_up["last_response_time"].isoformat()
                follow_ups.append(follow_up)
            
            # Determine original email (first chronologically)
            original_email = min(emails, key=lambda e: datetime.fromisoformat(e["received_at"]) if isinstance(e["received_at"], str) else e["received_at"])
            
            # Separate responses from the original
            responses = [e for e in emails if e["id"] != original_email["id"]]
            
            # Check if thread has responses (emails from different senders)
            original_sender = original_email.get("sender", "")
            original_received_at = datetime.fromisoformat(original_email["received_at"]) if isinstance(original_email["received_at"], str) else original_email["received_at"]
            
            has_response = any(
                email.get("sender", "") != original_sender and 
                (datetime.fromisoformat(email.get("received_at", "")) if isinstance(email.get("received_at"), str) else email.get("received_at", datetime.min)) > original_received_at
                for email in responses
            )
            
            # Get unique participants  
            participants = list(set([
                email.get("sender", "") for email in emails
            ] + [
                email.get("recipient", "") for email in emails  
            ]))
            participants = [p for p in participants if p]  # Remove empty strings
            
            thread_data = {
                "thread_id": thread_id,
                "subject": group["subject"],
                "participants": participants,
                "original_email": original_email,
                "follow_ups": follow_ups,
                "responses": responses,
                "has_response": has_response,
                "follow_ups_active": not has_response,  # Stop follow-ups if response received
                "last_activity": group["last_activity"].isoformat() if isinstance(group["last_activity"], datetime) else group["last_activity"],
                "created_at": group["created_at"].isoformat() if isinstance(group["created_at"], datetime) else group["created_at"]
            }
            threads.append(thread_data)
            
        return threads
        
    except Exception as e:
        logger.error(f"Error fetching email threads: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch email threads: {str(e)}")

@api_router.get("/emails/{email_id}", response_model=EmailMessage)
async def get_email(email_id: str):
    email_doc = await db.emails.find_one({"id": email_id})
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    return EmailMessage(**email_doc)

# Dashboard/Stats Routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    total_emails = await db.emails.count_documents({})
    processed_emails = await db.emails.count_documents({"status": {"$in": ["ready_to_send", "sent"]}})
    escalated_emails = await db.emails.count_documents({"status": "escalate"})
    sent_emails = await db.emails.count_documents({"status": "sent"})
    total_intents = await db.intents.count_documents({})
    total_accounts = await db.email_accounts.count_documents({})
    active_accounts = await db.email_accounts.count_documents({"is_active": True})
    
    # Polling status
    global polling_service
    polling_status = "running" if polling_service and polling_service.is_running else "stopped"
    
    return {
        "total_emails": total_emails,
        "processed_emails": processed_emails,
        "sent_emails": sent_emails,
        "escalated_emails": escalated_emails,
        "total_intents": total_intents,
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "polling_status": polling_status,
        "processing_rate": processed_emails / total_emails * 100 if total_emails > 0 else 0
    }

# Google OAuth endpoints
@api_router.post("/oauth/google/authorize")
async def initiate_google_oauth(
    requested_services: List[str],
    current_user: User = Depends(get_current_active_user)
):
    """
    Initiate Google OAuth flow for email and/or calendar access
    
    Body: ["email", "calendar"] - services to authorize
    """
    valid_services = ["email", "calendar"]
    if not requested_services or not all(service in valid_services for service in requested_services):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid services. Must be one or both of: email, calendar"
        )
    
    try:
        auth_data = await google_oauth_service.generate_auth_url(
            user_id=current_user.id,
            requested_services=requested_services
        )
        
        return {
            "auth_url": auth_data["auth_url"],
            "state": auth_data["state"],
            "requested_services": requested_services,
            "message": "Redirect user to auth_url to complete OAuth flow"
        }
        
    except Exception as e:
        logger.error(f"OAuth initiation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth: {str(e)}"
        )

@api_router.get("/oauth/google/callback")
async def handle_google_oauth_callback(code: str, state: str):
    """
    Handle Google OAuth callback
    
    Query params: code, state
    """
    try:
        result = await google_oauth_service.handle_callback(code, state)
        
        return {
            "success": True,
            "user_id": result["user_id"],
            "authorized_services": result["authorized_services"],
            "requested_services": result["requested_services"],
            "user_info": result["user_info"],
            "message": f"Successfully authorized {', '.join(result['authorized_services'])} services"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )

@api_router.get("/oauth/google/status")
async def get_google_oauth_status(current_user: User = Depends(get_current_active_user)):
    """Get current Google OAuth authorization status"""
    try:
        status = await google_oauth_service.get_oauth_status(current_user.id)
        return status
    except Exception as e:
        logger.error(f"OAuth status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OAuth status: {str(e)}"
        )

@api_router.post("/oauth/google/revoke")
async def revoke_google_oauth(current_user: User = Depends(get_current_active_user)):
    """Revoke Google OAuth tokens"""
    try:
        success = await google_oauth_service.revoke_tokens(current_user.id)
        return {
            "success": success,
            "message": "OAuth tokens revoked successfully" if success else "Failed to revoke some tokens"
        }
    except Exception as e:
        logger.error(f"OAuth revoke error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke OAuth: {str(e)}"
        )

# Follow-up Configuration Routes
@api_router.get("/follow-up/config", response_model=FollowUpConfig)
async def get_follow_up_config(current_user: User = Depends(get_current_active_user)):
    """Get user's follow-up configuration"""
    config = await db.follow_up_configs.find_one({"user_id": current_user.id})
    
    if not config:
        # Create default config if none exists
        default_config = FollowUpConfig(user_id=current_user.id)
        await db.follow_up_configs.insert_one(default_config.dict())
        return default_config
    
    return config

@api_router.post("/follow-up/config", response_model=FollowUpConfig)
async def create_follow_up_config(
    config_data: FollowUpConfigCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create or update user's follow-up configuration"""
    existing_config = await db.follow_up_configs.find_one({"user_id": current_user.id})
    
    if existing_config:
        # Update existing config
        updated_data = config_data.dict()
        updated_data["updated_at"] = datetime.utcnow()
        
        await db.follow_up_configs.update_one(
            {"user_id": current_user.id},
            {"$set": updated_data}
        )
        
        updated_config = await db.follow_up_configs.find_one({"user_id": current_user.id})
        return updated_config
    else:
        # Create new config
        new_config = FollowUpConfig(user_id=current_user.id, **config_data.dict())
        await db.follow_up_configs.insert_one(new_config.dict())
        return new_config

@api_router.put("/follow-up/config", response_model=FollowUpConfig)
async def update_follow_up_config(
    config_updates: FollowUpConfigUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update user's follow-up configuration"""
    existing_config = await db.follow_up_configs.find_one({"user_id": current_user.id})
    
    if not existing_config:
        raise HTTPException(status_code=404, detail="Follow-up configuration not found")
    
    # Update only provided fields
    update_data = {k: v for k, v in config_updates.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.follow_up_configs.update_one(
        {"user_id": current_user.id},
        {"$set": update_data}
    )
    
    updated_config = await db.follow_up_configs.find_one({"user_id": current_user.id})
    return updated_config

# Follow-up Email Management Routes
@api_router.get("/follow-ups", response_model=List[FollowUpEmail])
async def get_follow_up_emails(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user)
):
    """Get user's follow-up emails"""
    query = {"user_id": current_user.id}
    if status:
        query["status"] = status
    
    follow_ups = await db.follow_up_emails.find(query).limit(limit).to_list(100)
    return follow_ups

# Follow-up Analytics Routes (must be before parameterized routes)
@api_router.get("/follow-ups/analytics")
async def get_follow_up_analytics(current_user: User = Depends(get_current_active_user)):
    """Get follow-up analytics for the user"""
    # Count follow-ups by status
    pipeline = [
        {"$match": {"user_id": current_user.id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    
    status_counts = {}
    async for result in db.follow_up_emails.aggregate(pipeline):
        status_counts[result["_id"]] = result["count"]
    
    # Count pending follow-ups due today
    today = datetime.utcnow().replace(hour=23, minute=59, second=59)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    pending_today = await db.follow_up_emails.count_documents({
        "user_id": current_user.id,
        "status": "pending",
        "scheduled_time": {"$gte": today_start, "$lte": today}
    })
    
    # Count overdue follow-ups
    overdue = await db.follow_up_emails.count_documents({
        "user_id": current_user.id,
        "status": "pending",
        "scheduled_time": {"$lt": datetime.utcnow()}
    })
    
    # Get response rate (follow-ups that received responses)
    total_sent = status_counts.get("sent", 0)
    responses_received = await db.follow_up_emails.count_documents({
        "user_id": current_user.id,
        "status": "sent",
        "response_received": True
    })
    
    response_rate = (responses_received / total_sent * 100) if total_sent > 0 else 0
    
    return {
        "status_counts": status_counts,
        "pending_today": pending_today,
        "overdue": overdue,
        "response_rate": round(response_rate, 2),
        "total_sent": total_sent,
        "responses_received": responses_received
    }

@api_router.get("/follow-ups/{follow_up_id}", response_model=FollowUpEmail)
async def get_follow_up_email(
    follow_up_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get specific follow-up email"""
    follow_up = await db.follow_up_emails.find_one({
        "id": follow_up_id,
        "user_id": current_user.id
    })
    
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up email not found")
    
    return follow_up

@api_router.post("/follow-ups", response_model=FollowUpEmail)
async def create_follow_up_email(
    follow_up_data: FollowUpEmailCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new follow-up email"""
    # Get the original email to validate and extract thread info
    original_email = await db.emails.find_one({"id": follow_up_data.original_email_id})
    if not original_email:
        raise HTTPException(status_code=404, detail="Original email not found")
    
    # Create follow-up email
    new_follow_up = FollowUpEmail(
        user_id=current_user.id,
        thread_id=original_email.get("thread_id", ""),
        **follow_up_data.dict()
    )
    
    await db.follow_up_emails.insert_one(new_follow_up.dict())
    return new_follow_up

@api_router.put("/follow-ups/{follow_up_id}", response_model=FollowUpEmail)
async def update_follow_up_email(
    follow_up_id: str,
    follow_up_updates: FollowUpEmailUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update follow-up email"""
    existing_follow_up = await db.follow_up_emails.find_one({
        "id": follow_up_id,
        "user_id": current_user.id
    })
    
    if not existing_follow_up:
        raise HTTPException(status_code=404, detail="Follow-up email not found")
    
    # Update only provided fields
    update_data = {k: v for k, v in follow_up_updates.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.follow_up_emails.update_one(
        {"id": follow_up_id, "user_id": current_user.id},
        {"$set": update_data}
    )
    
    updated_follow_up = await db.follow_up_emails.find_one({
        "id": follow_up_id,
        "user_id": current_user.id
    })
    return updated_follow_up

@api_router.delete("/follow-ups/{follow_up_id}")
async def delete_follow_up_email(
    follow_up_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete/cancel follow-up email"""
    result = await db.follow_up_emails.delete_one({
        "id": follow_up_id,
        "user_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Follow-up email not found")
    
    return {"message": "Follow-up email cancelled successfully"}

@api_router.post("/follow-ups/{follow_up_id}/send")
async def send_follow_up_email(
    follow_up_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Manually send a follow-up email"""
    follow_up = await db.follow_up_emails.find_one({
        "id": follow_up_id,
        "user_id": current_user.id
    })
    
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up email not found")
    
    if follow_up["status"] != "pending":
        raise HTTPException(status_code=400, detail="Follow-up email is not in pending status")
    
    try:
        # Get email account
        account = await db.email_accounts.find_one({"id": follow_up["account_id"]})
        if not account:
            raise HTTPException(status_code=404, detail="Email account not found")
        
        # Import EmailConnection here to avoid circular imports
        from email_services import EmailConnection
        
        # Send the follow-up email
        connection = EmailConnection(account)
        success = connection.send_email(
            to_email=follow_up["recipient_email"],
            subject=follow_up["subject"],
            body=follow_up["draft_content"],
            body_html=follow_up["draft_html"]
        )
        
        if success:
            # Update follow-up status
            await db.follow_up_emails.update_one(
                {"id": follow_up_id},
                {"$set": {
                    "status": "sent",
                    "sent_time": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            return {"message": "Follow-up email sent successfully"}
        else:
            # Update with error status
            await db.follow_up_emails.update_one(
                {"id": follow_up_id},
                {"$set": {
                    "status": "failed",
                    "error_message": "Failed to send email",
                    "updated_at": datetime.utcnow()
                }}
            )
            raise HTTPException(status_code=500, detail="Failed to send follow-up email")
            
    except Exception as e:
        logger.error(f"Error sending follow-up email {follow_up_id}: {str(e)}")
        await db.follow_up_emails.update_one(
            {"id": follow_up_id},
            {"$set": {
                "status": "failed",
                "error_message": str(e),
                "updated_at": datetime.utcnow()
            }}
        )
        raise HTTPException(status_code=500, detail=f"Failed to send follow-up email: {str(e)}")



# Follow-up Processing Functions
async def create_follow_up_for_email(email_id: str, account_id: str, user_id: str = None):
    """Create follow-up entries for an email that needs follow-up"""
    try:
        # Get the email
        email = await db.emails.find_one({"id": email_id})
        if not email:
            logger.error(f"Email {email_id} not found for follow-up creation")
            return
        
        # CRITICAL: Check if thread already has responses - if so, don't create follow-ups
        thread_id = email.get("thread_id", "")
        if thread_id:
            # Check for response emails in the same thread
            original_sender = email.get("sender", "")
            original_received_at = email.get("received_at", datetime.min)
            
            # Look for emails in same thread from different senders after this email
            response_emails = await db.emails.find({
                "thread_id": thread_id,
                "received_at": {"$gt": original_received_at},
                "sender": {"$ne": original_sender},
                "id": {"$ne": email_id}
            }).to_list(10)
            
            if response_emails:
                logger.info(f"Thread {thread_id} already has {len(response_emails)} responses - skipping follow-up creation")
                return
        
        # Get user from account if not provided
        if not user_id:
            account = await db.email_accounts.find_one({"id": account_id})
            if not account:
                logger.error(f"Account {account_id} not found for follow-up creation")
                return
            # For now, we'll use a default user_id or get it from account if available
            user_id = account.get("user_id", "default_user")
        
        # Get user's follow-up configuration
        follow_up_config = await db.follow_up_configs.find_one({"user_id": user_id})
        if not follow_up_config:
            # Create default config
            default_config = FollowUpConfig(user_id=user_id)
            await db.follow_up_configs.insert_one(default_config.dict())
            follow_up_config = default_config.dict()
        
        # Check if follow-ups are enabled
        if not follow_up_config.get("auto_follow_up", True):
            logger.info(f"Auto follow-up disabled for user {user_id}")
            return
        
        # Get account follow-up settings
        account = await db.email_accounts.find_one({"id": account_id})
        if not account.get("enable_follow_ups", True):
            logger.info(f"Follow-ups disabled for account {account_id}")
            return
        
        # Calculate follow-up schedules
        max_follow_ups = account.get("max_follow_ups_override") or follow_up_config.get("max_follow_ups", 3)
        first_follow_up_hours = account.get("follow_up_hours_override") or follow_up_config.get("global_follow_up_hours", 24)
        interval_hours = follow_up_config.get("follow_up_interval_hours", 48)
        
        # Extract sender email for reply
        sender_email = email["sender"]
        if '<' in sender_email:
            sender_email = sender_email.split('<')[1].split('>')[0]
        
        # Generate follow-up subject
        subject = email["subject"]
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
        
        # Create follow-up emails
        current_time = datetime.utcnow()
        
        for follow_up_num in range(1, max_follow_ups + 1):
            # Calculate scheduled time for this follow-up
            if follow_up_num == 1:
                scheduled_time = current_time + timedelta(hours=first_follow_up_hours)
            else:
                scheduled_time = current_time + timedelta(hours=first_follow_up_hours + (follow_up_num - 1) * interval_hours)
            
            # Adjust for business hours if needed
            if follow_up_config.get("business_hours_only", False):
                scheduled_time = adjust_to_business_hours(
                    scheduled_time,
                    follow_up_config.get("business_start_hour", 9),
                    follow_up_config.get("business_end_hour", 17),
                    follow_up_config.get("business_days", [1, 2, 3, 4, 5]),
                    follow_up_config.get("exclude_weekends", True)
                )
            
            # Generate follow-up content based on number
            follow_up_content = await generate_follow_up_content(
                email, follow_up_num, account.get("custom_follow_up_template")
            )
            
            # Create follow-up email record
            follow_up_email = FollowUpEmail(
                original_email_id=email_id,
                account_id=account_id,
                user_id=user_id,
                thread_id=email.get("thread_id", ""),
                recipient_email=sender_email,
                subject=f"{subject} - Follow-up #{follow_up_num}",
                follow_up_number=follow_up_num,
                scheduled_time=scheduled_time,
                draft_content=follow_up_content["text"],
                draft_html=follow_up_content["html"]
            )
            
            await db.follow_up_emails.insert_one(follow_up_email.dict())
            logger.info(f"Created follow-up #{follow_up_num} for email {email_id}, scheduled for {scheduled_time}")
    
    except Exception as e:
        logger.error(f"Error creating follow-up for email {email_id}: {str(e)}")

async def cancel_follow_ups_for_thread(thread_id: str, reason: str = "Response received"):
    """Cancel all pending follow-ups for a thread when a response is received"""
    try:
        # Cancel all pending follow-ups for this thread
        result = await db.follow_up_emails.update_many(
            {
                "thread_id": thread_id,
                "status": "pending"
            },
            {
                "$set": {
                    "status": "cancelled",
                    "error_message": reason,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Cancelled {result.modified_count} pending follow-ups for thread {thread_id}: {reason}")
        
        return result.modified_count
        
    except Exception as e:
        logger.error(f"Error cancelling follow-ups for thread {thread_id}: {str(e)}")
        return 0

async def detect_and_handle_responses():
    """Background task to detect responses and cancel follow-ups"""
    try:
        # Find threads with pending follow-ups
        pending_threads = await db.follow_up_emails.distinct("thread_id", {"status": "pending"})
        
        for thread_id in pending_threads:
            # Get all emails in this thread, sorted by received time
            thread_emails = await db.emails.find({
                "thread_id": thread_id
            }).sort("received_at", 1).to_list(100)
            
            if len(thread_emails) < 2:
                continue  # Need at least 2 emails to detect response
            
            # Find the original email (earliest one)
            original_email = thread_emails[0]
            original_sender = original_email.get("sender", "")
            original_received_at = original_email.get("received_at", datetime.min)
            
            # Check for responses (emails from different senders after original)
            responses = [
                email for email in thread_emails[1:]
                if (email.get("sender", "") != original_sender and 
                    email.get("received_at", datetime.min) > original_received_at)
            ]
            
            if responses:
                # Response detected - cancel pending follow-ups
                cancelled_count = await cancel_follow_ups_for_thread(
                    thread_id, 
                    f"Response received from {responses[0].get('sender', 'unknown')}"
                )
                if cancelled_count > 0:
                    logger.info(f"Thread {thread_id}: Detected response, cancelled {cancelled_count} follow-ups")
        
    except Exception as e:
        logger.error(f"Error in response detection: {str(e)}")

def adjust_to_business_hours(target_time: datetime, start_hour: int, end_hour: int, 
                           business_days: List[int], exclude_weekends: bool) -> datetime:
    """Adjust scheduled time to fall within business hours"""
    # Monday=1, Sunday=7
    weekday = target_time.isoweekday()
    
    # Check if it's a weekend and weekends are excluded
    if exclude_weekends and weekday in [6, 7]:  # Saturday, Sunday
        # Move to next Monday
        days_until_monday = (8 - weekday) % 7
        if days_until_monday == 0:
            days_until_monday = 1
        target_time = target_time + timedelta(days=days_until_monday)
        target_time = target_time.replace(hour=start_hour, minute=0, second=0)
        return target_time
    
    # Check if it's a business day
    if weekday not in business_days:
        # Find next business day
        for i in range(1, 8):
            next_day = (weekday + i - 1) % 7 + 1
            if next_day in business_days:
                target_time = target_time + timedelta(days=i)
                target_time = target_time.replace(hour=start_hour, minute=0, second=0)
                break
        return target_time
    
    # Adjust hour if outside business hours
    if target_time.hour < start_hour:
        target_time = target_time.replace(hour=start_hour, minute=0, second=0)
    elif target_time.hour >= end_hour:
        # Move to next business day
        target_time = target_time + timedelta(days=1)
        target_time = target_time.replace(hour=start_hour, minute=0, second=0)
        # Recursively check if new day is a business day
        return adjust_to_business_hours(target_time, start_hour, end_hour, business_days, exclude_weekends)
    
    return target_time

async def generate_follow_up_content(email: Dict[str, Any], follow_up_number: int, 
                                   custom_template: Optional[str] = None) -> Dict[str, str]:
    """Generate follow-up email content using AI"""
    try:
        if custom_template:
            # Use custom template
            content = custom_template.format(
                original_subject=email["subject"],
                original_sender=email["sender"],
                follow_up_number=follow_up_number,
                days_ago=follow_up_number * 2  # Approximate
            )
            return {"text": content, "html": f"<p>{content.replace(chr(10), '</p><p>')}</p>"}
        
        # Generate AI follow-up content
        follow_up_prompts = {
            1: "Generate a polite follow-up email asking if the recipient had a chance to review the previous message.",
            2: "Generate a second follow-up email with a more direct approach, emphasizing the importance of the matter.",
            3: "Generate a final follow-up email indicating this is the last attempt to reach out on this matter."
        }
        
        prompt = follow_up_prompts.get(follow_up_number, follow_up_prompts[3])
        
        system_prompt = f"""
        You are writing a professional follow-up email. 
        
        Original email details:
        Subject: {email["subject"]}
        From: {email["sender"]}
        Body preview: {email["body"][:200] if email["body"] else "No preview available"}...
        
        {prompt}
        
        Keep the tone professional and friendly. The email should be concise and to the point.
        """
        
        # Use Groq API to generate follow-up content
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Write follow-up #{follow_up_number} for the above email."}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return {
                    "text": content,
                    "html": f"<p>{content.replace(chr(10), '</p><p>')}</p>"
                }
            else:
                logger.error(f"Groq API error in follow-up generation: {response.text}")
                # Fallback content
                fallback_content = f"""
Hi,

I wanted to follow up on my previous email regarding "{email["subject"]}".

I haven't heard back from you yet, and I wanted to make sure my message didn't get lost in your inbox.

Could you please let me know your thoughts when you have a chance?

Thank you for your time.

Best regards
                """.strip()
                return {"text": fallback_content, "html": f"<p>{fallback_content.replace(chr(10), '</p><p>')}</p>"}
    
    except Exception as e:
        logger.error(f"Error generating follow-up content: {str(e)}")
        # Fallback content
        fallback_content = f"""
Hi,

I wanted to follow up on my previous email regarding "{email.get('subject', 'our previous conversation')}".

Could you please provide an update when you have a moment?

Thank you.

Best regards
        """.strip()
        return {"text": fallback_content, "html": f"<p>{fallback_content.replace(chr(10), '</p><p>')}</p>"}

async def process_scheduled_follow_ups():
    """Process and send scheduled follow-up emails"""
    try:
        # Get all pending follow-ups that are due
        current_time = datetime.utcnow()
        due_follow_ups = await db.follow_up_emails.find({
            "status": "pending",
            "scheduled_time": {"$lte": current_time}
        }).to_list(100)
        
        logger.info(f"Processing {len(due_follow_ups)} due follow-ups")
        
        for follow_up in due_follow_ups:
            try:
                # Check if original email received a response
                if await check_email_received_response(follow_up["original_email_id"], follow_up["thread_id"]):
                    # Cancel remaining follow-ups for this thread
                    await db.follow_up_emails.update_many(
                        {
                            "thread_id": follow_up["thread_id"],
                            "status": "pending"
                        },
                        {"$set": {
                            "status": "cancelled",
                            "updated_at": current_time,
                            "error_message": "Response received, follow-up cancelled"
                        }}
                    )
                    logger.info(f"Cancelled follow-ups for thread {follow_up['thread_id']} - response received")
                    continue
                
                # Get account info
                account = await db.email_accounts.find_one({"id": follow_up["account_id"]})
                if not account or not account.get("is_active", True):
                    await db.follow_up_emails.update_one(
                        {"id": follow_up["id"]},
                        {"$set": {
                            "status": "failed",
                            "error_message": "Account not found or inactive",
                            "updated_at": current_time
                        }}
                    )
                    continue
                
                # Import EmailConnection here to avoid circular imports
                from email_services import EmailConnection
                
                # Send the follow-up email
                connection = EmailConnection(account)
                success = connection.send_email(
                    to_email=follow_up["recipient_email"],
                    subject=follow_up["subject"],
                    body=follow_up["draft_content"],
                    body_html=follow_up["draft_html"]
                )
                
                if success:
                    await db.follow_up_emails.update_one(
                        {"id": follow_up["id"]},
                        {"$set": {
                            "status": "sent",
                            "sent_time": current_time,
                            "updated_at": current_time
                        }}
                    )
                    logger.info(f"Successfully sent follow-up {follow_up['id']}")
                else:
                    await db.follow_up_emails.update_one(
                        {"id": follow_up["id"]},
                        {"$set": {
                            "status": "failed",
                            "error_message": "Failed to send email",
                            "updated_at": current_time
                        }}
                    )
                    logger.error(f"Failed to send follow-up {follow_up['id']}")
                
            except Exception as e:
                logger.error(f"Error processing follow-up {follow_up['id']}: {str(e)}")
                await db.follow_up_emails.update_one(
                    {"id": follow_up["id"]},
                    {"$set": {
                        "status": "failed",
                        "error_message": str(e),
                        "updated_at": current_time
                    }}
                )
    
    except Exception as e:
        logger.error(f"Error in process_scheduled_follow_ups: {str(e)}")

async def check_email_received_response(original_email_id: str, thread_id: str) -> bool:
    """Check if an email thread received a response"""
    try:
        # Get the original email
        original_email = await db.emails.find_one({"id": original_email_id})
        if not original_email:
            return False
        
        # Look for newer emails in the same thread
        newer_emails = await db.emails.find({
            "thread_id": thread_id,
            "received_at": {"$gt": original_email["received_at"]},
            "sender": {"$ne": original_email.get("account_email", "")}  # Not from the same account
        }).to_list(10)
        
        return len(newer_emails) > 0
    
    except Exception as e:
        logger.error(f"Error checking email response for {original_email_id}: {str(e)}")
        return False

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global polling_service
    logger.info("🚀 Starting up email assistant services...")
    
    # Initialize all seed data
    await initialize_email_accounts()
    await initialize_intents()
    await initialize_knowledge_base()
    await initialize_test_emails()  # Add test email data
    
    # Initialize email polling service
    try:
        polling_service = get_polling_service(mongo_url, os.environ['DB_NAME'])  
        # Start polling in background
        asyncio.create_task(polling_service.start_polling())
        logger.info("✅ Email polling service started automatically")
    except Exception as e:
        logger.error(f"❌ Failed to start email polling service: {str(e)}")
    
    # Start calendar reminder service
    try:
        asyncio.create_task(calendar_reminder_service())
        logger.info("✅ Calendar reminder service started")
    except Exception as e:
        logger.error(f"❌ Failed to start calendar reminder service: {str(e)}")
    
    # Start follow-up processing service
    try:
        asyncio.create_task(follow_up_service())
        logger.info("✅ Follow-up processing service started")
    except Exception as e:
        logger.error(f"❌ Failed to start follow-up processing service: {str(e)}")
    
    # Start response detection service
    try:
        asyncio.create_task(response_detection_service())
        logger.info("✅ Response detection service started")
    except Exception as e:
        logger.error(f"❌ Failed to start response detection service: {str(e)}")
    
    logger.info("🎉 Email assistant system fully initialized and ready!")

async def follow_up_service():
    """Background service to process scheduled follow-up emails"""
    logger.info("🔄 Follow-up processing service started")
    while True:
        try:
            await process_scheduled_follow_ups()
            # Wait 10 minutes before checking again
            await asyncio.sleep(600)
        except Exception as e:
            logger.error(f"Error in follow-up service: {str(e)}")
            await asyncio.sleep(600)  # Wait before retrying

async def response_detection_service():
    """Background service to detect responses and cancel follow-ups"""
    logger.info("🔍 Response detection service started")
    while True:
        try:
            await detect_and_handle_responses()
            # Check every 5 minutes for responses
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Error in response detection service: {str(e)}")
            await asyncio.sleep(300)  # Wait before retrying

async def calendar_reminder_service():
    """Background service to send calendar reminders"""
    while True:
        try:
            # Get all active users
            users = await db.users.find({"is_active": True}).to_list(1000)
            
            total_reminders = 0
            for user in users:
                try:
                    reminders_sent = await calendar_agent.send_meeting_reminders(user["id"])
                    total_reminders += reminders_sent
                except Exception as e:
                    logger.error(f"Error sending reminders for user {user['id']}: {e}")
            
            if total_reminders > 0:
                logger.info(f"📅 Sent {total_reminders} calendar reminders")
            
            # Wait 15 minutes before checking again
            await asyncio.sleep(900)
            
        except Exception as e:
            logger.error(f"Calendar reminder service error: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error

async def initialize_email_accounts():
    """Initialize default email accounts if they don't exist"""
    try:
        # Check if any email accounts exist
        existing_accounts = await db.email_accounts.count_documents({})
        
        if existing_accounts == 0:
            logger.info("📧 Initializing default email account...")
            
            # Create default Gmail account
            default_account = {
                "id": str(uuid.uuid4()),
                "email": "rohushanshinde@gmail.com",
                "username": "rohushanshinde@gmail.com",
                "password": "pajbdmcpcegppguz",  # App password from test files
                "name": "AI Email Assistant",
                "provider": "gmail",
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "is_active": True,
                "last_uid": 0,
                "uidvalidity": None,
                "last_polled": None,
                "persona": "I am a helpful AI assistant representing a technology company. I respond professionally and courteously to all emails, providing accurate information and appropriate next steps.",
                "signature": "Best regards,\nAI Email Assistant\nTechnology Solutions Team",
                "auto_send": True,
                "created_at": datetime.utcnow()
            }
            
            await db.email_accounts.insert_one(default_account)
            logger.info(f"✅ Created default email account: {default_account['email']}")
        else:
            logger.info(f"ℹ️  Found {existing_accounts} existing email accounts")
            
    except Exception as e:
        logger.error(f"❌ Error initializing email accounts: {str(e)}")

async def initialize_intents():
    """Initialize default intents for email classification"""
    try:
        existing_intents = await db.intents.count_documents({})
        
        if existing_intents == 0:
            logger.info("🎯 Initializing default intents...")
            
            default_intents = [
                {
                    "name": "Sales Inquiry",
                    "description": "Potential customer asking about products, services, or making purchase inquiries",
                    "examples": [
                        "I'm interested in your product",
                        "Can you tell me more about pricing?",
                        "I want to buy your service",
                        "What packages do you offer?",
                        "I need a quote for your solution"
                    ],
                    "system_prompt": "Respond professionally to sales inquiries. Provide helpful information, direct to appropriate resources like https://example.com/pricing for pricing details, and suggest next steps like scheduling a demo at https://example.com/demo or starting a free trial at https://example.com/trial.",
                    "confidence_threshold": 0.65,
                    "follow_up_hours": 4,
                    "is_meeting_related": False
                },
                {
                    "name": "Partnership Inquiry",
                    "description": "Business partnership, collaboration, or B2B relationship proposals",
                    "examples": [
                        "We'd like to explore a partnership",
                        "Let's collaborate on this project",
                        "I represent a company interested in working together",
                        "Business partnership opportunity",
                        "Strategic alliance proposal"
                    ],  
                    "system_prompt": "Handle partnership inquiries professionally. Express interest, gather initial information, and direct to appropriate decision makers or partnership team. Share our partnership information at https://example.com/partners and suggest scheduling a partnership discussion call.",
                    "confidence_threshold": 0.8,
                    "follow_up_hours": 24,
                    "is_meeting_related": True
                },
                {
                    "name": "Support Request",
                    "description": "Technical support, troubleshooting, or customer service issues",
                    "examples": [
                        "I'm having trouble with your product",
                        "This feature isn't working",
                        "I need help with setup",
                        "Technical issue with the system",
                        "How do I configure this?"
                    ],
                    "system_prompt": "Provide helpful support responses. Acknowledge the issue, provide initial troubleshooting steps if known, and direct to appropriate support channels. Include links to our help center at https://example.com/help and suggest submitting a support ticket at https://example.com/support for detailed assistance.",
                    "confidence_threshold": 0.7,
                    "follow_up_hours": 2,
                    "is_meeting_related": False
                },
                {
                    "name": "Meeting Request",
                    "description": "Requests to schedule meetings, calls, demos, or consultations",
                    "examples": [
                        "Can we schedule a meeting?",
                        "I'd like to book a demo",
                        "Let's set up a call",
                        "Available for a consultation?",
                        "When can we meet to discuss?"
                    ],
                    "system_prompt": "Respond positively to meeting requests. Provide available time slots or direct to scheduling system at https://calendly.com/company-meetings. Confirm meeting purpose and attendees. For product demos, also include link to our demo overview at https://example.com/demo.",
                    "confidence_threshold": 0.8,
                    "follow_up_hours": 8,
                    "is_meeting_related": True
                },
                {
                    "name": "Product Information",
                    "description": "General questions about products, features, capabilities, or specifications",
                    "examples": [
                        "What does your product do?",
                        "Tell me about the features",
                        "How does this work?",
                        "What are the specifications?",
                        "Product documentation request"
                    ],
                    "system_prompt": "Provide clear, informative responses about products. Use knowledge base information and direct to additional resources like documentation or product pages.",
                    "confidence_threshold": 0.7,
                    "follow_up_hours": 12,
                    "is_meeting_related": False
                },
                {
                    "name": "Complaint or Issue",
                    "description": "Customer complaints, dissatisfaction, or service issues",
                    "examples": [
                        "I'm not happy with the service",
                        "This is not working as expected",
                        "I want to complain about",
                        "Very disappointed with",
                        "This is unacceptable"
                    ],
                    "system_prompt": "Handle complaints with empathy and professionalism. Acknowledge concerns, apologize if appropriate, and provide clear next steps for resolution.",
                    "confidence_threshold": 0.65,
                    "follow_up_hours": 1,
                    "is_meeting_related": False
                },
                {
                    "name": "General Inquiry",
                    "description": "General questions, information requests, or miscellaneous inquiries",
                    "examples": [
                        "I have a question about",
                        "Can you help me understand",
                        "I'm curious about",
                        "General question",
                        "Need some information"
                    ],
                    "system_prompt": "Provide helpful, informative responses to general inquiries. Be friendly and professional while addressing the specific question asked.",
                    "confidence_threshold": 0.6,
                    "follow_up_hours": 24,
                    "is_meeting_related": False
                },
                {
                    "name": "Job Application",
                    "description": "Employment inquiries, job applications, or career-related communications",
                    "examples": [
                        "I'm interested in working for your company",
                        "Applying for the position",
                        "Resume attached for consideration",
                        "Career opportunities",
                        "Job opening inquiry"
                    ],
                    "system_prompt": "Respond professionally to job applications. Acknowledge receipt, provide information about the hiring process, and direct to appropriate HR contacts.",
                    "confidence_threshold": 0.8,
                    "follow_up_hours": 48,
                    "is_meeting_related": False
                },
                {
                    "name": "Meeting Request",
                    "description": "Requests to schedule meetings, calls, or appointments for discussions, demos, or consultations",
                    "examples": [
                        "I'd like to schedule a meeting",
                        "Can we set up a call to discuss",
                        "Are you available for a meeting",
                        "Let's schedule some time to talk",
                        "I would like to book an appointment",
                        "Can we arrange a demo session",
                        "Let's have a discussion about"
                    ],
                    "system_prompt": "Respond professionally to meeting requests. Acknowledge the request, suggest available time slots, and ask for any specific requirements or agenda items. Be helpful in coordinating schedules.",
                    "confidence_threshold": 0.7,
                    "follow_up_hours": 24,
                    "is_meeting_related": True
                },
                {
                    "name": "Interview Scheduling",
                    "description": "Scheduling job interviews, candidate evaluations, or interview-related communications",
                    "examples": [
                        "Interview scheduling",
                        "Available for interview on",
                        "Let's schedule your interview",
                        "Interview confirmation",
                        "Can we reschedule the interview",
                        "Interview time change",
                        "Final round interview"
                    ],
                    "system_prompt": "Handle interview scheduling professionally. Confirm availability, provide interview details, and ensure all logistics are clear. Be accommodating with scheduling changes when possible.", 
                    "confidence_threshold": 0.8,
                    "follow_up_hours": 12,
                    "is_meeting_related": True
                }
            ]
            
            # Create intents with embeddings
            for intent_data in default_intents:
                intent_obj = Intent(**intent_data)
                
                # Create embedding for intent description + examples
                text_for_embedding = f"{intent_obj.description} {' '.join(intent_obj.examples)}"
                embedding = await get_cohere_embedding(text_for_embedding)
                
                # Store with embedding
                doc = intent_obj.dict()
                doc["embedding"] = embedding
                await db.intents.insert_one(doc)
                
            logger.info(f"✅ Created {len(default_intents)} default intents")
        else:
            logger.info(f"ℹ️  Found {existing_intents} existing intents")
            
    except Exception as e:
        logger.error(f"❌ Error initializing intents: {str(e)}")

async def initialize_knowledge_base():
    """Initialize default knowledge base entries"""
    try:
        existing_kb = await db.knowledge_base.count_documents({})
        
        if existing_kb == 0:
            logger.info("📚 Initializing knowledge base...")
            
            kb_entries = [
                {
                    "title": "Company Overview",
                    "content": "We are a technology solutions company specializing in AI-powered email automation and business process optimization. Our mission is to help businesses streamline their email communications and improve response times through intelligent automation. Visit our website at https://example.com/about for more information.",
                    "tags": ["company", "about", "overview", "mission"]
                },
                {
                    "title": "Product Features",
                    "content": "Our AI Email Assistant offers: 1) Automated email classification and intent recognition, 2) AI-powered draft generation with customizable personas, 3) Multi-account email management, 4) Real-time email polling and processing, 5) Intelligent response validation, 6) Customizable knowledge base integration, 7) Auto-sending capabilities with manual override options. Learn more at https://example.com/features and see our demo at https://example.com/demo.",
                    "tags": ["product", "features", "capabilities", "automation"]
                },
                {
                    "title": "Pricing Information",
                    "content": "We offer flexible pricing plans: Starter Plan ($29/month) for up to 3 email accounts and 500 emails/month, Professional Plan ($99/month) for up to 10 accounts and 2000 emails/month, Enterprise Plan (custom pricing) for unlimited accounts and volume. All plans include 24/7 support and onboarding assistance. View detailed pricing at https://example.com/pricing and start your free trial at https://example.com/trial.",
                    "tags": ["pricing", "plans", "cost", "subscription"]
                },
                {
                    "title": "Support Channels",
                    "content": "We provide multiple support channels: 1) Email support at support@company.com, 2) Live chat available 9 AM - 6 PM EST, 3) Knowledge base with tutorials and FAQ at https://example.com/help, 4) Priority phone support for Enterprise customers, 5) Dedicated account managers for Enterprise plans. Average response time is under 2 hours. Submit a support ticket at https://example.com/support.",
                    "tags": ["support", "help", "contact", "assistance"]
                },
                {
                    "title": "Meeting Scheduling",
                    "content": "We're happy to schedule meetings for demos, consultations, or discussions. Available time slots: Monday-Friday 9 AM - 5 PM EST. Meeting types available: 1) Product demo (30 minutes), 2) Consultation call (45 minutes), 3) Technical setup call (60 minutes). Please book at https://calendly.com/company-meetings or reply with your preferred times. You can also view our calendar availability at https://example.com/calendar.",
                    "tags": ["meetings", "demo", "consultation", "schedule", "calendar"]
                },
                {
                    "title": "Integration Capabilities",
                    "content": "Our system integrates with: 1) All major email providers (Gmail, Outlook, Yahoo, Custom IMAP/SMTP), 2) CRM systems (Salesforce, HubSpot, Pipedrive), 3) Communication tools (Slack, Microsoft Teams), 4) Calendar systems (Google Calendar, Outlook Calendar), 5) Help desk platforms (Zendesk, ServiceNow). API documentation available at https://docs.example.com/api for custom integrations. View integration guides at https://example.com/integrations.",
                    "tags": ["integration", "api", "crm", "email providers", "platforms"]
                },
                {
                    "title": "Security and Privacy",
                    "content": "We prioritize security: 1) End-to-end encryption for all email data, 2) SOC 2 Type II compliance, 3) GDPR compliant data handling, 4) Multi-factor authentication, 5) Regular security audits, 6) Data residency options available. Email credentials are encrypted and stored securely. We never access email content without explicit permission. Read our security whitepaper at https://example.com/security and privacy policy at https://example.com/privacy.",
                    "tags": ["security", "privacy", "compliance", "encryption", "gdpr"]
                },
                {
                    "title": "Getting Started",
                    "content": "To get started: 1) Sign up for a free trial at https://example.com/signup, 2) Connect your email accounts using our secure setup wizard, 3) Configure your AI persona and response preferences, 4) Add knowledge base entries specific to your business, 5) Set up intents for your common email types, 6) Test the system with sample emails. Full onboarding typically takes 15-30 minutes. Access our getting started guide at https://example.com/getting-started and watch our tutorial videos at https://example.com/tutorials.",
                    "tags": ["onboarding", "setup", "getting started", "trial", "configuration"]
                }
            ]
            
            # Create knowledge base entries with embeddings
            for kb_data in kb_entries:
                kb_obj = KnowledgeBase(**kb_data)
                
                # Create embedding for content
                embedding = await get_cohere_embedding(kb_obj.content)
                
                # Store with embedding
                doc = kb_obj.dict()
                doc["embedding"] = embedding
                await db.knowledge_base.insert_one(doc)
                
            logger.info(f"✅ Created {len(kb_entries)} knowledge base entries")
        else:
            logger.info(f"ℹ️  Found {existing_kb} existing knowledge base entries")
            
    except Exception as e:
        logger.error(f"❌ Error initializing knowledge base: {str(e)}")

async def initialize_test_emails():
    """Initialize test email data for demonstration purposes"""
    try:
        existing_emails = await db.emails.count_documents({})
        
        if existing_emails == 0:
            logger.info("📧 Initializing test email data...")
            
            # Get the first email account for test emails
            account = await db.email_accounts.find_one({})
            if not account:
                logger.warning("⚠️  No email accounts found, skipping test email initialization")
                return
            
            test_emails = [
                {
                    "id": str(uuid.uuid4()),
                    "account_id": account["id"],
                    "message_id": f"test-msg-{uuid.uuid4()}",
                    "thread_id": f"test-thread-{uuid.uuid4()}",
                    "subject": "Inquiry about your AI Email Assistant",
                    "sender": "john.doe@example.com",
                    "recipient": account["email"],
                    "body": "Hi there! I'm interested in learning more about your AI Email Assistant product. Could you please provide me with information about pricing and features? I'm particularly interested in how it handles customer support emails. Thanks!",
                    "body_html": "",
                    "received_at": datetime.utcnow() - timedelta(hours=2),
                    "in_reply_to": "",
                    "references": "",
                    "status": "new",
                    "intents": [],
                    "draft": "",
                    "draft_html": "",
                    "validation_result": None,
                    "processed_at": None,
                    "sent_at": None,
                    "error": None,
                    "created_at": datetime.utcnow() - timedelta(hours=2)
                },
                {
                    "id": str(uuid.uuid4()),
                    "account_id": account["id"],
                    "message_id": f"test-msg-{uuid.uuid4()}",
                    "thread_id": f"test-thread-{uuid.uuid4()}",
                    "subject": "Partnership Opportunity",
                    "sender": "sarah.wilson@techcorp.com",
                    "recipient": account["email"],
                    "body": "Hello, I represent TechCorp and we're looking for strategic partnerships in the AI automation space. We believe there could be great synergy between our companies. Would you be interested in exploring a potential collaboration? I'd love to schedule a call to discuss this further.",
                    "body_html": "",
                    "received_at": datetime.utcnow() - timedelta(hours=1),
                    "in_reply_to": "",
                    "references": "",
                    "status": "new",
                    "intents": [],
                    "draft": "",
                    "draft_html": "",
                    "validation_result": None,
                    "processed_at": None,
                    "sent_at": None,
                    "error": None,
                    "created_at": datetime.utcnow() - timedelta(hours=1)
                },
                {
                    "id": str(uuid.uuid4()),
                    "account_id": account["id"],
                    "message_id": f"test-msg-{uuid.uuid4()}",
                    "thread_id": f"test-thread-{uuid.uuid4()}",
                    "subject": "Technical Support Needed",
                    "sender": "mike.johnson@company.com",
                    "recipient": account["email"],
                    "body": "I'm having trouble setting up the email integration with our IMAP server. The connection keeps timing out and I'm not sure what configuration settings I should be using. Can someone from your support team help me troubleshoot this issue?",
                    "body_html": "",
                    "received_at": datetime.utcnow() - timedelta(minutes=30),
                    "in_reply_to": "",
                    "references": "",
                    "status": "new",
                    "intents": [],
                    "draft": "",
                    "draft_html": "",
                    "validation_result": None,
                    "processed_at": None,
                    "sent_at": None,
                    "error": None,
                    "created_at": datetime.utcnow() - timedelta(minutes=30)
                }
            ]
            
            # Insert test emails
            for email_data in test_emails:
                await db.emails.insert_one(email_data)
            
            logger.info(f"✅ Created {len(test_emails)} test emails")
        else:
            logger.info(f"ℹ️  Found {existing_emails} existing emails")
            
    except Exception as e:
        logger.error(f"❌ Error initializing test emails: {str(e)}")

# Enhanced Email Accounts with OAuth support
class EmailAccountCreateOAuth(BaseModel):
    name: str
    email: str
    provider: str = "gmail"  # oauth provider
    auth_type: str = "oauth"  # "oauth" or "manual"
    # Manual fields (existing)
    username: Optional[str] = None
    password: Optional[str] = None
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    # OAuth fields
    use_oauth: bool = False
    signature: str = ""
    is_active: bool = True

@api_router.post("/email-accounts/oauth", response_model=Dict[str, Any])
async def create_oauth_email_account(
    account_data: EmailAccountCreateOAuth,
    current_user: User = Depends(get_current_active_user)
):
    """Create email account using OAuth credentials"""
    
    if not account_data.use_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for OAuth-based accounts only"
        )
    
    # Check if user has OAuth authorization for email
    oauth_status = await google_oauth_service.get_oauth_status(current_user.id)
    if not oauth_status["is_authorized"] or "email" not in oauth_status["authorized_services"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email access not authorized. Please complete OAuth flow first."
        )
    
    try:
        # Verify OAuth access by testing Gmail API
        gmail_service = await get_google_gmail_service(current_user.id)
        profile = await gmail_service.get_profile()
        
        # Use email from OAuth profile
        oauth_email = oauth_status["user_email"]
        
        account = EmailAccount(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            name=account_data.name,
            email=oauth_email,
            provider=account_data.provider,
            auth_type="oauth",
            use_oauth=True,
            # OAuth accounts don't need manual credentials
            username="",
            password="",
            imap_server="",
            imap_port=0,
            smtp_server="",
            smtp_port=0,
            signature=account_data.signature,
            is_active=account_data.is_active,
            last_uid=0,
            uidvalidity=None,
            last_polled=None
        )
        
        # Insert into database
        result = await db.email_accounts.insert_one(account.dict())
        
        # Return account without sensitive data
        account_dict = account.dict()
        account_dict["_id"] = str(result.inserted_id)
        account_dict["oauth_user"] = oauth_status["user_name"]
        
        return account_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating OAuth email account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create OAuth email account: {str(e)}"
        )

# Enhanced Calendar Provider with OAuth support
class CalendarProviderCreateOAuth(BaseModel):
    provider_type: str = "google"  # For OAuth
    provider_name: str
    use_oauth: bool = True
    timezone: str = "UTC"
    # Manual credentials (for non-OAuth)
    credentials: Optional[Dict[str, Any]] = {}

@api_router.post("/calendar/providers/oauth", response_model=CalendarProviderResponse)
async def create_oauth_calendar_provider(
    provider_data: CalendarProviderCreateOAuth,
    current_user: User = Depends(get_current_active_user)
):
    """Create calendar provider using OAuth credentials"""
    
    if not provider_data.use_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for OAuth-based providers only"
        )
    
    # Check if user has OAuth authorization for calendar
    oauth_status = await google_oauth_service.get_oauth_status(current_user.id)
    if not oauth_status["is_authorized"] or "calendar" not in oauth_status["authorized_services"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google calendar access not authorized. Please complete OAuth flow first."
        )
    
    try:
        # Verify OAuth access by testing Calendar API
        calendar_service = await get_google_calendar_service(current_user.id)
        calendars = await calendar_service.list_calendars()
        
        # Create provider record
        provider = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "provider_type": "google",
            "provider_name": provider_data.provider_name,
            "use_oauth": True,
            "encrypted_credentials": "",  # No manual credentials needed
            "is_active": True,
            "default_calendar_id": "primary",
            "timezone": provider_data.timezone,
            "oauth_user": oauth_status["user_name"],
            "oauth_email": oauth_status["user_email"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert into database
        await db.calendar_providers.insert_one(provider)
        
        return CalendarProviderResponse(
            id=provider["id"],
            provider_type=provider["provider_type"],
            provider_name=provider["provider_name"],
            is_active=provider["is_active"],
            timezone=provider["timezone"],
            calendar_count=len(calendars),
            created_at=provider["created_at"],
            updated_at=provider["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating OAuth calendar provider: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create OAuth calendar provider: {str(e)}"
        )

@app.on_event("shutdown")
async def shutdown_db_client():
    global polling_service
    if polling_service:
        polling_service.stop_polling()
    client.close()
