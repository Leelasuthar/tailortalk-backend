from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)
import json
import os
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
class GoogleCalendarService:
    """Enhanced Google Calendar Service with comprehensive functionality"""
    
    def __init__(self):
        """Initialize Google Calendar service"""
        try:
            # ✅ Read JSON credentials from env variable
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

            if not service_account_json:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not set in environment variables.")

            credentials_dict = json.loads(service_account_json)

            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/calendar"]
            )
            self.service = build("calendar", "v3", credentials=self.credentials)
            self.calendar_id = settings.CALENDAR_ID
            logger.info("✅ Google Calendar service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Calendar service: {e}")
            raise

    def test_connection(self) -> bool:
        """Test calendar connection"""
        try:
            # Try to get calendar info
            calendar = self.service.calendars().get(calendarId=self.calendar_id).execute()
            logger.info(f"Calendar connection test successful: {calendar.get('summary', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Calendar connection test failed: {e}")
            return False
    
    def check_availability(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if a time slot is available"""
        try:
            # Convert to ISO format with timezone
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            # Add 'Z' suffix if no timezone info
            if start_time.tzinfo is None:
                start_iso += 'Z'
            if end_time.tzinfo is None:
                end_iso += 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Check for conflicts
            for event in events:
                if event.get('status') != 'cancelled':
                    logger.info(f"Time slot conflict found: {event.get('summary', 'Untitled')}")
                    return False
            
            logger.info(f"Time slot available: {start_time} to {end_time}")
            return True
            
        except HttpError as e:
            logger.error(f"HTTP error checking availability: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False
    
    def create_event(self, title: str, start_time: datetime, end_time: datetime, 
                    description: str = "", attendees: List[str] = None, 
                    location: str = None) -> Dict[str, Any]:
        """Create a calendar event"""
        try:
            # Convert to ISO format with timezone
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            # Add 'Z' suffix if no timezone info
            if start_time.tzinfo is None:
                start_iso += 'Z'
            if end_time.tzinfo is None:
                end_iso += 'Z'
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_iso,
                    'timeZone': settings.CALENDAR_TIMEZONE,
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': settings.CALENDAR_TIMEZONE,
                },
            }
            
            # Add attendees if provided
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Add location if provided
            if location:
                event['location'] = location
            
            # Add reminders
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 24 hours
                    {'method': 'popup', 'minutes': 10},       # 10 minutes
                ],
            }
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id, 
                body=event,
                sendUpdates="all" ,
            ).execute()
            logger.info(f"Event created successfully: {created_event}")
            logger.info(f"Event created successfully: {created_event.get('id')}")
            return created_event
            
        except HttpError as e:
            logger.error(f"HTTP error creating event: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise
    
    def get_available_slots(self, date: datetime, duration_minutes: int = 60) -> List[str]:
        """Get available time slots for a given date"""
        try:
            # Define business hours for the given date
            start_of_day = date.replace(
                hour=settings.BUSINESS_START_HOUR, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            end_of_day = date.replace(
                hour=settings.BUSINESS_END_HOUR, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            
            # Check if it's a business day
            if date.weekday() not in settings.BUSINESS_DAYS:
                logger.info(f"Date {date.strftime('%Y-%m-%d')} is not a business day")
                return []
            
            # Get existing events for the day
            start_iso = start_of_day.isoformat() + 'Z'
            end_iso = end_of_day.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Filter out cancelled events and get busy times
            busy_times = []
            for event in events:
                if event.get('status') != 'cancelled':
                    event_start = self._parse_datetime(event['start'])
                    event_end = self._parse_datetime(event['end'])
                    if event_start and event_end:
                        busy_times.append((event_start, event_end))
            
            # Sort busy times
            busy_times.sort(key=lambda x: x[0])
            
            # Find available slots
            available_slots = []
            current_time = start_of_day
            slot_duration = timedelta(minutes=duration_minutes)
            buffer_duration = timedelta(minutes=settings.BOOKING_BUFFER_MINUTES)
            
            for busy_start, busy_end in busy_times:
                # Check if there's enough time before this busy period
                if (busy_start - current_time) >= (slot_duration + buffer_duration):
                    # Add available slots before this busy period
                    while (current_time + slot_duration + buffer_duration) <= busy_start:
                        available_slots.append(current_time.strftime('%I:%M %p'))
                        current_time += slot_duration
                
                # Move current time to after this busy period
                current_time = max(current_time, busy_end + buffer_duration)
            
            # Check for slots after the last busy period
            while (current_time + slot_duration) <= end_of_day:
                available_slots.append(current_time.strftime('%I:%M %p'))
                current_time += slot_duration
            
            logger.info(f"Found {len(available_slots)} available slots for {date.strftime('%Y-%m-%d')}")
            return available_slots[:settings.MAX_SUGGESTIONS]
            
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []
    
    def get_appointments_for_date(self, date: datetime) -> List[Dict[str, Any]]:
        """Get appointments for a specific date"""
        try:
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            start_iso = start_of_day.isoformat() + 'Z'
            end_iso = end_of_day.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            appointments = []
            
            for event in events:
                if event.get('status') != 'cancelled':
                    start_time = self._parse_datetime(event['start'])
                    appointments.append({
                        'id': event.get('id'),
                        'title': event.get('summary', 'Untitled'),
                        'start_time': start_time.strftime('%I:%M %p') if start_time else 'Unknown',
                        'description': event.get('description', ''),
                        'location': event.get('location', ''),
                        'attendees': [attendee.get('email', '') for attendee in event.get('attendees', [])]
                    })
            
            return appointments
            
        except Exception as e:
            logger.error(f"Error getting appointments for date: {e}")
            return []
    
    def get_upcoming_appointments(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming appointments"""
        try:
            now = datetime.now()
            future_date = now + timedelta(days=days_ahead)
            
            now_iso = now.isoformat() + 'Z'
            future_iso = future_date.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now_iso,
                timeMax=future_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            appointments = []
            
            for event in events:
                if event.get('status') != 'cancelled':
                    start_time = self._parse_datetime(event['start'])
                    appointments.append({
                        'id': event.get('id'),
                        'title': event.get('summary', 'Untitled'),
                        'start_time': start_time.strftime('%B %d, %Y at %I:%M %p') if start_time else 'Unknown',
                        'description': event.get('description', ''),
                        'location': event.get('location', ''),
                        'attendees': [attendee.get('email', '') for attendee in event.get('attendees', [])]
                    })
            
            return appointments
            
        except Exception as e:
            logger.error(f"Error getting upcoming appointments: {e}")
            return []
    
    def cancel_event(self, event_id: str) -> bool:
        """Cancel an event"""
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Event cancelled successfully: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"HTTP error cancelling event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling event: {e}")
            return False
    
    def update_event(self, event_id: str, **kwargs) -> bool:
        """Update an existing event"""
        try:
            # Get the existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            if 'title' in kwargs:
                event['summary'] = kwargs['title']
            if 'description' in kwargs:
                event['description'] = kwargs['description']
            if 'location' in kwargs:
                event['location'] = kwargs['location']
            if 'start_time' in kwargs:
                start_iso = kwargs['start_time'].isoformat()
                if kwargs['start_time'].tzinfo is None:
                    start_iso += 'Z'
                event['start'] = {
                    'dateTime': start_iso,
                    'timeZone': settings.CALENDAR_TIMEZONE
                }
            if 'end_time' in kwargs:
                end_iso = kwargs['end_time'].isoformat()
                if kwargs['end_time'].tzinfo is None:
                    end_iso += 'Z'
                event['end'] = {
                    'dateTime': end_iso,
                    'timeZone': settings.CALENDAR_TIMEZONE
                }
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Event updated successfully: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"HTTP error updating event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return False
    
    def _parse_datetime(self, datetime_obj: Dict[str, Any]) -> Optional[datetime]:
        """Parse datetime from Google Calendar API response"""
        try:
            if 'dateTime' in datetime_obj:
                dt_str = datetime_obj['dateTime']
                # Remove timezone info for simplicity
                if dt_str.endswith('Z'):
                    dt_str = dt_str[:-1]
                elif '+' in dt_str:
                    dt_str = dt_str.split('+')[0]
                elif dt_str.count('-') > 2:  # Has timezone offset
                    dt_str = dt_str.rsplit('-', 1)[0]
                
                return datetime.fromisoformat(dt_str)
            elif 'date' in datetime_obj:
                # All-day event
                return datetime.fromisoformat(datetime_obj['date'])
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            return None