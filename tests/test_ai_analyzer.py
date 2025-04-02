import pytest
import json
from unittest.mock import Mock, MagicMock # Use MagicMock for attribute access like .parsed
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from pydantic import ValidationError

# Import the class and Pydantic model to test
from src.ai_analyzer import AIAnalyzer, LocationResponse

# Define the path to the class/methods we need to mock
GENERATIVE_MODEL_MOCK_PATH = "src.ai_analyzer.genai.GenerativeModel"
CONFIGURE_MOCK_PATH = "src.ai_analyzer.genai.configure" # Mock configure to avoid real API key needs
OS_GETENV_MOCK_PATH = "src.ai_analyzer.os.getenv"
LOAD_DOTENV_MOCK_PATH = "src.ai_analyzer.load_dotenv"


# --- Test Fixtures ---
@pytest.fixture
def mock_generative_model(mocker):
    """Fixture to mock the genai.GenerativeModel class."""
    mock_model_instance = MagicMock() # Mock the instance that GenerativeModel() returns
    mock_model_class = mocker.patch(GENERATIVE_MODEL_MOCK_PATH, return_value=mock_model_instance)
    return mock_model_instance # Return the instance for configuring generate_content

@pytest.fixture
def mock_environment(mocker):
    """Fixture to mock environment functions (getenv, load_dotenv, configure)."""
    mocker.patch(CONFIGURE_MOCK_PATH) # Mock configure to do nothing
    mocker.patch(OS_GETENV_MOCK_PATH, return_value="DUMMY_API_KEY") # Provide a dummy key
    mocker.patch(LOAD_DOTENV_MOCK_PATH) # Mock load_dotenv to do nothing

# --- Test Cases ---

def test_analyze_caption_success_locations_found_parsed(mock_environment, mock_generative_model):
    """Tests successful analysis with locations found via response.parsed."""
    caption = "Amazing view from the Eiffel Tower!"
    expected_locations = ["Eiffel Tower"]
    expected_result = {"location_found": True, "locations": expected_locations}

    # Create a mock response object with a .parsed attribute
    mock_response = MagicMock()
    mock_response.parsed = LocationResponse(location_found=True, locations=expected_locations)
    # We don't strictly need .text if .parsed works, but good practice to have it
    mock_response.text = json.dumps(expected_result)

    # Configure the mock instance's generate_content method
    mock_generative_model.generate_content.return_value = mock_response

    # Instantiate the class (mocks are active via fixtures)
    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generative_model.generate_content.assert_called_once()
    # Optional: Assert prompt contains caption
    assert caption in mock_generative_model.generate_content.call_args[0][0]

def test_analyze_caption_success_no_locations_found_parsed(mock_environment, mock_generative_model):
    """Tests successful analysis with no locations found via response.parsed."""
    caption = "Just a random thought."
    expected_result = {"location_found": False, "locations": None}

    mock_response = MagicMock()
    mock_response.parsed = LocationResponse(location_found=False, locations=None)
    mock_response.text = json.dumps(expected_result)

    mock_generative_model.generate_content.return_value = mock_response

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_success_locations_found_fallback(mock_environment, mock_generative_model):
    """Tests successful analysis with locations found via fallback JSON parsing."""
    caption = "Dinner at Joe's Pizza."
    expected_locations = ["Joe's Pizza"]
    expected_result = {"location_found": True, "locations": expected_locations}
    raw_json_text = json.dumps(expected_result)

    # Simulate response.parsed being absent or None
    mock_response = MagicMock()
    mock_response.parsed = None # Or del mock_response.parsed
    mock_response.text = raw_json_text

    mock_generative_model.generate_content.return_value = mock_response

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_success_no_locations_found_fallback(mock_environment, mock_generative_model):
    """Tests successful analysis with no locations found via fallback JSON parsing."""
    caption = "Another day at the office."
    expected_result = {"location_found": False, "locations": None}
    raw_json_text = json.dumps(expected_result)

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = raw_json_text

    mock_generative_model.generate_content.return_value = mock_response

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_empty_input(mock_environment, mock_generative_model):
    """Tests handling of an empty input caption."""
    caption = ""
    expected_result = {"location_found": False, "locations": None, "error": "Empty caption provided"}

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generative_model.generate_content.assert_not_called() # API should not be called

def test_analyze_caption_api_error(mock_environment, mock_generative_model):
    """Tests handling of a Gemini API call error."""
    caption = "This caption will cause an error."
    error_message = "API rate limit exceeded"
    # Simulate an API error
    mock_generative_model.generate_content.side_effect = Exception(error_message)

    expected_error_fragment = f"Gemini API call failed: {error_message}"

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_fallback_json_decode_error(mock_environment, mock_generative_model):
    """Tests handling of invalid JSON in the fallback parsing path."""
    caption = "Caption leading to bad JSON."
    invalid_json_text = '{"location_found": true, "locations": ["Place"]' # Missing closing brace

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = invalid_json_text

    mock_generative_model.generate_content.return_value = mock_response

    expected_error_fragment = "Failed to parse fallback JSON response from AI"

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == invalid_json_text
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_fallback_invalid_structure(mock_environment, mock_generative_model):
    """Tests handling of valid JSON with incorrect structure in fallback."""
    caption = "Caption leading to wrong structure."
    wrong_structure_json = json.dumps({"name": "Eiffel Tower", "city": "Paris"})

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = wrong_structure_json

    mock_generative_model.generate_content.return_value = mock_response

    expected_error_fragment = "Invalid structure in fallback JSON"

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == wrong_structure_json
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_fallback_invalid_locations_format(mock_environment, mock_generative_model):
    """Tests handling of fallback JSON with invalid 'locations' field type."""
    caption = "Caption leading to bad locations type."
    # 'locations' should be a list or None, not a string
    bad_locations_json = json.dumps({"location_found": True, "locations": "Eiffel Tower"})

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = bad_locations_json

    mock_generative_model.generate_content.return_value = mock_response

    expected_error_fragment = "Invalid 'locations' format in fallback JSON"

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == bad_locations_json
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_processing_error_after_api_call(mock_environment, mock_generative_model):
    """Tests handling of an unexpected error during response processing (after API call)."""
    caption = "Caption causing processing error."
    # Ensure comma is present in expected_result
    expected_result = {"location_found": True, "locations": ["Some Place"]} # Added comma here
    raw_json_text = json.dumps(expected_result)

    # Simulate response.parsed exists, but calling model_dump on it causes an error
    mock_response = MagicMock()
    # Create a mock for the parsed object
    mock_parsed_object = Mock()
    # Make its model_dump method raise an error
    mock_parsed_object.model_dump.side_effect = AttributeError("Simulated model_dump error")
    # Assign this mock to the parsed attribute
    mock_response.parsed = mock_parsed_object
    mock_response.text = raw_json_text # Provide valid fallback text

    mock_generative_model.generate_content.return_value = mock_response

    analyzer = AIAnalyzer()
    # Even though .parsed fails, the fallback should succeed here
    result = analyzer.analyze_caption_for_location(caption)

    # Check that fallback parsing worked despite the initial error
    assert result == expected_result
    mock_generative_model.generate_content.assert_called_once()

def test_analyze_caption_processing_error_and_fallback_fails(mock_environment, mock_generative_model):
    """Tests handling of processing error AND fallback JSON error."""
    caption = "Caption causing double error."
    invalid_json_text = '{"bad": json'

    # Simulate response.parsed being None and fallback text being invalid JSON
    mock_response = MagicMock()
    mock_response.parsed = None # Set parsed to None
    mock_response.text = invalid_json_text # Provide invalid fallback text

    mock_generative_model.generate_content.return_value = mock_response

    # Expect the error from the json.JSONDecodeError block in the source code
    expected_error_fragment = "Failed to parse fallback JSON response from AI"

    analyzer = AIAnalyzer()
    result = analyzer.analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == invalid_json_text
    mock_generative_model.generate_content.assert_called_once()

# --- Tests for __init__ ---

def test_analyzer_init_with_api_key(mocker):
    """Tests initialization with an explicitly provided API key."""
    mock_configure = mocker.patch(CONFIGURE_MOCK_PATH)
    mock_model_class = mocker.patch(GENERATIVE_MODEL_MOCK_PATH)
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH)
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH)

    test_key = "explicit_key_123"
    test_model = "test-model-explicit"
    analyzer = AIAnalyzer(api_key=test_key, model_name=test_model)

    assert analyzer.api_key == test_key
    assert analyzer.model_name == test_model
    mock_configure.assert_called_once_with(api_key=test_key)
    mock_model_class.assert_called_once_with(test_model)
    mock_getenv.assert_not_called() # Should not be called if key is provided
    mock_loadenv.assert_not_called()

def test_analyzer_init_from_env_variable(mocker):
    """Tests initialization using an environment variable for the API key."""
    mock_configure = mocker.patch(CONFIGURE_MOCK_PATH)
    mock_model_class = mocker.patch(GENERATIVE_MODEL_MOCK_PATH)
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH, return_value="env_key_456")
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH)

    analyzer = AIAnalyzer() # No key provided

    assert analyzer.api_key == "env_key_456"
    assert analyzer.model_name == AIAnalyzer.DEFAULT_MODEL_NAME # Check default model
    mock_configure.assert_called_once_with(api_key="env_key_456")
    mock_model_class.assert_called_once_with(AIAnalyzer.DEFAULT_MODEL_NAME)
    mock_getenv.assert_called_once_with("GEMINI_API_KEY")
    mock_loadenv.assert_not_called() # Should not be called if env var is found

def test_analyzer_init_from_dotenv_file(mocker):
    """Tests initialization loading the API key from a .env file."""
    mock_configure = mocker.patch(CONFIGURE_MOCK_PATH)
    mock_model_class = mocker.patch(GENERATIVE_MODEL_MOCK_PATH)
    # Simulate getenv failing first, then succeeding after load_dotenv
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH, side_effect=[None, "dotenv_key_789"])
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH) # Mock load_dotenv itself

    analyzer = AIAnalyzer()

    assert analyzer.api_key == "dotenv_key_789"
    mock_configure.assert_called_once_with(api_key="dotenv_key_789")
    mock_model_class.assert_called_once_with(AIAnalyzer.DEFAULT_MODEL_NAME)
    assert mock_getenv.call_count == 2 # Called before and after load_dotenv
    mock_loadenv.assert_called_once() # load_dotenv should be called

def test_analyzer_init_no_api_key_found(mocker):
    """Tests that ValueError is raised if no API key can be found."""
    mock_configure = mocker.patch(CONFIGURE_MOCK_PATH)
    mock_model_class = mocker.patch(GENERATIVE_MODEL_MOCK_PATH)
    mock_getenv = mocker.patch(OS_GETENV_MOCK_PATH, return_value=None) # Simulate getenv always failing
    mock_loadenv = mocker.patch(LOAD_DOTENV_MOCK_PATH)

    with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
        AIAnalyzer()

    assert mock_getenv.call_count == 2
    mock_loadenv.assert_called_once()
    mock_configure.assert_not_called() # Configure shouldn't be called if init fails
    mock_model_class.assert_not_called()
