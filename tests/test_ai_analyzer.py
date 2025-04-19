import pytest
import json
from unittest.mock import Mock, MagicMock, patch
# Import new SDK parts
from google.genai import types, errors
from pydantic import ValidationError

# Import the class and Pydantic model to test
from src.ai_analyzer import AIAnalyzer, LocationResponse

# Define the path to the class/methods we need to mock
# We now mock the Client class and its instance methods
CLIENT_MOCK_PATH = "src.ai_analyzer.genai.Client"
OS_GETENV_MOCK_PATH = "src.ai_analyzer.os.getenv"
LOAD_DOTENV_MOCK_PATH = "src.ai_analyzer.load_dotenv"
# Path for mocking the Pydantic validation method if needed
PYDANTIC_VALIDATE_JSON_MOCK_PATH = "src.ai_analyzer.LocationResponse.model_validate_json"


# --- Test Fixtures ---
@pytest.fixture
def mock_genai_client(mocker):
    """Fixture to mock the genai.Client class and its relevant methods."""
    # Mock the Client class itself
    mock_client_class = mocker.patch(CLIENT_MOCK_PATH, autospec=True)
    # Mock the instance that Client() returns
    mock_client_instance = mock_client_class.return_value
    # Mock the nested 'models.generate_content' method on the instance
    # Use MagicMock for attribute chaining (models.generate_content)
    mock_client_instance.models = MagicMock()
    mock_client_instance.models.generate_content = MagicMock()
    return mock_client_instance # Return the mocked client instance

@pytest.fixture
def mock_environment(mocker):
    """Fixture to mock environment functions (getenv, load_dotenv)."""
    # configure is no longer used
    mocker.patch(OS_GETENV_MOCK_PATH, return_value="DUMMY_API_KEY") # Provide a dummy key
    mocker.patch(LOAD_DOTENV_MOCK_PATH) # Mock load_dotenv to do nothing

# --- Test Cases ---

def test_analyze_caption_success_locations_found(mock_environment, mock_genai_client):
    """Tests successful analysis with locations found via Pydantic validation."""
    caption = "Amazing view from the Eiffel Tower!"
    expected_locations = ["Eiffel Tower"]
    # Expected result after model_dump()
    expected_dict_result = {"location_found": True, "locations": expected_locations}
    raw_json_text = json.dumps(expected_dict_result)

    # Create a mock response object with only the .text attribute
    mock_response = Mock()
    mock_response.text = raw_json_text
    # Configure the mock client's generate_content method
    mock_genai_client.models.generate_content.return_value = mock_response

    # Instantiate the class (mocks are active via fixtures)
    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_dict_result
    mock_genai_client.models.generate_content.assert_called_once()
    # Check arguments passed to generate_content
    call_args, call_kwargs = mock_genai_client.models.generate_content.call_args
    assert call_kwargs['model'] == analyzer.model_name
    assert caption in call_kwargs['contents']
    assert isinstance(call_kwargs['config'], types.GenerateContentConfig)
    assert call_kwargs['config'].response_mime_type == "application/json"
    assert call_kwargs['config'].response_schema == LocationResponse

def test_analyze_caption_success_no_locations_found(mock_environment, mock_genai_client):
    """Tests successful analysis with no locations found via Pydantic validation."""
    caption = "Just a random thought."
    expected_dict_result = {"location_found": False, "locations": None}
    raw_json_text = json.dumps(expected_dict_result)

    mock_response = Mock()
    mock_response.text = raw_json_text
    mock_genai_client.models.generate_content.return_value = mock_response

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_dict_result
    mock_genai_client.models.generate_content.assert_called_once()

# The concept of a separate "fallback" path is less distinct now,
# as Pydantic validation is the primary path. We test validation errors instead.

def test_analyze_caption_pydantic_validation_error_fallback_success(mocker, mock_environment, mock_genai_client):
    """Tests fallback JSON parsing when Pydantic validation fails but JSON is valid."""
    caption = "Caption causing validation error but valid JSON."
    # This JSON is valid but doesn't match LocationResponse schema (missing location_found)
    mismatched_json_dict = {"locations": ["Place"]}
    raw_json_text = json.dumps(mismatched_json_dict)
    validation_error_message = "Field required [type=missing, input_value={'locations': ['Place']}, input_type=dict]"

    # Mock Pydantic validation to raise an error
    mock_validate = mocker.patch(PYDANTIC_VALIDATE_JSON_MOCK_PATH)
    mock_validate.side_effect = ValidationError.from_exception_data(
        title='LocationResponse', line_errors=[{'input': mismatched_json_dict, 'loc': ('location_found',), 'type': 'missing'}]
    )

    mock_response = Mock()
    mock_response.text = raw_json_text
    mock_genai_client.models.generate_content.return_value = mock_response

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    # Expect the fallback data, plus the added error key
    expected_result_with_error = mismatched_json_dict.copy()
    expected_result_with_error["error"] = f"Pydantic validation failed: {mock_validate.side_effect}"

    assert result == expected_result_with_error
    mock_genai_client.models.generate_content.assert_called_once()
    mock_validate.assert_called_once_with(raw_json_text) # Ensure validation was attempted

def test_analyze_caption_empty_input(mock_environment, mock_genai_client):
    """Tests handling of an empty input caption."""
    caption = ""
    expected_result = {"location_found": False, "locations": None, "error": "Empty caption provided"}

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_result
    mock_genai_client.models.generate_content.assert_not_called() # API should not be called

def test_analyze_caption_api_error(mock_environment, mock_genai_client):
    """Tests handling of a Gemini API call error using the new SDK's error type."""
    caption = "This caption will cause an error."
    error_message = "API rate limit exceeded"
    dummy_response_json = {"error": {"message": error_message, "status": "PERMISSION_DENIED"}}
    # Simulate an API error: pass message positionally, response_json as keyword
    mock_genai_client.models.generate_content.side_effect = errors.APIError(
        error_message, # Positional argument (assuming it's the message)
        response_json=dummy_response_json # Keyword argument
    )

    # The str(e) in the main code should include the message
    expected_error_fragment = f"Gemini API call failed: {error_message}"

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    mock_genai_client.models.generate_content.assert_called_once()

def test_analyze_caption_json_decode_error(mocker, mock_environment, mock_genai_client):
    """Tests handling of invalid JSON response from the API."""
    caption = "Caption leading to bad JSON."
    invalid_json_text = '{"location_found": true, "locations": ["Place"]' # Missing closing brace

    # Mock Pydantic validation to raise JSONDecodeError when called
    # (Simulates Pydantic trying to parse invalid JSON)
    mock_validate = mocker.patch(PYDANTIC_VALIDATE_JSON_MOCK_PATH)
    # The actual error comes from json.loads inside model_validate_json
    mock_validate.side_effect = json.JSONDecodeError("Expecting property name enclosed in double quotes", invalid_json_text, 0)

    mock_response = Mock()
    mock_response.text = invalid_json_text
    mock_genai_client.models.generate_content.return_value = mock_response

    # The error should be caught by the first `except json.JSONDecodeError` block
    expected_error_fragment = "Failed to decode JSON response from AI" # Updated expected message

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == invalid_json_text
    mock_genai_client.models.generate_content.assert_called_once()
    mock_validate.assert_called_once_with(invalid_json_text) # Ensure validation was attempted

# Removed tests specifically for fallback structure/format errors, as these
# are now handled by the Pydantic validation error path.

# Removed test_analyze_caption_processing_error_after_api_call as the .parsed
# attribute is gone, simplifying the flow.

def test_analyze_caption_unexpected_error_during_processing(mocker, mock_environment, mock_genai_client):
    """Tests handling of an unexpected error during response processing."""
    caption = "Caption causing unexpected processing error."
    valid_json_dict = {"location_found": True, "locations": ["Place"]}
    raw_json_text = json.dumps(valid_json_dict)
    error_message = "Something broke!"

    # Mock Pydantic validation to raise an unexpected error
    mock_validate = mocker.patch(PYDANTIC_VALIDATE_JSON_MOCK_PATH)
    mock_validate.side_effect = RuntimeError(error_message)

    mock_response = Mock()
    mock_response.text = raw_json_text
    mock_genai_client.models.generate_content.return_value = mock_response

    # Expect the error from the `except Exception as e:` block within the response processing try block
    expected_error_fragment = f"Unexpected error processing response: {error_message}" # Updated expected message

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == raw_json_text
    mock_genai_client.models.generate_content.assert_called_once()
    mock_validate.assert_called_once_with(raw_json_text)


# --- Tests for __init__ (Simplified as client/model are not created here anymore) ---

# Keep tests for API key loading logic

def test_analyzer_init_with_api_key(mocker):
    """Tests initialization with an explicitly provided API key."""
    # No need to mock genai Client or configure anymore for init
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH)
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH)

    test_key = "explicit_key_123"
    test_model = "test-model-explicit"
    analyzer = AIAnalyzer(api_key=test_key, model_name=test_model)

    assert analyzer.api_key == test_key
    assert analyzer.model_name == test_model
    mock_getenv.assert_not_called() # Should not be called if key is provided
    mock_loadenv.assert_not_called()

def test_analyzer_init_from_env_variable(mocker):
    """Tests initialization using an environment variable for the API key."""
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH, return_value="env_key_456")
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH)

    analyzer = AIAnalyzer() # No key provided

    assert analyzer.api_key == "env_key_456"
    assert analyzer.model_name == AIAnalyzer.DEFAULT_MODEL_NAME # Check default model
    mock_getenv.assert_called_once_with("GEMINI_API_KEY")
    mock_loadenv.assert_not_called() # Should not be called if env var is found

def test_analyzer_init_from_dotenv_file(mocker):
    """Tests initialization loading the API key from a .env file."""
    # Simulate getenv failing first, then succeeding after load_dotenv
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH, side_effect=[None, "dotenv_key_789"])
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH) # Mock load_dotenv itself

    analyzer = AIAnalyzer()

    assert analyzer.api_key == "dotenv_key_789"
    assert analyzer.model_name == AIAnalyzer.DEFAULT_MODEL_NAME
    assert mock_getenv.call_count == 2 # Called before and after load_dotenv
    mock_loadenv.assert_called_once() # load_dotenv should be called

def test_analyzer_init_no_api_key_found(mocker):
    """Tests that ValueError is raised if no API key can be found."""
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH, return_value=None) # Simulate getenv always failing
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH)

    with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
        AIAnalyzer()

    assert mock_getenv.call_count == 2
    mock_loadenv.assert_called_once()
