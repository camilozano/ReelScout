import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def set_env_vars_session_scope():
    """
    Set dummy environment variables required by modules at import time
    to prevent errors during test collection. Runs once per session.
    Uses os.environ directly as monkeypatch is function-scoped.
    """
    # Set dummy API keys unconditionally for the test session.
    # This ensures they are present before modules needing them are imported during collection.
    os.environ["GEMINI_API_KEY"] = "DUMMY_GEMINI_KEY_FOR_TESTING"
    os.environ["GOOGLE_PLACES_API"] = "DUMMY_PLACES_KEY_FOR_TESTING"

    # You can add other environment variables needed during import here
    # Note: These variables will persist for the entire test session.
    # If you need to clean them up, you might need a more complex setup,
    # but for preventing import errors, this is usually sufficient.
