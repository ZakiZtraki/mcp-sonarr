import json
import httpx
from typing import Dict, Any, List, Optional
from app.config.settings import settings
from app.core.utils import load_sonarr_openapi
from app.models.sonarr import SonarrCommand

class SonarrService:
    """
    Service for interacting with the Sonarr API.
    """
    def __init__(self):
        self.api_key = settings.SONARR_API_KEY
        self.api_url = settings.SONARR_API_URL
        self.headers = {"X-Api-Key": self.api_key}
    
    def validate_api_key(self) -> bool:
        """Validate the Sonarr API key by making a test request."""
        if not self.api_key:
            print("Error: SONARR_API_KEY environment variable is not set")
            return False
        if not self.api_url:
            print("Error: SONARR_API_URL environment variable is not set")
            return False
            
        try:
            resp = httpx.get(f"{self.api_url}/system/status", headers=self.headers, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"API key validation failed: {e}")
            return False
    
    def extract_sonarr_commands(self) -> List[SonarrCommand]:
        """Extract available commands from the Sonarr OpenAPI schema."""
        openapi = load_sonarr_openapi()
        commands = []
        for path, methods in openapi.get("paths", {}).items():
            for method, details in methods.items():
                operation_id = details.get("operationId", f"{method}_{path}")
                summary = details.get("summary", "")
                tag = details.get("tags", [""])[0]
                commands.append(SonarrCommand(
                    operationId=operation_id,
                    method=method.upper(),
                    path=path,
                    summary=summary,
                    tag=tag
                ))
        return commands
    
    def get_operation_parameters(self, operation_id: str) -> List[Dict[str, Any]]:
        """Get parameters for a specific operation."""
        spec = load_sonarr_openapi()
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if details.get("operationId") == operation_id:
                    return details.get("parameters", [])
        return []
    
    def resolve_series_title_to_id(self, title: str) -> Optional[int]:
        """Resolve a series title to its ID."""
        try:
            if not self.validate_api_key():
                return None
                
            resp = httpx.get(f"{self.api_url}/series", headers=self.headers, timeout=10)
            resp.raise_for_status()
            series = resp.json()
            match = next((s for s in series if s['title'].lower() == title.lower()), None)
            return match['id'] if match else None
        except Exception:
            return None
    
    def call_sonarr_operation(self, operation_id: str, params: Dict[str, Any]) -> Any:
        """Call a Sonarr API operation."""
        # Validate API key before proceeding
        if not self.validate_api_key():
            return "Error: Invalid API key or Sonarr server is not accessible."
            
        spec = load_sonarr_openapi()
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if details.get("operationId") == operation_id:
                    url = f"{self.api_url}{path}"
    
                    # Replace path params with actual values
                    for param_name in path.split("{")[1:]:
                        key = param_name.split("}")[0]
                        if key == "id" and "input" in params:
                            resolved_id = self.resolve_series_title_to_id(params["input"])
                            if resolved_id:
                                url = url.replace(f"{{{key}}}", str(resolved_id))
                            else:
                                return f"Could not resolve series title '{params['input']}' to an ID."
                        elif key in params:
                            url = url.replace(f"{{{key}}}", str(params[key]))
    
                    method = method.lower()
                    try:
                        if method == "get":
                            resp = httpx.get(url, headers=self.headers, timeout=10)
                        elif method == "post":
                            resp = httpx.post(url, headers=self.headers, json=params, timeout=10)
                        elif method == "put":
                            resp = httpx.put(url, headers=self.headers, json=params, timeout=10)
                        elif method == "delete":
                            resp = httpx.delete(url, headers=self.headers, timeout=10)
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

# Create a global instance of the service
sonarr_service = SonarrService()
