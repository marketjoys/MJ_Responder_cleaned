from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import re
import logging
import asyncio
from dateutil import parser as date_parser
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
import os
import httpx
from calendar_models import MeetingIntent, MeetingDetectionResponse, CalendarEvent
from calendar_services import calendar_service, TimezoneManager
from auth import increment_email_usage, check_email_quota

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import re
import logging
import asyncio
from dateutil import parser as date_parser
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
import os
import httpx
from calendar_models import MeetingIntent, MeetingDetectionResponse, CalendarEvent
from calendar_services import calendar_service, TimezoneManager
from auth import increment_email_usage, check_email_quota
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

# API Keys
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

class CalendarAgent:
    """Intelligent agent for managing calendar events from email conversations"""
    
    def __init__(self):
        self.timezone_manager = TimezoneManager()
        
        # Meeting detection patterns
        self.meeting_keywords = [
            'meeting', 'meet', 'call', 'discussion', 'conference', 'appointment',
            'sync', 'catch up', 'demo', 'presentation', 'interview', 'consultation',
            'session', 'workshop', 'training', 'webinar', 'briefing', 'review'
        ]
        
        self.time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)\b',
            r'\b(\d{1,2})\s*(am|pm|AM|PM)\b',
            r'\b(\d{1,2}):(\d{2})\b',
            r'\b(\d{4}-\d{2}-\d{2})\b',
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',
            r'\b(\d{1,2}-\d{1,2}-\d{4})\b'
        ]
        
        self.date_keywords = [
            'today', 'tomorrow', 'next week', 'next month', 'monday', 'tuesday',
            'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'jan', 'feb',
            'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
        ]
    
    async def analyze_email_for_meetings(self, email_content: str, subject: str, 
                                       sender: str, user_timezone: str = "UTC",
                                       thread_context: List[Dict] = None) -> MeetingDetectionResponse:
        """
        Analyze email content for meeting intents using AI and pattern matching
        """
        
        try:
            # Combine subject and content for analysis
            full_content = f"Subject: {subject}\n\nContent: {email_content}"
            
            # Use AI to detect meeting intent and extract details
            ai_detection = await self._ai_meeting_detection(full_content, user_timezone, thread_context)
            
            # Use pattern matching as backup/validation
            pattern_detection = await self._pattern_meeting_detection(email_content, subject, user_timezone)
            
            # Combine AI and pattern detection results
            combined_detection = self._combine_detection_results(ai_detection, pattern_detection)
            
            return MeetingDetectionResponse(
                meeting_detected=combined_detection['detected'],
                confidence_score=combined_detection['confidence'],
                detected_datetime=combined_detection.get('datetime'),
                detected_timezone=combined_detection.get('timezone'),
                detected_title=combined_detection.get('title') or subject,
                detected_location=combined_detection.get('location'),
                detected_attendees=combined_detection.get('attendees', [sender]),
                suggested_duration=combined_detection.get('duration', 30),
                needs_confirmation=combined_detection['confidence'] < 0.8
            )
            
        except Exception as e:
            logger.error(f"Error analyzing email for meetings: {e}")
            return MeetingDetectionResponse(
                meeting_detected=False,
                confidence_score=0.0,
                needs_confirmation=True
            )
    
    async def _ai_meeting_detection(self, content: str, user_timezone: str, 
                                  thread_context: List[Dict] = None) -> Dict:
        """Use AI to detect meeting intents and extract details"""
        
        try:
            # Prepare enhanced thread context - prioritize email bodies over subjects
            context_info = ""
            if thread_context:
                context_info = "PREVIOUS CONVERSATION CONTEXT (showing full message content):\n"
                for i, msg in enumerate(thread_context[-5:]):  # Last 5 messages for better context
                    msg_date = msg.get('received_at', 'Unknown date')
                    sender = msg.get('sender', 'Unknown sender')
                    subject = msg.get('subject', 'No subject')
                    body = msg.get('body', msg.get('draft', ''))[:500]  # Increased to 500 chars
                    
                    context_info += f"Message {i+1} ({msg_date}):\n"
                    context_info += f"From: {sender}\n"
                    context_info += f"Subject: {subject}\n"
                    context_info += f"Content: {body}...\n\n"
                context_info += "END OF CONVERSATION CONTEXT\n\n"
            
            # Get current time for context
            current_time = datetime.now(pytz.timezone(user_timezone))
            
            system_prompt = f"""You are an AI calendar agent that detects meeting intents in emails and extracts scheduling details.

CURRENT CONTEXT:
- Current Date/Time: {current_time.strftime('%Y-%m-%d %H:%M %Z')}
- User Timezone: {user_timezone}

{context_info}

TASK: Analyze the email content AND conversation context to determine if it contains a meeting request or scheduling intent.

ENHANCED DETECTION CRITERIA:
1. Meeting Intent: Look for explicit or implicit meeting language:
   - Direct: "meeting", "call", "appointment", "discussion", "demo", "interview"
   - Indirect: "let's connect", "catch up", "chat", "sync", "touch base", "get together"
   - Scheduling: "schedule", "book", "arrange", "set up", "plan"
   
2. Date/Time Information: Extract from BOTH current email and thread context:
   - Specific: "Tuesday at 3pm", "January 15th at 2:00", "tomorrow at 10am"
   - Relative: "next week", "this Friday", "in 2 hours"
   - Consider thread context for date/time mentioned in previous messages
   
3. Contextual Clues:
   - Replies to meeting requests should be treated as meeting-related
   - Follow-up emails about previously discussed meetings
   - Confirmation or rescheduling requests

EXTRACTION REQUIREMENTS:
- Date/Time: Extract the most specific date and time mentioned in email or context
- Duration: Estimate based on meeting type (30 min default, 60 min for demos/interviews)
- Location: Physical address, conference room, or virtual meeting link
- Attendees: Email addresses or names mentioned
- Title: Generate descriptive title based on meeting purpose

RESPONSE FORMAT (JSON):
{{
    "detected": true/false,
    "confidence": 0.0-1.0,
    "datetime": "YYYY-MM-DDTHH:MM:SS" (in user timezone),
    "timezone": "{user_timezone}",
    "duration": minutes (integer),
    "title": "Meeting title",
    "location": "Meeting location or null",
    "attendees": ["email1", "email2"],
    "reasoning": "Explanation of detection"
}}

ENHANCED DETECTION RULES:
- Set detected=true for ANY clear meeting intent, even with partial date/time info
- High confidence (>0.8): Specific date, time, and clear meeting purpose
- Medium confidence (0.5-0.8): Clear meeting intent with date OR time
- Low confidence (0.3-0.5): Meeting keywords present but vague timing
- Consider conversation context - if previous emails mentioned dates/times
- If current email is a reply to meeting discussion, inherit context
- Convert all times to user's timezone
- Use conversation context to infer missing date/time details
- Be generous with detection but conservative with confidence scoring

EMAIL TO ANALYZE:
{content}
"""
            
            messages = [
                {"role": "user", "content": "Analyze this email for meeting scheduling intent and extract details."}
            ]
            
            response = await self._groq_chat_completion(messages, system_prompt)
            
            # Parse JSON response
            import json
            try:
                detection_result = json.loads(response)
                
                # Validate and normalize the response
                if detection_result.get('detected') and detection_result.get('datetime'):
                    try:
                        # Parse and validate datetime
                        dt = date_parser.parse(detection_result['datetime'])
                        if dt.tzinfo is None:
                            dt = pytz.timezone(user_timezone).localize(dt)
                        
                        detection_result['datetime'] = dt
                        detection_result['timezone'] = user_timezone
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse AI-detected datetime: {e}")
                        detection_result['detected'] = False
                        detection_result['confidence'] = 0.0
                
                return detection_result
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI response as JSON: {e}")
                return {'detected': False, 'confidence': 0.0}
                
        except Exception as e:
            logger.error(f"AI meeting detection failed: {e}")
            return {'detected': False, 'confidence': 0.0}
    
    async def _pattern_meeting_detection(self, content: str, subject: str, user_timezone: str) -> Dict:
        """Use pattern matching to detect meeting intents"""
        
        try:
            full_text = f"{subject} {content}".lower()
            
            # Check for meeting keywords
            meeting_score = 0
            for keyword in self.meeting_keywords:
                if keyword in full_text:
                    meeting_score += 1
            
            # Normalize meeting score
            meeting_confidence = min(meeting_score / 3.0, 1.0)
            
            if meeting_confidence < 0.3:
                return {'detected': False, 'confidence': 0.0}
            
            # Extract time information
            time_info = self._extract_time_patterns(content, user_timezone)
            
            if time_info['found']:
                return {
                    'detected': True,
                    'confidence': min(meeting_confidence + 0.3, 1.0),
                    'datetime': time_info['datetime'],
                    'timezone': user_timezone,
                    'duration': 30,
                    'title': subject,
                    'location': self._extract_location(content),
                    'attendees': []
                }
            else:
                return {
                    'detected': False,
                    'confidence': meeting_confidence,
                    'reasoning': 'Meeting keywords found but no specific time'
                }
                
        except Exception as e:
            logger.error(f"Pattern meeting detection failed: {e}")
            return {'detected': False, 'confidence': 0.0}
    
    def _extract_time_patterns(self, content: str, user_timezone: str) -> Dict:
        """Extract time patterns from content"""
        
        try:
            tz = pytz.timezone(user_timezone)
            now = datetime.now(tz)
            
            # Look for time patterns
            for pattern in self.time_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        try:
                            # Try to parse the time
                            if len(match) == 3 and match[2]:  # Hour:Minute AM/PM
                                hour = int(match[0])
                                minute = int(match[1])
                                am_pm = match[2].upper()
                                
                                if am_pm == 'PM' and hour != 12:
                                    hour += 12
                                elif am_pm == 'AM' and hour == 12:
                                    hour = 0
                                
                                # Assume tomorrow if time has passed today
                                proposed_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                                if proposed_time <= now:
                                    proposed_time += timedelta(days=1)
                                
                                return {
                                    'found': True,
                                    'datetime': proposed_time,
                                    'confidence': 0.7
                                }
                                
                        except (ValueError, IndexError):
                            continue
            
            # Look for date keywords
            for keyword in self.date_keywords:
                if keyword in content.lower():
                    if keyword == 'today':
                        return {
                            'found': True,
                            'datetime': now.replace(hour=14, minute=0, second=0, microsecond=0),  # Default to 2 PM
                            'confidence': 0.5
                        }
                    elif keyword == 'tomorrow':
                        tomorrow = now + timedelta(days=1)
                        return {
                            'found': True,
                            'datetime': tomorrow.replace(hour=14, minute=0, second=0, microsecond=0),
                            'confidence': 0.6
                        }
            
            return {'found': False}
            
        except Exception as e:
            logger.error(f"Error extracting time patterns: {e}")
            return {'found': False}
    
    def _extract_location(self, content: str) -> Optional[str]:
        """Extract location information from content"""
        
        # Look for common location patterns
        location_patterns = [
            r'at\s+([^.\n]+(?:office|room|building|center|hall|zoom|teams|meet))',
            r'in\s+([^.\n]+(?:room|office|building|center|hall))',
            r'via\s+(zoom|teams|skype|google meet|webex)',
            r'on\s+(zoom|teams|skype|google meet|webex)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _combine_detection_results(self, ai_result: Dict, pattern_result: Dict) -> Dict:
        """Combine AI and pattern detection results"""
        
        # If AI detected with high confidence, use AI result
        if ai_result.get('detected') and ai_result.get('confidence', 0) >= 0.7:
            return ai_result
        
        # If pattern detected with time info, use pattern result
        if pattern_result.get('detected') and pattern_result.get('datetime'):
            return pattern_result
        
        # If AI detected but lower confidence, still use it
        if ai_result.get('detected'):
            return ai_result
        
        # Default to no detection
        return {'detected': False, 'confidence': 0.0}
    
    async def process_meeting_intent(self, email_id: str, user_id: str, 
                                   meeting_detection: MeetingDetectionResponse,
                                   thread_id: str) -> Optional[str]:
        """
        Process detected meeting intent and create calendar event if conditions are met
        """
        
        try:
            # Check if meeting has clear datetime and high confidence
            if (not meeting_detection.meeting_detected or 
                not meeting_detection.detected_datetime or 
                meeting_detection.confidence_score < 0.5):
                
                logger.info(f"Meeting intent not processed - insufficient confidence or missing datetime")
                return None
            
            # Check user quota
            user_data = await db.users.find_one({"id": user_id})
            if not user_data:
                logger.warning(f"User {user_id} not found")
                return None
            
            # Convert dict to User object for quota check
            from auth import User
            user_obj = User(**user_data)
            if not await check_email_quota(user_obj):
                logger.warning(f"User {user_id} exceeded email quota")
                return None
            
            # Create meeting intent record
            meeting_intent = MeetingIntent(
                email_id=email_id,
                user_id=user_id,
                thread_id=thread_id,
                detected_datetime=meeting_detection.detected_datetime,
                detected_timezone=meeting_detection.detected_timezone,
                detected_duration=meeting_detection.suggested_duration,
                detected_title=meeting_detection.detected_title,
                detected_location=meeting_detection.detected_location,
                detected_attendees=meeting_detection.detected_attendees,
                confidence_score=meeting_detection.confidence_score,
                status="detected"
            )
            
            # Store meeting intent
            await db.meeting_intents.insert_one(meeting_intent.dict())
            
            # If confidence is high enough, create calendar event immediately
            # Updated threshold to 0.5 to match meeting detection threshold
            if meeting_detection.confidence_score >= 0.5 and not meeting_detection.needs_confirmation:
                event_id = await self._create_calendar_event(meeting_intent, user_id)
                
                if event_id:
                    # Update meeting intent status
                    await db.meeting_intents.update_one(
                        {"id": meeting_intent.id},
                        {
                            "$set": {
                                "status": "created",
                                "created_event_id": event_id,
                                "processed_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                    
                    # Increment user's email usage
                    await increment_email_usage(user_id)
                    
                    logger.info(f"Successfully created calendar event {event_id} for meeting intent {meeting_intent.id}")
                    return event_id
            
            # If lower confidence, mark for manual review
            await db.meeting_intents.update_one(
                {"id": meeting_intent.id},
                {"$set": {"status": "pending_confirmation"}}
            )
            
            return meeting_intent.id
            
        except Exception as e:
            logger.error(f"Error processing meeting intent: {e}")
            return None
    
    async def _create_calendar_event(self, meeting_intent: MeetingIntent, user_id: str) -> Optional[str]:
        """Create calendar event from meeting intent"""
        
        try:
            # Get user's default calendar provider
            default_provider = await db.calendar_providers.find_one({
                "user_id": user_id,
                "is_active": True
            })
            
            if not default_provider:
                logger.warning(f"No calendar provider found for user {user_id}")
                return None
            
            # Get default calendar
            service = await calendar_service.get_service(default_provider["id"], user_id)
            calendars = await service.get_calendars()
            
            default_calendar = next((cal for cal in calendars if cal.get('is_primary')), calendars[0] if calendars else None)
            
            if not default_calendar:
                logger.warning(f"No calendars found for provider {default_provider['id']}")
                return None
            
            # Calculate end time
            start_time = meeting_intent.detected_datetime
            end_time = start_time + timedelta(minutes=meeting_intent.detected_duration)
            
            # Prepare event data
            event_data = {
                'title': meeting_intent.detected_title or "Meeting",
                'description': f"Meeting scheduled automatically from email conversation.",
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'timezone': meeting_intent.detected_timezone or "UTC",
                'location': meeting_intent.detected_location or "",
                'attendees': meeting_intent.detected_attendees,
                'meeting_intent_id': meeting_intent.id,
                'reminders': [
                    {'method': 'email', 'minutes': 60},  # 1 hour before
                    {'method': 'popup', 'minutes': 15}   # 15 minutes before
                ]
            }
            
            # Create the event in external calendar (Google/Microsoft)
            event_response = await calendar_service.create_event(
                default_provider["id"],
                default_calendar['id'],
                event_data,
                user_id
            )
            
            logger.info(f"Created calendar event: {event_response.id}")
            
            # CRITICAL FIX: Store event in calendar_events collection for tracking
            calendar_event_doc = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'provider_id': default_provider["id"],
                'calendar_id': default_calendar['id'],
                'external_event_id': event_response.id,  # ID from Google/Microsoft
                'meeting_intent_id': meeting_intent.id,
                'thread_id': meeting_intent.thread_id,
                'title': meeting_intent.detected_title or "Meeting",
                'description': event_data.get('description', ''),
                'start_time': start_time,
                'end_time': end_time,
                'timezone': meeting_intent.detected_timezone or "UTC",
                'location': meeting_intent.detected_location or "",
                'attendees': meeting_intent.detected_attendees,
                'status': 'confirmed',
                'reminder_sent': False,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            try:
                await db.calendar_events.insert_one(calendar_event_doc)
                logger.info(f"✅ Stored calendar event in DB: {calendar_event_doc['id']}")
            except Exception as db_error:
                logger.error(f"❌ Failed to store calendar event in DB: {db_error}")
                # Don't fail the whole operation, event is still created externally
            
            return event_response.id
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None
    
    async def update_meeting_from_email(self, email_content: str, thread_id: str, 
                                      user_id: str, user_timezone: str = "UTC") -> Optional[str]:
        """
        Update existing meeting based on email content (date/time changes, cancellations)
        """
        
        try:
            # Find existing meeting intents for this thread
            existing_intents = await db.meeting_intents.find({
                "user_id": user_id,
                "thread_id": thread_id,
                "status": {"$in": ["created", "pending_confirmation"]}
            }).to_list(10)
            
            if not existing_intents:
                logger.info(f"No existing meeting intents found for thread {thread_id}")
                return None
            
            # Analyze email for changes
            change_analysis = await self._analyze_meeting_changes(email_content, existing_intents, user_timezone)
            
            if change_analysis.get('action') == 'cancel':
                return await self._cancel_meetings(existing_intents, user_id)
            elif change_analysis.get('action') == 'reschedule':
                return await self._reschedule_meetings(existing_intents, change_analysis, user_id)
            elif change_analysis.get('action') == 'update':
                return await self._update_meeting_details(existing_intents, change_analysis, user_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating meeting from email: {e}")
            return None
    
    async def _analyze_meeting_changes(self, email_content: str, existing_intents: List[Dict], 
                                     user_timezone: str) -> Dict:
        """Analyze email content for meeting changes using AI"""
        
        try:
            # Prepare context about existing meetings
            meeting_context = "EXISTING MEETINGS:\n"
            for intent in existing_intents:
                meeting_context += f"- {intent.get('detected_title', 'Meeting')} on {intent.get('detected_datetime')} in {intent.get('detected_timezone')}\n"
            
            system_prompt = f"""You are an AI agent that analyzes emails for meeting changes (reschedule, cancel, update).

CONTEXT:
{meeting_context}

CURRENT USER TIMEZONE: {user_timezone}

TASK: Analyze the email content to determine if it requests changes to existing meetings.

POSSIBLE ACTIONS:
1. "cancel" - Meeting cancellation request
2. "reschedule" - Request to change date/time
3. "update" - Change in location, attendees, or other details
4. "none" - No changes requested

RESPONSE FORMAT (JSON):
{{
    "action": "cancel|reschedule|update|none",
    "confidence": 0.0-1.0,
    "new_datetime": "YYYY-MM-DDTHH:MM:SS" (if rescheduling),
    "new_timezone": "{user_timezone}" (if rescheduling),
    "new_location": "location" (if updating),
    "new_attendees": ["email1", "email2"] (if updating),
    "reasoning": "Explanation"
}}

EMAIL TO ANALYZE:
{email_content}
"""
            
            messages = [
                {"role": "user", "content": "Analyze this email for meeting changes."}
            ]
            
            response = await self._groq_chat_completion(messages, system_prompt)
            
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {'action': 'none', 'confidence': 0.0}
                
        except Exception as e:
            logger.error(f"Error analyzing meeting changes: {e}")
            return {'action': 'none', 'confidence': 0.0}
    
    async def _cancel_meetings(self, meeting_intents: List[Dict], user_id: str) -> str:
        """Cancel meetings based on email request"""
        
        try:
            cancelled_count = 0
            
            for intent in meeting_intents:
                if intent.get('created_event_id'):
                    # Find the calendar event
                    calendar_event = await db.calendar_events.find_one({
                        "user_id": user_id,
                        "external_event_id": intent['created_event_id']
                    })
                    
                    if calendar_event:
                        # Delete from calendar
                        success = await calendar_service.delete_event(
                            calendar_event['provider_id'],
                            calendar_event['calendar_id'],
                            calendar_event['external_event_id'],
                            user_id
                        )
                        
                        if success:
                            cancelled_count += 1
                
                # Update meeting intent status
                await db.meeting_intents.update_one(
                    {"id": intent["id"]},
                    {
                        "$set": {
                            "status": "cancelled",
                            "processed_at": datetime.now(timezone.utc)
                        }
                    }
                )
            
            logger.info(f"Cancelled {cancelled_count} meetings for user {user_id}")
            return f"cancelled_{cancelled_count}_meetings"
            
        except Exception as e:
            logger.error(f"Error cancelling meetings: {e}")
            return "cancellation_failed"
    
    async def _reschedule_meetings(self, meeting_intents: List[Dict], change_analysis: Dict, user_id: str) -> str:
        """Reschedule meetings based on email request"""
        
        try:
            if not change_analysis.get('new_datetime'):
                return "reschedule_failed_no_time"
            
            new_datetime = date_parser.parse(change_analysis['new_datetime'])
            reschedule_count = 0
            
            for intent in meeting_intents:
                if intent.get('created_event_id'):
                    # Find the calendar event
                    calendar_event = await db.calendar_events.find_one({
                        "user_id": user_id,
                        "external_event_id": intent['created_event_id']
                    })
                    
                    if calendar_event:
                        # Calculate new end time
                        duration = intent.get('detected_duration', 30)
                        new_end_time = new_datetime + timedelta(minutes=duration)
                        
                        # Update calendar event
                        update_data = {
                            'start_time': new_datetime.isoformat(),
                            'end_time': new_end_time.isoformat(),
                            'timezone': change_analysis.get('new_timezone', intent.get('detected_timezone', 'UTC'))
                        }
                        
                        updated_event = await calendar_service.update_event(
                            calendar_event['provider_id'],
                            calendar_event['calendar_id'],
                            calendar_event['external_event_id'],
                            update_data,
                            user_id
                        )
                        
                        if updated_event:
                            reschedule_count += 1
                
                # Update meeting intent
                await db.meeting_intents.update_one(
                    {"id": intent["id"]},
                    {
                        "$set": {
                            "detected_datetime": new_datetime,
                            "detected_timezone": change_analysis.get('new_timezone', intent.get('detected_timezone')),
                            "status": "rescheduled",
                            "processed_at": datetime.now(timezone.utc)
                        }
                    }
                )
            
            logger.info(f"Rescheduled {reschedule_count} meetings for user {user_id}")
            return f"rescheduled_{reschedule_count}_meetings"
            
        except Exception as e:
            logger.error(f"Error rescheduling meetings: {e}")
            return "reschedule_failed"
    
    async def _update_meeting_details(self, meeting_intents: List[Dict], change_analysis: Dict, user_id: str) -> str:
        """Update meeting details based on email request"""
        
        try:
            update_count = 0
            
            for intent in meeting_intents:
                if intent.get('created_event_id'):
                    # Find the calendar event
                    calendar_event = await db.calendar_events.find_one({
                        "user_id": user_id,
                        "external_event_id": intent['created_event_id']
                    })
                    
                    if calendar_event:
                        # Prepare update data
                        update_data = {}
                        
                        if change_analysis.get('new_location'):
                            update_data['location'] = change_analysis['new_location']
                        
                        if change_analysis.get('new_attendees'):
                            update_data['attendees'] = change_analysis['new_attendees']
                        
                        if update_data:
                            updated_event = await calendar_service.update_event(
                                calendar_event['provider_id'],
                                calendar_event['calendar_id'],
                                calendar_event['external_event_id'],
                                update_data,
                                user_id
                            )
                            
                            if updated_event:
                                update_count += 1
                
                # Update meeting intent
                update_fields = {"processed_at": datetime.now(timezone.utc)}
                if change_analysis.get('new_location'):
                    update_fields['detected_location'] = change_analysis['new_location']
                if change_analysis.get('new_attendees'):
                    update_fields['detected_attendees'] = change_analysis['new_attendees']
                
                await db.meeting_intents.update_one(
                    {"id": intent["id"]},
                    {"$set": update_fields}
                )
            
            logger.info(f"Updated details for {update_count} meetings for user {user_id}")
            return f"updated_{update_count}_meetings"
            
        except Exception as e:
            logger.error(f"Error updating meeting details: {e}")
            return "update_failed"
    
    async def send_meeting_reminders(self, user_id: str) -> int:
        """Send reminders for upcoming meetings"""
        
        try:
            # Find upcoming meetings that need reminders
            now = datetime.now(timezone.utc)
            reminder_window = now + timedelta(hours=24)  # 24 hour window
            
            upcoming_events = await db.calendar_events.find({
                "user_id": user_id,
                "start_time": {
                    "$gte": now,
                    "$lte": reminder_window
                },
                "reminder_sent": {"$ne": True}
            }).to_list(50)
            
            reminder_count = 0
            
            for event in upcoming_events:
                # Check if reminder should be sent (1 hour before)
                reminder_time = event['start_time'] - timedelta(hours=1)
                
                if now >= reminder_time:
                    # Send reminder (this would integrate with email service)
                    await self._send_event_reminder(event, user_id)
                    
                    # Mark reminder as sent
                    await db.calendar_events.update_one(
                        {"id": event["id"]},
                        {
                            "$set": {
                                "reminder_sent": True,
                                "last_reminder_sent": now
                            }
                        }
                    )
                    
                    reminder_count += 1
            
            return reminder_count
            
        except Exception as e:
            logger.error(f"Error sending meeting reminders: {e}")
            return 0
    
    async def _send_event_reminder(self, event: Dict, user_id: str):
        """Send reminder for specific event"""
        
        try:
            # Get user info
            user = await db.users.find_one({"id": user_id})
            if not user:
                return
            
            # Create reminder message
            reminder_message = f"""
            Meeting Reminder: {event.get('title', 'Untitled Meeting')}
            
            Time: {event['start_time'].strftime('%Y-%m-%d %H:%M %Z')}
            Location: {event.get('location', 'Not specified')}
            
            This meeting was automatically scheduled from your email conversation.
            """
            
            # Store reminder record
            reminder = {
                'id': f"reminder_{event['id']}_{int(datetime.now().timestamp())}",
                'event_id': event['id'],
                'user_id': user_id,
                'reminder_type': 'email',
                'reminder_time': datetime.now(timezone.utc),
                'message': reminder_message,
                'sent': True,
                'sent_at': datetime.now(timezone.utc),
                'created_at': datetime.now(timezone.utc)
            }
            
            await db.calendar_reminders.insert_one(reminder)
            
            logger.info(f"Sent reminder for event {event['id']} to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending event reminder: {e}")
    
    async def _groq_chat_completion(self, messages: List[Dict], system_prompt: str = "") -> str:
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
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.3,
                    "max_completion_tokens": 2048,
                    "top_p": 0.9,
                    "stream": False
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                raise Exception(f"Groq API error: {response.status_code}")

# Initialize global calendar agent
calendar_agent = CalendarAgent()