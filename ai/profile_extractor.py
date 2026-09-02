"""
Profile Extractor - Conversation to Beneficiary Profile Bridge

Extracts structured beneficiary profile information from conversation history.
Converts multilingual conversation messages into standardized profile dictionary.

Responsibilities:
- Extract profile information from conversation messages
- Support English, Hindi, Marathi conversation content
- Handle missing/incomplete information gracefully
- Validate input and propagate errors explicitly

Does NOT:
- Perform recommendations (separate module)
- Access database (separate module)
- Render UI (separate module)
- Modify conversation messages
- Translate content unnecessarily
"""

import logging
from typing import Type, TypeVar

from pydantic import BaseModel, Field, field_validator

from ai.gemini import GeminiClient, GeminiAPIError
from ai.conversation import Message

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BeneficiaryProfile(BaseModel):
    """
    Standardized beneficiary profile extracted from conversation.
    
    All fields are optional (can be None/empty) if information was not provided
    in the conversation. The extractor does NOT invent information.
    """
    education: str | None = Field(
        default=None,
        description="Education level (e.g., '8th Pass', '10th Pass', '12th Pass', 'ITI', 'Diploma')"
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of skills mentioned by beneficiary. Empty if none mentioned."
    )
    interests: list[str] = Field(
        default_factory=list,
        description="List of interests/sectors (e.g., 'Agriculture', 'Healthcare'). Empty if none mentioned."
    )
    district: str | None = Field(
        default=None,
        description="District/location mentioned by beneficiary"
    )
    employment_preference: str | None = Field(
        default=None,
        description="Employment preference (e.g., 'Self-Employment', 'Wage-Employment', 'Any')"
    )
    mobility: str | None = Field(
        default=None,
        description="Mobility preference (e.g., 'Local', 'District Level', 'State Wide')"
    )
    
    @field_validator("skills", "interests", mode="before")
    @classmethod
    def ensure_list(cls, v):
        """Ensure skills and interests are lists, never None."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []


class ProfileExtractor:
    """
    Extracts structured beneficiary profile from conversation history.
    
    Takes conversation Message objects from ConversationManager and extracts
    relevant profile information using Gemini's structured output capability.
    
    Handles multilingual input (English, Hindi, Marathi) without unnecessary
    translation. Gracefully handles missing information.
    """
    
    # Prompt template for profile extraction
    # Instructs Gemini to extract profile WITHOUT inventing information
    EXTRACTION_PROMPT_TEMPLATE = """You are a profile extraction specialist for Kaushal Marg, a skills and livelihood discovery platform.

Your task: Extract beneficiary profile information from the conversation history below.

IMPORTANT RULES:
1. Extract ONLY information that was explicitly mentioned by the beneficiary
2. Do NOT invent or assume any information
3. If information was not mentioned, leave the field as null (None)
4. Empty lists (not null) should be used only if the field is "skills" or "interests" and nothing was mentioned
5. The conversation may be in English, Hindi, or Marathi - extract the underlying information without unnecessary translation
6. Focus on USER messages (the beneficiary's statements), not assistant responses
7. For location (district): extract only if explicitly mentioned
8. For education: extract only if explicitly mentioned
9. For skills: list each distinct skill mentioned (in the conversation's language or standardized form)
10. For interests/sectors: list sectors/interests mentioned
11. For employment preference: extract only if explicitly stated (Self-Employment, Wage-Employment, Any, etc.)
12. For mobility: extract only if explicitly mentioned (Local, District Level, State Wide, etc.)

CONVERSATION HISTORY:
{conversation_text}

Extract the beneficiary's profile. Return ONLY valid JSON matching the schema. Do not include explanations."""
    
    def __init__(self, api_key: str | None = None):
        """
        Initialize the ProfileExtractor.
        
        Args:
            api_key: Gemini API key (optional, reads from env if not provided)
        
        Raises:
            ValueError: If GeminiClient initialization fails
        """
        try:
            self._gemini_client = GeminiClient(api_key=api_key, max_output_tokens=512)
            logger.debug("ProfileExtractor initialized successfully")
        except Exception as e:
            raise ValueError(f"Failed to initialize ProfileExtractor: {str(e)}") from e
    
    def extract_profile(self, messages: list[Message]) -> dict:
        """
        Extract beneficiary profile from conversation message history.
        
        Args:
            messages: List of Message objects from ConversationManager.
                     Must be a list with Message instances.
        
        Returns:
            Dictionary representation of BeneficiaryProfile with keys:
            - education (str | None)
            - skills (list[str])
            - interests (list[str])
            - district (str | None)
            - employment_preference (str | None)
            - mobility (str | None)
        
        Raises:
            ValueError: If messages parameter is invalid (not a list, contains non-Message items)
            GeminiAPIError: If Gemini API call fails (propagated explicitly)
        
        Note:
            If messages is empty, returns empty profile without making API call.
        """
        # Validate input
        if not isinstance(messages, list):
            raise ValueError(f"messages must be a list, got {type(messages).__name__}")
        
        if messages and not all(isinstance(msg, Message) for msg in messages):
            invalid_types = [type(msg).__name__ for msg in messages if not isinstance(msg, Message)]
            raise ValueError(f"All messages must be Message instances, found: {set(invalid_types)}")
        
        # Handle empty history
        if not messages:
            empty_profile = BeneficiaryProfile()
            logger.debug("Empty message history - returning empty profile")
            return empty_profile.model_dump()
        
        try:
            # Build conversation text from messages
            # Focus on user messages, but include context from assistant responses
            conversation_text = self._build_conversation_text(messages)
            
            # Build extraction prompt
            prompt = self.EXTRACTION_PROMPT_TEMPLATE.format(conversation_text=conversation_text)
            
            # Call Gemini with structured output
            profile = self._gemini_client.generate_structured(
                prompt=prompt,
                schema=BeneficiaryProfile,
            )
            
            # Convert to dictionary
            result = profile.model_dump()
            
            logger.debug(
                f"Profile extracted: education={result.get('education')}, "
                f"skills_count={len(result.get('skills', []))}, "
                f"interests_count={len(result.get('interests', []))}"
            )
            
            return result
        
        except ValueError:
            # Re-raise ValueError (invalid input to Gemini)
            raise
        except GeminiAPIError as e:
            # Propagate API errors explicitly
            logger.error(f"Profile extraction failed: {str(e)}")
            raise
    
    def _build_conversation_text(self, messages: list[Message]) -> str:
        """
        Build conversation text for profile extraction prompt.
        
        Formats message history with role labels, prioritizing user messages
        while maintaining context from assistant responses.
        
        Args:
            messages: List of Message objects
        
        Returns:
            Formatted conversation text with role labels
        """
        text_parts = []
        for msg in messages:
            role_label = "BENEFICIARY" if msg.role == "user" else "ASSISTANT"
            text_parts.append(f"{role_label}: {msg.content}")
        
        return "\n".join(text_parts)
