#!/usr/bin/env python
import getpass
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (
    TwoFactorRequired,
    ChallengeRequired,
    BadPassword,
    LoginRequired,
    ClientError,
)

# Define the directory and file path for saving the session
AUTH_DIR = Path("auth")
SESSION_FILE = AUTH_DIR / "instagram_session.json"

def get_instagram_session():
    """
    Logs into Instagram using username/password (handles 2FA)
    and saves the session data to a JSON file.
    """
    print("Instagram Login Helper")
    print("-" * 20)

    # Ensure the auth directory exists
    AUTH_DIR.mkdir(exist_ok=True)

    username = input("Enter your Instagram username: ")
    password = getpass.getpass("Enter your Instagram password: ")

    cl = Client()
    cl.delay_range = [1, 3] # Add a small delay between requests

    try:
        print("Attempting login...")
        cl.login(username, password)
        print("Login successful (without 2FA).")

    except TwoFactorRequired:
        print("Two-Factor Authentication required.")
        two_factor_code = input("Enter the 2FA code sent to your device: ")
        try:
            cl.login(username, password, verification_code=two_factor_code)
            print("Login successful (with 2FA).")
        except BadPassword:
            print("Error: Incorrect password or 2FA code.")
            return
        except ChallengeRequired as e:
            print(f"Error: Challenge required after 2FA. This script cannot handle complex challenges. Details: {e}")
            # You might need to log in via the app/website first.
            return
        except ClientError as e:
            print(f"An unexpected error occurred during 2FA login: {e}")
            return

    except BadPassword:
        print("Error: Incorrect password.")
        return
    except ChallengeRequired as e:
        print(f"Error: Challenge required. This script cannot handle complex challenges. Details: {e}")
        print("Please log in via the Instagram app or website to resolve the challenge, then try again.")
        return
    except LoginRequired as e:
         print(f"Error: Login required, but login failed. Details: {e}")
         return
    except ClientError as e:
        print(f"An unexpected error occurred during login: {e}")
        # Consider adding more specific exception handling based on instagrapi docs if needed
        return
    except Exception as e:
        print(f"An unexpected general error occurred: {e}")
        return


    try:
        print(f"Saving session data to {SESSION_FILE}...")
        cl.dump_settings(SESSION_FILE)
        print("Session data saved successfully.")
        print(f"\nYou can now use the file '{SESSION_FILE}' for authenticated requests.")
    except Exception as e:
        print(f"Error saving session data: {e}")

if __name__ == "__main__":
    get_instagram_session()
