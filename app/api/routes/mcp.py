from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List, Optional
from app.api.dependencies import validate_token
from app.services.sonarr_service import sonarr_service

router = APIRouter(tags=["mcp"])

# Define tool schemas
SONARR_TOOLS = [
    {
        "name": "search_series",
        "description": "Search for TV series by title",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the TV series to search for"
                }
            },
            "required": ["title"]
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "year": {"type": "integer"},
                    "status": {"type": "string"},
                    "tvdbId": {"type": "integer", "description": "The TVDB ID needed for adding the series"}
                }
            }
        }
    },
    {
        "name": "get_series",
        "description": "Get details about a specific TV series by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "The ID of the TV series"
                }
            },
            "required": ["id"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "year": {"type": "integer"},
                "status": {"type": "string"},
                "overview": {"type": "string"},
                "seasons": {"type": "array", "items": {"type": "object"}}
            }
        }
    },
    {
        "name": "get_quality_profiles",
        "description": "Get available quality profiles from Sonarr",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "upgradeAllowed": {"type": "boolean"}
                }
            }
        }
    },
    {
        "name": "get_root_folders",
        "description": "Get available root folders from Sonarr",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "path": {"type": "string"},
                    "freeSpace": {"type": "integer"}
                }
            }
        }
    },
    {
        "name": "add_series",
        "description": "Add a new TV series to Sonarr",
        "input_schema": {
            "type": "object",
            "properties": {
                "tvdbId": {
                    "type": "integer",
                    "description": "The TVDB ID of the series (obtained from search_series results)"
                },
                "title": {
                    "type": "string",
                    "description": "The title of the series"
                },
                "qualityProfileId": {
                    "type": "integer",
                    "description": "The quality profile ID to use (obtained from get_quality_profiles)"
                },
                "rootFolderPath": {
                    "type": "string",
                    "description": "The root folder path where the series should be stored (obtained from get_root_folders)"
                },
                "monitored": {
                    "type": "boolean",
                    "description": "Whether to monitor the series for new episodes",
                    "default": True
                },
                "seasonFolder": {
                    "type": "boolean",
                    "description": "Whether to create season folders",
                    "default": True
                }
            },
            "required": ["tvdbId", "title", "qualityProfileId", "rootFolderPath"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "status": {"type": "string"}
            }
        }
    },
    {
        "name": "get_calendar",
        "description": "Get upcoming episodes from the Sonarr calendar",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Start date for the calendar (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                    "description": "End date for the calendar (YYYY-MM-DD)"
                }
            },
            "required": []
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "seriesId": {"type": "integer"},
                    "seriesTitle": {"type": "string"},
                    "episodeTitle": {"type": "string"},
                    "seasonNumber": {"type": "integer"},
                    "episodeNumber": {"type": "integer"},
                    "airDateUtc": {"type": "string", "format": "date-time"}
                }
            }
        }
    }
]

# Legacy endpoints (kept for backward compatibility)
@router.get("/mcp_list_tools")
async def mcp_list_tools():
    """
    List all available tools on the MCP server.
    This endpoint is maintained for backward compatibility.
    """
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"]
            }
            for tool in SONARR_TOOLS
        ]
    }

@router.get("/mcp_tool_schema")
async def mcp_tool_schema(tool_name: Optional[str] = None):
    """
    Get detailed schema information for tools.
    If tool_name is provided, returns schema for that specific tool.
    Otherwise, returns schemas for all tools.
    This endpoint is maintained for backward compatibility.
    """
    if tool_name:
        tool = next((t for t in SONARR_TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        return tool
    else:
        return {"tools": SONARR_TOOLS}

@router.post("/mcp_call_tool")
async def mcp_call_tool(request: Request, api_key: str = Depends(validate_token)):
    """
    Call a specific tool with the provided arguments.
    This endpoint is maintained for backward compatibility.
    """
    try:
        data = await request.json()
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})
        
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing tool_name in request")
            
        # Find the tool
        tool = next((t for t in SONARR_TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            
        # Map tool names to Sonarr operations for legacy endpoint
        if tool_name == "search_series":
            result = sonarr_service.call_sonarr_operation("search_series", {"term": arguments.get("title", "")})
            return result
            
        elif tool_name == "get_series":
            result = sonarr_service.call_sonarr_operation("get_series", {"id": arguments.get("id", 0)})
            return result
            
        elif tool_name == "get_quality_profiles":
            result = sonarr_service.call_sonarr_operation("get_quality_profiles", {})
            return result
            
        elif tool_name == "get_root_folders":
            result = sonarr_service.call_sonarr_operation("get_root_folders", {})
            return result
            
        elif tool_name == "add_series":
            result = sonarr_service.call_sonarr_operation("add_series", arguments)
            return result
            
        elif tool_name == "get_calendar":
            params = {}
            if "start_date" in arguments:
                params["start_date"] = arguments["start_date"]
            if "end_date" in arguments:
                params["end_date"] = arguments["end_date"]
            result = sonarr_service.call_sonarr_operation("get_calendar", params)
            return result
            
        else:
            raise HTTPException(status_code=501, detail=f"Tool '{tool_name}' is not implemented")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling tool: {str(e)}")

# New OpenAI-compatible endpoints
@router.get("/api/v1/tools")
async def list_tools():
    """
    List all available tools on the MCP server.
    This endpoint follows OpenAI's plugin conventions.
    """
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"]
            }
            for tool in SONARR_TOOLS
        ]
    }

@router.get("/api/v1/schema")
async def get_tool_schema(tool_name: Optional[str] = None):
    """
    Get detailed schema information for tools.
    If tool_name is provided, returns schema for that specific tool.
    Otherwise, returns schemas for all tools.
    This endpoint follows OpenAI's plugin conventions.
    """
    if tool_name:
        tool = next((t for t in SONARR_TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        return tool
    else:
        return {"tools": SONARR_TOOLS}

@router.post("/api/v1/call")
async def call_tool(request: Request, api_key: str = Depends(validate_token)):
    """
    Call a specific tool with the provided arguments.
    This endpoint follows OpenAI's plugin conventions.
    """
    try:
        data = await request.json()
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})
        
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing tool_name in request")
            
        # Find the tool
        tool = next((t for t in SONARR_TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            
        # Map tool names to Sonarr operations for OpenAI endpoint
        if tool_name == "search_series":
            result = sonarr_service.call_sonarr_operation("search_series", {"term": arguments.get("title", "")})
            return result
            
        elif tool_name == "get_series":
            result = sonarr_service.call_sonarr_operation("get_series", {"id": arguments.get("id", 0)})
            return result
            
        elif tool_name == "get_quality_profiles":
            result = sonarr_service.call_sonarr_operation("get_quality_profiles", {})
            return result
            
        elif tool_name == "get_root_folders":
            result = sonarr_service.call_sonarr_operation("get_root_folders", {})
            return result
            
        elif tool_name == "add_series":
            result = sonarr_service.call_sonarr_operation("add_series", arguments)
            return result
            
        elif tool_name == "get_calendar":
            params = {}
            if "start_date" in arguments:
                params["start_date"] = arguments["start_date"]
            if "end_date" in arguments:
                params["end_date"] = arguments["end_date"]
            result = sonarr_service.call_sonarr_operation("get_calendar", params)
            return result
            
        else:
            raise HTTPException(status_code=501, detail=f"Tool '{tool_name}' is not implemented")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling tool: {str(e)}")