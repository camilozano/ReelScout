import click
import logging
import sys
import json
from pathlib import Path
import time # Import time for potential delays
from src.instagram_client import InstagramClient
from src.downloader import download_collection_media
from src.ai_analyzer import AIAnalyzer # Import the class
from src.location_enricher import enrich_location_data # Import the enrichment function

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Simplified format slightly
# Suppress noisy instagrapi logging unless needed
logging.getLogger("instagrapi").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """ReelScout: Collect and analyze Instagram Reels."""
    pass

# --- Collect Command ---
@cli.command('collect')
@click.option(
    '--session-file',
    # Removed exists=True, readable=True for easier testing
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=Path("auth/session.json"),
    help="Path to the Instagram session file.",
    show_default=True,
)
@click.option(
    '--download-dir',
    # Removed writable=True for easier testing
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("downloads"),
    help="Directory to download media and metadata into.",
    show_default=True,
)
@click.option(
    '--skip-download',
    is_flag=True,
    default=False,
    help="Skip downloading video files, only save metadata.",
    show_default=True,
)
def collect_reels(session_file: Path, download_dir: Path, skip_download: bool):
    """Login, choose a collection, and download its video Reels."""
    click.echo("--- ReelScout Collection ---")
    click.echo(f"Using session file: {session_file}")
    click.echo(f"Using download directory: {download_dir}")

    # 1. Initialize and login Instagram client
    click.echo("Attempting login...")
    # Pass the session_file path from the CLI option
    insta_client = InstagramClient(session_file=session_file)
    if not insta_client.login():
        click.echo(f"Login failed using {session_file}. Please check file and logs.", err=True)
        sys.exit(1)
    click.echo("Login successful.")

    # 2. Fetch and display collections
    click.echo("Fetching your saved collections...")
    collections = insta_client.get_collections()
    if not collections:
        click.echo("Failed to fetch collections or no collections found.", err=True)
        sys.exit(1)

    click.echo("\nAvailable Collections:")
    collection_map = {str(i + 1): coll for i, coll in enumerate(collections)}
    for i, coll in enumerate(collections):
        click.echo(f"  {i + 1}. {coll.name} (ID: {coll.id})") # Changed coll.pk to coll.id

    # 3. Prompt user for collection choice
    choice = click.prompt(
        "\nEnter the number of the collection to download",
        type=click.Choice(list(collection_map.keys()))
    )
    selected_collection = collection_map[choice]
    click.echo(f"Selected collection: '{selected_collection.name}'")

    # 4. Fetch media items for the chosen collection
    click.echo(f"Fetching media items for '{selected_collection.name}'...")
    media_items = insta_client.get_media_from_collection(selected_collection.id) # Changed selected_collection.pk to selected_collection.id
    if not media_items:
        click.echo(f"Failed to fetch media or no items found in collection '{selected_collection.name}'.", err=True)
        sys.exit(1)
    click.echo(f"Found {len(media_items)} total items in the collection.")

    # 5. Download videos and save metadata
    if skip_download:
        click.echo("Starting metadata collection process (skipping video downloads)...")
    else:
        click.echo("Starting download process (only videos will be downloaded)...")
    # Resolve the download directory to an absolute path before passing
    absolute_download_dir = download_dir.resolve()
    click.echo(f"Using absolute download directory: {absolute_download_dir}") # Optional: for clarity

    # Pass the absolute download_dir and skip_download flags from the CLI options
    success = download_collection_media(
        client=insta_client.client,
        media_items=media_items,
        collection_name=selected_collection.name,
        download_dir=absolute_download_dir, # Pass the resolved path
        skip_download=skip_download # Pass the flag here
    )

    if success:
        click.echo("\n--- Collection process completed successfully! ---")
    else:
        click.echo("\n--- Collection process finished with errors. ---", err=True)
        sys.exit(1)


# --- Analyze Command ---
@cli.command('analyze')
@click.option(
    '--collection-name',
    required=True,
    type=str,
    help="Name of the collection directory (and metadata file) to analyze.",
)
@click.option(
    '--download-dir',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path, exists=True), # Ensure base dir exists
    default=Path("downloads"),
    help="Base directory where collection data is stored.",
    show_default=True,
)
def analyze_collection(collection_name: str, download_dir: Path):
    """Analyze captions in a collection's metadata.json using Gemini."""
    click.echo("--- ReelScout Analysis ---")
    click.echo(f"Analyzing collection: {collection_name}")
    click.echo(f"Using download directory: {download_dir}")

    metadata_path = download_dir.resolve() / collection_name / "metadata.json"

    if not metadata_path.is_file():
        logger.error(f"Metadata file not found: {metadata_path}")
        click.echo(f"Error: Metadata file not found at {metadata_path}", err=True)
        sys.exit(1)

    click.echo(f"Reading metadata from: {metadata_path}")
    try:
        with open(metadata_path, 'r') as f:
            metadata_items = json.load(f)
    except json.JSONDecodeError:
        logger.exception(f"Failed to decode JSON from {metadata_path}")
        click.echo(f"Error: Could not read or parse JSON from {metadata_path}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Failed to read metadata file {metadata_path}")
        click.echo(f"Error: Could not read metadata file: {e}", err=True)
        sys.exit(1)

    if not metadata_items:
        click.echo("Metadata file is empty. Nothing to analyze.")
        sys.exit(0)

    click.echo(f"Found {len(metadata_items)} items to analyze.")
    updated_items = []
    analysis_errors = 0
    enrichment_errors = 0
    enrichment_success = 0

    # Instantiate the AI Analyzer
    try:
        analyzer = AIAnalyzer()
        click.echo(f"Using AI model: {analyzer.model_name}")
    except ValueError as e:
        logger.error(f"Failed to initialize AI Analyzer: {e}")
        click.echo(f"Error initializing AI Analyzer: {e}. Ensure GEMINI_API_KEY is set.", err=True)
        sys.exit(1)

    # Analyze captions first
    click.echo("Phase 1: Analyzing captions with AI...")
    with click.progressbar(metadata_items, label='Analyzing captions') as bar:
        for item in bar:
            # Ensure 'caption_analysis' key exists, even if skipping
            if 'caption_analysis' not in item:
                 item['caption_analysis'] = {}

            caption = item.get('caption')
            if not caption:
                logger.warning(f"Item with URL {item.get('url', 'N/A')} has no caption. Skipping analysis.")
                logger.warning(f"Item with URL {item.get('url', 'N/A')} has no caption. Skipping AI analysis.")
                item['caption_analysis'].update({"location_found": False, "locations": None, "error": "No caption provided"})
                # No need to append here, we process all items later
                continue

            try:
                # Call the analysis method on the analyzer instance
                analysis_result = analyzer.analyze_caption_for_location(caption)
                # Merge analysis results into existing dict
                item['caption_analysis'].update(analysis_result)
                if analysis_result.get("error"):
                    logger.warning(f"AI Analysis error for URL {item.get('url', 'N/A')}: {analysis_result['error']}")
                    analysis_errors += 1
            except Exception as e:
                # Catch unexpected errors during the analysis call itself
                logger.exception(f"Unexpected error during AI analysis for URL {item.get('url', 'N/A')}")
                item['caption_analysis'].update({"location_found": False, "locations": None, "error": f"Unexpected AI analysis error: {str(e)}"})
                analysis_errors += 1
            # No append here, process enrichment next

    click.echo(f"\nAI Caption Analysis complete. {analysis_errors} items had AI analysis errors.")

    # Phase 2: Enrich locations using Google Maps
    click.echo("\nPhase 2: Enriching found locations with Google Maps...")
    items_to_enrich = [item for item in metadata_items if item.get('caption_analysis', {}).get('location_found')]

    if not items_to_enrich:
        click.echo("No locations found by AI analysis. Skipping Google Maps enrichment.")
    else:
        click.echo(f"Found locations in {len(items_to_enrich)} items. Starting enrichment...")
        with click.progressbar(items_to_enrich, label='Enriching locations') as bar:
            for item in bar:
                locations_to_enrich = item.get('caption_analysis', {}).get('locations', [])
                if not locations_to_enrich:
                    continue # Should not happen if location_found is True, but safety check

                item['google_maps_enrichment'] = [] # Initialize enrichment list

                for loc_name in locations_to_enrich:
                    if not isinstance(loc_name, str) or not loc_name.strip():
                        logger.warning(f"Skipping invalid location name '{loc_name}' for URL {item.get('url', 'N/A')}")
                        item['google_maps_enrichment'].append({
                            "original_name": loc_name,
                            "google_maps_data": None,
                            "error": "Invalid location name provided by AI"
                        })
                        enrichment_errors += 1
                        continue

                    enriched_data = None
                    error_msg = None
                    try:
                        # Add a small delay to avoid hitting rate limits too quickly if any
                        # time.sleep(0.1) # Optional: uncomment if rate limiting becomes an issue
                        enriched_data = enrich_location_data(loc_name)
                        if enriched_data:
                            enrichment_success += 1
                        else:
                            # enrich_location_data logs warnings/errors internally
                            error_msg = "Enrichment failed or no results"
                            enrichment_errors += 1
                    except Exception as e:
                        logger.exception(f"Unexpected error during Google Maps enrichment for '{loc_name}' (URL: {item.get('url', 'N/A')})")
                        error_msg = f"Unexpected enrichment error: {str(e)}"
                        enrichment_errors += 1

                    item['google_maps_enrichment'].append({
                        "original_name": loc_name,
                        "google_maps_data": enriched_data,
                        "error": error_msg # Store error if enrichment failed
                    })

        click.echo(f"\nGoogle Maps Enrichment complete. Successfully enriched: {enrichment_success}, Errors/Not Found: {enrichment_errors}.")

    # Save the final results (all items, including those not enriched)
    click.echo(f"\nSaving updated metadata (including enrichment) back to: {metadata_path}")
    try:
        with open(metadata_path, 'w') as f:
            # Dump the original metadata_items list, which now contains updated items
            json.dump(metadata_items, f, indent=4)
        click.echo("Metadata file updated successfully.")
    except Exception as e:
        logger.exception(f"Failed to write updated metadata to {metadata_path}")
        click.echo(f"Error: Could not write updated metadata file: {e}", err=True)
        sys.exit(1)

    click.echo("\n--- Analysis & Enrichment process completed! ---")


if __name__ == '__main__':
    cli()
