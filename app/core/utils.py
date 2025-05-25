import os
import json
import httpx
from app.config.settings import settings

def load_sonarr_openapi():
    """Load the Sonarr OpenAPI schema from cache or download it."""
    if os.path.exists(settings.SONARR_CACHE_PATH):
        with open(settings.SONARR_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    resp = httpx.get(settings.SONARR_OPENAPI_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    with open(settings.SONARR_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data
