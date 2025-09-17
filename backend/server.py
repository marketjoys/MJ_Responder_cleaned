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

# Models - Updated with user_id fields for proper isolation
class Intent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Added for user isolation
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
    user_id: str  # Added for user isolation
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

class KnowledgeBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Added for user isolation
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

class AccountPollingStatus(BaseModel):
    account_id: str
    email: str
    polling_active: bool
    has_connection: bool
    last_polled: Optional[str] = None
    last_uid: int = 0

# Define EmailMessage model here to avoid circular imports
class EmailMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Added for user isolation
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
    """Get completion from Groq API"""
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "messages": messages,
                "model": "deepseek-r1-distill-llama-70b",
                "temperature": 0.6,
                "max_completion_tokens": 4096,
                "top_p": 0.95,
                "stream": False
            }
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise HTTPException(status_code=500, detail=f"Groq API error: {response.text}")

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
            logging.warning(f"Provider connection test failed: {e}")
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

# Intent CRUD Routes - Updated with user isolation
@api_router.post("/intents", response_model=Intent)
async def create_intent(intent: IntentCreate, current_user: User = Depends(get_current_active_user)):
    intent_dict = intent.dict()
    intent_dict["user_id"] = current_user.id  # Add user isolation
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
async def get_intents(current_user: User = Depends(get_current_active_user)):
    intents = await db.intents.find({"user_id": current_user.id}).to_list(1000)  # Filter by user
    return [Intent(**intent) for intent in intents]

@api_router.get("/intents/{intent_id}", response_model=Intent)
async def get_intent(intent_id: str, current_user: User = Depends(get_current_active_user)):
    intent_doc = await db.intents.find_one({"id": intent_id, "user_id": current_user.id})  # Filter by user
    if not intent_doc:
        raise HTTPException(status_code=404, detail="Intent not found")
    return Intent(**intent_doc)

@api_router.put("/intents/{intent_id}", response_model=Intent)
async def update_intent(intent_id: str, intent: IntentCreate, current_user: User = Depends(get_current_active_user)):
    # Check if intent exists and belongs to user
    existing_intent = await db.intents.find_one({"id": intent_id, "user_id": current_user.id})
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
        {"id": intent_id, "user_id": current_user.id},  # Filter by user
        {"$set": update_data}
    )
    
    # Return updated intent
    updated_intent = await db.intents.find_one({"id": intent_id, "user_id": current_user.id})
    return Intent(**updated_intent)

@api_router.delete("/intents/{intent_id}")
async def delete_intent(intent_id: str, current_user: User = Depends(get_current_active_user)):
    result = await db.intents.delete_one({"id": intent_id, "user_id": current_user.id})  # Filter by user
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Intent not found")
    return {"message": "Intent deleted successfully"}

# Email Account Management Routes - Updated with user isolation
@api_router.get("/email-providers")
async def get_email_providers():
    return EMAIL_PROVIDERS

@api_router.post("/email-accounts", response_model=EmailAccount)
async def create_email_account(account: EmailAccountCreate, current_user: User = Depends(get_current_active_user)):
    account_dict = account.dict()
    account_dict["user_id"] = current_user.id  # Add user isolation
    
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
async def get_email_accounts(current_user: User = Depends(get_current_active_user)):
    accounts = await db.email_accounts.find({"user_id": current_user.id}).to_list(1000)  # Filter by user
    # Don't return passwords in response
    for account in accounts:
        account["password"] = "***"
    return [EmailAccount(**account) for account in accounts]

@api_router.get("/email-accounts/{account_id}", response_model=EmailAccount)
async def get_email_account(account_id: str, current_user: User = Depends(get_current_active_user)):
    account_doc = await db.email_accounts.find_one({"id": account_id, "user_id": current_user.id})  # Filter by user
    if not account_doc:
        raise HTTPException(status_code=404, detail="Email account not found")
    # Don't return password
    account_doc["password"] = "***"
    return EmailAccount(**account_doc)

@api_router.put("/email-accounts/{account_id}", response_model=EmailAccount)
async def update_email_account(account_id: str, account: EmailAccountCreate, current_user: User = Depends(get_current_active_user)):
    # Check if account exists and belongs to user
    existing_account = await db.email_accounts.find_one({"id": account_id, "user_id": current_user.id})
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
                logging.info(f"🔌 Removed connection for updated account: {account.email}")
            except Exception as e:
                logging.warning(f"⚠️  Error removing connection during update: {str(e)}")
    
    # Update in database
    await db.email_accounts.update_one(
        {"id": account_id, "user_id": current_user.id},  # Filter by user
        {"$set": update_data}
    )
    
    # Return updated account (without password)
    updated_account = await db.email_accounts.find_one({"id": account_id, "user_id": current_user.id})
    updated_account["password"] = "***"
    return EmailAccount(**updated_account)

@api_router.delete("/email-accounts/{account_id}")
async def delete_email_account(account_id: str, current_user: User = Depends(get_current_active_user)):
    # Remove connection if exists
    global polling_service
    if polling_service and account_id in polling_service.connections:
        try:
            polling_service.connections[account_id].disconnect_imap()
            del polling_service.connections[account_id]
            logging.info(f"🔌 Removed connection for deleted account")
        except Exception as e:
            logging.warning(f"⚠️  Error removing connection during delete: {str(e)}")
    
    result = await db.email_accounts.delete_one({"id": account_id, "user_id": current_user.id})  # Filter by user
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Email account not found")
    return {"message": "Email account deleted successfully"}

@api_router.put("/email-accounts/{account_id}/toggle")
async def toggle_email_account(account_id: str, current_user: User = Depends(get_current_active_user)):
    """Toggle email account active status"""
    account = await db.email_accounts.find_one({"id": account_id, "user_id": current_user.id})  # Filter by user
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    new_status = not account.get("is_active", True)
    await db.email_accounts.update_one(
        {"id": account_id, "user_id": current_user.id},  # Filter by user
        {"$set": {"is_active": new_status}}
    )
    
    # If deactivating, remove connection
    if not new_status:
        global polling_service
        if polling_service and account_id in polling_service.connections:
            try:
                polling_service.connections[account_id].disconnect_imap()
                del polling_service.connections[account_id]
                logging.info(f"🔌 Removed connection for deactivated account: {account.get('email')}")
            except Exception as e:
                logging.warning(f"⚠️  Error removing connection during deactivation: {str(e)}")
    
    return {"message": f"Account {'activated' if new_status else 'deactivated'} successfully"}

@api_router.post("/email-accounts/{account_id}/polling")
async def control_account_polling(account_id: str, request: PollingControlRequest, current_user: User = Depends(get_current_active_user)):
    """Control polling for individual email account"""
    account = await db.email_accounts.find_one({"id": account_id, "user_id": current_user.id})  # Filter by user
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    global polling_service
    if not polling_service:
        raise HTTPException(status_code=500, detail="Polling service not initialized")
    
    if request.action == "start":
        # Activate account and add to polling
        await db.email_accounts.update_one(
            {"id": account_id, "user_id": current_user.id},  # Filter by user
            {"$set": {"is_active": True}}
        )
        
        # Force create new connection on next poll
        if account_id in polling_service.connections:
            try:
                polling_service.connections[account_id].disconnect_imap()
                del polling_service.connections[account_id]
            except Exception as e:
                logging.warning(f"⚠️  Error removing old connection: {str(e)}")
        
        return {"message": f"Polling started for account: {account['email']}"}
    
    elif request.action == "stop":
        # Deactivate account and remove from polling
        await db.email_accounts.update_one(
            {"id": account_id, "user_id": current_user.id},  # Filter by user
            {"$set": {"is_active": False}}
        )
        
        # Remove connection
        if account_id in polling_service.connections:
            try:
                polling_service.connections[account_id].disconnect_imap()
                del polling_service.connections[account_id]
                logging.info(f"🔌 Stopped polling for account: {account['email']}")
            except Exception as e:
                logging.warning(f"⚠️  Error stopping polling: {str(e)}")
        
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

# Knowledge Base Routes - Updated with user isolation
@api_router.post("/knowledge-base", response_model=KnowledgeBase)
async def create_knowledge_base(kb: KnowledgeBaseCreate, current_user: User = Depends(get_current_active_user)):
    kb_dict = kb.dict()
    kb_dict["user_id"] = current_user.id  # Add user isolation
    kb_obj = KnowledgeBase(**kb_dict)
    
    # Create embedding for content
    embedding = await get_cohere_embedding(kb_obj.content)
    
    # Store with embedding
    doc = kb_obj.dict()
    doc["embedding"] = embedding
    await db.knowledge_base.insert_one(doc)
    return kb_obj

@api_router.get("/knowledge-base", response_model=List[KnowledgeBase])
async def get_knowledge_base(current_user: User = Depends(get_current_active_user)):
    kb_items = await db.knowledge_base.find({"user_id": current_user.id}).to_list(1000)  # Filter by user
    return [KnowledgeBase(**kb) for kb in kb_items]

@api_router.get("/knowledge-base/{kb_id}", response_model=KnowledgeBase)
async def get_knowledge_base_item(kb_id: str, current_user: User = Depends(get_current_active_user)):
    kb_doc = await db.knowledge_base.find_one({"id": kb_id, "user_id": current_user.id})  # Filter by user
    if not kb_doc:
        raise HTTPException(status_code=404, detail="Knowledge base item not found")
    return KnowledgeBase(**kb_doc)

@api_router.put("/knowledge-base/{kb_id}", response_model=KnowledgeBase)
async def update_knowledge_base(kb_id: str, kb: KnowledgeBaseCreate, current_user: User = Depends(get_current_active_user)):
    # Check if KB item exists and belongs to user
    existing_kb = await db.knowledge_base.find_one({"id": kb_id, "user_id": current_user.id})
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
        {"id": kb_id, "user_id": current_user.id},  # Filter by user
        {"$set": update_data}
    )
    
    # Return updated KB item
    updated_kb = await db.knowledge_base.find_one({"id": kb_id, "user_id": current_user.id})
    return KnowledgeBase(**updated_kb)

@api_router.delete("/knowledge-base/{kb_id}")
async def delete_knowledge_base(kb_id: str, current_user: User = Depends(get_current_active_user)):
    result = await db.knowledge_base.delete_one({"id": kb_id, "user_id": current_user.id})  # Filter by user
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Knowledge base item not found")
    return {"message": "Knowledge base item deleted successfully"}

# Email Processing Routes
@api_router.post("/emails/test")
async def test_email_processing(request: EmailTestRequest, current_user: User = Depends(get_current_active_user)):
    """Test email processing with manual input"""
    # Create a test email message
    email_obj = EmailMessage(
        user_id=current_user.id,  # Add user isolation
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
    processed_email = await db.emails.find_one({"id": email_obj.id, "user_id": current_user.id})
    return EmailMessage(**processed_email)

@api_router.post("/emails/{email_id}/send")
async def send_email_reply(email_id: str, request: SendEmailRequest, current_user: User = Depends(get_current_active_user)):
    """Send email reply"""
    email_doc = await db.emails.find_one({"id": email_id, "user_id": current_user.id})  # Filter by user
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    if email_doc['status'] not in ['ready_to_send', 'needs_redraft'] and not request.manual_override:
        raise HTTPException(status_code=400, detail="Email not ready to send")
    
    # Get account (must belong to same user)
    account_doc = await db.email_accounts.find_one({"id": email_doc['account_id'], "user_id": current_user.id})
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
            {"id": email_id, "user_id": current_user.id},  # Filter by user
            {"$set": {
                "status": "sent",
                "sent_at": datetime.utcnow()
            }}
        )
        return {"message": "Email sent successfully"}
    else:
        # Mark as failed to send
        await db.emails.update_one(
            {"id": email_id, "user_id": current_user.id},  # Filter by user
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
async def get_all_accounts_polling_status(current_user: User = Depends(get_current_active_user)):
    """Get polling status for all accounts belonging to current user"""
    global polling_service
    
    accounts = await db.email_accounts.find({"user_id": current_user.id}).to_list(1000)  # Filter by user
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
        logging.info(f"🚫 Skipping delivery error/bounce email: {email_message.subject}")
        return []
    
    # Get email embedding
    email_embedding = await get_cohere_embedding(email_message.body)
    
    # Get all intents with embeddings for this user only
    intents = await db.intents.find({"user_id": email_message.user_id}).to_list(1000)  # Filter by user
    
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
        logging.info(f"🚫 Skipping draft generation for delivery error: {email_message.subject}")
        return {
            "plain_text": "",
            "html": "",
            "reasoning": "Skipped - delivery error/bounce email detected"
        }
    
    # Get account info (ensure it belongs to same user)
    account = await db.email_accounts.find_one({"id": email_message.account_id, "user_id": email_message.user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    # Get enhanced knowledge base context with links (user-scoped)
    kb_data = await get_enhanced_knowledge_context(email_message.body, intents, email_message.user_id)
    
    # Get thread history to avoid duplicates (user-scoped)
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
1. Generate ONLY the email body content - no subject lines, no signatures, no placeholders
2. Do not include any reasoning, thinking, or meta-content
3. MUST use information from the knowledge base when relevant - this is critical
4. Include relevant links naturally in the response when provided above
5. Keep response comprehensive but professional (200-400 words when detailed info is needed)
6. Address all identified intents directly using knowledge base information
7. Maintain a {account.get('persona', 'professional')} tone
8. Include actionable next steps where appropriate
9. If thread history exists, provide varied content - do not repeat previous responses exactly
10. Start directly with the email content (e.g., "Thank you for your inquiry...")
11. When links are provided, integrate them naturally (e.g., "You can learn more at [link]" or "Please visit [link] for details")

Generate the email body content now, ensuring you use the knowledge base information and include relevant links:"""

    messages = [
        {"role": "user", "content": f"Generate a comprehensive email body response using the knowledge base information and including relevant links for: {email_message.body}"}
    ]
    
    response = await groq_chat_completion(messages, system_prompt)
    
    # Clean the response to remove any unwanted content
    clean_response = response.strip()
    
    # Remove any <think> tags or reasoning content
    import re
    clean_response = re.sub(r'<think>.*?</think>', '', clean_response, flags=re.DOTALL)
    clean_response = re.sub(r'PLAIN_TEXT:|HTML:|Subject:|Re:.*?\n', '', clean_response)
    clean_response = re.sub(r'^-+|^=+', '', clean_response, flags=re.MULTILINE)  # Remove separator lines
    clean_response = clean_response.strip()
    
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

async def validate_draft(email_message: EmailMessage, draft: Dict[str, str], intents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enhanced draft validation using Agent B - checks KB usage, links, and thread context"""
    
    # Skip validation for delivery errors
    if is_bounce_or_delivery_error(email_message):
        return {
            "status": "SKIP",
            "feedback": "Delivery error email - no response needed",
            "coverage_report": "Email identified as delivery error/bounce notification"
        }
    
    # Get enhanced KB context and links for validation (user-scoped)
    kb_data = await get_enhanced_knowledge_context(email_message.body, intents, email_message.user_id)
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

AUTOMATED CHECK RESULTS:
- KB Information Available: {kb_info_present}
- Expected Links Count: {len(expected_links)}
- Thread History Present: {len(thread_history) > 0}

IMPORTANT: Start your response with either "PASS:" or "FAIL:" followed by detailed explanation.

For PASS: The draft must address intents, use available KB information, include relevant links, and provide unique content.
For FAIL: Clearly state what's missing - KB usage, links, intent coverage, or duplicate content issues.

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
    
    # Additional automated checks
    automated_issues = []
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
        "avoids_duplicates": avoids_duplicates
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
    """Get previous emails in the same thread to avoid duplicate responses (user-scoped)"""
    
    # Find emails in the same thread for this user
    thread_emails = await db.emails.find({
        "thread_id": email_message.thread_id,
        "user_id": email_message.user_id,  # Filter by user
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

async def get_enhanced_knowledge_context(email_body: str, intents: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    """Enhanced knowledge base context with better retrieval and link extraction (user-scoped)"""
    # Get email embedding
    email_embedding = await get_cohere_embedding(email_body)
    
    # Get all knowledge base items with embeddings for this user
    kb_items = await db.knowledge_base.find({"embedding": {"$exists": True}, "user_id": user_id}).to_list(1000)
    
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
    
    # Also include items that match intent keywords (user-scoped)
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

async def get_knowledge_context(email_body: str, user_id: str = None) -> str:
    """Legacy function for backward compatibility"""
    result = await get_enhanced_knowledge_context(email_body, [], user_id or "")
    return result["context"]

async def auto_send_email(email_id: str):
    """Auto-send approved email if account has auto_send enabled"""
    try:
        # Get email
        email_doc = await db.emails.find_one({"id": email_id})
        if not email_doc or email_doc['status'] != 'ready_to_send':
            return
        
        # Get account (must belong to same user as email)
        account_doc = await db.email_accounts.find_one({
            "id": email_doc['account_id'], 
            "user_id": email_doc['user_id']  # Ensure same user
        })
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
            logging.info(f"✅ Auto-sent reply for email: {email_doc['subject']}")
        else:
            # Mark as failed to send
            await db.emails.update_one(
                {"id": email_id},
                {"$set": {"status": "send_failed"}}
            )
            
    except Exception as e:
        logging.error(f"❌ Error auto-sending email {email_id}: {str(e)}")
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
        
        # Get account info to find user (must belong to same user as email)
        account_doc = await db.email_accounts.find_one({
            "id": email_message.account_id,
            "user_id": email_message.user_id  # Ensure same user
        })
        if not account_doc:
            logging.error(f"Account not found for email {email_id}")
            return
        
        # Find user associated with this account
        user_doc = await db.users.find_one({"id": email_message.user_id})
        if not user_doc:
            logging.error(f"User not found for email {email_id}")
            return
        
        logging.info(f"🔄 Processing email: {email_message.subject}")
        
        # Step 1: Classify email intents (user-scoped)
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "classifying"}}
        )
        
        intents = await classify_email_intents(email_message)
        
        # Step 2: Generate draft response (user-scoped)
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "drafting", "intents": intents}}
        )
        
        draft_result = await generate_draft(email_message, intents)
        
        # Step 3: Validate draft (user-scoped)
        validation_result = await validate_draft(email_message, draft_result, intents)
        
        # Check if we should process meeting-related emails with calendar agent
        meeting_intents = [intent for intent in intents if intent.get("is_meeting_related", False)]
        calendar_event_id = None
        
        if meeting_intents and user_doc:
            # Process meeting detection and calendar integration
            try:
                calendar_event_id = await calendar_agent.process_meeting_intent(
                    email_id, 
                    email_message.user_id,  # Use email's user_id
                    MeetingDetectionResponse(
                        detected=True,
                        confidence_score=meeting_intents[0]["confidence"],
                        detected_datetime=None,  # Will be detected by calendar agent
                        detected_timezone=user_doc.get("timezone", "UTC"),
                        needs_confirmation=True,
                        meeting_details={
                            "subject": email_message.subject,
                            "body": email_message.body,
                            "sender": email_message.sender
                        }
                    ),
                    email_message.thread_id
                )
            except Exception as e:
                logging.warning(f"⚠️  Calendar integration failed for email {email_id}: {str(e)}")
        
        # Update email with final status
        final_status = "ready_to_send" if validation_result["status"] == "PASS" else "needs_redraft"
        
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {
                "status": final_status,
                "intents": intents,
                "draft": draft_result["plain_text"],
                "draft_html": draft_result["html"],
                "validation_result": validation_result,
                "processed_at": datetime.utcnow(),
                "calendar_event_id": calendar_event_id
            }}
        )
        
        # Auto-send if approved and account has auto_send enabled
        if final_status == "ready_to_send" and account_doc.get("auto_send", True):
            await auto_send_email(email_id)
        
        logging.info(f"✅ Email processed successfully: {email_message.subject} -> {final_status}")
        
    except Exception as e:
        logging.error(f"❌ Error processing email {email_id}: {str(e)}")
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "error", "error": str(e)}}
        )

# Additional endpoint to get emails for current user
@api_router.get("/emails")
async def get_emails(current_user: User = Depends(get_current_active_user)):
    """Get all emails for current user"""
    emails = await db.emails.find({"user_id": current_user.id}).sort("received_at", -1).to_list(100)
    return [EmailMessage(**email) for email in emails]

@api_router.post("/emails/{email_id}/redraft")
async def redraft_email(email_id: str, request: DraftRequest, current_user: User = Depends(get_current_active_user)):
    """Redraft an email response"""
    email_doc = await db.emails.find_one({"id": email_id, "user_id": current_user.id})  # Filter by user
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Process the email again
    await process_email_async(email_id)
    
    # Return updated email
    updated_email = await db.emails.find_one({"id": email_id, "user_id": current_user.id})
    return EmailMessage(**updated_email)

# OAuth Google Routes (already user-scoped in oauth_google.py)
@api_router.get("/oauth/google/status")
async def get_google_oauth_status(current_user: User = Depends(get_current_active_user)):
    """Get Google OAuth authorization status for current user"""
    return await google_oauth_service.get_oauth_status(current_user.id)

@api_router.get("/oauth/google/authorize")
async def initiate_google_oauth(
    services: str = "email,calendar",  # Comma-separated list of services
    current_user: User = Depends(get_current_active_user)
):
    """Initiate Google OAuth authorization for specified services"""
    service_list = [s.strip() for s in services.split(",")]
    return await google_oauth_service.initiate_oauth(current_user.id, service_list)

@api_router.get("/oauth/google/callback")
async def handle_google_oauth_callback(
    code: str,
    state: str,
    error: Optional[str] = None
):
    """Handle Google OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    return await google_oauth_service.handle_oauth_callback(code, state)

@api_router.delete("/oauth/google/revoke")
async def revoke_google_oauth(current_user: User = Depends(get_current_active_user)):
    """Revoke Google OAuth tokens for current user"""
    return await google_oauth_service.revoke_oauth_tokens(current_user.id)

# Dashboard and Stats Routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_active_user)):
    """Get dashboard statistics for current user"""
    
    # Count user's data
    intents_count = await db.intents.count_documents({"user_id": current_user.id})
    kb_count = await db.knowledge_base.count_documents({"user_id": current_user.id})
    accounts_count = await db.email_accounts.count_documents({"user_id": current_user.id})
    emails_count = await db.emails.count_documents({"user_id": current_user.id})
    
    # Get recent emails
    recent_emails = await db.emails.find({"user_id": current_user.id}).sort("received_at", -1).limit(5).to_list(5)
    
    return {
        "intents_count": intents_count,
        "knowledge_base_count": kb_count,
        "email_accounts_count": accounts_count,
        "total_emails": emails_count,
        "recent_emails": [EmailMessage(**email) for email in recent_emails],
        "user_quota": {
            "used": current_user.emails_used,
            "limit": current_user.email_quota,
            "percentage": (current_user.emails_used / current_user.email_quota * 100) if current_user.email_quota > 0 else 0
        }
    }

# Health check
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Include the API router
app.include_router(api_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start polling service on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global polling_service
    try:
        # Remove any legacy hardcoded accounts for security
        legacy_accounts = await db.email_accounts.find({"email": "rohushanshinde@gmail.com"}).to_list(100)
        if legacy_accounts:
            result = await db.email_accounts.delete_many({"email": "rohushanshinde@gmail.com"})
            logging.info(f"🔒 Removed {result.deleted_count} legacy hardcoded email accounts for security")
        
        # Initialize polling service
        polling_service = get_polling_service(mongo_url, os.environ['DB_NAME'])
        asyncio.create_task(polling_service.start_polling())
        logging.info("🚀 Email polling service started")
        
    except Exception as e:
        logging.error(f"❌ Startup error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)