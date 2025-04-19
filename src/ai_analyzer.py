from google import genai
from google.genai import types, errors # Added types and errors
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
    #DEFAULT_MODEL_NAME = 'models/gemini-2.0-flash-lite'
    DEFAULT_MODEL_NAME = 'models/gemini-2.5-flash-preview-04-17'

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

        # API key loading logic remains the same

        self.model_name = model_name if model_name else self.DEFAULT_MODEL_NAME
        # Removed model initialization here, client is instantiated per-call now
        print(f"AIAnalyzer configured with model name: {self.model_name}") # Updated print message

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
        # Instantiate client here using the API key
        client = genai.Client(api_key=self.api_key)

        try:
            # Configure the model for JSON output with the defined schema using the new client and types
            response = client.models.generate_content(
                model=self.model_name, # Pass model name here
                contents=prompt,       # Use 'contents' instead of positional argument
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LocationResponse,
                    # Add other config like temperature if needed, e.g., temperature=0.5
                )
            )

            # New SDK primarily uses response.text. We need to parse it ourselves.
            # Use Pydantic for validation.
            try:
                # Attempt to validate and parse the JSON response text using Pydantic
                # This might raise json.JSONDecodeError if response.text is not valid JSON,
                # or ValidationError if JSON is valid but doesn't match the schema.
                parsed_data = LocationResponse.model_validate_json(response.text)
                print(f"\n--- Parsed Locations (Pydantic): {parsed_data.locations} ---")
                return parsed_data.model_dump() # Return as dict

            except json.JSONDecodeError as json_e:
                # Handle cases where the response text is not valid JSON at all
                print(f"Failed to decode JSON response: {json_e}")
                return {"location_found": False, "locations": None, "error": f"Failed to decode JSON response from AI: {json_e}", "raw_response": response.text}

            except ValidationError as ve:
                print(f"Pydantic validation failed: {ve}")
                # Fallback: Try basic JSON parsing if Pydantic fails (e.g., if structure is wrong)
                # This block is now less likely to be hit for JSON errors, but might catch
                # cases where the initial parse worked but validation failed, and we still
                # want to try a raw parse (though Pydantic should handle most structure issues).
                try:
                    fallback_data = json.loads(response.text)
                    # Basic check if it looks like our structure
                    if isinstance(fallback_data.get("locations"), list) or fallback_data.get("locations") is None:
                         print(f"--- Parsed Locations (Fallback JSON after Validation Error): {fallback_data.get('locations')} ---")
                         # Return the raw dict, but flag the validation issue
                         fallback_data["error"] = f"Pydantic validation failed: {ve}"
                         return fallback_data
                    else:
                         return {"location_found": False, "locations": None, "error": f"Invalid structure in fallback JSON after validation error: {ve}", "raw_response": response.text}
                except json.JSONDecodeError as json_e: # Should be less likely now
                    return {"location_found": False, "locations": None, "error": f"Failed to parse JSON response during fallback attempt: {json_e}", "raw_response": response.text}
                except Exception as e: # Catch any other unexpected error during fallback
                     return {"location_found": False, "locations": None, "error": f"Unexpected error during fallback response processing: {e}", "raw_response": response.text}
            except Exception as e: # Catch any other unexpected error during initial processing
                print(f"Unexpected error processing response: {e}")
                return {"location_found": False, "locations": None, "error": f"Unexpected error processing response: {e}", "raw_response": getattr(response, 'text', 'N/A')}


        except errors.APIError as e:
            # Catch specific API errors from the new SDK
            print(f"Error calling Gemini API: {e}")
            return {"location_found": False, "locations": None, "error": f"Gemini API call failed: {str(e)}"}
        except Exception as e:
            # Catch other potential exceptions during the API call itself (network issues, etc.)
            print(f"An unexpected error occurred during API call/generation: {e}")
            return {"location_found": False, "locations": None, "error": f"Unexpected error during API call: {str(e)}"}

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
