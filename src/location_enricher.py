import googlemaps
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file located in the auth directory
dotenv_path = Path(__file__).resolve().parent.parent / 'auth' / '.env'
load_dotenv(dotenv_path=dotenv_path)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_PLACES_API")

if not GOOGLE_MAPS_API_KEY:
    logging.error("GOOGLE_PLACES_API key not found in environment variables.")
    # Consider raising an error or handling this case appropriately
    gmaps = None
else:
    try:
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize Google Maps client: {e}")
        gmaps = None

def enrich_location_data(location_name: str) -> dict | None:
    """
    Queries the Google Maps Places API to find details for a given location name.

    Args:
        location_name: The name of the location to search for (e.g., "Eiffel Tower").

    Returns:
        A dictionary containing place details (name, address, url, place_id, lat, lng)
        if found, otherwise None.
    """
    if not gmaps:
        logging.error("Google Maps client is not initialized. Cannot enrich location.")
        return None
    if not location_name:
        logging.warning("Received empty location name for enrichment.")
        return None

    logging.info(f"Attempting to enrich location: {location_name}")
    try:
        # Use find_place to get the most likely candidate
        find_place_result = gmaps.find_place(
            input=location_name,
            input_type='textquery',
            # 'url' is not a valid field for find_place
            fields=['name', 'formatted_address', 'place_id', 'geometry/location']
        )

        if find_place_result['status'] == 'OK' and find_place_result['candidates']:
            candidate = find_place_result['candidates'][0] # Take the top candidate
            place_id = candidate.get('place_id')

            if not place_id:
                logging.warning(f"No place_id found for candidate of '{location_name}'.")
                return None

            # Now, use the place_id to get more details, including the Google Maps URI (field name 'url')
            logging.debug(f"Found place_id '{place_id}'. Fetching details...")
            place_details_result = gmaps.place(
                place_id=place_id,
                fields=['name', 'formatted_address', 'url', 'place_id', 'geometry/location'] # Request 'url' for Google Maps URI
            )

            if place_details_result['status'] == 'OK':
                place_details = place_details_result['result']
                enriched_data = {
                    'name': place_details.get('name'),
                    'address': place_details.get('formatted_address'),
                    'place_id': place_id,
                    'latitude': place_details.get('geometry', {}).get('location', {}).get('lat'),
                    'longitude': place_details.get('geometry', {}).get('location', {}).get('lng'),
                    'google_maps_uri': place_details.get('url') # Get the Google Maps URI
                }
                logging.info(f"Successfully enriched '{location_name}': {enriched_data['name']} ({enriched_data['place_id']})")
                return enriched_data
            else:
                logging.error(f"Failed to get place details for place_id '{place_id}': {place_details_result['status']}")
                # Optionally return partial data from find_place if desired, but returning None for consistency
                return None

        elif find_place_result['status'] == 'ZERO_RESULTS':
            logging.warning(f"No Google Maps results found for '{location_name}'.")
            return None
        else:
            logging.error(f"Google Maps API error for '{location_name}': {find_place_result['status']}")
            if 'error_message' in find_place_result:
                 logging.error(f"Error message: {find_place_result['error_message']}")
            return None

    except googlemaps.exceptions.ApiError as e:
        logging.error(f"Google Maps API Error during enrichment for '{location_name}': {e}")
        return None
    except googlemaps.exceptions.HTTPError as e:
         logging.error(f"Google Maps HTTP Error during enrichment for '{location_name}': {e}")
         return None
    except googlemaps.exceptions.Timeout:
        logging.error(f"Google Maps request timed out for '{location_name}'.")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during enrichment for '{location_name}': {e}", exc_info=True)
        return None

# Example usage (for testing purposes)
if __name__ == '__main__':
    test_location = "Joe's Stone Crab Miami Beach"
    details = enrich_location_data(test_location)
    if details:
        print(f"Details for {test_location}:")
        import json
        print(json.dumps(details, indent=2))
    else:
        print(f"Could not find details for {test_location}")

    test_location_invalid = "NonExistentPlace12345XYZ"
    details_invalid = enrich_location_data(test_location_invalid)
    if not details_invalid:
        print(f"Correctly handled non-existent place: {test_location_invalid}")

    # Test empty input
    details_empty = enrich_location_data("")
    if not details_empty:
        print("Correctly handled empty input.")
