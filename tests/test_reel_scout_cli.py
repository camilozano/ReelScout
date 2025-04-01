import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import the CLI entry point and the command function
from reel_scout_cli import cli, collect_reels

# --- Fixtures ---

@pytest.fixture
def runner():
    """Provides a CliRunner instance."""
    return CliRunner()

@pytest.fixture
def mock_collections_data():
    """Provides mock collection data similar to instagrapi types."""
    coll1 = MagicMock()
    coll1.id = "123" # Use id as string, matching instagrapi
    coll1.name = "Travel"
    coll2 = MagicMock()
    coll2.id = "456" # Use id as string
    coll2.name = "Food"
    return [coll1, coll2]

@pytest.fixture
def mock_media_data():
    """Provides mock media data similar to instagrapi types."""
    media1 = MagicMock(pk=111, media_type=2) # Video
    media2 = MagicMock(pk=222, media_type=1) # Photo
    return [media1, media2]

# --- Test Cases for 'collect' command ---

# Use patch context managers within the test function
def test_collect_success_defaults(runner, mock_collections_data, mock_media_data):
    """Test successful run of 'collect' with default paths and user selects '1'."""
    with patch('reel_scout_cli.InstagramClient') as MockInstagramClient, \
         patch('reel_scout_cli.download_collection_media') as mock_download, \
         patch('click.prompt') as mock_prompt:

        # Configure MockInstagramClient instance and its methods
        mock_instance = MockInstagramClient.return_value
        mock_instance.login.return_value = True
        mock_instance.get_collections.return_value = mock_collections_data
        mock_instance.get_media_from_collection.return_value = mock_media_data
        mock_instance.client = MagicMock() # Mock the inner client needed by downloader

        # Configure mock_download
        mock_download.return_value = True

        # Configure mock_prompt to return '1' (first collection)
        mock_prompt.return_value = '1'

        # Invoke the CLI command
        result = runner.invoke(cli, ['collect'])

        # Assertions
        assert result.exit_code == 0
        assert "--- ReelScout Collection ---" in result.output
        assert "Using session file: auth/session.json" in result.output # Default path
        assert "Using download directory: downloads" in result.output # Default path
        assert "Login successful." in result.output
        assert "1. Travel (ID: 123)" in result.output # Check for ID
        assert "2. Food (ID: 456)" in result.output # Check for ID
        mock_prompt.assert_called_once()
        assert "Selected collection: 'Travel'" in result.output
        assert f"Found {len(mock_media_data)} total items" in result.output
        assert "Starting download process" in result.output
        assert "--- Collection process completed successfully! ---" in result.output

        # Check mocks were called correctly
        MockInstagramClient.assert_called_once_with(session_file=Path("auth/session.json"))
        mock_instance.login.assert_called_once()
        mock_instance.get_collections.assert_called_once()
        mock_instance.get_media_from_collection.assert_called_once_with(mock_collections_data[0].id) # Use ID
        # Expect the resolved absolute path for download_dir
        expected_download_dir = Path("downloads").resolve()
        mock_download.assert_called_once_with(
                client=mock_instance.client,
                media_items=mock_media_data,
                collection_name=mock_collections_data[0].name,
                download_dir=expected_download_dir, # Expect resolved path
                skip_download=False # Add default skip_download flag
            )

def test_collect_success_custom_paths(runner, mock_collections_data, mock_media_data, tmp_path):
    """Test successful run with custom session and download paths."""
    custom_session = tmp_path / "my_session.json"
    custom_download = tmp_path / "my_reels"
    # Create the necessary file and directory to satisfy Click's checks
    custom_session.touch()
    custom_download.mkdir()

    # No longer need to patch os.path.exists or os.access for Click validation
    with patch('reel_scout_cli.InstagramClient') as MockInstagramClient, \
         patch('reel_scout_cli.download_collection_media') as mock_download, \
         patch('click.prompt') as mock_prompt:

        mock_instance = MockInstagramClient.return_value
        mock_instance.login.return_value = True
        mock_instance.get_collections.return_value = mock_collections_data
        mock_instance.get_media_from_collection.return_value = mock_media_data
        mock_instance.client = MagicMock()
        mock_download.return_value = True
        mock_prompt.return_value = '2' # Select second collection

        result = runner.invoke(cli, [
            'collect',
            '--session-file', str(custom_session),
            '--download-dir', str(custom_download)
        ])

        assert result.exit_code == 0
        assert f"Using session file: {custom_session}" in result.output
        assert f"Using download directory: {custom_download}" in result.output
        assert "Selected collection: 'Food'" in result.output # Second collection
        assert "--- Collection process completed successfully! ---" in result.output

        MockInstagramClient.assert_called_once_with(session_file=custom_session)
        mock_instance.get_media_from_collection.assert_called_once_with(mock_collections_data[1].id) # Use ID
        mock_download.assert_called_once_with(
            client=mock_instance.client,
            media_items=mock_media_data,
            collection_name=mock_collections_data[1].name,
            download_dir=custom_download,
            skip_download=False # Add default skip_download flag
        )

def test_collect_login_failure(runner):
    """Test CLI behavior when InstagramClient.login() fails."""
    with patch('reel_scout_cli.InstagramClient') as MockInstagramClient:
        mock_instance = MockInstagramClient.return_value
        mock_instance.login.return_value = False # Simulate login failure

        result = runner.invoke(cli, ['collect'])

        assert result.exit_code == 1 # Should exit with error code
        assert "Login failed using auth/session.json" in result.output
        mock_instance.login.assert_called_once()
        mock_instance.get_collections.assert_not_called() # Should not proceed

def test_collect_get_collections_failure(runner):
    """Test CLI behavior when get_collections() fails."""
    with patch('reel_scout_cli.InstagramClient') as MockInstagramClient:
        mock_instance = MockInstagramClient.return_value
        mock_instance.login.return_value = True
        mock_instance.get_collections.return_value = None # Simulate failure

        result = runner.invoke(cli, ['collect'])

        assert result.exit_code == 1
        assert "Login successful." in result.output
        assert "Failed to fetch collections or no collections found." in result.output
        mock_instance.get_collections.assert_called_once()
        mock_instance.get_media_from_collection.assert_not_called() # Should not proceed

def test_collect_get_media_failure(runner, mock_collections_data):
    """Test CLI behavior when get_media_from_collection() fails."""
    with patch('reel_scout_cli.InstagramClient') as MockInstagramClient, \
         patch('click.prompt') as mock_prompt:

        mock_instance = MockInstagramClient.return_value
        mock_instance.login.return_value = True
        mock_instance.get_collections.return_value = mock_collections_data
        mock_instance.get_media_from_collection.return_value = None # Simulate failure
        mock_prompt.return_value = '1'

        result = runner.invoke(cli, ['collect'])

        assert result.exit_code == 1
        assert "Selected collection: 'Travel'" in result.output
        assert "Fetching media items for 'Travel'..." in result.output
        assert "Failed to fetch media or no items found in collection 'Travel'." in result.output
        mock_instance.get_media_from_collection.assert_called_once_with(mock_collections_data[0].id) # Use ID
        # download_collection_media should not be called
        # Need to patch it even if not called to avoid ModuleNotFoundError if src.downloader isn't importable in test env
        with patch('reel_scout_cli.download_collection_media') as mock_download:
             mock_download.assert_not_called()


def test_collect_download_failure(runner, mock_collections_data, mock_media_data):
    """Test CLI behavior when download_collection_media() returns False."""
    with patch('reel_scout_cli.InstagramClient') as MockInstagramClient, \
         patch('reel_scout_cli.download_collection_media') as mock_download, \
         patch('click.prompt') as mock_prompt:

        mock_instance = MockInstagramClient.return_value
        mock_instance.login.return_value = True
        mock_instance.get_collections.return_value = mock_collections_data
        mock_instance.get_media_from_collection.return_value = mock_media_data
        mock_instance.client = MagicMock()
        mock_download.return_value = False # Simulate download failure
        mock_prompt.return_value = '1'

        result = runner.invoke(cli, ['collect'])

        assert result.exit_code == 1
        assert "Starting download process" in result.output
        assert "--- Collection process finished with errors. ---" in result.output
        mock_download.assert_called_once()

# Note: Testing invalid user input for click.prompt is tricky as it handles
# the re-prompting internally. We trust click's behavior here.
# Testing specific exceptions raised by dependencies is covered in the
# unit tests for InstagramClient and download_collection_media.
