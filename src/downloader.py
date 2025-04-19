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
    skipped_exists_count = 0 # Counter for already existing files/resources
    skipped_type_count = 0 # Counter for unsupported media types (should be 0 now)
    downloaded_video_count = 0
    downloaded_photo_count = 0
    downloaded_carousel_resource_count = 0
    metadata_only_count = 0 # Counter for --skip-download flag
    error_count = 0 # Counter for errors

    print(f"Processing {total_items} items for collection '{collection_name}'...")

    for index, media in enumerate(media_items):
        print(f"  [{index + 1}/{total_items}] Processing item PK: {media.pk} (Type: {media.media_type})...", end=" ")

        # --- Metadata Collection (Common Fields) ---
        post_url = f"https://www.instagram.com/p/{media.code}/"
        caption = media.caption_text or ""
        post_url = f"https://www.instagram.com/p/{media.code}/"
        caption = media.caption_text or ""
        relative_path_str: str | None = None # Holds filename or subdir path
        already_exists = False # Flag for top-level file/dir existence

        item_metadata = {
            "relative_path": None, # Initialize, will be updated
            "caption": caption,
            "url": post_url,
            "pk": media.pk,
            "media_type": media.media_type,
            "product_type": media.product_type,
        }

        # --- Handle based on Media Type ---

        if media.media_type == 1: # Photo
            # Check if photo file already exists
            existing_files = list(collection_dir.glob(f"{media.pk}*.jpg")) # Assume jpg for photos
            if existing_files:
                already_exists = True
                found_path = existing_files[0]
                relative_path_str = found_path.name
                item_metadata["relative_path"] = relative_path_str
                skipped_exists_count += 1
                print(f"Skipped (photo already exists: {relative_path_str}).")
                logger.info(f"Skipping photo download for PK {media.pk}, file already exists: {found_path}")
            elif not skip_download:
                try:
                    logger.info(f"Attempting to download photo for media PK: {media.pk}")
                    download_path = client.photo_download(media.pk, folder=collection_dir)
                    if download_path:
                        filename = download_path.name
                        relative_path_str = filename
                        item_metadata["relative_path"] = relative_path_str
                        downloaded_photo_count += 1
                        print(f"Downloaded photo. Filename: {relative_path_str}")
                        logger.info(f"Successfully downloaded photo PK {media.pk} to {download_path}. Storing filename: {relative_path_str}")
                    else:
                        print("Photo download failed (no path returned).")
                        logger.warning(f"Photo download for PK {media.pk} returned no path.")
                        error_count += 1
                except ClientError as e:
                    print(f"API Error downloading photo: {e}")
                    logger.error(f"ClientError downloading photo PK {media.pk}: {e}")
                    error_count += 1
                except Exception as e:
                    print(f"Unexpected Error downloading photo: {e}")
                    logger.exception(f"Unexpected error downloading photo PK {media.pk}: {e}", exc_info=True)
                    error_count += 1
            else: # Skip download flag is True
                print("Skipped photo download (metadata only).")
                logger.info(f"Skipping photo download for media PK: {media.pk} due to --skip-download flag.")
                metadata_only_count += 1

        elif media.media_type == 2: # Video
            # Check if video file already exists
            existing_files = list(collection_dir.glob(f"{media.pk}*.mp4")) # Assume mp4 for videos
            if existing_files:
                already_exists = True
                found_path = existing_files[0]
                relative_path_str = found_path.name
                item_metadata["relative_path"] = relative_path_str
                skipped_exists_count += 1
                print(f"Skipped (video already exists: {relative_path_str}).")
                logger.info(f"Skipping video download for PK {media.pk}, file already exists: {found_path}")
            elif not skip_download:
                try:
                    logger.info(f"Attempting to download video for media PK: {media.pk}")
                    download_path = client.video_download(media.pk, folder=collection_dir)
                    if download_path:
                        filename = download_path.name
                        relative_path_str = filename
                        item_metadata["relative_path"] = relative_path_str
                        downloaded_video_count += 1
                        print(f"Downloaded video. Filename: {relative_path_str}")
                        logger.info(f"Successfully downloaded video PK {media.pk} to {download_path}. Storing filename: {relative_path_str}")
                    else:
                        print("Video download failed (no path returned).")
                        logger.warning(f"Video download for PK {media.pk} returned no path.")
                        error_count += 1
                except ClientError as e:
                    print(f"API Error downloading video: {e}")
                    logger.error(f"ClientError downloading video PK {media.pk}: {e}")
                    error_count += 1
                except Exception as e:
                    print(f"Unexpected Error downloading video: {e}")
                    logger.exception(f"Unexpected error downloading video PK {media.pk}: {e}", exc_info=True)
                    error_count += 1
            else: # Skip download flag is True
                print("Skipped video download (metadata only).")
                logger.info(f"Skipping video download for media PK: {media.pk} due to --skip-download flag.")
                metadata_only_count += 1

        elif media.media_type == 8: # Carousel (Album)
            carousel_subdir_name = str(media.pk)
            carousel_subdir = collection_dir / carousel_subdir_name
            relative_path_str = f"{carousel_subdir_name}/" # Store subdir path
            item_metadata["relative_path"] = relative_path_str # Store relative subdir path

            # Check if subdirectory exists (as proxy for 'already processed')
            if carousel_subdir.exists() and any(carousel_subdir.iterdir()):
                 already_exists = True
                 skipped_exists_count += 1 # Count the whole carousel as skipped
                 print(f"Skipped (carousel subdir exists: {relative_path_str}).")
                 logger.info(f"Skipping carousel download for PK {media.pk}, subdir already exists: {carousel_subdir}")
            elif not skip_download:
                try:
                    carousel_subdir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created subdirectory for carousel PK {media.pk}: {carousel_subdir}")
                    print(f"Created subdir {relative_path_str}. Downloading resources...")

                    if not media.resources:
                         print("Warning: Carousel has no resources listed.")
                         logger.warning(f"Carousel PK {media.pk} has no resources.")

                    for res_index, resource in enumerate(media.resources):
                        res_pk = resource.pk
                        res_type = resource.media_type
                        res_target_path = None
                        res_exists = False

                        # Check if resource file exists within the carousel subdir
                        existing_res_files = list(carousel_subdir.glob(f"{res_pk}*"))
                        if existing_res_files:
                            res_exists = True
                            skipped_exists_count += 1 # Count skipped resources too
                            print(f"  - Resource {res_index+1}/{len(media.resources)} (PK: {res_pk}) skipped (already exists).")
                            logger.info(f"Skipping resource PK {res_pk} in carousel {media.pk}, file exists: {existing_res_files[0]}")
                            continue # Skip to next resource

                        # Download resource if it doesn't exist
                        try:
                            if res_type == 1: # Photo resource
                                logger.debug(f"Attempting photo download for resource PK {res_pk} in carousel {media.pk}")
                                res_target_path = client.photo_download(res_pk, folder=carousel_subdir)
                                if res_target_path:
                                    downloaded_carousel_resource_count += 1
                                    print(f"  - Downloaded photo resource {res_index+1}/{len(media.resources)} (PK: {res_pk}). Filename: {res_target_path.name}")
                                    logger.debug(f"Successfully downloaded photo resource PK {res_pk} to {res_target_path}")
                                else:
                                    error_count += 1
                                    print(f"  - Failed photo resource {res_index+1}/{len(media.resources)} (PK: {res_pk}) download (no path).")
                                    logger.warning(f"Photo resource download for PK {res_pk} in carousel {media.pk} returned no path.")
                            elif res_type == 2: # Video resource
                                logger.debug(f"Attempting video download for resource PK {res_pk} in carousel {media.pk}")
                                res_target_path = client.video_download(res_pk, folder=carousel_subdir)
                                if res_target_path:
                                    downloaded_carousel_resource_count += 1
                                    print(f"  - Downloaded video resource {res_index+1}/{len(media.resources)} (PK: {res_pk}). Filename: {res_target_path.name}")
                                    logger.debug(f"Successfully downloaded video resource PK {res_pk} to {res_target_path}")
                                else:
                                    error_count += 1
                                    print(f"  - Failed video resource {res_index+1}/{len(media.resources)} (PK: {res_pk}) download (no path).")
                                    logger.warning(f"Video resource download for PK {res_pk} in carousel {media.pk} returned no path.")
                            else:
                                print(f"  - Skipped unknown resource type {res_type} (PK: {res_pk}).")
                                logger.warning(f"Unknown resource type {res_type} for PK {res_pk} in carousel {media.pk}")
                                skipped_type_count += 1 # Count unknown resource types

                        except ClientError as e_res:
                            error_count += 1
                            print(f"  - API Error downloading resource {res_index+1}/{len(media.resources)} (PK: {res_pk}): {e_res}")
                            logger.error(f"ClientError downloading resource PK {res_pk} in carousel {media.pk}: {e_res}")
                        except Exception as e_res:
                            error_count += 1
                            print(f"  - Unexpected Error downloading resource {res_index+1}/{len(media.resources)} (PK: {res_pk}): {e_res}")
                            logger.exception(f"Unexpected error downloading resource PK {res_pk} in carousel {media.pk}: {e_res}", exc_info=True)

                except OSError as e:
                    print(f"Error creating carousel subdirectory {carousel_subdir}: {e}")
                    logger.error(f"Failed to create carousel subdirectory {carousel_subdir}: {e}")
                    error_count += 1 # Count failure to create subdir as an error
                    # Ensure relative_path is None if subdir creation failed
                    item_metadata["relative_path"] = None
                except Exception as e: # Catch other potential errors during carousel setup
                    print(f"Unexpected Error processing carousel PK {media.pk}: {e}")
                    logger.exception(f"Unexpected error processing carousel PK {media.pk}: {e}", exc_info=True)
                    error_count += 1
                    item_metadata["relative_path"] = None # Ensure path is None on error
            else: # Skip download flag is True for carousel
                print(f"Skipped carousel download (metadata only, created subdir: {relative_path_str}).")
                # Still create the subdir for consistency, even if skipping downloads
                try:
                    carousel_subdir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created carousel subdirectory {carousel_subdir} for PK {media.pk} (skipped download).")
                except OSError as e:
                     print(f"Warning: Could not create carousel subdirectory {carousel_subdir} while skipping download: {e}")
                     logger.warning(f"Could not create carousel subdirectory {carousel_subdir} for PK {media.pk} while skipping download: {e}")
                     item_metadata["relative_path"] = None # Set path to None if subdir fails
                metadata_only_count += 1 # Count the main carousel item as skipped

        else: # Unknown media type
            print(f"Skipped (unsupported media type: {media.media_type}).")
            logger.warning(f"Skipping media PK {media.pk} due to unsupported type: {media.media_type}")
            skipped_type_count += 1
            # Don't add metadata for unsupported types
            continue # Skip appending metadata for this item

        # Append metadata for processed types (photo, video, carousel)
        metadata_list.append(item_metadata)

    print(f"\nCollection Summary for '{collection_name}':")
    print(f"  Downloaded Videos:       {downloaded_video_count}")
    print(f"  Downloaded Photos:       {downloaded_photo_count}")
    print(f"  Downloaded Carousel Res: {downloaded_carousel_resource_count}")
    print(f"  Skipped (already exists):{skipped_exists_count} (includes items/resources)")
    print(f"  Skipped (--skip-download):{metadata_only_count}")
    print(f"  Skipped (unsupported):   {skipped_type_count}")
    print(f"  Errors:                  {error_count}")

    # Save metadata (only includes processed types)
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
