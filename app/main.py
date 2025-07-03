from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class ChatMessage(BaseModel):
    content: str
    timestamp: Optional[datetime] = None

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime

class BookingRequest(BaseModel):
    title: str
    date: str
    time: str
    duration: Optional[int] = 60  # minutes
    description: Optional[str] = ""

# Initialize FastAPI app
app = FastAPI(
    title="Calendar Booking Agent API",
    description="AI-powered calendar booking agent with natural language processing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent (will be imported)
calendar_agent = None

@app.on_event("startup")
async def startup_event():
    global calendar_agent
    try:
        from app.agent.calendar_agent import CalendarAgent
        calendar_agent = CalendarAgent()
        logger.info("Calendar agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize calendar agent: {e}")
        raise

@app.get("/")
async def root():
    return {"message": "Calendar Booking Agent API", "status": "running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Process chat message and return agent response
    """
    try:
        if not calendar_agent:
            raise HTTPException(status_code=500, detail="Agent not initialized")
        
        logger.info(f"Processing message: {message.content}")
        response = await calendar_agent.process_message(message.content)
        
        return ChatResponse(
            response=response,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/book")
async def book_appointment(booking: BookingRequest):
    """
    Direct booking endpoint
    """
    try:
        if not calendar_agent:
            raise HTTPException(status_code=500, detail="Agent not initialized")
        
        # Format booking request as natural language
        booking_message = f"Book an appointment titled '{booking.title}' on {booking.date} at {booking.time} for {booking.duration} minutes"
        if booking.description:
            booking_message += f" with description: {booking.description}"
        
        response = await calendar_agent.process_message(booking_message)
        return {"message": response, "booking_details": booking.dict()}
    
    except Exception as e:
        logger.error(f"Booking error: {e}")
        raise HTTPException(status_code=500, detail=f"Error booking appointment: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "agent_status": "initialized" if calendar_agent else "not_initialized"
    }

@app.get("/available-slots/{date}")
async def get_available_slots(date: str):
    """
    Get available time slots for a specific date
    """
    try:
        if not calendar_agent:
            raise HTTPException(status_code=500, detail="Agent not initialized")
        
        message = f"What times are available on {date}?"
        response = await calendar_agent.process_message(message)
        
        return {"date": date, "response": response}
    
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting available slots: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)