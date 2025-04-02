import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ValidationError

# Define the expected response structure using Pydantic (outside the class)
class LocationResponse(BaseModel):
    location_found: bool
    locations: Optional[List[str]]

class AIAnalyzer:
    """
    A class to handle AI analysis using the Google Gemini API.

    Attributes:
        api_key (str): The API key used for authentication.
        model_name (str): The name of the Gemini model to use.
        model (genai.GenerativeModel): The initialized Gemini model instance.
    """
    DEFAULT_MODEL_NAME = 'models/gemini-2.0-flash-lite'

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initializes the AIAnalyzer.

        Args:
            api_key: The Gemini API key. If None, attempts to load from
                     environment variable 'GEMINI_API_KEY' or 'auth/.env'.
            model_name: The name of the Gemini model to use. If None, defaults
                        to 'models/gemini-2.0-flash-lite'.

        Raises:
            ValueError: If the API key cannot be found.
        """
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                # Attempt to load from .env file if not found in environment variables
                dotenv_path = Path(__file__).parent.parent / 'auth' / '.env'
                load_dotenv(dotenv_path=dotenv_path)
                self.api_key = os.getenv("GEMINI_API_KEY")

            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found. Ensure it is set in the environment or in auth/.env file.")

        # Configure the genai library with the determined API key
        genai.configure(api_key=self.api_key)

        self.model_name = model_name if model_name else self.DEFAULT_MODEL_NAME
        self.model = genai.GenerativeModel(self.model_name)
        print(f"AIAnalyzer initialized with model: {self.model_name}") # Added for confirmation

    def analyze_caption_for_location(self, caption: str) -> Dict[str, Any]:
        """
        Analyzes a text caption using the Gemini API (with JSON mode) to find specific locations.

        Args:
            caption: The text caption to analyze.

        Returns:
            A dictionary with the analysis results, expected format:
            {
                "location_found": bool,
                "locations": Optional[List[str]]
            }
            Returns a default error structure if analysis fails.
        """
        if not caption:
            return {"location_found": False, "locations": None, "error": "Empty caption provided"}

        # Simplified prompt focusing on the task, not the format
        prompt = f"""
Analyze the following Instagram post caption to identify specific locations mentioned.
Focus on precise places like restaurants, landmarks, points of interest, shops, parks, specific addresses, etc.
For each specific location found, also include any mentioned city, state, region, or country that provides context for that location.
If only a general area (like a city or country) is mentioned without a specific point of interest, include that as well only if there is not a specific location mentioned.
Do not include general areas as individual items in the list, include them as part of the context for specific locations.

Caption:
"{caption}"
"""

        try:
            # Configure the model for JSON output with the defined schema
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=LocationResponse,
                )
            )

            # The SDK should parse the JSON response automatically when a schema is provided.
            # Note: Pydantic validation errors are suppressed by the SDK currently.
            # We attempt to access the parsed object, falling back to manual parsing if needed.
            try:
                # Access the parsed Pydantic model instance
                # Note: response.parsed might not exist or be None if parsing/validation failed silently
                 if hasattr(response, 'parsed') and response.parsed:
                      # Convert Pydantic model to dict for consistent return type
                     parsed_data = response.parsed.model_dump() # Use model_dump() for Pydantic v2
                     print(f"\n--- Parsed Locations (Pydantic): {parsed_data.get('locations')} ---") # ADDED PRINT
                     return parsed_data
                 else:
                     # Fallback: Manually parse the text if .parsed is not available
                    # The API should guarantee valid JSON here due to response_mime_type
                    try:
                        parsed_fallback = json.loads(response.text)
                        # Basic validation of fallback
                        if "location_found" in parsed_fallback and "locations" in parsed_fallback:
                             # Validate locations format
                             if parsed_fallback["locations"] is None or isinstance(parsed_fallback["locations"], list):
                                 print(f"\n--- Parsed Locations: {parsed_fallback.get('locations')} ---")
                                 return parsed_fallback
                             else:
                                 # No locations found or invalid format, don't print
                                 return {"location_found": False, "locations": None, "error": "Invalid 'locations' format in fallback JSON", "raw_response": response.text}
                        else:
                             return {"location_found": False, "locations": None, "error": "Invalid structure in fallback JSON", "raw_response": response.text}
                    except json.JSONDecodeError:
                         return {"location_found": False, "locations": None, "error": "Failed to parse fallback JSON response from AI", "raw_response": response.text}

            except (AttributeError, ValidationError, Exception) as parse_error:
                 # Catch potential issues accessing/validating response.parsed or other unexpected errors
                 print(f"Error processing Gemini response: {parse_error}")
                 # Attempt fallback parsing even if initial access failed
                 try:
                     parsed_fallback = json.loads(response.text)
                     if "location_found" in parsed_fallback and "locations" in parsed_fallback:
                         if parsed_fallback["locations"] is None or isinstance(parsed_fallback["locations"], list):
                             print(f"--- Parsed Locations (Fallback JSON after Error): {parsed_fallback.get('locations')} ---") # ADDED PRINT
                             return parsed_fallback
                         else:
                             # Invalid format, don't print
                             return {"location_found": False, "locations": None, "error": "Invalid 'locations' format in fallback JSON after error", "raw_response": response.text}
                     else:
                         return {"location_found": False, "locations": None, "error": "Invalid structure in fallback JSON after error", "raw_response": response.text}
                 except Exception as fallback_e:
                     return {"location_found": False, "locations": None, "error": f"Failed to process or parse response: {fallback_e}", "raw_response": response.text}


        except Exception as e:
            # Catch potential API call errors or other exceptions during generation
            print(f"Error calling Gemini API: {e}")
            return {"location_found": False, "locations": None, "error": f"Gemini API call failed: {str(e)}"}

# Example usage (optional, can be removed or kept for testing)
if __name__ == '__main__':
    # This block will only run when the script is executed directly
    try:
        analyzer = AIAnalyzer() # Uses default API key loading and model
        test_caption = "Had an amazing time exploring the Eiffel Tower in Paris, France! Then grabbed coffee at Café de Flore."
        result = analyzer.analyze_caption_for_location(test_caption)
        print("\n--- Analysis Result ---")
        print(json.dumps(result, indent=2))

        test_caption_city_only = "Visited Berlin this weekend."
        result_city = analyzer.analyze_caption_for_location(test_caption_city_only)
        print("\n--- Analysis Result (City Only) ---")
        print(json.dumps(result_city, indent=2))

        test_caption_none = "Just chilling at home."
        result_none = analyzer.analyze_caption_for_location(test_caption_none)
        print("\n--- Analysis Result (No Location) ---")
        print(json.dumps(result_none, indent=2))

    except ValueError as ve:
        print(f"Initialization Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
