from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Union, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

class CalendarProvider(Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    APPLE = "apple"
    CALCOM = "calcom"

class CalendarProviderConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider_type: CalendarProvider
    provider_name: str
    encrypted_credentials: str
    is_active: bool = True
    default_calendar_id: Optional[str] = None
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CalendarProviderCreate(BaseModel):
    provider_type: CalendarProvider
    provider_name: str
    credentials: Dict[str, Any]
    timezone: str = "UTC"
    
    @validator('credentials')
    def validate_credentials(cls, v, values):
        provider_type = values.get('provider_type')
        
        if provider_type == CalendarProvider.GOOGLE:
            required = ['client_id', 'client_secret']
            for field in required:
                if field not in v:
                    raise ValueError(f"Google Calendar requires '{field}' in credentials")
        
        elif provider_type == CalendarProvider.MICROSOFT:
            required = ['client_id', 'client_secret']
            for field in required:
                if field not in v:
                    raise ValueError(f"Microsoft Calendar requires '{field}' in credentials")
        
        elif provider_type == CalendarProvider.APPLE:
            required = ['username', 'password']
            for field in required:
                if field not in v:
                    raise ValueError(f"Apple Calendar requires '{field}' in credentials")
        
        elif provider_type == CalendarProvider.CALCOM:
            required = ['api_key']
            for field in required:
                if field not in v:
                    raise ValueError(f"Cal.com requires '{field}' in credentials")
        
        return v

class CalendarProviderResponse(BaseModel):
    id: str
    provider_type: CalendarProvider
    provider_name: str
    is_active: bool
    timezone: str
    calendar_count: int = 0
    created_at: datetime
    updated_at: datetime

class CalendarInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    timezone: str
    provider_id: str
    provider_name: str
    provider_type: CalendarProvider
    is_primary: bool = False
    access_role: Optional[str] = None

class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field("", max_length=2000)
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    location: Optional[str] = Field("", max_length=255)
    attendees: Optional[List[str]] = Field([], description="List of attendee email addresses")
    reminders: Optional[List[Dict[str, Any]]] = Field([], description="Reminder configurations")
    recurrence: Optional[str] = Field(None, description="Recurrence rule (RRULE format)")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    @validator('attendees')
    def validate_attendees(cls, v):
        if v:
            for email in v:
                if '@' not in email or len(email.split('@')) != 2:
                    raise ValueError(f'Invalid email address: {email}')
        return v

class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    attendees: Optional[List[str]] = None
    reminders: Optional[List[Dict[str, Any]]] = None
    recurrence: Optional[str] = None

class EventResponse(BaseModel):
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    timezone: str
    location: str
    attendees: List[str]
    created: Optional[datetime]
    updated: Optional[datetime]
    provider_id: str
    calendar_id: str
    provider_type: CalendarProvider
    html_link: Optional[str]
    recurrence: Optional[Union[str, List[str]]]
    reminders: Optional[List[Dict[str, Any]]]
    status: str = "confirmed"

class MeetingIntent(BaseModel):
    """Model for detected meeting intents in emails"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email_id: str
    user_id: str
    thread_id: str
    detected_datetime: Optional[datetime] = None
    detected_timezone: Optional[str] = None
    detected_duration: int = 30  # minutes
    detected_title: Optional[str] = None
    detected_location: Optional[str] = None
    detected_attendees: List[str] = []
    confidence_score: float = 0.0
    status: str = "detected"  # detected, processed, created, failed
    created_event_id: Optional[str] = None
    created_provider_id: Optional[str] = None
    created_calendar_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None

class CalendarEvent(BaseModel):
    """Internal calendar event model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider_id: str
    calendar_id: str
    external_event_id: str
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime
    timezone: str
    location: str = ""
    attendees: List[str] = []
    reminders: List[Dict[str, Any]] = []  # Store reminder configurations
    meeting_intent_id: Optional[str] = None  # Link to meeting intent if created by email
    reminder_sent: bool = False
    last_reminder_sent: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CalendarReminder(BaseModel):
    """Model for calendar reminders"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    user_id: str
    reminder_type: str  # email, notification
    reminder_time: datetime
    message: str
    sent: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response models for API endpoints
class EventSyncRequest(BaseModel):
    source_provider_id: str
    source_event_id: str
    target_provider_ids: List[str]

class EventSyncResponse(BaseModel):
    sync_results: Dict[str, Dict[str, Any]]
    total_targets: int
    successful_syncs: int
    failed_syncs: int

class MeetingDetectionRequest(BaseModel):
    """Request model for manual meeting detection"""
    email_content: str
    sender: str
    subject: str
    user_timezone: str = "UTC"

class MeetingDetectionResponse(BaseModel):
    """Response model for meeting detection"""
    meeting_detected: bool
    confidence_score: float
    detected_datetime: Optional[datetime]
    detected_timezone: Optional[str]
    detected_title: Optional[str]
    detected_location: Optional[str]
    detected_attendees: List[str]
    suggested_duration: int = 30
    needs_confirmation: bool = True

class QuotaInfo(BaseModel):
    """User quota information"""
    email_quota: int
    emails_used: int
    emails_remaining: int
    quota_reset_date: datetime
    days_until_reset: int
    quota_percentage_used: float

class UserProfile(BaseModel):
    """User profile information"""
    id: str
    email: str
    full_name: str
    timezone: str
    email_quota: int
    emails_used: int
    is_active: bool
    created_at: datetime
    quota_info: QuotaInfo