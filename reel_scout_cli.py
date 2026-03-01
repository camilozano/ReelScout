import click
import logging
import sys
from pathlib import Path
from src.instagram_client import InstagramClient
from src.downloader import download_collection_media
from src.pipeline import run_analyze_pipeline

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

    try:
        summary = run_analyze_pipeline(
            collection_name=collection_name,
            download_dir=download_dir.resolve(),
        )
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during analysis pipeline")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"\nTotal items: {summary['total_items']}")
    click.echo(f"Analysis errors: {summary['analysis_errors']}")
    click.echo(f"Enrichment success: {summary['enrichment_success']}")
    click.echo(f"Enrichment errors: {summary['enrichment_errors']}")
    click.echo(f"\n--- Analysis & Enrichment process completed! ---")


@cli.command('serve')
@click.option('--host', default='0.0.0.0', show_default=True, help="Host to bind to.")
@click.option('--port', default=8000, show_default=True, help="Port to listen on.")
@click.option('--reload', is_flag=True, default=False, help="Enable auto-reload (dev mode).")
def serve(host, port, reload):
    """Start the ReelScout web UI server."""
    import uvicorn
    uvicorn.run("src.api.app:app", host=host, port=port, reload=reload)


if __name__ == '__main__':
    cli()
