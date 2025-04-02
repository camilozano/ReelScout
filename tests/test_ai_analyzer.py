import pytest
import json
from unittest.mock import Mock, MagicMock # Use MagicMock for attribute access like .parsed
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions # For simulating API errors
from pydantic import ValidationError

# Import the function and Pydantic model to test
from src.ai_analyzer import analyze_caption_for_location, LocationResponse

# Define the path to the function we need to mock
GENERATE_CONTENT_MOCK_PATH = "src.ai_analyzer.model.generate_content"

# --- Test Fixtures (Optional, but can be useful) ---
@pytest.fixture
def mock_generate_content(mocker):
    """Fixture to mock the genai model's generate_content method."""
    return mocker.patch(GENERATE_CONTENT_MOCK_PATH)

# --- Test Cases ---

def test_analyze_caption_success_locations_found_parsed(mock_generate_content):
    """Tests successful analysis with locations found via response.parsed."""
    caption = "Amazing view from the Eiffel Tower!"
    expected_locations = ["Eiffel Tower"]
    expected_result = {"location_found": True, "locations": expected_locations}

    # Create a mock response object with a .parsed attribute
    mock_response = MagicMock()
    mock_response.parsed = LocationResponse(location_found=True, locations=expected_locations)
    # We don't strictly need .text if .parsed works, but good practice to have it
    mock_response.text = json.dumps(expected_result)

    mock_generate_content.return_value = mock_response

    result = analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generate_content.assert_called_once()
    # Optional: Assert prompt contains caption
    assert caption in mock_generate_content.call_args[0][0]

def test_analyze_caption_success_no_locations_found_parsed(mock_generate_content):
    """Tests successful analysis with no locations found via response.parsed."""
    caption = "Just a random thought."
    expected_result = {"location_found": False, "locations": None}

    mock_response = MagicMock()
    mock_response.parsed = LocationResponse(location_found=False, locations=None)
    mock_response.text = json.dumps(expected_result)

    mock_generate_content.return_value = mock_response

    result = analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generate_content.assert_called_once()

def test_analyze_caption_success_locations_found_fallback(mock_generate_content):
    """Tests successful analysis with locations found via fallback JSON parsing."""
    caption = "Dinner at Joe's Pizza."
    expected_locations = ["Joe's Pizza"]
    expected_result = {"location_found": True, "locations": expected_locations}
    raw_json_text = json.dumps(expected_result)

    # Simulate response.parsed being absent or None
    mock_response = MagicMock()
    mock_response.parsed = None # Or del mock_response.parsed
    mock_response.text = raw_json_text

    mock_generate_content.return_value = mock_response

    result = analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generate_content.assert_called_once()

def test_analyze_caption_success_no_locations_found_fallback(mock_generate_content):
    """Tests successful analysis with no locations found via fallback JSON parsing."""
    caption = "Another day at the office."
    expected_result = {"location_found": False, "locations": None}
    raw_json_text = json.dumps(expected_result)

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = raw_json_text

    mock_generate_content.return_value = mock_response

    result = analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generate_content.assert_called_once()

def test_analyze_caption_empty_input(mock_generate_content):
    """Tests handling of an empty input caption."""
    caption = ""
    expected_result = {"location_found": False, "locations": None, "error": "Empty caption provided"}

    result = analyze_caption_for_location(caption)

    assert result == expected_result
    mock_generate_content.assert_not_called() # API should not be called

def test_analyze_caption_api_error(mock_generate_content):
    """Tests handling of a Gemini API call error."""
    caption = "This caption will cause an error."
    error_message = "API rate limit exceeded"
    # Simulate an API error (using a generic Exception for simplicity, could use specific google_exceptions)
    mock_generate_content.side_effect = Exception(error_message)

    expected_error_fragment = f"Gemini API call failed: {error_message}"

    result = analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    mock_generate_content.assert_called_once()

def test_analyze_caption_fallback_json_decode_error(mock_generate_content):
    """Tests handling of invalid JSON in the fallback parsing path."""
    caption = "Caption leading to bad JSON."
    invalid_json_text = '{"location_found": true, "locations": ["Place"]' # Missing closing brace

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = invalid_json_text

    mock_generate_content.return_value = mock_response

    expected_error_fragment = "Failed to parse fallback JSON response from AI"

    result = analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == invalid_json_text
    mock_generate_content.assert_called_once()

def test_analyze_caption_fallback_invalid_structure(mock_generate_content):
    """Tests handling of valid JSON with incorrect structure in fallback."""
    caption = "Caption leading to wrong structure."
    wrong_structure_json = json.dumps({"name": "Eiffel Tower", "city": "Paris"})

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = wrong_structure_json

    mock_generate_content.return_value = mock_response

    expected_error_fragment = "Invalid structure in fallback JSON"

    result = analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == wrong_structure_json
    mock_generate_content.assert_called_once()

def test_analyze_caption_fallback_invalid_locations_format(mock_generate_content):
    """Tests handling of fallback JSON with invalid 'locations' field type."""
    caption = "Caption leading to bad locations type."
    # 'locations' should be a list or None, not a string
    bad_locations_json = json.dumps({"location_found": True, "locations": "Eiffel Tower"})

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = bad_locations_json

    mock_generate_content.return_value = mock_response

    expected_error_fragment = "Invalid 'locations' format in fallback JSON"

    result = analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == bad_locations_json
    mock_generate_content.assert_called_once()

# Dedent the following function to fix nesting
def test_analyze_caption_processing_error_after_api_call(mock_generate_content):
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

    mock_generate_content.return_value = mock_response

    # Even though .parsed fails, the fallback should succeed here
    result = analyze_caption_for_location(caption)

    # Check that fallback parsing worked despite the initial error
    assert result == expected_result
    mock_generate_content.assert_called_once()

def test_analyze_caption_processing_error_and_fallback_fails(mock_generate_content):
    """Tests handling of processing error AND fallback JSON error."""
    caption = "Caption causing double error."
    invalid_json_text = '{"bad": json'

    # Simulate response.parsed being None and fallback text being invalid JSON
    mock_response = MagicMock()
    mock_response.parsed = None # Set parsed to None
    mock_response.text = invalid_json_text # Provide invalid fallback text

    mock_generate_content.return_value = mock_response

    # Expect the error from the json.JSONDecodeError block in the source code
    expected_error_fragment = "Failed to parse fallback JSON response from AI"

    result = analyze_caption_for_location(caption)

    assert result["location_found"] is False
    assert result["locations"] is None
    assert "error" in result
    assert expected_error_fragment in result["error"]
    assert "raw_response" in result
    assert result["raw_response"] == invalid_json_text
    mock_generate_content.assert_called_once()
