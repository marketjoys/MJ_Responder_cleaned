from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import json
import logging
import pytz
from cryptography.fernet import Fernet
import os
from motor.motor_asyncio import AsyncIOMotorClient
from calendar_models import CalendarProvider, CalendarInfo, EventResponse, CalendarEvent
from fastapi import HTTPException, status

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import json
import logging
import pytz
from cryptography.fernet import Fernet
import os
from motor.motor_asyncio import AsyncIOMotorClient
from calendar_models import CalendarProvider, CalendarInfo, EventResponse, CalendarEvent
from fastapi import HTTPException, status
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Initialize logging
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

class CredentialManager:
    """Manages encryption/decryption of calendar provider credentials"""
    
    def __init__(self):
        encryption_key = os.environ.get("ENCRYPTION_KEY")
        if not encryption_key:
            # Generate a key for development (in production, this should be set in env)
            encryption_key = Fernet.generate_key().decode()
            logger.warning("Using generated encryption key. Set ENCRYPTION_KEY in production.")
        
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher_suite = Fernet(encryption_key)
    
    def encrypt_credentials(self, credentials_dict: dict) -> str:
        """Encrypt credentials dictionary"""
        credentials_json = json.dumps(credentials_dict)
        encrypted_data = self.cipher_suite.encrypt(credentials_json.encode())
        return encrypted_data.decode()
    
    def decrypt_credentials(self, encrypted_credentials: str) -> dict:
        """Decrypt credentials string to dictionary"""
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_credentials.encode())
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decrypt provider credentials"
            )

class TimezoneManager:
    """Manages timezone operations for calendar events"""
    
    def __init__(self):
        self.utc = pytz.UTC
        self.common_timezones = {
            'UTC': pytz.UTC,
            'US/Eastern': pytz.timezone('US/Eastern'),
            'US/Central': pytz.timezone('US/Central'),
            'US/Mountain': pytz.timezone('US/Mountain'),
            'US/Pacific': pytz.timezone('US/Pacific'),
            'Europe/London': pytz.timezone('Europe/London'),
            'Europe/Paris': pytz.timezone('Europe/Paris'),
            'Asia/Tokyo': pytz.timezone('Asia/Tokyo'),
            'Australia/Sydney': pytz.timezone('Australia/Sydney')
        }
    
    def get_timezone(self, timezone_str: str) -> pytz.BaseTzInfo:
        """Get timezone object from string identifier"""
        try:
            if timezone_str in self.common_timezones:
                return self.common_timezones[timezone_str]
            return pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {timezone_str}, defaulting to UTC")
            return self.utc
    
    def normalize_datetime(self, dt_input: datetime, target_timezone: str = 'UTC') -> datetime:
        """Normalize datetime to target timezone"""
        try:
            if dt_input.tzinfo is None:
                dt_input = self.utc.localize(dt_input)
            
            target_tz = self.get_timezone(target_timezone)
            return dt_input.astimezone(target_tz)
        except Exception as e:
            logger.error(f"Failed to normalize datetime: {e}")
            return dt_input

class BaseCalendarService(ABC):
    """Abstract base class for calendar service implementations"""
    
    def __init__(self, credentials: dict, provider_config: dict = None):
        self.credentials = credentials
        self.provider_config = provider_config or {}
        self.timezone_manager = TimezoneManager()
    
    @abstractmethod
    async def get_calendars(self) -> List[Dict]:
        """Retrieve list of available calendars"""
        pass
    
    @abstractmethod
    async def create_event(self, calendar_id: str, event_data: Dict) -> Dict:
        """Create a new calendar event"""
        pass
    
    @abstractmethod
    async def get_events(self, calendar_id: str, start_time: str = None, 
                        end_time: str = None, max_results: int = 250) -> List[Dict]:
        """Retrieve calendar events within date range"""
        pass
    
    @abstractmethod
    async def update_event(self, calendar_id: str, event_id: str, event_data: Dict) -> Dict:
        """Update existing calendar event"""
        pass
    
    @abstractmethod
    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete calendar event"""
        pass

class MockCalendarService(BaseCalendarService):
    """Mock implementation for development and testing"""
    
    def __init__(self, credentials: dict, provider_config: dict = None):
        super().__init__(credentials, provider_config)
        self.mock_calendars = [
            {
                'id': 'primary',
                'name': 'Primary Calendar',
                'description': 'Main calendar',
                'timezone': 'UTC',
                'is_primary': True
            }
        ]
        self.mock_events = {}
    
    async def get_calendars(self) -> List[Dict]:
        """Return mock calendars"""
        return self.mock_calendars
    
    async def create_event(self, calendar_id: str, event_data: Dict) -> Dict:
        """Create mock event"""
        event_id = f"mock_event_{len(self.mock_events) + 1}"
        created_event = {
            'id': event_id,
            'title': event_data.get('title', ''),
            'description': event_data.get('description', ''),
            'start_time': event_data.get('start_time'),
            'end_time': event_data.get('end_time'),
            'location': event_data.get('location', ''),
            'attendees': event_data.get('attendees', []),
            'created': datetime.now(timezone.utc).isoformat(),
            'updated': datetime.now(timezone.utc).isoformat(),
            'html_link': f'https://calendar.example.com/event/{event_id}',
            'recurrence': event_data.get('recurrence'),
            'reminders': event_data.get('reminders', {})
        }
        
        self.mock_events[event_id] = created_event
        return created_event
    
    async def get_events(self, calendar_id: str, start_time: str = None, 
                        end_time: str = None, max_results: int = 250) -> List[Dict]:
        """Return mock events"""
        return list(self.mock_events.values())[:max_results]
    
    async def update_event(self, calendar_id: str, event_id: str, event_data: Dict) -> Dict:
        """Update mock event"""
        if event_id not in self.mock_events:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event = self.mock_events[event_id]
        event.update(event_data)
        event['updated'] = datetime.now(timezone.utc).isoformat()
        return event
    
    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete mock event"""
        if event_id in self.mock_events:
            del self.mock_events[event_id]
            return True
        return False

class CalendarServiceFactory:
    """Factory for creating calendar service instances"""
    
    @staticmethod
    def create_service(provider: CalendarProvider, credentials: dict, 
                      provider_config: dict = None) -> BaseCalendarService:
        """Create calendar service instance based on provider type"""
        
        # For now, return mock service for all providers
        # In production, implement actual provider services
        logger.info(f"Creating mock calendar service for provider: {provider}")
        return MockCalendarService(credentials, provider_config)

class UnifiedCalendarService:
    """Unified service layer for multi-provider calendar operations"""
    
    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager
        self.active_services = {}
        self.factory = CalendarServiceFactory()
    
    async def get_service(self, provider_id: str, user_id: str) -> BaseCalendarService:
        """Get or create calendar service instance for provider"""
        
        cache_key = f"{user_id}:{provider_id}"
        
        if cache_key not in self.active_services:
            # Load provider credentials from database
            provider = await db.calendar_providers.find_one({
                "id": provider_id,
                "user_id": user_id,
                "is_active": True
            })
            
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Calendar provider not found"
                )
            
            # Decrypt credentials
            credentials = self.credential_manager.decrypt_credentials(
                provider["encrypted_credentials"]
            )
            
            # Create service instance
            provider_type = CalendarProvider(provider["provider_type"])
            service = self.factory.create_service(
                provider_type, credentials, provider.get("provider_config", {})
            )
            
            self.active_services[cache_key] = service
        
        return self.active_services[cache_key]
    
    async def get_all_calendars(self, user_id: str) -> Dict[str, List[CalendarInfo]]:
        """Get calendars from all configured providers for user"""
        
        providers = await db.calendar_providers.find({
            "user_id": user_id,
            "is_active": True
        }).to_list(100)
        
        all_calendars = {}
        
        for provider in providers:
            try:
                service = await self.get_service(provider["id"], user_id)
                calendars = await service.get_calendars()
                
                calendar_info_list = []
                for calendar in calendars:
                    calendar_info = CalendarInfo(
                        id=calendar['id'],
                        name=calendar['name'],
                        description=calendar.get('description', ''),
                        timezone=calendar.get('timezone', 'UTC'),
                        provider_id=provider["id"],
                        provider_name=provider["provider_name"],
                        provider_type=CalendarProvider(provider["provider_type"]),
                        is_primary=calendar.get('is_primary', False),
                        access_role=calendar.get('access_role')
                    )
                    calendar_info_list.append(calendar_info)
                
                all_calendars[provider["provider_name"]] = calendar_info_list
                
            except Exception as e:
                logger.error(f"Failed to get calendars for provider {provider['id']}: {e}")
                all_calendars[provider["provider_name"]] = []
        
        return all_calendars
    
    async def create_event(self, provider_id: str, calendar_id: str, 
                          event_data: Dict, user_id: str) -> EventResponse:
        """Create event in specific calendar"""
        
        try:
            service = await self.get_service(provider_id, user_id)
            created_event = await service.create_event(calendar_id, event_data)
            
            # Store event in database for tracking
            calendar_event = CalendarEvent(
                user_id=user_id,
                provider_id=provider_id,
                calendar_id=calendar_id,
                external_event_id=created_event['id'],
                title=created_event['title'],
                description=created_event['description'],
                start_time=datetime.fromisoformat(created_event['start_time'].replace('Z', '')),
                end_time=datetime.fromisoformat(created_event['end_time'].replace('Z', '')),
                timezone=event_data.get('timezone', 'UTC'),
                location=created_event.get('location', ''),
                attendees=created_event.get('attendees', []),
                meeting_intent_id=event_data.get('meeting_intent_id')
            )
            
            await db.calendar_events.insert_one(calendar_event.dict())
            
            # Get provider info for response
            provider = await db.calendar_providers.find_one({"id": provider_id})
            
            return EventResponse(
                id=created_event['id'],
                title=created_event['title'],
                description=created_event['description'],
                start_time=datetime.fromisoformat(created_event['start_time'].replace('Z', '')),
                end_time=datetime.fromisoformat(created_event['end_time'].replace('Z', '')),
                timezone=event_data.get('timezone', 'UTC'),
                location=created_event.get('location', ''),
                attendees=created_event.get('attendees', []),
                created=datetime.fromisoformat(created_event['created'].replace('Z', '')) if created_event.get('created') else None,
                updated=datetime.fromisoformat(created_event['updated'].replace('Z', '')) if created_event.get('updated') else None,
                provider_id=provider_id,
                calendar_id=calendar_id,
                provider_type=CalendarProvider(provider["provider_type"]),
                html_link=created_event.get('html_link'),
                recurrence=created_event.get('recurrence'),
                reminders=created_event.get('reminders'),
                status="confirmed"
            )
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create event: {str(e)}"
            )
    
    async def get_events(self, provider_id: str, calendar_id: str,
                        start_time: str = None, end_time: str = None,
                        max_results: int = 100, user_id: str = None) -> List[EventResponse]:
        """Get events from specific calendar"""
        
        try:
            service = await self.get_service(provider_id, user_id)
            events = await service.get_events(calendar_id, start_time, end_time, max_results)
            
            # Get provider info
            provider = await db.calendar_providers.find_one({"id": provider_id})
            
            event_responses = []
            for event in events:
                try:
                    event_response = EventResponse(
                        id=event['id'],
                        title=event['title'],
                        description=event['description'],
                        start_time=datetime.fromisoformat(event['start_time'].replace('Z', '')),
                        end_time=datetime.fromisoformat(event['end_time'].replace('Z', '')),
                        timezone=event.get('timezone', 'UTC'),
                        location=event.get('location', ''),
                        attendees=event.get('attendees', []),
                        created=datetime.fromisoformat(event['created'].replace('Z', '')) if event.get('created') else None,
                        updated=datetime.fromisoformat(event['updated'].replace('Z', '')) if event.get('updated') else None,
                        provider_id=provider_id,
                        calendar_id=calendar_id,
                        provider_type=CalendarProvider(provider["provider_type"]),
                        html_link=event.get('html_link'),
                        recurrence=event.get('recurrence'),
                        reminders=event.get('reminders'),
                        status="confirmed"
                    )
                    event_responses.append(event_response)
                except Exception as parse_error:
                    logger.warning(f"Failed to parse event {event.get('id', 'unknown')}: {parse_error}")
                    continue
            
            return event_responses
            
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get events: {str(e)}"
            )
    
    async def update_event(self, provider_id: str, calendar_id: str, event_id: str,
                          event_data: Dict, user_id: str) -> EventResponse:
        """Update event in specific calendar"""
        
        try:
            service = await self.get_service(provider_id, user_id)
            updated_event = await service.update_event(calendar_id, event_id, event_data)
            
            # Update event in database
            await db.calendar_events.update_one(
                {
                    "user_id": user_id,
                    "provider_id": provider_id,
                    "external_event_id": event_id
                },
                {
                    "$set": {
                        "title": updated_event.get('title'),
                        "description": updated_event.get('description'),
                        "location": updated_event.get('location', ''),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Get provider info
            provider = await db.calendar_providers.find_one({"id": provider_id})
            
            return EventResponse(
                id=updated_event['id'],
                title=updated_event['title'],
                description=updated_event['description'],
                start_time=datetime.fromisoformat(updated_event['start_time'].replace('Z', '')),
                end_time=datetime.fromisoformat(updated_event['end_time'].replace('Z', '')),
                timezone=event_data.get('timezone', 'UTC'),
                location=updated_event.get('location', ''),
                attendees=updated_event.get('attendees', []),
                created=datetime.fromisoformat(updated_event['created'].replace('Z', '')) if updated_event.get('created') else None,
                updated=datetime.fromisoformat(updated_event['updated'].replace('Z', '')) if updated_event.get('updated') else None,
                provider_id=provider_id,
                calendar_id=calendar_id,
                provider_type=CalendarProvider(provider["provider_type"]),
                html_link=updated_event.get('html_link'),
                recurrence=updated_event.get('recurrence'),
                reminders=updated_event.get('reminders'),
                status="confirmed"
            )
            
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update event: {str(e)}"
            )
    
    async def delete_event(self, provider_id: str, calendar_id: str, event_id: str, user_id: str) -> bool:
        """Delete event from specific calendar"""
        
        try:
            service = await self.get_service(provider_id, user_id)
            success = await service.delete_event(calendar_id, event_id)
            
            if success:
                # Remove event from database
                await db.calendar_events.delete_one({
                    "user_id": user_id,
                    "provider_id": provider_id,
                    "external_event_id": event_id
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to delete event: {str(e)}"
            )

# Initialize global services
credential_manager = CredentialManager()
calendar_service = UnifiedCalendarService(credential_manager)