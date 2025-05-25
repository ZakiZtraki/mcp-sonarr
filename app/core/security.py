import os
import uuid
import secrets
from app.config.settings import settings

def generate_api_key():
    """Generate a secure API key using a combination of UUID and random bytes."""
    # Create a base using UUID4 (random UUID)
    uuid_part = str(uuid.uuid4()).replace('-', '')
    # Add some additional randomness with secrets
    random_part = secrets.token_hex(8)
    # Combine them
    return f"{uuid_part}{random_part}"

def get_or_create_api_key():
    """Get the API key from environment or file, or create a new one if needed."""
    api_key = settings.API_KEY
    
    # If not in environment, check if we have a saved key
    if not api_key and os.path.exists(settings.API_KEY_FILE):
        try:
            with open(settings.API_KEY_FILE, "r") as f:
                api_key = f.read().strip()
        except Exception as e:
            print(f"Error reading API key file: {e}")
    
    # If still no API key, generate one and save it
    if not api_key:
        api_key = generate_api_key()
        try:
            with open(settings.API_KEY_FILE, "w") as f:
                f.write(api_key)
            print(f"Generated new API key: {api_key}")
            print(f"This key has been saved to {settings.API_KEY_FILE}")
        except Exception as e:
            print(f"Warning: Could not save API key to file: {e}")
            print(f"Your API key is: {api_key}")
            print("Please save this key as it will be required for authentication.")
    
    return api_key
