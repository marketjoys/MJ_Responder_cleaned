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
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_url = "https://graph.microsoft.com/v1.0"
        
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token"""
        access_token = await microsoft_oauth_service.get_valid_token(self.user_id, 'email')
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
                    logger.error(f"Failed to list messages: {response.text}")
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
    """Microsoft Graph Calendar API service using OAuth"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.base_url = "https://graph.microsoft.com/v1.0"
        
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token"""
        access_token = await microsoft_oauth_service.get_valid_token(self.user_id, 'calendar')
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
