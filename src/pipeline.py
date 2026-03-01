import json
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from src.ai_analyzer import AIAnalyzer
from src.location_enricher import enrich_location_data
from src.instagram_client import InstagramClient
from src.downloader import download_collection_media

logger = logging.getLogger(__name__)


def run_analyze_pipeline(
    collection_name: str,
    download_dir: Path,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Run the full analyze+enrich pipeline for a collection.

    progress_callback signature: (phase, current, total, message)
    phase is "analyze" or "enrich".

    Returns a summary dict with keys:
        total_items, analysis_errors, enrichment_success, enrichment_errors, metadata_path
    """
    metadata_path = download_dir / collection_name / "metadata.json"

    if not metadata_path.is_file():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with open(metadata_path, "r") as f:
        metadata_items = json.load(f)

    if not metadata_items:
        return {
            "total_items": 0,
            "analysis_errors": 0,
            "enrichment_success": 0,
            "enrichment_errors": 0,
            "metadata_path": str(metadata_path),
        }

    total = len(metadata_items)
    analysis_errors = 0
    enrichment_errors = 0
    enrichment_success = 0

    try:
        analyzer = AIAnalyzer()
    except ValueError as e:
        raise RuntimeError(f"Failed to initialize AI Analyzer: {e}") from e

    # Phase 1: AI caption analysis
    for i, item in enumerate(metadata_items):
        if "caption_analysis" not in item:
            item["caption_analysis"] = {}

        caption = item.get("caption")
        if progress_callback:
            progress_callback("analyze", i, total, f"Analyzing item {i + 1}/{total}")

        if not caption:
            item["caption_analysis"].update(
                {"location_found": False, "locations": None, "error": "No caption provided"}
            )
            continue

        try:
            result = analyzer.analyze_caption_for_location(caption)
            item["caption_analysis"].update(result)
            if result.get("error"):
                analysis_errors += 1
        except Exception as e:
            logger.exception(f"Unexpected error during AI analysis for URL {item.get('url', 'N/A')}")
            item["caption_analysis"].update(
                {"location_found": False, "locations": None, "error": f"Unexpected error: {e}"}
            )
            analysis_errors += 1

    if progress_callback:
        progress_callback("analyze", total, total, "Caption analysis complete")

    # Phase 2: Google Maps enrichment
    items_to_enrich = [
        item
        for item in metadata_items
        if item.get("caption_analysis", {}).get("location_found")
    ]
    enrich_total = sum(
        len(item.get("caption_analysis", {}).get("locations") or [])
        for item in items_to_enrich
    )

    enrich_idx = 0
    for item in items_to_enrich:
        locations = item.get("caption_analysis", {}).get("locations") or []
        if not locations:
            continue

        item["google_maps_enrichment"] = []

        for loc_name in locations:
            if progress_callback:
                progress_callback(
                    "enrich", enrich_idx, enrich_total, f"Enriching: {loc_name}"
                )

            if not isinstance(loc_name, str) or not loc_name.strip():
                item["google_maps_enrichment"].append(
                    {
                        "original_name": loc_name,
                        "google_maps_data": None,
                        "error": "Invalid location name provided by AI",
                    }
                )
                enrichment_errors += 1
                enrich_idx += 1
                continue

            enriched_data = None
            error_msg = None
            try:
                enriched_data = enrich_location_data(loc_name)
                if enriched_data:
                    enrichment_success += 1
                else:
                    error_msg = "Enrichment failed or no results"
                    enrichment_errors += 1
            except Exception as e:
                logger.exception(
                    f"Unexpected error during enrichment for '{loc_name}'"
                )
                error_msg = f"Unexpected enrichment error: {e}"
                enrichment_errors += 1

            item["google_maps_enrichment"].append(
                {
                    "original_name": loc_name,
                    "google_maps_data": enriched_data,
                    "error": error_msg,
                }
            )
            enrich_idx += 1

    if progress_callback:
        progress_callback("enrich", enrich_total, enrich_total, "Enrichment complete")

    with open(metadata_path, "w") as f:
        json.dump(metadata_items, f, indent=4)

    return {
        "total_items": total,
        "analysis_errors": analysis_errors,
        "enrichment_success": enrichment_success,
        "enrichment_errors": enrichment_errors,
        "metadata_path": str(metadata_path),
    }


def run_collect_pipeline(
    collection_id: str,
    collection_name: str,
    download_dir: Path,
    session_file: Path,
    skip_download: bool = False,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Run the full collect pipeline: login → fetch → download.

    progress_callback signature: (phase, current, total, message)
    phase is "collect".

    Returns: {total_items, metadata_path}
    """
    insta_client = InstagramClient(session_file=session_file)
    if not insta_client.login():
        raise RuntimeError("Instagram login failed. Check session file.")

    if progress_callback:
        progress_callback("collect", 0, 0, "Fetching media from collection...")

    media_items = insta_client.get_media_from_collection(collection_id)
    if not media_items:
        raise RuntimeError(f"No media items found in collection '{collection_name}'")

    total = len(media_items)
    if progress_callback:
        progress_callback("collect", 0, total, f"Found {total} items. Starting download...")

    success = download_collection_media(
        client=insta_client.client,
        media_items=media_items,
        collection_name=collection_name,
        download_dir=download_dir.resolve(),
        skip_download=skip_download,
    )

    if progress_callback:
        progress_callback("collect", total, total, "Collection complete")

    if not success:
        raise RuntimeError("Download process failed")

    metadata_path = download_dir.resolve() / collection_name / "metadata.json"
    return {
        "total_items": total,
        "metadata_path": str(metadata_path),
    }
