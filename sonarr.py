import json
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional

# Configuration class for Sonarr API settings
class SonarrSettings(BaseSettings):
    api_key: str = os.getenv("SONARR_API_KEY", "a8bb15e3d1c5702e1a854a2ea29655a70537a64f")
    api_url: str = os.getenv("SONARR_API_URL", "https://sonarr.zakitraki.com/api")
    openapi_url: str = "https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json"
    cache_path: str = os.path.join(os.path.dirname(__file__), "sonarr_openapi_cache.json")
    
    class Config:
        env_file = ".env"
        env_prefix = "SONARR_"

# Initialize settings
settings = SonarrSettings()

# Constants
CACHE_PATH = settings.cache_path
SONARR_OPENAPI_URL = settings.openapi_url
SONARR_API_KEY = settings.api_key
SONARR_API_URL = settings.api_url
SONARR_HEADERS = {"X-Api-Key": SONARR_API_KEY}

# API Key security for FastAPI endpoints
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Function to validate API key in FastAPI requests
async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == SONARR_API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=401,
        detail="Invalid API Key"
    )

router = APIRouter()

class SonarrQueryModel(BaseModel):
    intent: str
    input: Optional[str] = None
    user_id: Optional[str] = None

def load_sonarr_openapi():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    resp = httpx.get(SONARR_OPENAPI_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data

def extract_sonarr_commands():
    openapi = load_sonarr_openapi()
    commands = []
    for path, methods in openapi.get("paths", {}).items():
        for method, details in methods.items():
            operation_id = details.get("operationId", f"{method}_{path}")
            summary = details.get("summary", "")
            tag = details.get("tags", [""])[0]
            commands.append({
                "operationId": operation_id,
                "method": method.upper(),
                "path": path,
                "summary": summary,
                "tag": tag
            })
    return commands

def get_operation_parameters(operation_id):
    spec = load_sonarr_openapi()
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if details.get("operationId") == operation_id:
                return details.get("parameters", [])
    return []

def validate_api_key():
    """Validate the Sonarr API key by making a test request."""
    try:
        resp = httpx.get(f"{SONARR_API_URL}/system/status", headers=SONARR_HEADERS, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"API key validation failed: {e}")
        return False

def resolve_series_title_to_id(title):
    try:
        if not validate_api_key():
            return None
            
        resp = httpx.get(f"{SONARR_API_URL}/series", headers=SONARR_HEADERS, timeout=10)
        resp.raise_for_status()
        series = resp.json()
        match = next((s for s in series if s['title'].lower() == title.lower()), None)
        return match['id'] if match else None
    except Exception:
        return None

def call_sonarr_operation(operation_id, params):
    # Validate API key before proceeding
    if not validate_api_key():
        return "Error: Invalid API key or Sonarr server is not accessible."
        
    spec = load_sonarr_openapi()
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if details.get("operationId") == operation_id:
                url = f"{SONARR_API_URL}{path}"

                # Replace path params with actual values
                for param_name in path.split("{")[1:]:
                    key = param_name.split("}")[0]
                    if key == "id" and "input" in params:
                        resolved_id = resolve_series_title_to_id(params["input"])
                        if resolved_id:
                            url = url.replace(f"{{{key}}}", str(resolved_id))
                        else:
                            return f"Could not resolve series title '{params['input']}' to an ID."
                    elif key in params:
                        url = url.replace(f"{{{key}}}", str(params[key]))

                method = method.lower()
                try:
                    if method == "get":
                        resp = httpx.get(url, headers=SONARR_HEADERS, timeout=10)
                    elif method == "post":
                        resp = httpx.post(url, headers=SONARR_HEADERS, json=params, timeout=10)
                    elif method == "put":
                        resp = httpx.put(url, headers=SONARR_HEADERS, json=params, timeout=10)
                    elif method == "delete":
                        resp = httpx.delete(url, headers=SONARR_HEADERS, timeout=10)
                    else:
                        return f"Unsupported HTTP method: {method.upper()}"
                    
                    resp.raise_for_status()  # Raise exception for 4XX/5XX responses
                    return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        return "Error: Unauthorized. Please check your API key."
                    elif e.response.status_code == 403:
                        return "Error: Forbidden. You don't have permission to access this resource."
                    else:
                        return f"HTTP Error: {e.response.status_code} - {e.response.reason_phrase}"
                except Exception as e:
                    return f"Request failed: {e}"
    return f"OperationId '{operation_id}' not found."

@router.post("/mcp/sonarr-query")
async def sonarr_query(request: SonarrQueryModel, api_key: str = Depends(get_api_key)):
    intent = request.intent.lower()
    result = call_sonarr_operation(intent, {"input": request.input})
    return {"type": "text", "content": str(result)}

@router.get("/mcp/sonarr-capabilities")
async def list_sonarr_capabilities(api_key: str = Depends(get_api_key)):
    return {"type": "json", "commands": extract_sonarr_commands()}

@router.get("/mcp/sonarr-help")
async def sonarr_help(api_key: str = Depends(get_api_key)):
    commands = extract_sonarr_commands()
    lines = [
        f"- **{cmd['operationId']}** ({cmd['method']} {cmd['path']}): {cmd['summary'] or 'No description'}"
        for cmd in commands
    ]
    return {"type": "text", "content": "\n".join(lines)}

@router.get("/mcp/sonarr-operation-params/{operation_id}")
async def get_required_params(operation_id: str, api_key: str = Depends(get_api_key)):
    params = get_operation_parameters(operation_id)
    return {"operationId": operation_id, "parameters": params}

@router.get("/mcp/sonarr-status")
async def get_sonarr_status(api_key: str = Depends(get_api_key)):
    """Check if the Sonarr API is accessible and the API key is valid."""
    if validate_api_key():
        return {"status": "ok", "message": "Sonarr API is accessible and API key is valid."}
    else:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key or Sonarr server is not accessible."
        )
