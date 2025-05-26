"""
Service for managing OpenAI tools integration with Sonarr API.
"""
import json
import httpx
from typing import Dict, Any, List, Optional, Union
import logging

from app.config.settings import settings
from app.core.utils import load_sonarr_openapi
from app.core.openai_tools import get_sonarr_tools

logger = logging.getLogger("mcp_sonarr.openai_tools")

class OpenAIToolsService:
    """
    Service for managing OpenAI tools integration with Sonarr API.
    """
    def __init__(self):
        self.api_key = settings.SONARR_API_KEY
        self.api_url = settings.SONARR_API_URL
        self.headers = {"X-Api-Key": self.api_key}
        self._openapi_spec = None
        self._tools_cache = {}
    
    @property
    def openapi_spec(self) -> Dict[str, Any]:
        """
        Get the Sonarr OpenAPI specification.
        """
        if self._openapi_spec is None:
            self._openapi_spec = load_sonarr_openapi()
        return self._openapi_spec
    
    def get_tools(self, 
                  capabilities: Optional[List[str]] = None,
                  include_tags: Optional[List[str]] = None,
                  exclude_tags: Optional[List[str]] = None,
                  max_tools: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get OpenAI tools for Sonarr API.
        
        Args:
            capabilities: Filter tools by these capability keywords
            include_tags: Only include operations with these tags
            exclude_tags: Exclude operations with these tags
            max_tools: Maximum number of tools to generate
        
        Returns:
            A list of OpenAI tool definitions for Sonarr
        """
        # Create a cache key
        cache_key = json.dumps({
            "capabilities": capabilities,
            "include_tags": include_tags,
            "exclude_tags": exclude_tags,
            "max_tools": max_tools
        })
        
        # Check if we have a cached result
        if cache_key in self._tools_cache:
            return self._tools_cache[cache_key]
        
        # Generate tools
        tools = get_sonarr_tools(
            self.openapi_spec,
            capabilities=capabilities,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            max_tools=max_tools
        )
        
        # Cache the result
        self._tools_cache[cache_key] = tools
        
        return tools
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an OpenAI tool against the Sonarr API.
        
        Args:
            tool_name: The name of the tool to execute
            params: The parameters to pass to the tool
        
        Returns:
            The result of the tool execution
        """
        # Find the tool definition
        tool = None
        for t in self.get_tools():
            if t["function"]["name"] == tool_name:
                tool = t
                break
        
        if not tool:
            return {"error": f"Tool '{tool_name}' not found"}
        
        # Extract the operation details from the tool name
        # Most tool names will be in the format "operationId"
        operation_id = tool_name
        
        # Find the path and method for this operation
        path = None
        method = None
        
        for p, path_item in self.openapi_spec.get("paths", {}).items():
            for m, operation in path_item.items():
                if m not in ["get", "post", "put", "delete", "patch"]:
                    continue
                
                if operation.get("operationId") == operation_id:
                    path = p
                    method = m
                    break
            
            if path and method:
                break
        
        if not path or not method:
            return {"error": f"Operation '{operation_id}' not found in OpenAPI spec"}
        
        # Build the URL
        url = f"{self.api_url}{path}"
        
        # Replace path parameters
        for param_name, param_value in params.items():
            if f"{{{param_name}}}" in url:
                url = url.replace(f"{{{param_name}}}", str(param_value))
        
        # Separate query parameters from body parameters
        query_params = {}
        body_params = {}
        
        # Find the operation to get parameter details
        operation = self.openapi_spec["paths"][path][method]
        
        for param in operation.get("parameters", []):
            param_name = param["name"]
            if param_name in params:
                if param["in"] == "query":
                    query_params[param_name] = params[param_name]
        
        # If it's a POST, PUT, or PATCH, add remaining params to body
        if method in ["post", "put", "patch"]:
            # Check if there's a request body schema
            if "requestBody" in operation:
                content = operation["requestBody"].get("content", {})
                json_content = content.get("application/json", {})
                
                if "schema" in json_content:
                    # Add all params that aren't in query_params to body_params
                    for param_name, param_value in params.items():
                        if param_name not in query_params:
                            body_params[param_name] = param_value
        
        try:
            # Make the request
            if method == "get":
                resp = httpx.get(url, params=query_params, headers=self.headers, timeout=10)
            elif method == "post":
                resp = httpx.post(url, params=query_params, json=body_params, headers=self.headers, timeout=10)
            elif method == "put":
                resp = httpx.put(url, params=query_params, json=body_params, headers=self.headers, timeout=10)
            elif method == "delete":
                resp = httpx.delete(url, params=query_params, headers=self.headers, timeout=10)
            elif method == "patch":
                resp = httpx.patch(url, params=query_params, json=body_params, headers=self.headers, timeout=10)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
            
            # Check for errors
            resp.raise_for_status()
            
            # Return the response
            if resp.headers.get("content-type", "").startswith("application/json"):
                return resp.json()
            else:
                return {"content": resp.text}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing tool {tool_name}: {e}")
            return {
                "error": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text
            }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}

# Create a global instance of the service
openai_tools_service = OpenAIToolsService()