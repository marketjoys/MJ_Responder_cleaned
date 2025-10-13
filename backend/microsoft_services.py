"""
Microsoft Graph API Services for Email and Calendar using OAuth tokens
"""
import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from oauth_microsoft import microsoft_oauth_service

logger = logging.getLogger(__name__)

class MicrosoftMailService:
    """Microsoft Outlook Mail API service using OAuth"""
    
    def __init__(self, user_id: str, oauth_email: Optional[str] = None):
        self.user_id = user_id
        self.oauth_email = oauth_email  # Specific email for multi-account support
        self.base_url = "https://graph.microsoft.com/v1.0"
        
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token for specific account"""
        access_token = await microsoft_oauth_service.get_valid_token(self.user_id, 'email', self.oauth_email)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Microsoft email access not authorized or expired"
            )
        
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    async def list_messages(self, folder: str = 'inbox', max_results: int = 100) -> List[Dict[str, Any]]:
        """
        List email messages from specified folder
        
        Args:
            folder: Folder name (inbox, sent, drafts, etc.)
            max_results: Maximum number of messages to retrieve
            
        Returns:
            List of email messages
        """
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/me/mailFolders/{folder}/messages",
                    headers=headers,
                    params={
                        '$top': max_results,
                        '$select': 'id,subject,from,toRecipients,receivedDateTime,isRead,bodyPreview,body',
                        '$orderby': 'receivedDateTime desc'
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to list messages: Status {response.status_code}, Response: {response.text}")
                    logger.error(f"Request headers: {headers}")
                    logger.error(f"Request URL: {response.url}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to retrieve messages: {response.text}"
                    )
                
                data = response.json()
                return data.get('value', [])
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing messages: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list messages: {str(e)}"
            )
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Get a specific email message
        
        Args:
            message_id: Message ID
            
        Returns:
            Email message details
        """
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/me/messages/{message_id}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get message: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to retrieve message: {response.text}"
                    )
                
                return response.json()
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get message: {str(e)}"
            )
    
    async def send_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        body_type: str = 'HTML',
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email message
        
        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body content
            body_type: Body content type ('HTML' or 'Text')
            cc: List of CC recipients
            bcc: List of BCC recipients
            reply_to: Reply-to email address
            
        Returns:
            Sent message details
        """
        try:
            headers = await self._get_headers()
            
            # Build message structure
            message = {
                'subject': subject,
                'body': {
                    'contentType': body_type,
                    'content': body
                },
                'toRecipients': [{'emailAddress': {'address': addr}} for addr in to]
            }
            
            if cc:
                message['ccRecipients'] = [{'emailAddress': {'address': addr}} for addr in cc]
            
            if bcc:
                message['bccRecipients'] = [{'emailAddress': {'address': addr}} for addr in bcc]
            
            if reply_to:
                message['replyTo'] = [{'emailAddress': {'address': reply_to}}]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/me/sendMail",
                    headers=headers,
                    json={'message': message}
                )
                
                if response.status_code not in [200, 202]:
                    logger.error(f"Failed to send message: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to send message: {response.text}"
                    )
                
                return {'status': 'sent', 'message': 'Email sent successfully'}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send message: {str(e)}"
            )

class MicrosoftCalendarService:
    """Microsoft Graph Calendar API service using OAuth (supports multiple accounts)"""
    
    def __init__(self, user_id: str, oauth_email: Optional[str] = None):
        self.user_id = user_id
        self.oauth_email = oauth_email  # Specific email for multi-account support
        self.base_url = "https://graph.microsoft.com/v1.0"
        
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token for specific account"""
        access_token = await microsoft_oauth_service.get_valid_token(self.user_id, 'calendar', self.oauth_email)
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    async def list_events(
        self,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List calendar events
        
        Args:
            start_datetime: Start datetime filter
            end_datetime: End datetime filter
            max_results: Maximum number of events to retrieve
            
        Returns:
            List of calendar events
        """
        try:
            headers = await self._get_headers()
            
            params = {
                '$top': max_results,
                '$orderby': 'start/dateTime',
                '$select': 'id,subject,start,end,location,attendees,organizer,body'
            }
            
            # Add date filter if provided
            if start_datetime and end_datetime:
                start_str = start_datetime.strftime('%Y-%m-%dT%H:%M:%S')
                end_str = end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
                params['$filter'] = f"start/dateTime ge '{start_str}' and end/dateTime le '{end_str}'"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/me/events",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to list events: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to retrieve events: {response.text}"
                    )
                
                data = response.json()
                return data.get('value', [])
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list events: {str(e)}"
            )
    
    async def create_event(
        self,
        subject: str,
        start: datetime,
        end: datetime,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        body: Optional[str] = None,
        timezone: str = 'UTC'
    ) -> Dict[str, Any]:
        """
        Create a calendar event
        
        Args:
            subject: Event title
            start: Event start datetime
            end: Event end datetime
            location: Event location
            attendees: List of attendee email addresses
            body: Event description
            timezone: Timezone for the event
            
        Returns:
            Created event details
        """
        try:
            headers = await self._get_headers()
            
            # Build event structure
            event = {
                'subject': subject,
                'start': {
                    'dateTime': start.strftime('%Y-%m-%dT%H:%M:%S'),
                    'timeZone': timezone
                },
                'end': {
                    'dateTime': end.strftime('%Y-%m-%dT%H:%M:%S'),
                    'timeZone': timezone
                }
            }
            
            if location:
                event['location'] = {'displayName': location}
            
            if attendees:
                event['attendees'] = [
                    {
                        'emailAddress': {'address': addr},
                        'type': 'required'
                    }
                    for addr in attendees
                ]
            
            if body:
                event['body'] = {
                    'contentType': 'HTML',
                    'content': body
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/me/events",
                    headers=headers,
                    json=event
                )
                
                if response.status_code not in [200, 201]:
                    logger.error(f"Failed to create event: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to create event: {response.text}"
                    )
                
                return response.json()
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create event: {str(e)}"
            )
    
    async def get_event(self, event_id: str) -> Dict[str, Any]:
        """
        Get a specific calendar event
        
        Args:
            event_id: Event ID
            
        Returns:
            Event details
        """
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/me/events/{event_id}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get event: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to retrieve event: {response.text}"
                    )
                
                return response.json()
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting event: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get event: {str(e)}"
            )
    
    # Adapter methods to match BaseCalendarService interface
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """Adapter method for UnifiedCalendarService compatibility"""
        # Microsoft typically has one default calendar per user
        return [
            {
                'id': 'primary',
                'name': 'Calendar',
                'description': 'Microsoft Outlook Calendar',
                'timezone': 'UTC',
                'is_primary': True,
                'access_role': 'owner'
            }
        ]
    
    async def get_events(self, calendar_id: str, start_time: str = None, 
                        end_time: str = None, max_results: int = 250) -> List[Dict[str, Any]]:
        """Adapter method for UnifiedCalendarService compatibility"""
        # Convert string dates to datetime if provided
        start_dt = None
        end_dt = None
        if start_time:
            from dateutil import parser as date_parser
            start_dt = date_parser.parse(start_time)
        if end_time:
            from dateutil import parser as date_parser
            end_dt = date_parser.parse(end_time)
        
        events = await self.list_events(start_dt, end_dt, max_results)
        
        # Transform Microsoft Graph event format to standard format
        result = []
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})
            
            result.append({
                'id': event.get('id'),
                'title': event.get('subject', 'No Title'),
                'description': event.get('body', {}).get('content', ''),
                'start_time': start.get('dateTime'),
                'end_time': end.get('dateTime'),
                'timezone': start.get('timeZone', 'UTC'),
                'location': event.get('location', {}).get('displayName', ''),
                'attendees': [att.get('emailAddress', {}).get('address') for att in event.get('attendees', [])],
                'created': event.get('createdDateTime'),
                'updated': event.get('lastModifiedDateTime'),
                'html_link': event.get('webLink'),
                'recurrence': event.get('recurrence'),
                'reminders': event.get('isReminderOn')
            })
        return result
    
    async def update_event(self, calendar_id: str, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter method for UnifiedCalendarService compatibility"""
        try:
            headers = await self._get_headers()
            
            # Transform standard format to Microsoft Graph format
            update_payload = {}
            if 'title' in event_data:
                update_payload['subject'] = event_data['title']
            if 'description' in event_data:
                update_payload['body'] = {
                    'contentType': 'HTML',
                    'content': event_data['description']
                }
            if 'start_time' in event_data:
                update_payload['start'] = {
                    'dateTime': event_data['start_time'],
                    'timeZone': event_data.get('timezone', 'UTC')
                }
            if 'end_time' in event_data:
                update_payload['end'] = {
                    'dateTime': event_data['end_time'],
                    'timeZone': event_data.get('timezone', 'UTC')
                }
            if 'location' in event_data:
                update_payload['location'] = {'displayName': event_data['location']}
            if 'attendees' in event_data:
                update_payload['attendees'] = [
                    {
                        'emailAddress': {'address': addr},
                        'type': 'required'
                    }
                    for addr in event_data['attendees']
                ]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    f"{self.base_url}/me/events/{event_id}",
                    headers=headers,
                    json=update_payload
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to update event: {response.text}"
                    )
                
                # Get the updated event and transform it
                updated_event = response.json()
                start = updated_event.get('start', {})
                end = updated_event.get('end', {})
                
                return {
                    'id': updated_event.get('id'),
                    'title': updated_event.get('subject', ''),
                    'description': updated_event.get('body', {}).get('content', ''),
                    'start_time': start.get('dateTime'),
                    'end_time': end.get('dateTime'),
                    'timezone': start.get('timeZone', 'UTC'),
                    'location': updated_event.get('location', {}).get('displayName', ''),
                    'attendees': [att.get('emailAddress', {}).get('address') for att in updated_event.get('attendees', [])],
                    'created': updated_event.get('createdDateTime'),
                    'updated': updated_event.get('lastModifiedDateTime'),
                    'html_link': updated_event.get('webLink'),
                    'recurrence': updated_event.get('recurrence'),
                    'reminders': updated_event.get('isReminderOn')
                }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update event: {str(e)}"
            )
    
    async def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Adapter method for UnifiedCalendarService compatibility"""
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}/me/events/{event_id}",
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
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete event: {str(e)}"
            )
