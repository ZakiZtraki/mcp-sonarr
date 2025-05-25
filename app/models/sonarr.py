from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import os

class SonarrSettings(BaseSettings):
    """Settings for Sonarr API."""
    api_key: str = ""
    api_url: str = ""
    openapi_url: str = "https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json"
    cache_path: str = "sonarr_openapi_cache.json"
    
    class Config:
        env_file = ".env"
        env_prefix = "SONARR_"

class SonarrCommand(BaseModel):
    """Model for Sonarr command information."""
    operationId: str
    method: str
    path: str
    summary: str
    tag: str
