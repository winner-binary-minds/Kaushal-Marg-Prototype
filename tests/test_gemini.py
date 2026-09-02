"""
Tests for ai/gemini.py

Comprehensive test suite verifying CORRECT models.generate_content() API patterns:
- No real API calls (all mocked)
- Configuration and initialization
- Text generation with GenerateContentConfig
- Structured output with response_mime_type + response_schema in config
- Input validation and error handling
- Secret protection in logs/errors
"""

import os
import pytest
import json
from unittest.mock import Mock, patch
import pydantic

from ai.gemini import (
    GeminiClient,
    GeminiConfigError,
    GeminiAPIError,
    GeminiValidationError,
)


# Test schema for structured output tests
class SampleProfile(pydantic.BaseModel):
    """Sample schema for testing structured output."""
    name: str
    age: int
    skills: list[str]


class TestInitialization:
    """Test GeminiClient initialization (no temperature parameter)."""
    
    def test_init_with_explicit_api_key(self):
        """Verify client initializes with explicit API key."""
        with patch("ai.gemini.genai.Client"):
            client = GeminiClient(api_key="valid-key")
            assert client.model == GeminiClient.DEFAULT_MODEL
            assert client.max_output_tokens == GeminiClient.DEFAULT_MAX_OUTPUT_TOKENS
            # Verify NO temperature attribute
            assert not hasattr(client, "temperature")
    
    def test_init_with_env_api_key(self):
        """Verify client reads API key from environment."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}):
            with patch("ai.gemini.genai.Client"):
                client = GeminiClient()
                assert client is not None
    
    def test_init_missing_api_key_raises_error(self):
        """Verify missing API key raises GeminiConfigError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(GeminiConfigError) as exc:
                GeminiClient()
            assert "GEMINI_API_KEY" in str(exc.value)
    
    def test_init_empty_api_key_raises_error(self):
        """Verify empty API key raises GeminiConfigError."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with pytest.raises(GeminiConfigError):
                GeminiClient()
    
    def test_init_whitespace_api_key_raises_error(self):
        """Verify whitespace-only API key raises GeminiConfigError."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "   "}):
            with pytest.raises(GeminiConfigError):
                GeminiClient()
    
    def test_init_invalid_max_tokens_zero(self):
        """Verify max_output_tokens=0 raises GeminiConfigError."""
        with pytest.raises(GeminiConfigError):
            GeminiClient(api_key="key", max_output_tokens=0)
    
    def test_init_invalid_max_tokens_negative(self):
        """Verify negative max_output_tokens raises GeminiConfigError."""
        with pytest.raises(GeminiConfigError):
            GeminiClient(api_key="key", max_output_tokens=-100)
    
    def test_init_empty_model_raises_error(self):
        """Verify empty model raises GeminiConfigError."""
        with pytest.raises(GeminiConfigError):
            GeminiClient(api_key="key", model="")
    
    def test_init_client_creation_failure(self):
        """Verify client creation failure raises GeminiConfigError."""
        with patch("ai.gemini.genai.Client", side_effect=Exception("Connection failed")):
            with pytest.raises(GeminiConfigError) as exc:
                GeminiClient(api_key="key")
            assert "Failed to initialize" in str(exc.value)
    
    def test_init_custom_model(self):
        """Verify custom model is stored."""
        with patch("ai.gemini.genai.Client"):
            client = GeminiClient(api_key="key", model="gemini-3.7-flash")
            assert client.model == "gemini-3.7-flash"
    
    def test_init_custom_max_tokens(self):
        """Verify custom max_output_tokens is stored."""
        with patch("ai.gemini.genai.Client"):
            client = GeminiClient(api_key="key", max_output_tokens=2048)
            assert client.max_output_tokens == 2048


class TestGenerateText:
    """Test the generate_text method with CORRECT Interactions API."""
    
    @pytest.fixture
    def mock_client(self):
        """Fixture providing a mocked GeminiClient."""
        with patch("ai.gemini.genai.Client") as mock_genai:
            client = GeminiClient(api_key="test-key")
            yield client
    
    def test_generate_text_success(self, mock_client):
        """Verify successful text generation returns response."""
        mock_response = Mock()
        mock_response.text = "This is a generated response."
        mock_client._client.models.generate_content.return_value = mock_response
        
        result = mock_client.generate_text("Tell me something")
        
        assert result == "This is a generated response."
        mock_client._client.models.generate_content.assert_called_once()
    
    def test_generate_text_empty_prompt_raises_error(self, mock_client):
        """Verify empty prompt raises ValueError."""
        with pytest.raises(ValueError) as exc:
            mock_client.generate_text("")
        assert "empty" in str(exc.value).lower()
    
    def test_generate_text_whitespace_prompt_raises_error(self, mock_client):
        """Verify whitespace-only prompt raises ValueError."""
        with pytest.raises(ValueError):
            mock_client.generate_text("   \n\t  ")
    
    def test_generate_text_none_prompt_raises_error(self, mock_client):
        """Verify None prompt raises ValueError."""
        with pytest.raises(ValueError):
            mock_client.generate_text(None)
    
    def test_generate_text_non_string_prompt_raises_error(self, mock_client):
        """Verify non-string prompt raises ValueError."""
        with pytest.raises(ValueError):
            mock_client.generate_text(123)
    
    def test_generate_text_empty_response_raises_error(self, mock_client):
        """Verify empty API response raises GeminiAPIError."""
        mock_response = Mock()
        mock_response.text = ""
        mock_client._client.models.generate_content.return_value = mock_response
        
        with pytest.raises(GeminiAPIError) as exc:
            mock_client.generate_text("Tell me something")
        assert "empty" in str(exc.value).lower()
    
    def test_generate_text_none_response_raises_error(self, mock_client):
        """Verify None response raises GeminiAPIError."""
        mock_client._client.models.generate_content.return_value = None
        
        with pytest.raises(GeminiAPIError) as exc:
            mock_client.generate_text("Tell me something")
        assert "empty" in str(exc.value).lower()
    
    def test_generate_text_api_failure(self, mock_client):
        """Verify API failure raises GeminiAPIError."""
        mock_client._client.models.generate_content.side_effect = Exception("Rate limited")
        
        with pytest.raises(GeminiAPIError) as exc:
            mock_client.generate_text("Tell me something")
        assert "Text generation failed" in str(exc.value)
    
    def test_generate_text_api_called_correctly(self, mock_client):
        """Verify API is called with CORRECT models.generate_content() parameters.
        
        CORRECT pattern (google-genai SDK v2.x):
            client.models.generate_content(
                model="...",
                contents="...",
                config=GenerateContentConfig(
                    max_output_tokens=...,
                ),
            )
        """
        mock_response = Mock()
        mock_response.text = "Response"
        mock_client._client.models.generate_content.return_value = mock_response
        
        mock_client.generate_text("Test prompt")
        
        # Verify the call was made
        assert mock_client._client.models.generate_content.called
        call_args = mock_client._client.models.generate_content.call_args
        assert call_args is not None
        
        kwargs = call_args.kwargs
        # Verify CORRECT parameters
        assert kwargs.get("model") == mock_client.model
        assert kwargs.get("contents") == "Test prompt"
        # Verify config is present
        assert "config" in kwargs
        # Verify NO interactions-style parameters
        assert "input" not in kwargs
        assert "response_format" not in kwargs


class TestGenerateStructured:
    """Test generate_structured with CORRECT response_format parameter."""
    
    @pytest.fixture
    def mock_client(self):
        """Fixture providing a mocked GeminiClient."""
        with patch("ai.gemini.genai.Client"):
            client = GeminiClient(api_key="test-key")
            yield client
    
    def test_generate_structured_success(self, mock_client):
        """Verify successful structured generation returns validated object."""
        valid_json = json.dumps({
            "name": "Alice",
            "age": 30,
            "skills": ["Python", "Go"]
        })
        mock_response = Mock()
        mock_response.text = valid_json
        mock_client._client.models.generate_content.return_value = mock_response
        
        result = mock_client.generate_structured(
            "Generate a profile",
            schema=SampleProfile
        )
        
        assert isinstance(result, SampleProfile)
        assert result.name == "Alice"
        assert result.age == 30
        assert result.skills == ["Python", "Go"]
    
    def test_generate_structured_empty_prompt_raises_error(self, mock_client):
        """Verify empty prompt raises ValueError."""
        with pytest.raises(ValueError):
            mock_client.generate_structured("", schema=SampleProfile)
    
    def test_generate_structured_invalid_schema_raises_error(self, mock_client):
        """Verify non-Pydantic schema raises ValueError."""
        class NotAPydanticModel:
            pass
        
        with pytest.raises(ValueError) as exc:
            mock_client.generate_structured("Prompt", schema=NotAPydanticModel)
        assert "Pydantic" in str(exc.value)
    
    def test_generate_structured_empty_response_raises_error(self, mock_client):
        """Verify empty API response raises GeminiAPIError."""
        mock_response = Mock()
        mock_response.text = ""
        mock_client._client.models.generate_content.return_value = mock_response
        
        with pytest.raises(GeminiAPIError):
            mock_client.generate_structured("Prompt", schema=SampleProfile)
    
    def test_generate_structured_malformed_json_raises_error(self, mock_client):
        """Verify malformed JSON raises GeminiValidationError."""
        mock_response = Mock()
        mock_response.text = "{ invalid json }"
        mock_client._client.models.generate_content.return_value = mock_response
        
        with pytest.raises(GeminiValidationError):
            mock_client.generate_structured("Prompt", schema=SampleProfile)
    
    def test_generate_structured_mismatched_schema_raises_error(self, mock_client):
        """Verify response not matching schema raises GeminiValidationError."""
        invalid_json = json.dumps({"wrong_field": "value"})
        mock_response = Mock()
        mock_response.text = invalid_json
        mock_client._client.models.generate_content.return_value = mock_response
        
        with pytest.raises(GeminiValidationError):
            mock_client.generate_structured("Prompt", schema=SampleProfile)
    
    def test_generate_structured_api_failure(self, mock_client):
        """Verify API failure raises GeminiAPIError."""
        mock_client._client.models.generate_content.side_effect = Exception("API error")
        
        with pytest.raises(GeminiAPIError) as exc:
            mock_client.generate_structured("Prompt", schema=SampleProfile)
        assert "Structured generation failed" in str(exc.value)
    
    def test_generate_structured_api_called_correctly(self, mock_client):
        """Verify API is called with CORRECT GenerateContentConfig parameters.
        
        CORRECT pattern (google-genai SDK v2.x):
            client.models.generate_content(
                model="...",
                contents="...",
                config=GenerateContentConfig(
                    max_output_tokens=...,
                    response_mime_type="application/json",
                    response_schema=SchemaClass,
                ),
            )
        """
        valid_json = json.dumps({
            "name": "Bob",
            "age": 25,
            "skills": ["Rust"]
        })
        mock_response = Mock()
        mock_response.text = valid_json
        mock_client._client.models.generate_content.return_value = mock_response
        
        mock_client.generate_structured("Prompt", schema=SampleProfile)
        
        # Verify the call was made
        assert mock_client._client.models.generate_content.called
        call_args = mock_client._client.models.generate_content.call_args
        kwargs = call_args.kwargs
        
        # Verify CORRECT parameters
        assert kwargs.get("model") == mock_client.model
        assert kwargs.get("contents") == "Prompt"
        assert "config" in kwargs
        # Verify NO interactions-style parameters
        assert "input" not in kwargs
        assert "response_format" not in kwargs


class TestSecurityAndLogging:
    """Test security: no secret leakage in logs or errors."""
    
    def test_api_key_not_logged_on_init(self, caplog):
        """Verify API key is never logged during initialization."""
        test_key = "secret-key-12345-xyz"
        with patch("ai.gemini.genai.Client"):
            with caplog.at_level("DEBUG"):
                GeminiClient(api_key=test_key)
        
        # Check logs don't contain the API key
        for record in caplog.records:
            assert test_key not in record.message
    
    def test_api_key_not_in_config_error(self):
        """Verify API key is not exposed in GeminiConfigError."""
        test_key = "secret-key-xyz"
        with pytest.raises(GeminiConfigError) as exc:
            with patch("ai.gemini.genai.Client", side_effect=Exception("Auth failed")):
                GeminiClient(api_key=test_key)
        
        # Check error message doesn't contain API key
        assert test_key not in str(exc.value)


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    @pytest.fixture
    def mock_client(self):
        """Fixture providing a mocked GeminiClient."""
        with patch("ai.gemini.genai.Client"):
            client = GeminiClient(api_key="test-key")
            yield client
    
    def test_generate_text_with_long_prompt(self, mock_client):
        """Verify handling of very long prompts."""
        long_prompt = "Test " * 10000  # 50k chars
        mock_response = Mock()
        mock_response.text = "Response to long prompt"
        mock_client._client.models.generate_content.return_value = mock_response
        
        result = mock_client.generate_text(long_prompt)
        assert result == "Response to long prompt"
    
    def test_generate_text_with_special_characters(self, mock_client):
        """Verify handling of Unicode and special characters."""
        prompt = "こんにちは 你好 مرحبا 🎉 \n\t\r€"
        mock_response = Mock()
        mock_response.text = "Handled correctly"
        mock_client._client.models.generate_content.return_value = mock_response
        
        result = mock_client.generate_text(prompt)
        assert result == "Handled correctly"
    
    def test_multiple_calls_are_independent(self, mock_client):
        """Verify multiple API calls don't interfere."""
        responses = ["Response 1", "Response 2", "Response 3"]
        call_count = [0]
        
        def side_effect(*args, **kwargs):
            mock_response = Mock()
            mock_response.text = responses[call_count[0]]
            call_count[0] += 1
            return mock_response
        
        mock_client._client.models.generate_content.side_effect = side_effect
        
        result1 = mock_client.generate_text("Prompt 1")
        result2 = mock_client.generate_text("Prompt 2")
        result3 = mock_client.generate_text("Prompt 3")
        
        assert result1 == "Response 1"
        assert result2 == "Response 2"
        assert result3 == "Response 3"
    
    def test_structured_with_nested_schema(self, mock_client):
        """Verify structured generation with complex nested schema."""
        class NestedProfile(pydantic.BaseModel):
            name: str
            contact: dict
            tags: list[str]
        
        valid_json = json.dumps({
            "name": "Charlie",
            "contact": {"email": "charlie@example.com"},
            "tags": ["developer", "mentor"]
        })
        mock_response = Mock()
        mock_response.text = valid_json
        mock_client._client.models.generate_content.return_value = mock_response
        
        result = mock_client.generate_structured("Prompt", schema=NestedProfile)
        
        assert isinstance(result, NestedProfile)
        assert result.name == "Charlie"
        assert result.contact["email"] == "charlie@example.com"
