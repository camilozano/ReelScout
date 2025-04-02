import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from instagrapi import Client
from instagrapi.exceptions import ClientError
from instagrapi.types import Media

# DOWNLOADS_DIR = Path("downloads") # Removed - will be passed via CLI

logger = logging.getLogger(__name__)

def download_collection_media(
    client: Client,
    media_items: List[Media],
    collection_name: str,
    download_dir: Path,
    skip_download: bool = False, # Added skip_download flag
) -> bool:
    """
    Downloads video media items (or just collects metadata) from a list
    to a specific collection folder within the specified download directory
    and saves metadata about them.

    Args:
        client: Authenticated instagrapi Client instance.
        media_items: List of Media objects to process.
        collection_name: Name of the collection (used for folder name).
        download_dir: The base directory where the collection folder should be created.
        skip_download: If True, only metadata is saved, video download is skipped.

    Returns:
        True if metadata was successfully saved, False otherwise.
    within the specified download directory and saves metadata about them.

    Args:
        client: Authenticated instagrapi Client instance.
        media_items: List of Media objects to process.
        collection_name: Name of the collection (used for folder name).
        download_dir: The base directory where the collection folder should be created.

    Returns:
        True if metadata was successfully saved, False otherwise.
    """
    # Construct the specific collection directory path using the provided base download_dir
    collection_dir = download_dir / collection_name
    try:
        collection_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured download directory exists: {collection_dir}")
    except OSError as e:
        logger.error(f"Failed to create download directory {collection_dir}: {e}")
        print(f"Error: Could not create directory {collection_dir}. Check permissions.")
        return False

    metadata_list: List[Dict[str, Any]] = []
    total_items = len(media_items)
    download_count = 0
    metadata_only_count = 0 # Counter for --skip-download flag
    skipped_exists_count = 0 # Counter for already existing files
    skipped_type_count = 0 # Counter for non-video types
    error_count = 0 # Counter for errors

    print(f"Processing {total_items} items for collection '{collection_name}'...")

    for index, media in enumerate(media_items):
        print(f"  [{index + 1}/{total_items}] Processing item PK: {media.pk}...", end=" ")

        # Only process videos (media_type=2 includes videos, reels, IGTV)
        if media.media_type != 2:
            print("Skipped (not a video).")
            skipped_type_count += 1
            continue

        # --- Metadata Collection ---
        # Always collect metadata regardless of download skip
        post_url = f"https://www.instagram.com/p/{media.code}/"
        caption = media.caption_text or ""
        # Initialize relative_path as None, update if downloaded or found existing
        relative_path_str: str | None = None
        already_exists = False # Flag to track if file already exists

        item_metadata = {
            "relative_path": relative_path_str, # Will be updated if downloaded or found
            "caption": caption,
            "url": post_url,
            "pk": media.pk,
            "media_type": media.media_type,
            "product_type": media.product_type,
        }

        # --- Check for Existing File ---
        # Check if a file starting with the PK already exists in the directory
        existing_files = list(collection_dir.glob(f"*{media.pk}*"))
        if existing_files:
            already_exists = True
            found_path = existing_files[0] # Use the first match
            relative_path_str = found_path.name
            item_metadata["relative_path"] = relative_path_str
            skipped_exists_count += 1
            print(f"Skipped (already exists: {relative_path_str}).")
            logger.info(f"Skipping download for PK {media.pk}, file already exists: {found_path}")
        # --- Conditional Download (only if not skipping and not already existing) ---
        elif not skip_download: # Note: Use elif here to avoid download attempt if already exists
            try:
                logger.info(f"Attempting to download video for media PK: {media.pk}")
                # Use video_download as it should handle reels/igtv too
                download_path = client.video_download(media.pk, folder=collection_dir)

                if download_path:
                    # Extract filename from the download path
                    try:
                        # Get only the filename
                        filename = download_path.name
                        relative_path_str = filename # Store Path object's name
                        item_metadata["relative_path"] = relative_path_str # Store filename string in metadata
                        download_count += 1
                    except Exception as e: # Catch broader exceptions just in case .name fails unexpectedly
                        # Log the error and keep relative_path as None
                        logger.error(f"Could not extract filename from path {download_path}: {e}")
                        # Keep relative_path = None (already initialized in the outer scope)
                        error_count += 1 # Count this as an error case
                        print(f"Error extracting filename for {download_path}.")
                        # The item_metadata will be added with relative_path=None

                    # Only print/log success if filename extraction succeeded
                    if relative_path_str:
                        # Update print/log messages to reflect filename storage
                        print(f"Downloaded. Filename: {relative_path_str}")
                        logger.info(f"Successfully downloaded video PK {media.pk} to {download_path}. Storing filename: {relative_path_str}")
                    # If filename extraction failed, the error is already printed/logged above
                else: # Corresponds to `if download_path:`
                    print("Download failed (no path returned).")
                    logger.warning(f"Video download for PK {media.pk} returned no path.")
                    error_count += 1

            except ClientError as e:
                print(f"API Error downloading: {e}")
                logger.error(f"ClientError downloading video PK {media.pk}: {e}")
                error_count += 1
            except Exception as e:
                print(f"Unexpected Error downloading: {e}")
                logger.exception(f"Unexpected error downloading video PK {media.pk}: {e}", exc_info=True)
                error_count += 1
        else:
            # Skip download flag is True
            print("Skipped download (metadata only).")
            logger.info(f"Skipping video download for media PK: {media.pk} due to --skip-download flag.")
            metadata_only_count += 1
        # Note: The 'already_exists' case is handled before this 'elif not skip_download' block

        # Append metadata regardless of download success/skip status
        metadata_list.append(item_metadata)

    print(f"\nCollection Summary for '{collection_name}':")
    print(f"  Successfully downloaded: {download_count}")
    print(f"  Skipped (already exists):{skipped_exists_count}")
    print(f"  Skipped (--skip-download):{metadata_only_count}")
    print(f"  Skipped (not video):     {skipped_type_count}")
    print(f"  Errors:                  {error_count}")

    # Save metadata
    metadata_file = collection_dir / "metadata.json"
    try:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata_list, f, indent=4, ensure_ascii=False)
        logger.info(f"Metadata saved successfully to {metadata_file}")
        print(f"Metadata saved to {metadata_file}")
        return True
    except IOError as e:
        logger.error(f"Failed to save metadata file {metadata_file}: {e}")
        print(f"Error: Could not save metadata file {metadata_file}.")
        return False
    except TypeError as e:
        logger.error(f"Failed to serialize metadata to JSON: {e}")
        print(f"Error: Could not serialize metadata to JSON: {e}")
        return False
