"""
MCP Protocol implementation for Sonarr integration.
This module handles the Model Context Protocol (MCP) message processing.
"""
import json
import logging
from typing import Dict, Any, List, Optional

# Configure logger
logger = logging.getLogger("mcp_protocol")

# MCP Protocol version
MCP_PROTOCOL_VERSION = "2025-03-26"

# Server information
SERVER_INFO = {
    "name": "mcp-sonarr",
    "version": "1.0.0"
}

# Import the utility to load the Sonarr OpenAPI schema
from app.core.utils import load_sonarr_openapi
from app.api.routes.mcp import SONARR_TOOLS as STATIC_SONARR_TOOLS

def get_sonarr_tools():
    """
    Dynamically generate tool schemas from the Sonarr OpenAPI specification.
    Falls back to static definitions if the OpenAPI schema cannot be loaded.
    """
    try:
        # Try to load the OpenAPI schema
        openapi = load_sonarr_openapi()
        logger.info("Successfully loaded Sonarr OpenAPI schema")
        
        # Convert the static tools to MCP format
        tools = []
        for tool in STATIC_SONARR_TOOLS:
            # Convert from input_schema/output_schema to inputSchema format
            mcp_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool.get("input_schema", {})
            }
            
            # Rename keys to match MCP format
            if "input_schema" in mcp_tool["inputSchema"]:
                mcp_tool["inputSchema"] = mcp_tool["inputSchema"]["input_schema"]
                
            tools.append(mcp_tool)
            
        logger.info(f"Using {len(tools)} predefined Sonarr tools in MCP format")
        return tools
    except Exception as e:
        logger.error(f"Error loading Sonarr OpenAPI schema: {str(e)}")
        
        # Create a minimal set of tools as fallback
        fallback_tools = [
            {
                "name": "search_series",
                "description": "Search for TV series by title",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the TV series to search for"
                        }
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "get_series",
                "description": "Get details about a specific TV series by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the TV series"
                        }
                    },
                    "required": ["id"]
                }
            }
        ]
        
        logger.info("Falling back to minimal tool definitions")
        return fallback_tools

# Get the tools (will be called once when the module is loaded)
SONARR_TOOLS = get_sonarr_tools()

def create_jsonrpc_response(id: Any, result: Any) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 success response."""
    return {
        "jsonrpc": "2.0",
        "id": id,
        "result": result
    }

def create_jsonrpc_error(id: Any, code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 error response."""
    error = {
        "code": code,
        "message": message
    }
    if data is not None:
        error["data"] = data
    
    return {
        "jsonrpc": "2.0",
        "id": id,
        "error": error
    }

def handle_initialize(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP initialize request."""
    logger.info(f"Handling initialize request: {request}")
    
    # Extract client capabilities if needed
    client_capabilities = request.get("params", {}).get("capabilities", {})
    logger.info(f"Client capabilities: {client_capabilities}")
    
    # Respond with server capabilities
    return create_jsonrpc_response(
        id=request.get("id"),
        result={
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "serverInfo": SERVER_INFO,
            "capabilities": {
                "tools": {}  # We support tools capability
            }
        }
    )

def handle_initialized(notification: Dict[str, Any]) -> None:
    """Handle MCP initialized notification."""
    logger.info(f"Received initialized notification: {notification}")
    # No response needed for notifications

def handle_tools_list(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tools/list request."""
    logger.info(f"Handling tools/list request: {request}")
    
    return create_jsonrpc_response(
        id=request.get("id"),
        result={
            "tools": SONARR_TOOLS
        }
    )

def handle_tools_call(request: Dict[str, Any], sonarr_service) -> Dict[str, Any]:
    """Handle MCP tools/call request."""
    logger.info(f"Handling tools/call request: {request}")
    
    params = request.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if not tool_name:
        return create_jsonrpc_error(
            id=request.get("id"),
            code=-32602,
            message="Missing required parameter: name"
        )
    
    try:
        # Find the tool
        tool = next((t for t in SONARR_TOOLS if t["name"] == tool_name), None)
        if not tool:
            return create_jsonrpc_error(
                id=request.get("id"),
                code=-32601,
                message=f"Tool not found: {tool_name}"
            )
        
        # Map tool names to Sonarr operations
        if tool_name == "search_series":
            title = arguments.get("title", "")
            if not title:
                return create_jsonrpc_error(
                    id=request.get("id"),
                    code=-32602,
                    message="Missing required parameter: title"
                )
            
            result = sonarr_service.call_sonarr_operation("search_series", {"term": title})
            return create_jsonrpc_response(
                id=request.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            )
            
        elif tool_name == "get_series":
            series_id = arguments.get("id")
            if not series_id:
                return create_jsonrpc_error(
                    id=request.get("id"),
                    code=-32602,
                    message="Missing required parameter: id"
                )
            
            result = sonarr_service.call_sonarr_operation("get_series", {"id": series_id})
            return create_jsonrpc_response(
                id=request.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            )
            
        elif tool_name == "get_quality_profiles":
            # No parameters needed for this call
            result = sonarr_service.call_sonarr_operation("get_quality_profiles", {})
            return create_jsonrpc_response(
                id=request.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            )
            
        elif tool_name == "get_root_folders":
            # No parameters needed for this call
            result = sonarr_service.call_sonarr_operation("get_root_folders", {})
            return create_jsonrpc_response(
                id=request.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            )
            
        elif tool_name == "add_series":
            # Check required parameters and map to correct Sonarr API parameter names
            required_params = {
                "tvdbId": arguments.get("tvdbId") or arguments.get("tvdb_id"),
                "title": arguments.get("title"),
                "qualityProfileId": arguments.get("qualityProfileId") or arguments.get("quality_profile_id"),
                "rootFolderPath": arguments.get("rootFolderPath") or arguments.get("root_folder_path")
            }
            
            # Check if any required parameters are missing
            missing_params = [k for k, v in required_params.items() if v is None]
            if missing_params:
                return create_jsonrpc_error(
                    id=request.get("id"),
                    code=-32602,
                    message=f"Missing required parameters: {', '.join(missing_params)}"
                )
            
            # Create a new arguments dict with the correct parameter names
            sonarr_args = {
                "tvdbId": required_params["tvdbId"],
                "title": required_params["title"],
                "qualityProfileId": required_params["qualityProfileId"],
                "rootFolderPath": required_params["rootFolderPath"],
                # Add any other parameters that might be in the arguments dict
                "monitored": arguments.get("monitored", True),
                "seasonFolder": arguments.get("seasonFolder", True),
                "addOptions": arguments.get("addOptions", {})
            }
            
            result = sonarr_service.call_sonarr_operation("add_series", sonarr_args)
            return create_jsonrpc_response(
                id=request.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            )
            
        elif tool_name == "get_calendar":
            params = {}
            if "start_date" in arguments:
                params["start_date"] = arguments["start_date"]
            if "end_date" in arguments:
                params["end_date"] = arguments["end_date"]
            
            result = sonarr_service.call_sonarr_operation("get_calendar", params)
            return create_jsonrpc_response(
                id=request.get("id"),
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            )
            
        else:
            return create_jsonrpc_error(
                id=request.get("id"),
                code=-32601,
                message=f"Tool not implemented: {tool_name}"
            )
            
    except Exception as e:
        logger.error(f"Error calling tool: {str(e)}")
        return create_jsonrpc_error(
            id=request.get("id"),
            code=-32603,
            message=f"Error calling tool: {str(e)}"
        )

def process_mcp_message(message: Dict[str, Any], sonarr_service) -> Optional[Dict[str, Any]]:
    """
    Process an MCP message and return the appropriate response.
    
    Args:
        message: The parsed JSON-RPC message
        sonarr_service: The Sonarr service instance for API calls
        
    Returns:
        A JSON-RPC response or None for notifications
    """
    # Check if this is a valid JSON-RPC message
    if "jsonrpc" not in message or message.get("jsonrpc") != "2.0":
        logger.warning(f"Not a valid JSON-RPC 2.0 message: {message}")
        return None
    
    # Handle requests (messages with an ID)
    if "id" in message:
        method = message.get("method")
        
        if method == "initialize":
            return handle_initialize(message)
        elif method == "tools/list":
            return handle_tools_list(message)
        elif method == "tools/call":
            return handle_tools_call(message, sonarr_service)
        else:
            logger.warning(f"Unknown method: {method}")
            return create_jsonrpc_error(
                id=message.get("id"),
                code=-32601,
                message=f"Method not found: {method}"
            )
    
    # Handle notifications (messages without an ID)
    else:
        method = message.get("method")
        
        if method == "initialized":
            handle_initialized(message)
            return None
        else:
            logger.warning(f"Unknown notification method: {method}")
            return None