import logging
from pathlib import Path
from typing import List, Optional

from instagrapi import Client
from instagrapi.exceptions import ClientError, LoginRequired
from instagrapi.types import Collection, Media

# SESSION_FILE = Path("auth/session") # Removed - will be passed via CLI
DOWNLOADS_DIR = Path("downloads") # Keep this for now, downloader uses it

logger = logging.getLogger(__name__)

class InstagramClient:
    """Handles interactions with the Instagram API via instagrapi."""

    def __init__(self, session_file: Path): # Removed default value
        self.client = Client()
        self.session_file = session_file
        self.logged_in = False

    def login(self) -> bool:
        """
        Logs in to Instagram using the session file.
        Returns True if login is successful, False otherwise.
        """
        if not self.session_file.exists():
            logger.error(f"Session file not found: {self.session_file}")
            print(f"Error: Session file not found at {self.session_file}")
            print("Please ensure you have logged in previously or run an initial login script.")
            return False

        try:
            logger.info(f"Attempting to load session from {self.session_file}")
            self.client.load_settings(self.session_file)
            logger.info("Session loaded successfully. Verifying session...")

            # Verify the session by making a simple API call
            # Using account_info() as it's a basic check
            self.client.account_info()
            self.logged_in = True
            logger.info("Session verified. Login successful.")
            print("Login successful using session file.")
            return True

        except FileNotFoundError:
            logger.error(f"Session file disappeared unexpectedly: {self.session_file}")
            print(f"Error: Session file not found at {self.session_file}")
            return False
        except (LoginRequired, ClientError) as e:
            logger.error(f"Session is invalid or expired: {e}")
            print(f"Error: Session is invalid or expired. Please refresh your session file. Details: {e}")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred during session login: {e}", exc_info=True)
            print(f"An unexpected error occurred during login: {e}")
            return False

    def get_collections(self) -> Optional[List[Collection]]:
        """Fetches all saved media collections for the logged-in user."""
        if not self.logged_in:
            logger.warning("Attempted to get collections without being logged in.")
            print("Error: Not logged in.")
            return None
        try:
            logger.info("Fetching collections...")
            collections = self.client.collections()
            logger.info(f"Found {len(collections)} collections.")
            return collections
        except (LoginRequired, ClientError) as e:
            logger.error(f"Login required or client error while fetching collections: {e}")
            print(f"Error fetching collections (login may have expired): {e}")
            self.logged_in = False
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred fetching collections: {e}", exc_info=True)
            print(f"An unexpected error occurred fetching collections: {e}")
            return None

    def get_media_from_collection(self, collection_pk: int) -> Optional[List[Media]]:
        """Fetches all media items within a specific collection."""
        if not self.logged_in:
            logger.warning("Attempted to get media from collection without being logged in.")
            print("Error: Not logged in.")
            return None
        try:
            logger.info(f"Fetching media for collection PK: {collection_pk}")
            # amount=0 fetches all media
            medias = self.client.collection_medias(collection_pk, amount=0)
            logger.info(f"Found {len(medias)} media items in collection {collection_pk}.")
            return medias
        except (LoginRequired, ClientError) as e:
            logger.error(f"Login required or client error while fetching media: {e}")
            print(f"Error fetching media (login may have expired): {e}")
            self.logged_in = False
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred fetching media: {e}", exc_info=True)
            print(f"An unexpected error occurred fetching media: {e}")
            return None

# Example usage (for testing purposes, can be removed later)
# Note: This example block will no longer run directly without providing a session file path.
# if __name__ == "__main__":
#     import argparse
#     parser = argparse.ArgumentParser(description="Test InstagramClient login and collection fetching.")
#     parser.add_argument("--session", type=Path, default=Path("auth/session"), help="Path to the session file.")
#     args = parser.parse_args()

#     logging.basicConfig(level=logging.INFO)

#     insta_client = InstagramClient(session_file=args.session)
#     if insta_client.login():
#         collections = insta_client.get_collections()
#         if collections:
#             print("\nAvailable Collections:")
#             for i, coll in enumerate(collections):
#                 print(f"{i + 1}. {coll.name} (ID: {coll.pk})")

#             if collections:
#                 choice = input(f"Enter the number of the collection to fetch (1-{len(collections)}): ")
#                 try:
#                     index = int(choice) - 1
#                     if 0 <= index < len(collections):
#                         selected_collection = collections[index]
#                         print(f"\nFetching media for '{selected_collection.name}'...")
#                         media_items = insta_client.get_media_from_collection(selected_collection.pk)
#                         if media_items:
#                             print(f"Successfully fetched {len(media_items)} items.")
#                             # Further processing would happen here
#                         else:
#                             print("Could not fetch media items.")
#                     else:
#                         print("Invalid choice.")
#                 except ValueError:
#                     print("Invalid input. Please enter a number.")
#             else:
#                 print("No collections found.")
            print("\nAvailable Collections:")
            for i, coll in enumerate(collections):
                print(f"{i + 1}. {coll.name} (ID: {coll.pk})")

            if collections:
                choice = input(f"Enter the number of the collection to fetch (1-{len(collections)}): ")
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(collections):
                        selected_collection = collections[index]
                        print(f"\nFetching media for '{selected_collection.name}'...")
                        media_items = insta_client.get_media_from_collection(selected_collection.pk)
                        if media_items:
                            print(f"Successfully fetched {len(media_items)} items.")
                            # Further processing would happen here
                        else:
                            print("Could not fetch media items.")
                    else:
                        print("Invalid choice.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            else:
                print("No collections found.")
