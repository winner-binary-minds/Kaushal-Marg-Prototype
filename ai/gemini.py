"""
Gemini AI Client Wrapper

A secure, production-quality wrapper around the Google Gemini API.

Key responsibilities:
- Secure API key management (environment variable only)
- Client initialization with validation
- Text generation via models.generate_content()
- Structured/JSON generation with Pydantic schema validation
- Explicit error handling (no silent failures)
- Safe logging (no secrets or sensitive data)
"""

import os
import logging
from typing import Any, Type, TypeVar
from dotenv import load_dotenv

load_dotenv()

import pydantic
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Type variable for structured output schema
T = TypeVar("T", bound=pydantic.BaseModel)


# Custom Exceptions
class GeminiConfigError(Exception):
    """Raised when Gemini client is not properly configured."""
    pass


class GeminiAPIError(Exception):
    """Raised when Gemini API call fails."""
    pass


class GeminiValidationError(Exception):
    """Raised when structured output doesn't match schema."""
    pass


class GeminiQuotaError(GeminiAPIError):
    """Raised when API quota is exhausted (HTTP 429)."""
    def __init__(self, message: str, retry_delay: int = 40):
        super().__init__(message)
        self.retry_delay = retry_delay


# ---------------------------------------------------------------------------
# Centralized Model Configuration
# ---------------------------------------------------------------------------
from config import GEMINI_CHAT_MODEL

GEMINI_MODEL: str = GEMINI_CHAT_MODEL
DEFAULT_MODEL: str = GEMINI_MODEL


class GeminiClient:
    """
    Secure wrapper around the Google Gemini API via Interactions API.
    
    This client:
    - Reads API key from GEMINI_API_KEY environment variable
    - Uses Interactions API (current standard, not legacy generateContent)
    - Provides simple text generation
    - Provides structured output with Pydantic schema validation
    - Validates all inputs and outputs
    - Never logs secrets or sensitive data
    
    Attributes:
        model (str): The Gemini model to use
        max_output_tokens (int): Maximum tokens in response
    """
    
    # Current supported model for google-genai SDK v2.x
    DEFAULT_MODEL = GEMINI_MODEL
    DEFAULT_MAX_OUTPUT_TOKENS = 1024
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
                     Must not be empty.
            model: Model identifier (must be valid Gemini model).
            max_output_tokens: Maximum response tokens (must be positive).
        
        Raises:
            GeminiConfigError: If API key missing, invalid, or config invalid.
        """
        # Validate and get API key
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
        else:
            api_key = str(api_key).strip()
        
        if not api_key:
            raise GeminiConfigError(
                "GEMINI_API_KEY not set. Set environment variable "
                "GEMINI_API_KEY or pass api_key to GeminiClient()."
            )
        
        # Validate max_output_tokens
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise GeminiConfigError(
                f"max_output_tokens must be positive integer, got {max_output_tokens}"
            )
        
        # Validate model
        if not model or not isinstance(model, str):
            raise GeminiConfigError(f"model must be non-empty string, got {model}")
        
        # Store configuration
        self.model = model
        self.max_output_tokens = max_output_tokens
        
        # Initialize Gemini client
        try:
            self._client = genai.Client(api_key=api_key)
            logger.debug(f"Gemini client initialized: model={self.model}")
        except Exception as e:
            raise GeminiConfigError(
                f"Failed to initialize Gemini client: {str(e)}"
            ) from e
    
    def _call_generate_content(
        self,
        contents: Any,
        config: types.GenerateContentConfig,
    ) -> Any:
        """Invokes generate_content."""
        try:
            resp = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return resp
        except Exception as e:
            err_str = str(e).lower()
            
            # Check for 429 Resource Exhausted / Quota Limits
            if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                # Try to parse retry delay from the error message if it says e.g. "retry in 40s"
                import re
                delay_match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str)
                delay = int(float(delay_match.group(1))) if delay_match else 40
                raise GeminiQuotaError(f"Gemini API Quota Exceeded. {e}", retry_delay=delay)

            raise e

    def generate_text(self, prompt: str) -> str:
        """
        Generate text from a prompt using Gemini.
        
        Args:
            prompt: Input prompt (must be non-empty string).
        
        Returns:
            Generated text response.
        
        Raises:
            ValueError: If prompt is empty or invalid.
            GeminiAPIError: If API call fails or returns empty response.
        """
        # Validate prompt
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                "prompt must be a non-empty string"
            )
        
        prompt = prompt.strip()
        
        try:
            # Call Gemini API via models.generate_content()
            response = self._call_generate_content(
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=self.max_output_tokens,
                ),
            )
            
            # Validate response
            if not response or not response.text:
                raise GeminiAPIError(
                    "Gemini returned empty response. "
                    "Check prompt or API service status."
                )
            
            return response.text
        
        except ValueError:
            raise
        except GeminiAPIError:
            raise
        except Exception as e:
            raise GeminiAPIError(
                f"Text generation failed: {str(e)}"
            ) from e
    
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
    ) -> T:
        """
        Generate structured output matching a Pydantic schema.
        
        Uses Gemini's structured output capability to ensure response
        matches the provided Pydantic model. Validates the response
        and returns an instance of the schema class.
        
        Args:
            prompt: Input prompt (must be non-empty string).
                   Should describe what structure is expected.
            schema: Pydantic BaseModel class defining output structure.
        
        Returns:
            Instance of schema class with validated data.
        
        Raises:
            ValueError: If prompt is empty or schema invalid.
            GeminiAPIError: If API call fails.
            GeminiValidationError: If response doesn't match schema.
        """
        # Validate inputs
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be non-empty string")
        
        if not isinstance(schema, type) or not issubclass(schema, pydantic.BaseModel):
            raise ValueError("schema must be a Pydantic BaseModel subclass")
        
        prompt = prompt.strip()
        
        try:
            # Call Gemini with structured output via response_mime_type + response_schema
            response = self._call_generate_content(
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=self.max_output_tokens,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            
            # Validate response
            if not response or not response.text:
                raise GeminiAPIError(
                    "Gemini returned empty structured response"
                )
            
            # Parse and validate against schema
            try:
                result = schema.model_validate_json(response.text)
                return result
            except pydantic.ValidationError as e:
                raise GeminiValidationError(
                    f"Response doesn't match schema: {str(e)}"
                ) from e
        
        except ValueError:
            raise
        except GeminiAPIError:
            raise
        except GeminiValidationError:
            raise
        except Exception as e:
            raise GeminiAPIError(
                f"Structured generation failed: {str(e)}"
            ) from e
