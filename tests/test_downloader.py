import pytest
import json
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from instagrapi.exceptions import ClientError
# Remove direct import of Media type, we'll use MagicMock
# from instagrapi.types import Media

# Import the function to be tested
from src.downloader import download_collection_media

# --- Fixtures ---

@pytest.fixture
def mock_instagrapi_client():
    """Provides a mock instagrapi.Client instance."""
    return MagicMock()

@pytest.fixture
def mock_media_items():
    """Provides a list of mock Media objects using MagicMock."""
    video_media = MagicMock()
    video_media.pk = 111
    video_media.code = "CVideo1"
    video_media.media_type = 2 # Video
    video_media.product_type = "feed" # Example product type
    video_media.caption_text = "This is a cool video"

    photo_media = MagicMock()
    photo_media.pk = 222
    photo_media.code = "CPhoto1"
    photo_media.media_type = 1 # Photo
    photo_media.product_type = "feed"
    photo_media.caption_text = "This is a photo"

    video_media_no_caption = MagicMock()
    video_media_no_caption.pk = 333
    video_media_no_caption.code = "CVideo2"
    video_media_no_caption.media_type = 2 # Video
    video_media_no_caption.product_type = "clips" # Reel
    video_media_no_caption.caption_text = None # Test None caption

    return [video_media, photo_media, video_media_no_caption]

@pytest.fixture
def collection_name():
    """Provides a sample collection name."""
    return "Test Collection"

# --- Test Cases ---

def test_download_success(mock_instagrapi_client, mock_media_items, collection_name, tmp_path):
    """Test successful download of videos and metadata creation."""
    download_dir = tmp_path / "downloads" # Use tmp_path for isolation
    collection_dir = download_dir / collection_name
    expected_video1_path = collection_dir / "video_111.mp4" # Example path structure
    expected_video2_path = collection_dir / "video_333.mp4"
    expected_metadata_path = collection_dir / "metadata.json"

    # Configure mock client download behavior
    def mock_video_download(pk, folder):
        if pk == 111:
            # Simulate file creation by returning the expected path
            expected_video1_path.parent.mkdir(parents=True, exist_ok=True)
            expected_video1_path.touch()
            return expected_video1_path
        elif pk == 333:
            expected_video2_path.parent.mkdir(parents=True, exist_ok=True)
            expected_video2_path.touch()
            return expected_video2_path
        return None # Should not be called for photo

    mock_instagrapi_client.video_download.side_effect = mock_video_download

    # Patch open and json.dump for metadata verification
    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:

        # Call the function
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=mock_media_items,
            collection_name=collection_name,
            download_dir=download_dir
        )

    # Assertions
    assert result is True
    # Check directory was created (implicitly by side_effect, but good practice)
    assert collection_dir.exists()

    # Check video_download calls
    assert mock_instagrapi_client.video_download.call_count == 2 # Only for videos
    mock_instagrapi_client.video_download.assert_has_calls([
        call(111, folder=collection_dir),
        call(333, folder=collection_dir)
    ], any_order=True)

    # Check metadata file write
    mock_open.assert_called_once_with(expected_metadata_path, "w", encoding="utf-8")
    # Check metadata content passed to json.dump
    # The relative path is now calculated relative to download_dir
    # Check metadata content passed to json.dump
    # The relative path should now be just the filename
    expected_filename1 = expected_video1_path.name # e.g., "video_111.mp4"
    expected_filename2 = expected_video2_path.name # e.g., "video_333.mp4"
    expected_metadata = [
        {
            "relative_path": str(expected_filename1), # Expect filename
            "caption": "This is a cool video",
            "url": "https://www.instagram.com/p/CVideo1/",
            "pk": 111,
            "media_type": 2,
            "product_type": "feed",
        },
        {
            "relative_path": str(expected_filename2), # Expect filename
            "caption": "", # Handled None caption
            "url": "https://www.instagram.com/p/CVideo2/",
            "pk": 333,
            "media_type": 2,
            "product_type": "clips",
        },
    ]
    mock_json_dump.assert_called_once_with(
        expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False
    )

def test_download_skip_non_video(mock_instagrapi_client, mock_media_items, collection_name, tmp_path):
    """Test that non-video items are skipped."""
    download_dir = tmp_path / "downloads"
    # Only provide the photo media item
    photo_item = [m for m in mock_media_items if m.media_type == 1]

    with patch("builtins.open", MagicMock()), patch("json.dump", MagicMock()):
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=photo_item,
            collection_name=collection_name,
            download_dir=download_dir
        )

    assert result is True # Metadata saving should still succeed (empty list)
    mock_instagrapi_client.video_download.assert_not_called()

def test_download_client_error_on_download(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of ClientError during video download."""
    download_dir = tmp_path / "downloads"
    video_item = [m for m in mock_media_items if m.pk == 111] # Just one video

    # Configure download to raise ClientError
    mock_instagrapi_client.video_download.side_effect = ClientError("Download forbidden")

    with patch("builtins.open", MagicMock()), patch("json.dump", MagicMock()):
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=video_item,
            collection_name=collection_name,
            download_dir=download_dir
        )
    captured = capsys.readouterr()

    assert result is True # Metadata saving should still succeed (empty list)
    mock_instagrapi_client.video_download.assert_called_once_with(111, folder=download_dir / collection_name)
    assert "API Error downloading: Download forbidden" in captured.out

def test_download_unexpected_error_on_download(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of unexpected Exception during video download."""
    download_dir = tmp_path / "downloads"
    video_item = [m for m in mock_media_items if m.pk == 111]

    # Configure download to raise generic Exception
    mock_instagrapi_client.video_download.side_effect = Exception("Network timeout")

    with patch("builtins.open", MagicMock()), patch("json.dump", MagicMock()):
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=video_item,
            collection_name=collection_name,
            download_dir=download_dir
        )
    captured = capsys.readouterr()

    assert result is True # Metadata saving should still succeed (empty list)
    mock_instagrapi_client.video_download.assert_called_once_with(111, folder=download_dir / collection_name)
    assert "Unexpected Error downloading: Network timeout" in captured.out

def test_download_mkdir_error(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker, capsys):
    """Test handling of OSError when creating the collection directory."""
    download_dir = tmp_path / "downloads"
    # Mock Path.mkdir to raise OSError
    mocker.patch.object(Path, "mkdir", side_effect=OSError("Permission denied"))

    result = download_collection_media(
        client=mock_instagrapi_client,
        media_items=mock_media_items,
        collection_name=collection_name,
        download_dir=download_dir
    )
    captured = capsys.readouterr()

    assert result is False
    mock_instagrapi_client.video_download.assert_not_called()
    assert f"Error: Could not create directory {download_dir / collection_name}" in captured.out

def test_download_metadata_save_io_error(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of IOError when saving metadata."""
    download_dir = tmp_path / "downloads"
    # Let download succeed
    mock_instagrapi_client.video_download.return_value = download_dir / collection_name / "video.mp4"

    # Patch open to raise IOError
    with patch("builtins.open", side_effect=IOError("Disk full")) as mock_open:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[m for m in mock_media_items if m.media_type == 2], # Only videos
            collection_name=collection_name,
            download_dir=download_dir
        )
    captured = capsys.readouterr()

    assert result is False
    mock_open.assert_called_once_with(download_dir / collection_name / "metadata.json", "w", encoding="utf-8")
    assert f"Error: Could not save metadata file {download_dir / collection_name / 'metadata.json'}" in captured.out

def test_download_metadata_save_type_error(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of TypeError during JSON serialization."""
    download_dir = tmp_path / "downloads"
    # Let download succeed
    mock_instagrapi_client.video_download.return_value = download_dir / collection_name / "video.mp4"

    # Patch json.dump to raise TypeError
    with patch("builtins.open", MagicMock()), \
         patch("json.dump", side_effect=TypeError("Cannot serialize object")) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[m for m in mock_media_items if m.media_type == 2], # Only videos
            collection_name=collection_name,
            download_dir=download_dir
        )
    captured = capsys.readouterr()

    assert result is False
    mock_json_dump.assert_called_once() # Check it was called
    assert "Error: Could not serialize metadata to JSON: Cannot serialize object" in captured.out
