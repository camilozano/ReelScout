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

    # Carousel Media
    carousel_media = MagicMock()
    carousel_media.pk = 888
    carousel_media.code = "CCarousel1"
    carousel_media.media_type = 8 # Carousel
    carousel_media.product_type = "carousel"
    carousel_media.caption_text = "A carousel post"

    # Resources within the carousel
    carousel_resource_photo = MagicMock()
    carousel_resource_photo.pk = 88801
    carousel_resource_photo.media_type = 1 # Photo resource

    carousel_resource_video = MagicMock()
    carousel_resource_video.pk = 88802
    carousel_resource_video.media_type = 2 # Video resource

    carousel_media.resources = [carousel_resource_photo, carousel_resource_video]

    return [video_media, photo_media, video_media_no_caption, carousel_media]

@pytest.fixture
def collection_name():
    """Provides a sample collection name."""
    return "Test Collection"

# --- Test Cases ---

def test_download_success_mixed_types(mock_instagrapi_client, mock_media_items, collection_name, tmp_path):
    """Test successful download of mixed media types (video, photo, carousel) and metadata creation."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    expected_video1_path = collection_dir / "111_video.mp4"
    expected_video2_path = collection_dir / "333_video.mp4"
    expected_photo_path = collection_dir / "222_photo.jpg"
    carousel_pk = 888
    carousel_subdir = collection_dir / str(carousel_pk)
    expected_carousel_res_photo_path = carousel_subdir / "88801_res_photo.jpg"
    expected_carousel_res_video_path = carousel_subdir / "88802_res_video.mp4"
    expected_metadata_path = collection_dir / "metadata.json"

    # Configure mock client download behavior
    def mock_download(pk, folder):
        target_path = None
        if pk == 111: target_path = expected_video1_path
        elif pk == 333: target_path = expected_video2_path
        elif pk == 222: target_path = expected_photo_path
        elif pk == 88801: target_path = expected_carousel_res_photo_path
        elif pk == 88802: target_path = expected_carousel_res_video_path

        if target_path:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.touch()
            return target_path
        return None

    mock_instagrapi_client.video_download.side_effect = mock_download
    mock_instagrapi_client.photo_download.side_effect = mock_download

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
    assert collection_dir.exists()
    assert carousel_subdir.exists() # Check carousel subdir was created

    # Check download calls
    assert mock_instagrapi_client.video_download.call_count == 3 # 2 top-level, 1 resource
    assert mock_instagrapi_client.photo_download.call_count == 2 # 1 top-level, 1 resource
    mock_instagrapi_client.video_download.assert_has_calls([
        call(111, folder=collection_dir),
        call(333, folder=collection_dir),
        call(88802, folder=carousel_subdir) # Resource download
    ], any_order=True)
    mock_instagrapi_client.photo_download.assert_has_calls([
        call(222, folder=collection_dir),
        call(88801, folder=carousel_subdir) # Resource download
    ], any_order=True)


    # Check metadata file write
    mock_open.assert_called_once_with(expected_metadata_path, "w", encoding="utf-8")

    # Check metadata content passed to json.dump
    expected_metadata = [
        { # Video 1
            "relative_path": expected_video1_path.name,
            "caption": "This is a cool video",
            "url": "https://www.instagram.com/p/CVideo1/",
            "pk": 111,
            "media_type": 2,
            "product_type": "feed",
        },
        { # Photo
            "relative_path": expected_photo_path.name,
            "caption": "This is a photo",
            "url": "https://www.instagram.com/p/CPhoto1/",
            "pk": 222,
            "media_type": 1,
            "product_type": "feed",
        },
        { # Video 2
            "relative_path": expected_video2_path.name,
            "caption": "", # Handled None caption
            "url": "https://www.instagram.com/p/CVideo2/",
            "pk": 333,
            "media_type": 2,
            "product_type": "clips",
        },
        { # Carousel
            "relative_path": f"{carousel_pk}/", # Path to subdir
            "caption": "A carousel post",
            "url": "https://www.instagram.com/p/CCarousel1/",
            "pk": carousel_pk,
            "media_type": 8,
            "product_type": "carousel",
        },
    ]
    mock_json_dump.assert_called_once_with(
        expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False
    )

# --- Tests for --skip-download flag ---

def test_download_skip_download_flag_no_existing_file(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test skip_download=True for various types when no file/dir exists."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    # Use all items from the fixture
    video_item = next(m for m in mock_media_items if m.pk == 111)
    photo_item = next(m for m in mock_media_items if m.pk == 222)
    carousel_item = next(m for m in mock_media_items if m.pk == 888)
    carousel_subdir = collection_dir / str(carousel_item.pk)

    # Mock Path.glob to return empty list (no existing file/dir)
    # Need to handle glob calls for items and resources
    def glob_side_effect(pattern):
        # Simulate no existing top-level files/dirs or resource files
        return []
    mocker.patch('pathlib.Path.glob', side_effect=glob_side_effect)
    # Remove global mocks for exists/iterdir for this test, let mkdir work
    # mock_carousel_subdir_exists = mocker.patch.object(Path, 'exists', return_value=False) # REMOVED
    # mock_carousel_subdir_iterdir = mocker.patch.object(Path, 'iterdir', return_value=[]) # REMOVED


    collection_dir.mkdir(parents=True, exist_ok=True) # Ensure base dir exists

    # Patch open and json.dump for metadata verification
    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:

        # Call the function with skip_download=True
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=mock_media_items, # Use all items
            collection_name=collection_name,
            download_dir=download_dir,
            skip_download=True # Explicitly set skip flag
        )

    # Assertions
    assert result is True # Metadata saving should still succeed
    # Crucially, no download functions should be called
    mock_instagrapi_client.video_download.assert_not_called()
    mock_instagrapi_client.photo_download.assert_not_called()
    # Check glob calls (only for top-level items when skipping download)
    # It's called for 111 (video), 222 (photo), 333 (video). Carousel check uses exists/iterdir.
    assert Path.glob.call_count == 3
    # Check carousel subdir was still created (mkdir is called even when skipping)
    assert carousel_subdir.exists()

    # Check metadata content passed to json.dump
    expected_metadata = [
        { # Video 1
            "relative_path": None, # Skipped download
            "caption": video_item.caption_text,
            "url": f"https://www.instagram.com/p/{video_item.code}/",
            "pk": video_item.pk,
            "media_type": video_item.media_type,
            "product_type": video_item.product_type,
        },
        { # Photo
            "relative_path": None, # Skipped download
            "caption": photo_item.caption_text,
            "url": f"https://www.instagram.com/p/{photo_item.code}/",
            "pk": photo_item.pk,
            "media_type": photo_item.media_type,
            "product_type": photo_item.product_type,
        },
        { # Video 2 (no caption)
            "relative_path": None, # Skipped download
            "caption": "",
            "url": f"https://www.instagram.com/p/{mock_media_items[2].code}/",
            "pk": mock_media_items[2].pk,
            "media_type": mock_media_items[2].media_type,
            "product_type": mock_media_items[2].product_type,
        },
         { # Carousel
            "relative_path": f"{carousel_item.pk}/", # Subdir path is still set
            "caption": carousel_item.caption_text,
            "url": f"https://www.instagram.com/p/{carousel_item.code}/",
            "pk": carousel_item.pk,
            "media_type": carousel_item.media_type,
            "product_type": carousel_item.product_type,
        },
    ]
    mock_json_dump.assert_called_once_with(
        expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False
    )


# Test skipping unsupported types (though currently we handle 1, 2, 8)
def test_download_skip_unsupported_type(mock_instagrapi_client, collection_name, tmp_path):
    """Test that unsupported media types are skipped and not in metadata."""
    download_dir = tmp_path / "downloads"
    unsupported_media = MagicMock()
    unsupported_media.pk = 999
    unsupported_media.code = "CUnsupported"
    unsupported_media.media_type = 99 # Made up type
    unsupported_media.caption_text = "Unsupported"

    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[unsupported_media],
            collection_name=collection_name,
            download_dir=download_dir
        )

    assert result is True # Metadata saving succeeds (empty list)
    mock_instagrapi_client.video_download.assert_not_called()
    mock_instagrapi_client.photo_download.assert_not_called()
    # Metadata should be empty
    mock_json_dump.assert_called_once_with(
        [], mock_open().__enter__(), indent=4, ensure_ascii=False
    )


def test_download_client_error_on_photo_download(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of ClientError during photo download."""
    download_dir = tmp_path / "downloads"
    photo_item = [m for m in mock_media_items if m.media_type == 1] # Just the photo

    mock_instagrapi_client.photo_download.side_effect = ClientError("Download forbidden")

    # Patch open and json.dump for metadata verification
    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=photo_item,
            collection_name=collection_name,
            download_dir=download_dir
        )
        # Assertions using mocks inside the 'with' block
        expected_metadata = [{
            "relative_path": None, "caption": "This is a photo", "url": "https://www.instagram.com/p/CPhoto1/",
            "pk": 222, "media_type": 1, "product_type": "feed"
        }]
        mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)

    # Assertions outside the 'with' block
    captured = capsys.readouterr()
    assert result is True # Metadata saving should still succeed
    mock_instagrapi_client.photo_download.assert_called_once_with(222, folder=download_dir / collection_name)
    assert "API Error downloading photo: Download forbidden" in captured.out


def test_download_unexpected_error_on_video_download(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of unexpected Exception during video download."""
    download_dir = tmp_path / "downloads"
    video_item = [m for m in mock_media_items if m.pk == 111]

    mock_instagrapi_client.video_download.side_effect = Exception("Network timeout")

    # Patch open and json.dump
    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=video_item,
            collection_name=collection_name,
            download_dir=download_dir
        )
        # Assertions using mocks inside the 'with' block
        expected_metadata = [{
            "relative_path": None, "caption": "This is a cool video", "url": "https://www.instagram.com/p/CVideo1/",
            "pk": 111, "media_type": 2, "product_type": "feed"
        }]
        mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)

    # Assertions outside the 'with' block
    captured = capsys.readouterr()
    assert result is True # Metadata saving should still succeed
    mock_instagrapi_client.video_download.assert_called_once_with(111, folder=download_dir / collection_name)
    assert "Unexpected Error downloading video: Network timeout" in captured.out


def test_download_mkdir_error(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker, capsys):
    """Test handling of OSError when creating the main collection directory."""
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
    mock_instagrapi_client.photo_download.assert_not_called()
    assert f"Error: Could not create directory {download_dir / collection_name}" in captured.out

def test_download_metadata_save_io_error(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of IOError when saving metadata."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    # Let downloads succeed (or be skipped)
    mock_instagrapi_client.video_download.return_value = collection_dir / "video.mp4"
    mock_instagrapi_client.photo_download.return_value = collection_dir / "photo.jpg"

    # Patch open to raise IOError during metadata save
    with patch("builtins.open", side_effect=IOError("Disk full")) as mock_open:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=mock_media_items, # Use all items
            collection_name=collection_name,
            download_dir=download_dir
        )
    captured = capsys.readouterr()

    assert result is False
    # Check it attempted to open the metadata file
    mock_open.assert_called_once_with(collection_dir / "metadata.json", "w", encoding="utf-8")
    assert f"Error: Could not save metadata file {collection_dir / 'metadata.json'}" in captured.out

def test_download_metadata_save_type_error(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, capsys):
    """Test handling of TypeError during JSON serialization."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    # Let downloads succeed (or be skipped)
    mock_instagrapi_client.video_download.return_value = collection_dir / "video.mp4"
    mock_instagrapi_client.photo_download.return_value = collection_dir / "photo.jpg"

    # Patch json.dump to raise TypeError
    with patch("builtins.open", MagicMock()), \
         patch("json.dump", side_effect=TypeError("Cannot serialize object")) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=mock_media_items, # Use all items
            collection_name=collection_name,
            download_dir=download_dir
        )
    captured = capsys.readouterr()

    assert result is False
    mock_json_dump.assert_called_once() # Check it was called
    assert "Error: Could not serialize metadata to JSON: Cannot serialize object" in captured.out


# --- Tests for Skip Existing Logic ---

def test_download_skip_existing_video_file(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test skipping download if a video file with the PK prefix already exists."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    video_item = next(m for m in mock_media_items if m.pk == 111)
    existing_file_name = f"{video_item.pk}_existing_video.mp4"
    existing_file_path = collection_dir / existing_file_name

    # Mock Path.glob to find the existing file
    mocker.patch('pathlib.Path.glob', return_value=[existing_file_path])
    collection_dir.mkdir(parents=True, exist_ok=True)

    # Patch open and json.dump for metadata verification
    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:

        # Call the function
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[video_item],
            collection_name=collection_name,
            download_dir=download_dir
        )

    # Assertions
    assert result is True # Metadata saving should still succeed
    mock_instagrapi_client.video_download.assert_not_called() # Download skipped
    Path.glob.assert_called_once_with(f"{video_item.pk}*.mp4") # Check glob pattern

    # Check metadata reflects the existing file
    expected_metadata = [{
        "relative_path": existing_file_name, "caption": video_item.caption_text,
        "url": f"https://www.instagram.com/p/{video_item.code}/", "pk": video_item.pk,
        "media_type": video_item.media_type, "product_type": video_item.product_type,
    }]
    mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)


def test_download_skip_existing_photo_file(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test skipping download if a photo file with the PK prefix already exists."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    photo_item = next(m for m in mock_media_items if m.pk == 222)
    existing_file_name = f"{photo_item.pk}_existing_photo.jpg"
    existing_file_path = collection_dir / existing_file_name

    mocker.patch('pathlib.Path.glob', return_value=[existing_file_path])
    collection_dir.mkdir(parents=True, exist_ok=True)

    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[photo_item],
            collection_name=collection_name,
            download_dir=download_dir
        )

    assert result is True
    mock_instagrapi_client.photo_download.assert_not_called() # Download skipped
    Path.glob.assert_called_once_with(f"{photo_item.pk}*.jpg") # Check glob pattern

    expected_metadata = [{
        "relative_path": existing_file_name, "caption": photo_item.caption_text,
        "url": f"https://www.instagram.com/p/{photo_item.code}/", "pk": photo_item.pk,
        "media_type": photo_item.media_type, "product_type": photo_item.product_type,
    }]
    mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)


def test_download_skip_existing_carousel_subdir(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test skipping download if a carousel subdirectory already exists and is not empty."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    carousel_item = next(m for m in mock_media_items if m.pk == 888)
    carousel_subdir = collection_dir / str(carousel_item.pk)

    # Patch Path.exists and Path.iterdir globally with side effects again
    # The side_effect function needs to accept the instance argument (self)
    def exists_side_effect(instance_self): # Rename arg to avoid clash
        if instance_self == carousel_subdir:
            return True # Simulate subdir exists
        # Fallback to original behavior or a default False if needed elsewhere
        # For simplicity here, assume we only care about the carousel_subdir check
        # Need to handle the case where the original method might be called on other paths
        # A more robust mock might call the original method for other paths
        # but for this test, returning False might suffice if no other paths are checked.
        original_exists = getattr(Path, '__original_exists__', Path.exists) # Store original if not already done
        if not hasattr(Path, '__original_exists__'): setattr(Path, '__original_exists__', Path.exists)
        # Avoid infinite recursion if original_exists is already the mock
        if original_exists.__name__ == 'exists_side_effect': return False
        # return original_exists(instance_self) # This causes issues in test teardown
        return False # Simplified fallback


    def iterdir_side_effect(instance_self): # Rename arg
        if instance_self == carousel_subdir:
            return iter([carousel_subdir / "dummy_file.jpg"]) # Simulate non-empty, return iterator
        return iter([]) # Default empty iterator

    # Use mocker.patch correctly
    mock_exists = mocker.patch('pathlib.Path.exists', side_effect=exists_side_effect, autospec=True)
    mock_iterdir = mocker.patch('pathlib.Path.iterdir', side_effect=iterdir_side_effect, autospec=True)


    collection_dir.mkdir(parents=True, exist_ok=True) # Ensure base dir exists

    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[carousel_item],
            collection_name=collection_name,
            download_dir=download_dir
        )

    assert result is True
    # No download functions should be called for resources
    mock_instagrapi_client.photo_download.assert_not_called()
    mock_instagrapi_client.video_download.assert_not_called()
    # Check exists and iterdir were called, specifically for the carousel_subdir
    # Check the call args on the globally patched methods
    exists_called_for_subdir = any(call.args[0] == carousel_subdir for call in mock_exists.call_args_list)
    iterdir_called_for_subdir = any(call.args[0] == carousel_subdir for call in mock_iterdir.call_args_list)
    assert exists_called_for_subdir
    assert iterdir_called_for_subdir


    # Check metadata reflects the existing subdir path
    expected_metadata = [{
        "relative_path": f"{carousel_item.pk}/", "caption": carousel_item.caption_text,
        "url": f"https://www.instagram.com/p/{carousel_item.code}/", "pk": carousel_item.pk,
        "media_type": carousel_item.media_type, "product_type": carousel_item.product_type,
    }]
    mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)


def test_download_skip_existing_carousel_resource(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test skipping download of an individual resource within a carousel if it exists."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    carousel_item = next(m for m in mock_media_items if m.pk == 888)
    carousel_subdir = collection_dir / str(carousel_item.pk)
    existing_resource_pk = carousel_item.resources[0].pk # The photo resource
    existing_resource_path = carousel_subdir / f"{existing_resource_pk}_existing.jpg"

    # Mock exists/iterdir for the main subdir check (return False/empty to proceed)
    mocker.patch.object(Path, 'exists', return_value=False)
    mocker.patch.object(Path, 'iterdir', return_value=[])

    # Mock glob for resource checks: find the first resource, not the second
    def glob_side_effect(pattern):
        if f"{existing_resource_pk}" in pattern:
            return [existing_resource_path] # Found existing photo resource
        else:
            return [] # Did not find video resource
    mocker.patch('pathlib.Path.glob', side_effect=glob_side_effect)

    # Mock the video download for the second resource
    expected_video_resource_path = carousel_subdir / f"{carousel_item.resources[1].pk}_new.mp4"
    mock_instagrapi_client.video_download.return_value = expected_video_resource_path

    collection_dir.mkdir(parents=True, exist_ok=True) # Ensure base dir exists

    with patch("builtins.open", MagicMock()), patch("json.dump", MagicMock()):
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[carousel_item],
            collection_name=collection_name,
            download_dir=download_dir
        )

    assert result is True
    # Photo resource download should NOT be called
    mock_instagrapi_client.photo_download.assert_not_called()
    # Video resource download SHOULD be called
    mock_instagrapi_client.video_download.assert_called_once_with(
        carousel_item.resources[1].pk, folder=carousel_subdir
    )
    # Check glob calls for resources
    assert Path.glob.call_count == 2 # Called for each resource inside the loop
    Path.glob.assert_has_calls([
        call(f"{carousel_item.resources[0].pk}*"),
        call(f"{carousel_item.resources[1].pk}*"),
    ], any_order=True)


def test_download_existing_file_with_skip_download_flag(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test existing file check takes precedence over skip_download flag for metadata (using video)."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    video_item = next(m for m in mock_media_items if m.pk == 111)
    existing_file_name = f"{video_item.pk}_another_existing.mp4"
    existing_file_path = collection_dir / existing_file_name

    mocker.patch('pathlib.Path.glob', return_value=[existing_file_path])
    collection_dir.mkdir(parents=True, exist_ok=True)

    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[video_item],
            collection_name=collection_name,
            download_dir=download_dir,
            skip_download=True # Explicitly set skip flag
        )

    assert result is True
    mock_instagrapi_client.video_download.assert_not_called()
    Path.glob.assert_called_once_with(f"{video_item.pk}*.mp4")

    expected_metadata = [{
        "relative_path": existing_file_name, # Existing filename takes precedence
        "caption": video_item.caption_text,
        "url": f"https://www.instagram.com/p/{video_item.code}/", "pk": video_item.pk,
        "media_type": video_item.media_type, "product_type": video_item.product_type,
    }]
    mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)


def test_download_no_existing_file_proceeds(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test download proceeds normally if no existing file is found (using photo)."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    photo_item = next(m for m in mock_media_items if m.pk == 222)
    expected_download_path = collection_dir / f"{photo_item.pk}_new_download.jpg"

    mocker.patch('pathlib.Path.glob', return_value=[]) # No existing file
    collection_dir.mkdir(parents=True, exist_ok=True)
    mock_instagrapi_client.photo_download.return_value = expected_download_path # Mock successful download

    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[photo_item],
            collection_name=collection_name,
            download_dir=download_dir
        )

    assert result is True
    Path.glob.assert_called_once_with(f"{photo_item.pk}*.jpg")
    mock_instagrapi_client.photo_download.assert_called_once_with(photo_item.pk, folder=collection_dir) # Download called

    expected_metadata = [{
        "relative_path": expected_download_path.name, # Name of the new file
        "caption": photo_item.caption_text,
        "url": f"https://www.instagram.com/p/{photo_item.code}/", "pk": photo_item.pk,
        "media_type": photo_item.media_type, "product_type": photo_item.product_type,
    }]
    mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)


# --- Additional Carousel Tests ---

def test_download_carousel_empty_resources(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker):
    """Test handling of a carousel item with an empty resources list."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    carousel_item = next(m for m in mock_media_items if m.pk == 888)
    carousel_item.resources = [] # Make resources empty
    carousel_subdir = collection_dir / str(carousel_item.pk)

    # Remove mocks for exists/iterdir - let mkdir happen in the function
    mocker.patch('pathlib.Path.glob', return_value=[]) # No existing resources

    collection_dir.mkdir(parents=True, exist_ok=True) # Create the base collection dir

    with patch("builtins.open", MagicMock()) as mock_open, \
         patch("json.dump", MagicMock()) as mock_json_dump:
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[carousel_item],
            collection_name=collection_name,
            download_dir=download_dir
        )

    assert result is True
    assert carousel_subdir.exists() # Subdir should still be created
    # No download calls should happen
    mock_instagrapi_client.photo_download.assert_not_called()
    mock_instagrapi_client.video_download.assert_not_called()

    # Check metadata reflects the subdir path
    expected_metadata = [{
        "relative_path": f"{carousel_item.pk}/", "caption": carousel_item.caption_text,
        "url": f"https://www.instagram.com/p/{carousel_item.code}/", "pk": carousel_item.pk,
        "media_type": carousel_item.media_type, "product_type": carousel_item.product_type,
    }]
    mock_json_dump.assert_called_once_with(expected_metadata, mock_open().__enter__(), indent=4, ensure_ascii=False)


def test_download_carousel_resource_download_error(mock_instagrapi_client, mock_media_items, collection_name, tmp_path, mocker, capsys):
    """Test handling of an error during a carousel resource download."""
    download_dir = tmp_path / "downloads"
    collection_dir = download_dir / collection_name
    carousel_item = next(m for m in mock_media_items if m.pk == 888)
    carousel_subdir = collection_dir / str(carousel_item.pk)

    # Remove mocks for exists/iterdir - let mkdir happen in the function
    mocker.patch('pathlib.Path.glob', return_value=[]) # No existing resources

    # Make the first resource (photo) download fail
    mock_instagrapi_client.photo_download.side_effect = ClientError("Resource download failed")
    # Let the second resource (video) succeed
    expected_video_resource_path = carousel_subdir / f"{carousel_item.resources[1].pk}_new.mp4"
    mock_instagrapi_client.video_download.return_value = expected_video_resource_path

    collection_dir.mkdir(parents=True, exist_ok=True)

    with patch("builtins.open", MagicMock()), patch("json.dump", MagicMock()):
        result = download_collection_media(
            client=mock_instagrapi_client,
            media_items=[carousel_item],
            collection_name=collection_name,
            download_dir=download_dir
        )
    captured = capsys.readouterr()

    assert result is True # Overall metadata save should still succeed
    assert carousel_subdir.exists()
    # Check photo download was attempted and failed
    mock_instagrapi_client.photo_download.assert_called_once_with(
        carousel_item.resources[0].pk, folder=carousel_subdir
    )
    assert f"API Error downloading resource 1/{len(carousel_item.resources)}" in captured.out
    # Check video download was attempted and succeeded
    mock_instagrapi_client.video_download.assert_called_once_with(
        carousel_item.resources[1].pk, folder=carousel_subdir
    )
    assert f"Downloaded video resource 2/{len(carousel_item.resources)}" in captured.out
