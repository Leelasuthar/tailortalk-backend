from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from app.services.calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)

class CalendarTools:
    """
    Calendar tools for booking, checking availability, and managing appointments
    """
    
    def __init__(self):
        self.calendar_service = GoogleCalendarService()
    
    def check_availability(self, start_time: datetime, duration_minutes: int = 60) -> str:
        """
        Check if a specific date/time is available
        
        Args:
            start_time: The start time to check
            duration_minutes: Duration of the appointment in minutes
            
        Returns:
            String describing availability
        """
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            is_available = self.calendar_service.check_availability(start_time, end_time)
            
            if is_available:
                return f"✅ The time slot on {start_time.strftime('%B %d, %Y at %I:%M %p')} is available!"
            else:
                return f"❌ The time slot on {start_time.strftime('%B %d, %Y at %I:%M %p')} is not available. Please choose a different time."
                
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return f"I couldn't check availability due to an error: {str(e)}"
    
    def book_appointment(self, title: str, start_time: datetime, duration_minutes: int = 60, description: str = "") -> str:
        """
        Book an appointment
        
        Args:
            title: Title of the appointment
            start_time: Start time of the appointment
            duration_minutes: Duration in minutes
            description: Optional description
            
        Returns:
            Confirmation message
        """
        try:
            # end_time = start_time + timedelta(minutes=duration_minutes)
            duration = duration_minutes if duration_minutes is not None else 60
            end_time = start_time + timedelta(minutes=duration)
            
            # First check if time is available
            if not self.calendar_service.check_availability(start_time, end_time):
                return f"❌ Sorry, the time slot on {start_time.strftime('%B %d, %Y at %I:%M %p')} is not available. Please choose a different time."
            
            # Create the event
            event = self.calendar_service.create_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description
            )
            status = event.get('status', 'confirmed')
            htmlLink = event.get('htmlLink', '')
            return f"""✅ Appointment '{title}' successfully booked for {start_time.strftime('%B %d, %Y at %I:%M %p')} ({duration_minutes} minutes)! and
            {'Status: ' + status if status else ''} {'Link: ' + htmlLink if htmlLink else ''}"""
            
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return f"❌ I couldn't book the appointment due to an error: {str(e)}"
    
    def suggest_available_times(self, date: datetime, duration_minutes: int = 60, num_suggestions: int = 5) -> str:
        """
        Suggest available time slots for a given date
        
        Args:
            date: The date to check
            duration_minutes: Duration of appointment in minutes
            num_suggestions: Number of suggestions to provide
            
        Returns:
            String with available time suggestions
        """
        try:
            available_slots = self.calendar_service.get_available_slots(
                date=date,
                duration_minutes=duration_minutes
            )
            
            if not available_slots:
                return f"❌ No available time slots found for {date.strftime('%B %d, %Y')}. Please try a different date."
            
            # Format the suggestions
            suggestions = []
            for slot in available_slots[:num_suggestions]:
                suggestions.append(f"• {slot}")
            
            suggestion_text = "\n".join(suggestions)
            
            return f"📅 Available time slots for {date.strftime('%B %d, %Y')}:\n\n{suggestion_text}"
            
        except Exception as e:
            logger.error(f"Error suggesting times: {e}")
            return f"❌ I couldn't suggest available times due to an error: {str(e)}"
    
    def list_appointments(self, date: Optional[str] = None) -> str:
        """
        List appointments for a specific date or upcoming appointments
        
        Args:
            date: Optional date to filter appointments
            
        Returns:
            String with appointment list
        """
        try:
            if date:
                # Parse date and get appointments for that day
                from dateutil import parser
                target_date = parser.parse(date)
                appointments = self.calendar_service.get_appointments_for_date(target_date)
                date_str = target_date.strftime('%B %d, %Y')
            else:
                # Get upcoming appointments
                appointments = self.calendar_service.get_upcoming_appointments()
                date_str = "upcoming"
            
            if not appointments:
                return f"📅 No appointments found for {date_str}."
            
            # Format appointments
            appointment_list = []
            for apt in appointments:
                start_time = apt.get('start_time', 'Unknown time')
                title = apt.get('title', 'No title')
                appointment_list.append(f"• {start_time} - {title}")
            
            appointments_text = "\n".join(appointment_list)
            
            return f"📅 Appointments for {date_str}:\n\n{appointments_text}"
            
        except Exception as e:
            logger.error(f"Error listing appointments: {e}")
            return f"❌ I couldn't list appointments due to an error: {str(e)}"
    
    def cancel_appointment(self, appointment_id: str) -> str:
        """
        Cancel an appointment
        
        Args:
            appointment_id: ID of the appointment to cancel
            
        Returns:
            Confirmation message
        """
        try:
            success = self.calendar_service.cancel_event(appointment_id)
            
            if success:
                return f"✅ Appointment successfully canceled!"
            else:
                return f"❌ I couldn't cancel the appointment. Please check the appointment ID."
                
        except Exception as e:
            logger.error(f"Error canceling appointment: {e}")
            return f"❌ I couldn't cancel the appointment due to an error: {str(e)}"
    
    def modify_appointment(self, appointment_id: str, **kwargs) -> str:
        """
        Modify an existing appointment
        
        Args:
            appointment_id: ID of the appointment to modify
            **kwargs: Fields to update (title, start_time, end_time, description)
            
        Returns:
            Confirmation message
        """
        try:
            success = self.calendar_service.update_event(appointment_id, **kwargs)
            
            if success:
                return f"✅ Appointment successfully updated!"
            else:
                return f"❌ I couldn't update the appointment. Please check the appointment ID."
                
        except Exception as e:
            logger.error(f"Error modifying appointment: {e}")
            return f"❌ I couldn't modify the appointment due to an error: {str(e)}"
    
    def get_calendar_status(self) -> str:
        """
        Get general calendar status and connectivity
        
        Returns:
            Status message
        """
        try:
            status = self.calendar_service.test_connection()
            
            if status:
                return "✅ Calendar is connected and working properly!"
            else:
                return "❌ Calendar connection issues detected."
                
        except Exception as e:
            logger.error(f"Error checking calendar status: {e}")
            return f"❌ Calendar status check failed: {str(e)}"
    
    def find_next_available_slot(self, preferred_date: datetime, duration_minutes: int = 60) -> str:
        """
        Find the next available time slot starting from a preferred date
        
        Args:
            preferred_date: Starting date to search from
            duration_minutes: Duration of appointment in minutes
            
        Returns:
            Next available slot information
        """
        try:
            # Search for next 7 days
            for i in range(7):
                search_date = preferred_date + timedelta(days=i)
                available_slots = self.calendar_service.get_available_slots(
                    date=search_date,
                    duration_minutes=duration_minutes
                )
                
                if available_slots:
                    next_slot = available_slots[0]
                    return f"🔍 Next available slot: {next_slot} on {search_date.strftime('%B %d, %Y')}"
            
            return "❌ No available slots found in the next 7 days. Please try a different time range."
            
        except Exception as e:
            logger.error(f"Error finding next available slot: {e}")
            return f"❌ I couldn't find the next available slot due to an error: {str(e)}"