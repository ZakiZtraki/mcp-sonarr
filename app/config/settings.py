import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with fallbacks.
    """
    # API settings
    API_KEY: Optional[str] = None
    API_KEY_FILE: str = ".api_key"
    
    # Sonarr API settings
    SONARR_API_KEY: str = ""
    SONARR_API_URL: str = ""
    SONARR_OPENAPI_URL: str = "https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json"
    SONARR_CACHE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sonarr_openapi_cache.json")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create a global settings instance
settings = Settings(
    API_KEY=os.getenv("MCP_API_KEY"),
    SONARR_API_KEY=os.getenv("SONARR_API_KEY", ""),
    SONARR_API_URL=os.getenv("SONARR_API_URL", ""),
)
