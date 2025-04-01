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
    download_dir: Path, # Added download_dir argument
) -> bool:
    """
    Downloads video media items from a list to a specific collection folder
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
    skipped_count = 0

    print(f"Processing {total_items} items for collection '{collection_name}'...")

    for index, media in enumerate(media_items):
        print(f"  [{index + 1}/{total_items}] Processing item PK: {media.pk}...", end=" ")

        # Only download videos (media_type=2 includes videos, reels, IGTV)
        if media.media_type != 2:
            print("Skipped (not a video).")
            skipped_count += 1
            continue

        try:
            logger.info(f"Attempting to download video for media PK: {media.pk}")
            # Use video_download as it should handle reels/igtv too
            download_path = client.video_download(media.pk, folder=collection_dir)

            if download_path:
                # Calculate relative path based on the *parent* of the provided download_dir
                # This assumes download_dir is relative to the project root (e.g., "downloads")
                # If download_dir is absolute, this might need adjustment, but for CLI args, relative is typical.
                relative_path_base = download_dir.parent
                relative_path = download_path.relative_to(relative_path_base)
                post_url = f"https://www.instagram.com/p/{media.code}/"
                caption = media.caption_text or ""

                metadata_list.append({
                    "relative_path": str(relative_path),
                    "caption": caption,
                    "url": post_url,
                    "pk": media.pk,
                    "media_type": media.media_type,
                    "product_type": media.product_type,
                })
                download_count += 1
                print(f"Downloaded to {relative_path}")
                logger.info(f"Successfully downloaded video PK {media.pk} to {download_path}")
            else:
                print("Download failed (no path returned).")
                logger.warning(f"Video download for PK {media.pk} returned no path.")
                skipped_count += 1

        except ClientError as e:
            print(f"API Error downloading: {e}")
            logger.error(f"ClientError downloading video PK {media.pk}: {e}")
            skipped_count += 1
        except Exception as e:
            print(f"Unexpected Error downloading: {e}")
            logger.exception(f"Unexpected error downloading video PK {media.pk}: {e}", exc_info=True)
            skipped_count += 1

    print(f"\nDownload Summary for '{collection_name}':")
    print(f"  Successfully downloaded: {download_count}")
    print(f"  Skipped/Errors:        {skipped_count}")

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

# Example usage (for testing purposes, can be removed later)
if __name__ == "__main__":
    # This part requires a logged-in client and media_items,
    # which are typically obtained from instagram_client.py
    print("Downloader module - run reel_scout_cli.py for actual use.")
    # Example structure (won't run without client/media):
    # from instagram_client import InstagramClient
    # logging.basicConfig(level=logging.INFO)
    # insta_client = InstagramClient()
    # if insta_client.login():
    #     # Assume we got collections and selected one
    #     collection_pk_to_test = 123456789 # Replace with a real PK if testing
    #     collection_name_to_test = "Test Collection" # Replace
    #     media = insta_client.get_media_from_collection(collection_pk_to_test)
    #     if media:
    #         download_collection_media(insta_client.client, media, collection_name_to_test)
