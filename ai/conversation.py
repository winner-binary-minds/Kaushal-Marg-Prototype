"""
Conversation Manager - Multilingual Conversational Orchestration Layer

Manages conversations between beneficiaries and the Gemini AI assistant.
Handles message history, language support, and information gathering for
skills and livelihood discovery.

Does NOT perform: recommendation logic, profile extraction, database ops,
voice processing, or UI rendering. Those are separate modules.
"""

import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

from ai.gemini import GeminiClient, GeminiAPIError

logger = logging.getLogger(__name__)


# Supported languages
class Language(str, Enum):
    """Supported conversation languages."""
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"


# Pydantic models for type-safe conversation structure
class Message(BaseModel):
    """A single message in the conversation."""
    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")
    language: str = Field(..., description="Language code (en, hi, mr)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When message was created")
    
    class Config:
        """Pydantic config."""
        # Allow arbitrary types for datetime
        arbitrary_types_allowed = True


class ConversationState(BaseModel):
    """Safe representation of conversation state for external access."""
    language: str = Field(..., description="Current conversation language")
    is_active: bool = Field(..., description="Whether conversation is active")
    message_count: int = Field(..., description="Total messages in history")
    turn_count: int = Field(..., description="Number of user-assistant turns")


class ConversationManager:
    """
    Manages multilingual conversations for Kaushal Marg beneficiaries.
    
    Responsibilities:
    - Maintain conversation history with type-safe structures
    - Generate responses using GeminiClient
    - Support English, Hindi, Marathi
    - Validate inputs and handle errors explicitly
    - Collect information naturally (name, age, skills, etc.)
    
    Does NOT:
    - Perform profile extraction (separate module)
    - Make recommendations (separate module)
    - Access database directly (separate module)
    - Handle voice/audio (separate module)
    - Render UI (separate module)
    """
    
    # System prompts for each language
    SYSTEM_PROMPTS = {
        Language.ENGLISH.value: """You are a respectful, helpful assistant for Kaushal Marg - a skills and livelihood discovery platform for Indian youth.

Your role:
- Help beneficiaries explore their skills, interests, and career preferences
- Speak simply, avoiding technical jargon
- Ask one clear question at a time
- Listen carefully to answers and never repeat questions already answered
- Never invent or assume beneficiary information
- Be inclusive and avoid discriminatory assumptions
- Help with skills, education, work experience, interests, and livelihood preferences

Information to naturally gather (do not ask all at once):
- Name and age
- Gender (only if relevant to job preference)
- Current location
- Education level
- Current skills
- Interests and hobbies
- Work experience
- Preferred type of work
- Constraints or barriers (language, mobility, family, etc.)

Stay focused on discovering skills and livelihood paths, not on solving external problems.
Be encouraging and respectful of all responses.""",
        
        Language.HINDI.value: """आप कौशल मार्ग के लिए एक सम्मानपूर्ण और सहायक सहायक हैं - भारतीय युवाओं के लिए कौशल और आजीविका खोज मंच।

आपकी भूमिका:
- लाभार्थियों को अपने कौशल, रुचियों और कैरियर वरीयताओं का पता लगाने में मदद करें
- सरल भाषा बोलें, तकनीकी शब्दजाल से बचें
- एक समय में एक स्पष्ट प्रश्न पूछें
- उत्तरों को ध्यान से सुनें और पहले से पूछे गए प्रश्नों को दोहराएं नहीं
- कभी भी लाभार्थी की जानकारी का आविष्कार या अनुमान न लगाएं
- समावेशी बनें और भेदभावपूर्ण मान्यताओं से बचें
- कौशल, शिक्षा, कार्य अनुभव, रुचि और आजीविका वरीयताओं में सहायता करें

स्वाभाविक रूप से एकत्र की जाने वाली जानकारी (एक साथ सब कुछ न पूछें):
- नाम और आयु
- लिंग (केवल यदि नौकरी की वरीयता के लिए प्रासंगिक हो)
- वर्तमान स्थान
- शिक्षा स्तर
- वर्तमान कौशल
- रुचियां और शौक
- कार्य अनुभव
- काम का पसंदीदा प्रकार
- बाधाएं या कठिनाइयां (भाषा, गतिविधि, परिवार, आदि)

कौशल और आजीविका पथों की खोज पर ध्यान केंद्रित करें, बाहरी समस्याओं को हल करने पर नहीं।
सभी प्रतिक्रियाओं के लिए प्रोत्साहक और सम्मानपूर्ण रहें।""",
        
        Language.MARATHI.value: """आप कौशल मार्गासाठी एक आदरणीय आणि मददगार सहायक आहात - भारतीय युवकांसाठी कौशल आणि आजीविका शोध प्लॅटफॉर्म।

आपली भूमिका:
- लाभार्थींना त्यांचे कौशल, रुची आणि कारकीर्द प्राधान्य शोधण्यात मदत करा
- सरल भाषा बोला, तांत्रिक शब्दावली टाळा
- एक वेळी एक स्पष्ट प्रश्न विचारा
- उत्तरे काळजीपूर्वक ऐका आणि आधीच विचारलेले प्रश्न पुन्हा न विचारा
- कधीही लाभार्थीची माहिती बनवू किंवा गृहीत धरू नका
- समावेशक राहा आणि भेदभावपूर्ण धारणा टाळा
- कौशल, शिक्षा, कार्य अनुभव, रुची आणि आजीविका प्राधान्यात मदत करा

नैसर्गिकरित्या संकलित करायची माहिती (एकाचवेळी सर्व विचारू नका):
- नाव आणि वय
- लिंग (फक्त जर कामाच्या पसंदीसाठी प्रासंगिक असेल)
- वर्तमान स्थान
- शिक्षा पातळी
- वर्तमान कौशल
- रुची आणि छंद
- कार्य अनुभव
- काम करण्याचा पसंदीदा प्रकार
- अडचणी किंवा अडथळे (भाषा, गतिशीलता, कुटुंब, इ)

कौशल आणि आजीविका मार्गांच्या शोधावर लक्ष केंद्रित ठेवा, बाह्य समस्या सोडवण्यावर नाही।
सर्व प्रतिक्रियांसाठी प्रोत्साहक आणि आदरणीय राहा।"""
    }
    
    def __init__(
        self,
        api_key: str | None = None,
        language: str = Language.ENGLISH.value,
        max_history_size: int = 50,
    ):
        """
        Initialize the conversation manager.
        
        Args:
            api_key: Gemini API key (optional, reads from env if not provided)
            language: Initial language ('en', 'hi', 'mr'). Defaults to English.
            max_history_size: Maximum messages to keep in history. Defaults to 50.
        
        Raises:
            ValueError: If language is not supported or max_history_size is invalid.
            GeminiConfigError: If GeminiClient initialization fails.
        """
        # Validate language
        if language not in [lang.value for lang in Language]:
            raise ValueError(
                f"Language must be one of {[lang.value for lang in Language]}, got '{language}'"
            )
        
        # Validate max_history_size
        if not isinstance(max_history_size, int) or max_history_size <= 0:
            raise ValueError(f"max_history_size must be positive integer, got {max_history_size}")
        
        # Initialize attributes
        self._language = language
        self._max_history_size = max_history_size
        self._history: list[Message] = []
        self._is_active = False
        
        # Initialize Gemini client
        try:
            self._gemini_client = GeminiClient(
                api_key=api_key,
                max_output_tokens=1024,
            )
            logger.debug(f"ConversationManager initialized: language={language}, max_history={max_history_size}")
        except Exception as e:
            raise ValueError(f"Failed to initialize conversation manager: {str(e)}") from e
    
    def start_conversation(self) -> str:
        """
        Start a new conversation and return the initial greeting.
        
        Returns:
            Initial greeting message from the assistant.
        
        Raises:
            GeminiAPIError: If API call fails.
        """
        # Reset conversation state
        self._history = []
        self._is_active = True
        
        # Generate initial greeting
        try:
            greeting_prompt = "Provide a warm, welcoming greeting to start a conversation. Keep it brief (1-2 sentences)."
            response = self._gemini_client.generate_text(
                f"{self.SYSTEM_PROMPTS[self._language]}\n\n{greeting_prompt}"
            )
            
            # Add assistant message to history
            self._add_message(role="assistant", content=response)
            
            logger.info(f"Conversation started: language={self._language}")
            return response
        
        except GeminiAPIError as e:
            self._is_active = False
            logger.error(f"Failed to start conversation: {str(e)}")
            raise
    
    def send_message(self, user_message: str) -> str:
        """
        Process a user message and generate an assistant response.
        
        Args:
            user_message: The beneficiary's message (must be non-empty string).
        
        Returns:
            Assistant's response message.
        
        Raises:
            ValueError: If message is empty or conversation not active.
            GeminiAPIError: If API call fails.
        """
        # Validate inputs
        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("user_message must be a non-empty string")
        
        if not self._is_active:
            raise ValueError("Conversation not active. Call start_conversation() first.")
        
        user_message = user_message.strip()
        
        try:
            # Add user message to history
            self._add_message(role="user", content=user_message)
            
            # Build conversation context
            context = self._build_conversation_context()
            
            # Generate response
            response = self._gemini_client.generate_text(context)
            
            # Add assistant message to history
            self._add_message(role="assistant", content=response)
            
            logger.debug(f"Message processed: turn={len(self._history)//2}")
            return response
        
        except GeminiAPIError as e:
            logger.error(f"Failed to generate response: {str(e)}")
            raise
    
    def reset(self) -> None:
        """Reset the conversation - clear history and mark as inactive."""
        self._history = []
        self._is_active = False
        logger.info("Conversation reset")
    
    def set_language(self, language: str) -> None:
        """
        Change the conversation language.
        
        Args:
            language: New language code ('en', 'hi', 'mr').
        
        Raises:
            ValueError: If language is not supported.
        """
        if language not in [lang.value for lang in Language]:
            raise ValueError(
                f"Language must be one of {[lang.value for lang in Language]}, got '{language}'"
            )
        
        self._language = language
        logger.info(f"Language changed to: {language}")
    
    def get_state(self) -> ConversationState:
        """
        Get the current conversation state (safe, no sensitive content).
        
        Returns:
            ConversationState with metadata about the conversation.
        """
        return ConversationState(
            language=self._language,
            is_active=self._is_active,
            message_count=len(self._history),
            turn_count=len(self._history) // 2,  # Each turn is user + assistant
        )
    
    def get_language(self) -> str:
        """
        Get the current conversation language.
        
        Returns:
            Language code ('en', 'hi', 'mr').
        """
        return self._language
    
    def get_history(self) -> list[Message]:
        """
        Get the conversation message history.
        
        Returns:
            List of Message objects representing the full conversation.
        """
        return self._history
    
    # Private helper methods
    
    def _add_message(self, role: str, content: str) -> None:
        """
        Add a message to history, respecting max size limit.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        message = Message(
            role=role,
            content=content,
            language=self._language,
        )
        
        self._history.append(message)
        
        # Trim history if needed
        if len(self._history) > self._max_history_size:
            removed_count = len(self._history) - self._max_history_size
            self._history = self._history[-self._max_history_size:]
            logger.debug(f"Trimmed {removed_count} messages from history")
    
    def _build_conversation_context(self) -> str:
        """
        Build the full conversation context for the API call.
        
        Includes system prompt and recent message history.
        
        Returns:
            Formatted conversation prompt.
        """
        # Start with system prompt
        context = self.SYSTEM_PROMPTS[self._language]
        
        # Add recent conversation history
        context += "\n\n--- Conversation History ---\n"
        for msg in self._history:
            prefix = "User:" if msg.role == "user" else "Assistant:"
            context += f"{prefix} {msg.content}\n"
        
        context += "\nNow respond to the user's latest message:"
        
        return context
