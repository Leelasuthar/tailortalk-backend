# app/__init__.py
"""
Calendar Booking Agent Application
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# app/agent/__init__.py
"""
Calendar Agent Module
"""

from .calendar_agent import CalendarAgent
from .tools import CalendarTools

__all__ = ["CalendarAgent", "CalendarTools"]

# app/services/__init__.py
"""
Services Module
"""

from app.services.calendar_service import GoogleCalendarService

__all__ = ["GoogleCalendarService"]

# app/config/__init__.py
"""
Configuration Module
"""

from app.config.settings import settings

__all__ = ["settings"]