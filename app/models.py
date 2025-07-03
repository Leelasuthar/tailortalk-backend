from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ChatMessage(BaseModel):
    """Chat message model for user input"""
    content: str = Field(..., description="User message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    user_id: Optional[str] = Field(None, description="Optional user identifier")

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str = Field(..., description="Agent response")
    timestamp: datetime = Field(default_factory=datetime.now)
    intent: Optional[str] = Field(None, description="Detected intent")
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")

class BookingRequest(BaseModel):
    """Direct booking request model"""
    title: str = Field(..., description="Appointment title")
    date: str = Field(..., description="Appointment date (YYYY-MM-DD)")
    time: str = Field(..., description="Appointment time (HH:MM)")
    duration: Optional[int] = Field(60, description="Duration in minutes")
    description: Optional[str] = Field("", description="Appointment description")
    attendees: Optional[List[str]] = Field(None, description="List of attendee emails")

class AvailabilityRequest(BaseModel):
    """Availability check request model"""
    date: str = Field(..., description="Date to check (YYYY-MM-DD)")
    time: str = Field(..., description="Time to check (HH:MM)")
    duration: Optional[int] = Field(60, description="Duration in minutes")

class TimeSlot(BaseModel):
    """Time slot model"""
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    available: bool = Field(..., description="Whether slot is available")

class Appointment(BaseModel):
    """Appointment model"""
    id: str = Field(..., description="Appointment ID")
    title: str = Field(..., description="Appointment title")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    description: Optional[str] = Field(None, description="Appointment description")
    attendees: Optional[List[str]] = Field(None, description="List of attendees")
    location: Optional[str] = Field(None, description="Meeting location")

class AppointmentStatus(str, Enum):
    """Appointment status enumeration"""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"

class CalendarEvent(BaseModel):
    """Calendar event model"""
    id: Optional[str] = Field(None, description="Event ID")
    summary: str = Field(..., description="Event summary/title")
    description: Optional[str] = Field(None, description="Event description")
    start: datetime = Field(..., description="Start datetime")
    end: datetime = Field(..., description="End datetime")
    attendees: Optional[List[str]] = Field(None, description="Attendee emails")
    location: Optional[str] = Field(None, description="Event location")
    status: AppointmentStatus = Field(AppointmentStatus.CONFIRMED, description="Event status")

class AgentState(BaseModel):
    """Agent state model for LangGraph"""
    user_message: str = Field(..., description="User input message")
    intent: Optional[str] = Field(None, description="Detected intent")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    tool_results: Optional[str] = Field(None, description="Tool execution results")
    response: Optional[str] = Field(None, description="Generated response")
    error: Optional[str] = Field(None, description="Error message if any")

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_status: str = Field(..., description="Agent initialization status")
    calendar_connected: bool = Field(..., description="Calendar connection status")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now)

class SuccessResponse(BaseModel):
    """Success response model"""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")
    timestamp: datetime = Field(default_factory=datetime.now)