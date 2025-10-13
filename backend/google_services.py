"""
Google API Services for Email and Calendar using OAuth tokens
"""
import os
import logging
import base64
import email
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from fastapi import HTTPException, status
from oauth_google import google_oauth_service

logger = logging.getLogger(__name__)

class GoogleGmailService:
    """Gmail API service using OAuth (supports multiple accounts)"""
    
    def __init__(self, user_id: str, oauth_email: Optional[str] = None):
        self.user_id = user_id
        self.oauth_email = oauth_email  # Specific email for multi-account support
        self.base_url = "https://gmail.googleapis.com/gmail/v1"
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token for specific account"""
        access_token = await google_oauth_service.get_valid_token(self.user_id, 'email', self.oauth_email)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google email access not authorized or expired"
            )
        
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get Gmail profile information"""
        headers = await self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/me/profile",
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to get Gmail profile: {response.text}"
                )
            
            return response.json()
    
    async def list_messages(self, query: str = "", max_results: int = 100) -> List[Dict[str, Any]]:
        """List Gmail messages with optional query"""
        headers = await self._get_headers()
        
        params = {
            'maxResults': min(max_results, 500),  # Gmail API limit
            'q': query
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/me/messages",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to list messages: {response.text}"
                )
            
            data = response.json()
            return data.get('messages', [])
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get full message details by ID"""
        headers = await self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/me/messages/{message_id}",
                headers=headers,
                params={'format': 'raw'}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to get message: {response.text}"
                )
            
            return response.json()
    
    async def send_message(self, to_email: str, subject: str, body: str, 
                          body_html: str = None, in_reply_to: str = None) -> Dict[str, Any]:
        """Send email through Gmail API"""
        headers = await self._get_headers()
        
        # Create message
        msg = MIMEMultipart('alternative') if body_html else MIMEText(body, 'plain', 'utf-8')
        
        if isinstance(msg, MIMEMultipart):
            msg['To'] = to_email
            msg['Subject'] = subject
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
            
            # Add text part
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, 'html', 'utf-8')
                msg.attach(html_part)
        else:
            msg['To'] = to_email
            msg['Subject'] = subject
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        
        message_data = {
            'raw': raw_message
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/users/me/messages/send",
                headers=headers,
                json=message_data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to send message: {response.text}"
                )
            
            return response.json()
    
    async def create_watch(self, topic_name: str) -> Dict[str, Any]:
        """Set up Gmail push notifications (optional for real-time email)"""
        headers = await self._get_headers()
        
        watch_data = {
            'topicName': topic_name,
            'labelIds': ['INBOX'],
            'labelFilterAction': 'include'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/users/me/watch",
                headers=headers,
                json=watch_data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to create watch: {response.text}"
                )
            
            return response.json()

class GoogleCalendarService:
    """Google Calendar API service using OAuth"""
    
    def __init__(self, user_id: str, oauth_email: Optional[str] = None):
        self.user_id = user_id
        self.oauth_email = oauth_email  # Specific email for multi-account support
        self.base_url = "https://www.googleapis.com/calendar/v3"
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token for specific account"""
        access_token = await google_oauth_service.get_valid_token(self.user_id, 'calendar', self.oauth_email)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google calendar access not authorized or expired"
            )
        
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    async def list_calendars(self) -> List[Dict[str, Any]]:
        """List user's calendars"""
        headers = await self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/me/calendarList",
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to list calendars: {response.text}"
                )
            
            data = response.json()
            return data.get('items', [])
    
    async def create_event(self, calendar_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create calendar event"""
        headers = await self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/calendars/{calendar_id}/events",
                headers=headers,
                json=event_data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to create event: {response.text}"
                )
            
            return response.json()
    
    async def list_events(self, calendar_id: str = 'primary', 
                         time_min: str = None, time_max: str = None,
                         max_results: int = 250) -> List[Dict[str, Any]]:
        """List calendar events"""
        headers = await self._get_headers()
        
        params = {
            'maxResults': min(max_results, 2500),  # Calendar API limit
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if time_min:
            params['timeMin'] = time_min
        if time_max:
            params['timeMax'] = time_max
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/calendars/{calendar_id}/events",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to list events: {response.text}"
                )
            
            data = response.json()
            return data.get('items', [])
    
    async def update_event(self, calendar_id: str, event_id: str, 
                          event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update calendar event"""
        headers = await self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
                json=event_data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to update event: {response.text}"
                )
            
            return response.json()
    
    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete calendar event"""
        headers = await self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/calendars/{calendar_id}/events/{event_id}",
                headers=headers
            )
            
            if response.status_code == 204:
                return True
            elif response.status_code == 404:
                return True  # Already deleted
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to delete event: {response.text}"
                )
    
    # Adapter methods to match BaseCalendarService interface
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """Adapter method for UnifiedCalendarService compatibility"""
        calendars = await self.list_calendars()
        # Transform Google Calendar format to standard format
        return [
            {
                'id': cal.get('id'),
                'name': cal.get('summary', ''),
                'description': cal.get('description', ''),
                'timezone': cal.get('timeZone', 'UTC'),
                'is_primary': cal.get('primary', False),
                'access_role': cal.get('accessRole', '')
            }
            for cal in calendars
        ]
    
    async def get_events(self, calendar_id: str, start_time: str = None, 
                        end_time: str = None, max_results: int = 250) -> List[Dict[str, Any]]:
        """Adapter method for UnifiedCalendarService compatibility"""
        events = await self.list_events(calendar_id, start_time, end_time, max_results)
        # Transform Google Calendar event format to standard format
        result = []
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Handle all-day events and regular events
            start_time = start.get('dateTime') or start.get('date')
            end_time = end.get('dateTime') or end.get('date')
            
            result.append({
                'id': event.get('id'),
                'title': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start_time': start_time,
                'end_time': end_time,
                'timezone': start.get('timeZone', 'UTC'),
                'location': event.get('location', ''),
                'attendees': [att.get('email') for att in event.get('attendees', [])],
                'created': event.get('created'),
                'updated': event.get('updated'),
                'html_link': event.get('htmlLink'),
                'recurrence': event.get('recurrence'),
                'reminders': event.get('reminders')
            })
        return result


async def get_google_gmail_service(user_id: str, oauth_email: Optional[str] = None) -> GoogleGmailService:
    """Get Gmail service instance for user (supports multiple accounts)"""
    return GoogleGmailService(user_id, oauth_email)

async def get_google_calendar_service(user_id: str, oauth_email: Optional[str] = None) -> GoogleCalendarService:
    """Get Calendar service instance for user (supports multiple accounts)"""
    return GoogleCalendarService(user_id, oauth_email)