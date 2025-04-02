# Unit tests for the location_enricher module
import pytest
from unittest.mock import patch, MagicMock
# Removed os import and pre-import setup

# Import the function under test first
from src.location_enricher import enrich_location_data
# Import googlemaps later for exceptions etc.
import googlemaps

# Removed setup_env fixture

@pytest.fixture
def mock_gmaps_client():
    """Mocks the global gmaps client instance in the enricher module."""
    # Create a mock instance that simulates the googlemaps.Client
    # spec=googlemaps.Client ensures the mock has the same methods/attributes
    mock_client = MagicMock(spec=googlemaps.Client)
    # Patch the 'gmaps' variable *within* the location_enricher module
    with patch('src.location_enricher.gmaps', mock_client) as patched_client:
        # Yield the mock client itself, tests can access its methods
        yield patched_client


# --- Test Cases ---

def test_enrich_location_success(mock_gmaps_client):
    """Test successful enrichment with a valid location name."""
    location_name = "Eiffel Tower"
    place_id = 'ChIJLU7jZClu5kcR4PcOOO6Dd8Q'
    google_maps_uri = 'https://maps.google.com/?cid=10281108625141988416'

    # Configure the mock methods directly on the mock_gmaps_client
    mock_gmaps_client.find_place.return_value = {
        'status': 'OK',
        'candidates': [{'place_id': place_id}]
    }
    mock_gmaps_client.place.return_value = {
        'status': 'OK',
        'result': {
            'name': 'Eiffel Tower',
            'formatted_address': 'Champ de Mars, 5 Av. Anatole France, 75007 Paris, France',
            'url': google_maps_uri, # This is the google maps uri
            'place_id': place_id,
            'geometry': {
                'location': {'lat': 48.85837009999999, 'lng': 2.2944813}
            }
        }
    }

    result = enrich_location_data(location_name)

    assert result is not None
    assert result['name'] == 'Eiffel Tower'
    assert result['address'] == 'Champ de Mars, 5 Av. Anatole France, 75007 Paris, France'
    assert result['place_id'] == place_id
    assert result['latitude'] == 48.85837009999999
    assert result['longitude'] == 2.2944813
    assert result['google_maps_uri'] == google_maps_uri # Check the new field

    # Assert methods were called on the mock client
    mock_gmaps_client.find_place.assert_called_once_with(
        input=location_name,
        input_type='textquery',
        fields=['name', 'formatted_address', 'place_id', 'geometry/location']
    )
    mock_gmaps_client.place.assert_called_once_with(
        place_id=place_id,
        fields=['name', 'formatted_address', 'url', 'place_id', 'geometry/location']
    )


def test_enrich_location_zero_results(mock_gmaps_client):
    """Test enrichment when find_place returns ZERO_RESULTS."""
    location_name = "NonExistentPlace12345XYZ"
    mock_gmaps_client.find_place.return_value = {'status': 'ZERO_RESULTS', 'candidates': []}

    result = enrich_location_data(location_name)

    assert result is None
    mock_gmaps_client.find_place.assert_called_once_with(
        input=location_name,
        input_type='textquery',
        fields=['name', 'formatted_address', 'place_id', 'geometry/location']
    )
    mock_gmaps_client.place.assert_not_called() # place() should not be called


def test_enrich_location_find_place_api_error_status(mock_gmaps_client):
    """Test enrichment when find_place returns an error status."""
    location_name = "Some Place"
    mock_gmaps_client.find_place.return_value = {'status': 'REQUEST_DENIED', 'error_message': 'API key invalid.', 'candidates': []}

    result = enrich_location_data(location_name)

    assert result is None
    mock_gmaps_client.find_place.assert_called_once_with(
        input=location_name,
        input_type='textquery',
        fields=['name', 'formatted_address', 'place_id', 'geometry/location']
    )
    mock_gmaps_client.place.assert_not_called()


def test_enrich_location_find_place_api_exception(mock_gmaps_client):
    """Test enrichment when find_place raises an ApiError."""
    location_name = "Problem Place"
    mock_gmaps_client.find_place.side_effect = googlemaps.exceptions.ApiError(status='OVER_QUERY_LIMIT')

    result = enrich_location_data(location_name)

    assert result is None
    mock_gmaps_client.find_place.assert_called_once_with(
        input=location_name,
        input_type='textquery',
        fields=['name', 'formatted_address', 'place_id', 'geometry/location']
    )
    mock_gmaps_client.place.assert_not_called()


def test_enrich_location_find_place_http_exception(mock_gmaps_client):
    """Test enrichment when find_place raises an HTTPError."""
    location_name = "Network Issue Place"
    mock_gmaps_client.find_place.side_effect = googlemaps.exceptions.HTTPError(status_code=500)

    result = enrich_location_data(location_name)

    assert result is None
    mock_gmaps_client.find_place.assert_called_once_with(
        input=location_name,
        input_type='textquery',
        fields=['name', 'formatted_address', 'place_id', 'geometry/location']
    )
    mock_gmaps_client.place.assert_not_called()


def test_enrich_location_find_place_timeout_exception(mock_gmaps_client):
    """Test enrichment when find_place raises a Timeout."""
    location_name = "Slow Place"
    mock_gmaps_client.find_place.side_effect = googlemaps.exceptions.Timeout()

    result = enrich_location_data(location_name)

    assert result is None
    mock_gmaps_client.find_place.assert_called_once_with(
        input=location_name,
        input_type='textquery',
        fields=['name', 'formatted_address', 'place_id', 'geometry/location']
    )
    mock_gmaps_client.place.assert_not_called()


def test_enrich_location_find_place_unexpected_exception(mock_gmaps_client):
    """Test enrichment when find_place raises an unexpected error."""
    location_name = "Weird Place"
    mock_gmaps_client.find_place.side_effect = ValueError("Something unexpected happened")

    result = enrich_location_data(location_name)

    assert result is None
    mock_gmaps_client.find_place.assert_called_once_with(
        input=location_name,
        input_type='textquery',
        fields=['name', 'formatted_address', 'place_id', 'geometry/location']
    )
    mock_gmaps_client.place.assert_not_called()


def test_enrich_location_place_details_fails_status(mock_gmaps_client):
    """Test when find_place succeeds but place details call returns an error status."""
    location_name = "Eiffel Tower"
    place_id = 'ChIJLU7jZClu5kcR4PcOOO6Dd8Q'

    mock_gmaps_client.find_place.return_value = {'status': 'OK', 'candidates': [{'place_id': place_id}]}
    mock_gmaps_client.place.return_value = {'status': 'INVALID_REQUEST', 'result': {}} # Simulate error from place() call

    result = enrich_location_data(location_name)

    assert result is None # Should fail if place details fail
    mock_gmaps_client.find_place.assert_called_once()
    mock_gmaps_client.place.assert_called_once_with(
        place_id=place_id,
        fields=['name', 'formatted_address', 'url', 'place_id', 'geometry/location']
    )


def test_enrich_location_place_details_api_exception(mock_gmaps_client):
    """Test when find_place succeeds but place details call raises ApiError."""
    location_name = "Eiffel Tower"
    place_id = 'ChIJLU7jZClu5kcR4PcOOO6Dd8Q'

    mock_gmaps_client.find_place.return_value = {'status': 'OK', 'candidates': [{'place_id': place_id}]}
    mock_gmaps_client.place.side_effect = googlemaps.exceptions.ApiError(status='OVER_QUERY_LIMIT')

    result = enrich_location_data(location_name)

    assert result is None # Should fail if place details fail
    mock_gmaps_client.find_place.assert_called_once()
    mock_gmaps_client.place.assert_called_once_with(
        place_id=place_id,
        fields=['name', 'formatted_address', 'url', 'place_id', 'geometry/location']
    )


def test_enrich_location_empty_input(mock_gmaps_client):
    """Test enrichment with an empty location name string."""
    result = enrich_location_data("")
    assert result is None
    mock_gmaps_client.find_place.assert_not_called()
    mock_gmaps_client.place.assert_not_called()


def test_enrich_location_none_input(mock_gmaps_client):
    """Test enrichment with None as location name."""
    result = enrich_location_data(None)
    assert result is None
    mock_gmaps_client.find_place.assert_not_called()
    mock_gmaps_client.place.assert_not_called()


def test_enrich_location_no_place_id_in_candidate(mock_gmaps_client):
    """Test case where find_place candidate lacks a place_id."""
    location_name = "Place Without ID"
    mock_gmaps_client.find_place.return_value = {
        'status': 'OK',
        'candidates': [{'name': 'Place Without ID'}] # 'place_id' is missing
    }

    result = enrich_location_data(location_name)

    assert result is None # Should fail if place_id is missing
    mock_gmaps_client.find_place.assert_called_once()
    mock_gmaps_client.place.assert_not_called() # place() should not be called


# Optional: Test case if the global gmaps client failed to initialize
@patch('src.location_enricher.gmaps', None) # Temporarily set the global client to None
def test_enrich_location_gmaps_not_initialized(): # Removed fixture from signature
    """Test behavior when the gmaps client is not initialized."""
    # We don't need the mocks here as the function should exit early.
    result = enrich_location_data("Any Place")
    assert result is None
    # No API call should be attempted
