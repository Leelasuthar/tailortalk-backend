import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    def __init__(self):
        # === API & Server Configuration ===
        self.API_TITLE = os.getenv("API_TITLE", "Calendar Booking Agent API")
        self.API_VERSION = os.getenv("API_VERSION", "1.0.0")
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", 8000))
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"

        # === LLM Configuration ===
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gemini-pro")
        self.MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.3"))
        self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", 2048))

        # === Google Calendar ===
        self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./credentials/service-account-key.json")
        self.CALENDAR_ID = os.getenv("CALENDAR_ID")
        self.CALENDAR_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "UTC")

        # === CORS ===
        self.CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")]

        # === Business Hours ===
        self.BUSINESS_START_HOUR = int(os.getenv("BUSINESS_START_HOUR", 9))
        self.BUSINESS_END_HOUR = int(os.getenv("BUSINESS_END_HOUR", 17))
        self.BUSINESS_DAYS = [int(day.strip()) for day in os.getenv("BUSINESS_DAYS", "0,1,2,3,4").split(",")]

        # === Appointment ===
        self.DEFAULT_APPOINTMENT_DURATION = int(os.getenv("DEFAULT_APPOINTMENT_DURATION", 60))
        self.MIN_APPOINTMENT_DURATION = int(os.getenv("MIN_APPOINTMENT_DURATION", 15))
        self.MAX_APPOINTMENT_DURATION = int(os.getenv("MAX_APPOINTMENT_DURATION", 480))
        self.BOOKING_BUFFER_MINUTES = int(os.getenv("BOOKING_BUFFER_MINUTES", 15))

        # === Availability ===
        self.MAX_SUGGESTIONS = int(os.getenv("MAX_SUGGESTIONS", 10))
        self.AVAILABILITY_SEARCH_DAYS = int(os.getenv("AVAILABILITY_SEARCH_DAYS", 30))

        # === Logging ===
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        # === Security ===
        self.SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

        # === Rate Limiting ===
        self.RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
        self.RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))

        # === Agent Info ===
        self.AGENT_NAME = os.getenv("AGENT_NAME", "Calendar Assistant")
        self.AGENT_DESCRIPTION = os.getenv(
            "AGENT_DESCRIPTION",
            "I'm your calendar assistant. I can help you book appointments, check availability, and manage your schedule."
        )

        # === Features ===
        self.ENABLE_BOOKING = os.getenv("ENABLE_BOOKING", "true").lower() == "true"
        self.ENABLE_CANCELLATION = os.getenv("ENABLE_CANCELLATION", "true").lower() == "true"
        self.ENABLE_MODIFICATION = os.getenv("ENABLE_MODIFICATION", "true").lower() == "true"
        self.ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"
        self.ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"

        # === Cache ===
        self.CACHE_TTL = int(os.getenv("CACHE_TTL", 300))

        # === Development ===
        self.MOCK_CALENDAR = os.getenv("MOCK_CALENDAR", "false").lower() == "true"
        self.SAVE_CONVERSATIONS = os.getenv("SAVE_CONVERSATIONS", "false").lower() == "true"

        # === Optional ===
        self.NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")
        self.DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ Export instance
settings = Settings()
