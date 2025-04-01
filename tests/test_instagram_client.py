import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from instagrapi.exceptions import ClientError, LoginRequired

# Import the class to be tested
from src.instagram_client import InstagramClient

# Define a fixture for the session file path
@pytest.fixture
def mock_session_file():
    return Path("auth/test_session")

# Define a fixture for the InstagramClient instance
@pytest.fixture
def insta_client(mock_session_file):
    # Patch the Client class within the module where it's imported
    with patch('src.instagram_client.Client') as MockInstagrapiClient:
        # Configure the mock instance returned by Client()
        mock_client_instance = MockInstagrapiClient.return_value
        # Create the InstagramClient instance, passing the mock session file
        client = InstagramClient(session_file=mock_session_file)
        # Attach the mock instagrapi client instance for later assertions if needed
        client.mock_instagrapi_client = mock_client_instance
        yield client # Yield the client instance for the test

# --- Tests for login() method ---

def test_login_success(insta_client, mock_session_file, mocker):
    """Test successful login when session file exists and is valid."""
    # Mock Path.exists() to return True
    mocker.patch.object(Path, 'exists', return_value=True)

    # Configure the mock instagrapi client methods
    insta_client.mock_instagrapi_client.load_settings.return_value = None
    insta_client.mock_instagrapi_client.account_info.return_value = MagicMock() # Simulate successful verification

    # Call the login method
    result = insta_client.login()

    # Assertions
    assert result is True
    assert insta_client.logged_in is True
    insta_client.mock_instagrapi_client.load_settings.assert_called_once_with(mock_session_file)
    insta_client.mock_instagrapi_client.account_info.assert_called_once()

def test_login_file_not_found(insta_client, mock_session_file, mocker, capsys):
    """Test login failure when session file does not exist."""
    # Mock Path.exists() to return False
    mocker.patch.object(Path, 'exists', return_value=False)

    # Call the login method
    result = insta_client.login()
    captured = capsys.readouterr() # Capture printed output

    # Assertions
    assert result is False
    assert insta_client.logged_in is False
    insta_client.mock_instagrapi_client.load_settings.assert_not_called()
    insta_client.mock_instagrapi_client.account_info.assert_not_called()
    assert f"Error: Session file not found at {mock_session_file}" in captured.out

def test_login_invalid_session_login_required(insta_client, mock_session_file, mocker, capsys):
    """Test login failure due to LoginRequired exception."""
    # Mock Path.exists() to return True
    mocker.patch.object(Path, 'exists', return_value=True)

    # Configure load_settings to raise LoginRequired
    insta_client.mock_instagrapi_client.load_settings.side_effect = LoginRequired("Session expired")

    # Call the login method
    result = insta_client.login()
    captured = capsys.readouterr()

    # Assertions
    assert result is False
    assert insta_client.logged_in is False
    insta_client.mock_instagrapi_client.load_settings.assert_called_once_with(mock_session_file)
    insta_client.mock_instagrapi_client.account_info.assert_not_called()
    assert "Error: Session is invalid or expired." in captured.out
    assert "Session expired" in captured.out # Check if exception message is included

def test_login_invalid_session_client_error(insta_client, mock_session_file, mocker, capsys):
    """Test login failure due to ClientError exception during verification."""
    # Mock Path.exists() to return True
    mocker.patch.object(Path, 'exists', return_value=True)

    # Configure load_settings to succeed, but account_info to fail
    insta_client.mock_instagrapi_client.load_settings.return_value = None
    insta_client.mock_instagrapi_client.account_info.side_effect = ClientError("Verification failed")

    # Call the login method
    result = insta_client.login()
    captured = capsys.readouterr()

    # Assertions
    assert result is False
    assert insta_client.logged_in is False # Should still be false after failure
    insta_client.mock_instagrapi_client.load_settings.assert_called_once_with(mock_session_file)
    insta_client.mock_instagrapi_client.account_info.assert_called_once()
    assert "Error: Session is invalid or expired." in captured.out
    assert "Verification failed" in captured.out

def test_login_unexpected_error(insta_client, mock_session_file, mocker, capsys):
    """Test login failure due to an unexpected generic exception."""
    # Mock Path.exists() to return True
    mocker.patch.object(Path, 'exists', return_value=True)

    # Configure load_settings to raise a generic Exception
    insta_client.mock_instagrapi_client.load_settings.side_effect = Exception("Something went wrong")

    # Call the login method
    result = insta_client.login()
    captured = capsys.readouterr()

    # Assertions
    assert result is False
    assert insta_client.logged_in is False
    insta_client.mock_instagrapi_client.load_settings.assert_called_once_with(mock_session_file)
    insta_client.mock_instagrapi_client.account_info.assert_not_called()
    assert "An unexpected error occurred during login: Something went wrong" in captured.out

# --- Tests for get_collections() method ---

# Helper fixture to create mock Collection objects
@pytest.fixture
def mock_collections():
    coll1 = MagicMock()
    coll1.pk = 123
    coll1.name = "Travel"
    coll2 = MagicMock()
    coll2.pk = 456
    coll2.name = "Food"
    return [coll1, coll2]

def test_get_collections_success(insta_client, mock_collections):
    """Test successfully fetching collections when logged in."""
    # Assume client is logged in
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collections.return_value = mock_collections

    # Call the method
    result = insta_client.get_collections()

    # Assertions
    assert result == mock_collections
    insta_client.mock_instagrapi_client.collections.assert_called_once()

def test_get_collections_not_logged_in(insta_client, capsys):
    """Test attempting to fetch collections when not logged in."""
    # Ensure client is not logged in
    insta_client.logged_in = False

    # Call the method
    result = insta_client.get_collections()
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    insta_client.mock_instagrapi_client.collections.assert_not_called()
    assert "Error: Not logged in." in captured.out

def test_get_collections_login_required(insta_client, capsys):
    """Test fetching collections failure due to LoginRequired."""
    # Assume client was logged in, but session expired
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collections.side_effect = LoginRequired("Session expired during fetch")

    # Call the method
    result = insta_client.get_collections()
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    assert insta_client.logged_in is False # Should be logged out after error
    insta_client.mock_instagrapi_client.collections.assert_called_once()
    assert "Error fetching collections (login may have expired)" in captured.out
    assert "Session expired during fetch" in captured.out

def test_get_collections_client_error(insta_client, capsys):
    """Test fetching collections failure due to ClientError."""
    # Assume client is logged in
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collections.side_effect = ClientError("API limit reached")

    # Call the method
    result = insta_client.get_collections()
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    assert insta_client.logged_in is False # Should be logged out after error
    insta_client.mock_instagrapi_client.collections.assert_called_once()
    assert "Error fetching collections (login may have expired)" in captured.out # Message is generic
    assert "API limit reached" in captured.out

def test_get_collections_unexpected_error(insta_client, capsys):
    """Test fetching collections failure due to unexpected error."""
    # Assume client is logged in
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collections.side_effect = Exception("Network issue")

    # Call the method
    result = insta_client.get_collections()
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    assert insta_client.logged_in is True # Should remain logged in for unexpected errors? Check impl. (Current impl keeps logged_in=True)
    insta_client.mock_instagrapi_client.collections.assert_called_once()
    assert "An unexpected error occurred fetching collections: Network issue" in captured.out


# --- Tests for get_media_from_collection() method ---

# Helper fixture to create mock Media objects
@pytest.fixture
def mock_media_items():
    media1 = MagicMock()
    media1.pk = 111
    media1.code = "C1"
    media1.media_type = 2 # Video
    media1.caption_text = "Video 1"
    media2 = MagicMock()
    media2.pk = 222
    media2.code = "C2"
    media2.media_type = 1 # Photo
    media2.caption_text = "Photo 1"
    return [media1, media2]

def test_get_media_success(insta_client, mock_media_items):
    """Test successfully fetching media for a collection when logged in."""
    collection_pk = 123
    # Assume client is logged in
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collection_medias.return_value = mock_media_items

    # Call the method
    result = insta_client.get_media_from_collection(collection_pk)

    # Assertions
    assert result == mock_media_items
    insta_client.mock_instagrapi_client.collection_medias.assert_called_once_with(collection_pk, amount=0)

def test_get_media_not_logged_in(insta_client, capsys):
    """Test attempting to fetch media when not logged in."""
    collection_pk = 123
    # Ensure client is not logged in
    insta_client.logged_in = False

    # Call the method
    result = insta_client.get_media_from_collection(collection_pk)
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    insta_client.mock_instagrapi_client.collection_medias.assert_not_called()
    assert "Error: Not logged in." in captured.out

def test_get_media_login_required(insta_client, capsys):
    """Test fetching media failure due to LoginRequired."""
    collection_pk = 123
    # Assume client was logged in, but session expired
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collection_medias.side_effect = LoginRequired("Session expired during media fetch")

    # Call the method
    result = insta_client.get_media_from_collection(collection_pk)
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    assert insta_client.logged_in is False # Should be logged out
    insta_client.mock_instagrapi_client.collection_medias.assert_called_once_with(collection_pk, amount=0)
    assert "Error fetching media (login may have expired)" in captured.out
    assert "Session expired during media fetch" in captured.out

def test_get_media_client_error(insta_client, capsys):
    """Test fetching media failure due to ClientError."""
    collection_pk = 123
    # Assume client is logged in
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collection_medias.side_effect = ClientError("Collection not found")

    # Call the method
    result = insta_client.get_media_from_collection(collection_pk)
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    assert insta_client.logged_in is False # Should be logged out
    insta_client.mock_instagrapi_client.collection_medias.assert_called_once_with(collection_pk, amount=0)
    assert "Error fetching media (login may have expired)" in captured.out # Generic message
    assert "Collection not found" in captured.out

def test_get_media_unexpected_error(insta_client, capsys):
    """Test fetching media failure due to unexpected error."""
    collection_pk = 123
    # Assume client is logged in
    insta_client.logged_in = True
    insta_client.mock_instagrapi_client.collection_medias.side_effect = Exception("Timeout")

    # Call the method
    result = insta_client.get_media_from_collection(collection_pk)
    captured = capsys.readouterr()

    # Assertions
    assert result is None
    assert insta_client.logged_in is True # Should remain logged in? Check impl. (Current impl keeps logged_in=True)
    insta_client.mock_instagrapi_client.collection_medias.assert_called_once_with(collection_pk, amount=0)
    assert "An unexpected error occurred fetching media: Timeout" in captured.out
