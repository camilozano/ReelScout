import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ValidationError

# Load environment variables from .env file in the auth directory
dotenv_path = Path(__file__).parent.parent / 'auth' / '.env'
load_dotenv(dotenv_path=dotenv_path)

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Check auth/.env file.")

genai.configure(api_key=API_KEY)

# Using the requested experimental Flash model
model = genai.GenerativeModel('models/gemini-2.0-flash-exp')

# Define the expected response structure using Pydantic
class LocationResponse(BaseModel):
    location_found: bool
    locations: Optional[List[str]]

def analyze_caption_for_location(caption: str) -> Dict[str, Any]:
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

Caption:
"{caption}"
"""

    try:
        # Configure the model for JSON output with the defined schema
        response = model.generate_content(
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
                 return response.parsed.model_dump() # Use model_dump() for Pydantic v2
             else:
                 # Fallback: Manually parse the text if .parsed is not available
                # The API should guarantee valid JSON here due to response_mime_type
                try:
                    parsed_fallback = json.loads(response.text)
                    # Basic validation of fallback
                    if "location_found" in parsed_fallback and "locations" in parsed_fallback:
                         # Validate locations format
                         if parsed_fallback["locations"] is None or isinstance(parsed_fallback["locations"], list):
                             return parsed_fallback
                         else:
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
                         return parsed_fallback
                     else:
                         return {"location_found": False, "locations": None, "error": "Invalid 'locations' format in fallback JSON after error", "raw_response": response.text}
                 else:
                     return {"location_found": False, "locations": None, "error": "Invalid structure in fallback JSON after error", "raw_response": response.text}
             except Exception as fallback_e:
                 return {"location_found": False, "locations": None, "error": f"Failed to process or parse response: {fallback_e}", "raw_response": response.text}


    except Exception as e:
        # Catch potential API call errors or other exceptions during generation
        print(f"Error calling Gemini API: {e}")
        return {"location_found": False, "locations": None, "error": f"Gemini API call failed: {str(e)}"}

# Example usage (for testing purposes)
if __name__ == '__main__':
    test_caption_1 = "Had an amazing time at the Eiffel Tower today! #paris #travel"
    test_caption_2 = "Best pizza ever at Joe's Pizza on Carmine St."
    test_caption_3 = "Just exploring California."
    test_caption_4 = "" # Empty caption

    print(f"Analyzing: '{test_caption_1}'")
    print(analyze_caption_for_location(test_caption_1))
    print("-" * 20)

    print(f"Analyzing: '{test_caption_2}'")
    print(analyze_caption_for_location(test_caption_2))
    print("-" * 20)

    print(f"Analyzing: '{test_caption_3}'")
    print(analyze_caption_for_location(test_caption_3))
    print("-" * 20)

    print(f"Analyzing: '{test_caption_4}'")
    print(analyze_caption_for_location(test_caption_4))
    print("-" * 20)
