from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from typing import Dict, Any, List
import json
import logging
import re
from datetime import datetime, timedelta
from app.agent.tools import CalendarTools
from app.config.settings import settings

logger = logging.getLogger(__name__)

class CalendarAgent:
    """
    LangGraph-based calendar booking agent that processes natural language
    requests and performs calendar operations.
    """
    
    def __init__(self):
        # Updated model name - use one of these current model names
        model_name = getattr(settings, 'MODEL_NAME', 'gemini-1.5-flash')
        
        # Map old model names to new ones
        model_mapping = {
            'gemini-pro': 'gemini-1.5-flash',
            'gemini-pro-latest': 'gemini-1.5-pro',
            'gemini-pro-vision': 'gemini-1.5-pro'
        }
        
        # Use mapped model name if the current one is outdated
        if model_name in model_mapping:
            model_name = model_mapping[model_name]
            logger.warning(f"Updated model name from {settings.MODEL_NAME} to {model_name}")
        
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3
        )
        self.calendar_tools = CalendarTools()
        self.graph = self._create_graph()
        logger.info(f"Calendar agent initialized with model: {model_name}")
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        # Define the state schema
        def default_state():
            return {
                "user_message": "",
                "intent": None,
                "entities": {},
                "tool_results": None,
                "response": None,
                "error": None
            }
        
        # Create state graph
        graph = StateGraph(dict)
        
        # Add nodes
        graph.add_node("understand_intent", self._understand_intent)
        graph.add_node("extract_entities", self._extract_entities)
        graph.add_node("use_tools", self._use_tools)
        graph.add_node("generate_response", self._generate_response)
        graph.add_node("handle_error", self._handle_error)
        
        # Add edges with conditional logic for error handling
        graph.add_edge("understand_intent", "extract_entities")
        graph.add_conditional_edges(
            "extract_entities",
            lambda x: "handle_error" if x.get("error") else "use_tools"
        )
        graph.add_conditional_edges(
            "use_tools",
            lambda x: "handle_error" if x.get("error") else "generate_response"
        )
        graph.add_edge("generate_response", END)
        graph.add_edge("handle_error", END)
        
        # Set entry point
        graph.set_entry_point("understand_intent")
        
        return graph.compile()
    
    async def process_message(self, message: str) -> str:
        """Process user message and return response"""
        try:
            initial_state = {
                "user_message": message,
                "intent": None,
                "entities": {},
                "tool_results": None,
                "response": None,
                "error": None
            }
            
            result = await self.graph.ainvoke(initial_state)
            
            if result.get("error"):
                return f"I apologize, but I encountered an error: {result['error']}"
            
            return result.get("response", "I'm sorry, I couldn't process your request.")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def _understand_intent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user message to determine intent"""
        try:
            prompt = f"""
            Analyze this user message and determine the primary intent:
            
            Message: "{state['user_message']}"
            
            Choose ONE of these intents:
            1. book_appointment - user wants to book/schedule a new appointment
            2. check_availability - user wants to check if a specific time is available
            3. suggest_times - user wants suggestions for available times
            4. cancel_appointment - user wants to cancel an existing appointment
            5. modify_appointment - user wants to change an existing appointment
            6. list_appointments - user wants to see their scheduled appointments
            7. general_query - general conversation or unclear intent
            
            Respond with ONLY the intent name (e.g., "book_appointment").
            """
            
            response = self.llm.invoke(prompt)
            intent = response.content.strip().lower()
            
            state["intent"] = intent
            logger.info(f"Detected intent: {intent}")
            
        except Exception as e:
            logger.error(f"Error understanding intent: {e}")
            state["error"] = f"Failed to understand your request: {str(e)}"
        
        return state
    
    def _extract_entities(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant entities from user message"""
        try:
            if state.get("error"):
                return state
            
            prompt = f"""
            Extract relevant information from this message for calendar booking:
            
            Message: "{state['user_message']}"
            Intent: {state['intent']}
            
            Extract the following information if present:
            - title: appointment title/subject
            - date: any date mentioned (convert to YYYY-MM-DD format, use today's date as reference)
            - time: any time mentioned (convert to HH:MM format, 24-hour)
            - duration: duration in minutes if mentioned
            - description: any additional details
            - participant: other people mentioned
            
            Important: Return ONLY valid JSON without any markdown formatting or code blocks.
            If information is not present, use null.
            Example: {{"title": "Meeting", "date": "2024-01-15", "time": "14:00", "duration": 60, "description": null, "participant": null}}
            
            Current date for reference: {datetime.now().strftime('%Y-%m-%d')}
            """
            
            response = self.llm.invoke(prompt)
            entities_text = response.content.strip()
            
            # Clean up potential markdown formatting
            entities_text = self._clean_json_response(entities_text)
            
            # Try to parse JSON
            try:
                entities = json.loads(entities_text)
                logger.info(f"Successfully parsed JSON entities: {entities}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from LLM response: {entities_text}")
                logger.warning(f"JSON error: {e}")
                # Fallback to simple extraction
                entities = self._simple_entity_extraction(state['user_message'])
                logger.info(f"Using fallback extraction: {entities}")
            
            state["entities"] = entities
            logger.info(f"Final extracted entities: {entities}")
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            state["error"] = f"Failed to extract information from your message: {str(e)}"
        
        return state
    
    def _clean_json_response(self, text: str) -> str:
        """Clean JSON response from potential markdown formatting"""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Remove any leading/trailing whitespace
        text = text.strip()
        
        # Try to find JSON object in the text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group()
        
        return text
    
    def _simple_entity_extraction(self, message: str) -> Dict[str, Any]:
        """Enhanced fallback entity extraction using regex patterns"""
        entities = {}
        
        # Extract date patterns
        date_patterns = [
            (r'\b(today)\b', 'today'),
            (r'\b(tomorrow)\b', 'tomorrow'),
            (r'\b(yesterday)\b', 'yesterday'),
            (r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', None),
            (r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', None),
            (r'\b(next|this)\s+(week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', None)
        ]
        
        # Extract time patterns
        time_patterns = [
            (r'\b(\d{1,2})\s*(pm|PM)\b', 'pm'),
            (r'\b(\d{1,2})\s*(am|AM)\b', 'am'),
            (r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?\b', 'full'),
            (r'\b(\d{1,2}):(\d{2})\b', '24hr')
        ]
        
        # Extract date
        for pattern, date_type in date_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                if date_type:
                    entities['date'] = date_type
                else:
                    entities['date'] = match.group().strip()
                break
        
        # Extract time
        for pattern, time_type in time_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                if time_type == 'pm':
                    hour = int(match.group(1))
                    if hour != 12:
                        hour += 12
                    entities['time'] = f"{hour:02d}:00"
                elif time_type == 'am':
                    hour = int(match.group(1))
                    if hour == 12:
                        hour = 0
                    entities['time'] = f"{hour:02d}:00"
                elif time_type == 'full':
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    if len(match.groups()) > 2 and match.group(3):
                        if match.group(3).lower() == 'pm' and hour != 12:
                            hour += 12
                        elif match.group(3).lower() == 'am' and hour == 12:
                            hour = 0
                    entities['time'] = f"{hour:02d}:{minute:02d}"
                else:
                    entities['time'] = match.group().strip()
                break
        
        # Extract title (look for appointment-related keywords)
        title_keywords = ['meeting', 'call', 'appointment', 'session', 'conference', 'interview']
        for keyword in title_keywords:
            if keyword in message.lower():
                entities['title'] = keyword.capitalize()
                break
        
        # If no specific title found, use generic
        if 'title' not in entities:
            entities['title'] = 'Appointment'
        
        return entities
    
    def _use_tools(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute appropriate tools based on intent and entities"""
        try:
            if state.get("error"):
                return state
            
            intent = state["intent"]
            entities = state["entities"]
            
            if intent == "book_appointment":
                result = self._handle_booking(entities)
            elif intent == "check_availability":
                result = self._handle_availability_check(entities)
            elif intent == "suggest_times":
                result = self._handle_time_suggestions(entities)
            elif intent == "list_appointments":
                result = self._handle_list_appointments(entities)
            elif intent == "cancel_appointment":
                result = self._handle_cancellation(entities)
            elif intent == "modify_appointment":
                result = self._handle_modification(entities)
            else:
                result = "I can help you book appointments, check availability, suggest times, or manage your calendar. What would you like to do?"
            
            state["tool_results"] = result
            
        except Exception as e:
            logger.error(f"Error using tools: {e}")
            state["error"] = f"Error executing calendar operation: {str(e)}"
        
        return state
    
    def _handle_booking(self, entities: Dict[str, Any]) -> str:
        """Handle appointment booking"""
        try:
            title = entities.get('title', 'Appointment')
            date = entities.get('date')
            time = entities.get('time')
            duration = entities.get('duration', 60)
            description = entities.get('description', '')
            
            if not date or not time:
                return "I need both a date and time to book an appointment. Please provide both."
            
            # Convert to datetime
            booking_datetime = self._parse_datetime(date, time)
            if not booking_datetime:
                return "I couldn't understand the date and time. Please provide them in a clear format like 'tomorrow at 2 PM' or 'October 27th at 2:00 PM'."
            
            # Book the appointment
            result = self.calendar_tools.book_appointment(
                title=title,
                start_time=booking_datetime,
                duration_minutes=duration if duration else 60,
                description=description
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in booking handler: {e}")
            return f"Error booking appointment: {str(e)}"
    
    def _handle_availability_check(self, entities: Dict[str, Any]) -> str:
        """Handle availability checking"""
        try:
            date = entities.get('date')
            time = entities.get('time')
            
            if not date or not time:
                return "Please provide both a date and time to check availability."
            
            check_datetime = self._parse_datetime(date, time)
            if not check_datetime:
                return "I couldn't understand the date and time format."
            
            result = self.calendar_tools.check_availability(check_datetime)
            return result
            
        except Exception as e:
            logger.error(f"Error in availability check: {e}")
            return f"Error checking availability: {str(e)}"
    
    def _handle_time_suggestions(self, entities: Dict[str, Any]) -> str:
        """Handle time suggestions"""
        try:
            date = entities.get('date')
            if not date:
                return "Please provide a date to suggest available times."
            
            # Parse date
            target_date = self._parse_date(date)
            if not target_date:
                return "I couldn't understand the date format."
            
            result = self.calendar_tools.suggest_available_times(target_date)
            return result
            
        except Exception as e:
            logger.error(f"Error in time suggestions: {e}")
            return f"Error suggesting times: {str(e)}"
    
    def _handle_list_appointments(self, entities: Dict[str, Any]) -> str:
        """Handle listing appointments"""
        try:
            date = entities.get('date')
            result = self.calendar_tools.list_appointments(date)
            return result
        except Exception as e:
            logger.error(f"Error listing appointments: {e}")
            return f"Error listing appointments: {str(e)}"
    
    def _handle_cancellation(self, entities: Dict[str, Any]) -> str:
        """Handle appointment cancellation"""
        try:
            # This would need more sophisticated entity extraction
            return "Appointment cancellation is not yet implemented. Please specify which appointment you'd like to cancel."
        except Exception as e:
            logger.error(f"Error in cancellation: {e}")
            return f"Error canceling appointment: {str(e)}"
    
    def _handle_modification(self, entities: Dict[str, Any]) -> str:
        """Handle appointment modification"""
        try:
            return "Appointment modification is not yet implemented. Please specify which appointment you'd like to modify."
        except Exception as e:
            logger.error(f"Error in modification: {e}")
            return f"Error modifying appointment: {str(e)}"
    
    def _generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate natural language response"""
        try:
            if state.get("error"):
                return state
            
            prompt = f"""
            Generate a natural, conversational response based on the following:
            
            User Message: "{state['user_message']}"
            Intent: {state['intent']}
            Tool Results: {state['tool_results']}
            
            Make the response:
            - Natural and conversational
            - Helpful and informative
            - Professional but friendly
            - Concise but complete
            
            Do not mention technical details about intents or tools.
            """
            
            response = self.llm.invoke(prompt)
            state["response"] = response.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            state["response"] = state.get("tool_results", "I'm sorry, I couldn't generate a proper response.")
        
        return state
    
    def _handle_error(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors gracefully"""
        error_msg = state.get("error", "Unknown error occurred")
        state["response"] = f"I apologize, but I encountered an issue: {error_msg}. Please try again or rephrase your request."
        logger.error(f"Error state reached: {error_msg}")
        return state
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into datetime object"""
        try:
            logger.info(f"Parsing datetime: date='{date_str}', time='{time_str}'")
            
            # First, get the target date
            target_date = self._parse_date_component(date_str)
            if not target_date:
                logger.error(f"Could not parse date component: {date_str}")
                return None
            
            # Then, get the target time
            target_time = self._parse_time_component(time_str)
            if not target_time:
                logger.error(f"Could not parse time component: {time_str}")
                return None
            
            # Combine date and time
            result = datetime.combine(target_date, target_time)
            logger.info(f"Successfully parsed datetime: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            return None
    
    def _parse_date_component(self, date_str: str) -> datetime.date:
        """Parse date component"""
        try:
            if not date_str:
                return None
            
            date_str = date_str.lower().strip()
            now = datetime.now()
            
            # Handle relative dates
            if date_str == 'today':
                return now.date()
            elif date_str == 'tomorrow':
                return (now + timedelta(days=1)).date()
            elif date_str == 'yesterday':
                return (now - timedelta(days=1)).date()
            
            # Handle absolute dates
            # Try different formats
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%m-%d-%Y',
                '%d/%m/%Y',
                '%d-%m-%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            # Try with dateutil if available
            try:
                from dateutil import parser
                parsed = parser.parse(date_str)
                return parsed.date()
            except (ImportError, ValueError):
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date component: {e}")
            return None
    
    def _parse_time_component(self, time_str: str) -> datetime.time:
        """Parse time component"""
        try:
            if not time_str:
                return None
            
            time_str = time_str.lower().strip()
            
            # Handle 12-hour format with AM/PM
            if 'pm' in time_str or 'am' in time_str:
                is_pm = 'pm' in time_str
                time_str = time_str.replace('pm', '').replace('am', '').strip()
                
                if ':' in time_str:
                    hour, minute = map(int, time_str.split(':'))
                else:
                    hour = int(time_str)
                    minute = 0
                
                # Convert to 24-hour format
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
                
                return datetime.min.time().replace(hour=hour, minute=minute)
            
            # Handle 24-hour format
            if ':' in time_str:
                hour, minute = map(int, time_str.split(':'))
                return datetime.min.time().replace(hour=hour, minute=minute)
            
            # Handle hour only
            hour = int(time_str)
            return datetime.min.time().replace(hour=hour, minute=0)
            
        except Exception as e:
            logger.error(f"Error parsing time component: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string into datetime object"""
        try:
            target_date = self._parse_date_component(date_str)
            if target_date:
                return datetime.combine(target_date, datetime.min.time())
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date: {e}")
            return None