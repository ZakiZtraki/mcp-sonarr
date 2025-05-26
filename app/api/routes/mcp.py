from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List, Optional
from app.api.dependencies import validate_token
from app.services.sonarr_service import sonarr_service
from app.services.openai_tools_service import openai_tools_service

router = APIRouter(tags=["mcp"])

# Define tool schemas
SONARR_TOOLS = [
    {
        "name": "list_series",
        "description": "List all TV series in your Sonarr collection",
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
                    "title": {"type": "string"},
                    "year": {"type": "integer"},
                    "status": {"type": "string"},
                    "overview": {"type": "string"}
                }
            }
        }
    },
    {
        "name": "discover_tools",
        "description": "Discover additional Sonarr API tools based on specific needs or categories",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category of tools to discover (e.g., 'Series', 'Calendar', 'System', etc.)",
                    "enum": ["Series", "Calendar", "System", "Episode", "Command", "Quality", "All"]
                },
                "keyword": {
                    "type": "string",
                    "description": "Keyword to search for in tool names and descriptions"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of tools to return",
                    "default": 10
                }
            },
            "required": []
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                }
            }
        }
    },
    {
        "name": "get_tool_schema",
        "description": "Get the detailed schema for a specific tool by name",
        "input_schema": {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "The name of the tool to get the schema for"
                }
            },
            "required": ["tool_name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "parameters": {"type": "object"},
                "returns": {"type": "object"}
            }
        }
    },
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
            
        # Handle meta-tools
        if tool_name == "discover_tools":
            category = arguments.get("category", "All")
            keyword = arguments.get("keyword", "")
            max_results = arguments.get("max_results", 10)
            
            # Map category to tags
            include_tags = None
            if category != "All":
                include_tags = [category]
            
            # Get dynamic tools from Sonarr OpenAPI
            capabilities = [keyword] if keyword else []
            
            dynamic_tools = openai_tools_service.get_tools(
                capabilities=capabilities,
                include_tags=include_tags,
                max_tools=max_results
            )
            
            # Format the response
            tool_list = []
            for t in dynamic_tools:
                tool_list.append({
                    "name": t["function"]["name"],
                    "description": t["function"]["description"]
                })
            
            return {"tools": tool_list}
            
        elif tool_name == "get_tool_schema":
            requested_tool = arguments.get("tool_name")
            if not requested_tool:
                return {"error": "Missing tool_name parameter"}
            
            # First check predefined tools
            predefined_tool = next((t for t in SONARR_TOOLS if t["name"] == requested_tool), None)
            if predefined_tool:
                return {
                    "name": predefined_tool["name"],
                    "description": predefined_tool["description"],
                    "parameters": predefined_tool["input_schema"],
                    "returns": predefined_tool["output_schema"]
                }
            
            # If not found, check dynamic tools
            dynamic_tools = openai_tools_service.get_tools()
            for t in dynamic_tools:
                if t["function"]["name"] == requested_tool:
                    return {
                        "name": t["function"]["name"],
                        "description": t["function"]["description"],
                        "parameters": t["function"]["parameters"],
                        "returns": {
                            "type": "object",
                            "description": "Response from Sonarr API"
                        }
                    }
            
            return {"error": f"Tool '{requested_tool}' not found"}
        
        # Map tool names to Sonarr operations
        elif tool_name == "list_series":
            result = sonarr_service.call_sonarr_operation("get_all_series", {})
            return result
            
        elif tool_name == "search_series":
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
async def list_tools(
    dynamic: bool = False,
    capabilities: Optional[List[str]] = None,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    max_tools: Optional[int] = None
):
    """
    List all available tools on the MCP server.
    This endpoint follows OpenAI's plugin conventions.
    
    Args:
        dynamic: If True, include dynamically generated tools from Sonarr OpenAPI
        capabilities: Filter dynamic tools by these capability keywords
        include_tags: Only include operations with these tags
        exclude_tags: Exclude operations with these tags
        max_tools: Maximum number of dynamic tools to include
    """
    # Start with our predefined tools
    tools_list = [
        {
            "name": tool["name"],
            "description": tool["description"]
        }
        for tool in SONARR_TOOLS
    ]
    
    # Add dynamic tools if requested
    if dynamic:
        dynamic_tools = openai_tools_service.get_tools(
            capabilities=capabilities,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            max_tools=max_tools
        )
        
        for tool in dynamic_tools:
            tools_list.append({
                "name": tool["function"]["name"],
                "description": tool["function"]["description"]
            })
    
    return {"tools": tools_list}

@router.get("/api/v1/schema")
async def get_tool_schema(
    tool_name: Optional[str] = None,
    dynamic: bool = False,
    capabilities: Optional[List[str]] = None,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    max_tools: Optional[int] = None
):
    """
    Get detailed schema information for tools.
    If tool_name is provided, returns schema for that specific tool.
    Otherwise, returns schemas for all tools.
    This endpoint follows OpenAI's plugin conventions.
    
    Args:
        tool_name: The name of the specific tool to get schema for
        dynamic: If True, include dynamically generated tools from Sonarr OpenAPI
        capabilities: Filter dynamic tools by these capability keywords
        include_tags: Only include operations with these tags
        exclude_tags: Exclude operations with these tags
        max_tools: Maximum number of dynamic tools to include
    """
    # If a specific tool is requested
    if tool_name:
        # First check predefined tools
        tool = next((t for t in SONARR_TOOLS if t["name"] == tool_name), None)
        if tool:
            return tool
        
        # If not found and dynamic is enabled, check dynamic tools
        if dynamic:
            # Get all dynamic tools
            dynamic_tools = openai_tools_service.get_tools()
            
            # Find the requested tool
            for tool in dynamic_tools:
                if tool["function"]["name"] == tool_name:
                    return tool
        
        # If we get here, the tool wasn't found
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    # If no specific tool is requested, return all tools
    tools_list = list(SONARR_TOOLS)
    
    # Add dynamic tools if requested
    if dynamic:
        dynamic_tools = openai_tools_service.get_tools(
            capabilities=capabilities,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            max_tools=max_tools
        )
        
        # Convert dynamic tools to the same format as predefined tools
        for tool in dynamic_tools:
            function = tool["function"]
            tools_list.append({
                "name": function["name"],
                "description": function["description"],
                "input_schema": function["parameters"],
                "output_schema": {
                    "type": "object",
                    "description": "Response from Sonarr API"
                }
            })
    
    return {"tools": tools_list}

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
            
        # First check if it's one of our predefined tools
        tool = next((t for t in SONARR_TOOLS if t["name"] == tool_name), None)
        if tool:
            # Handle the discover_tools meta-tool
            if tool_name == "discover_tools":
                category = arguments.get("category", "All")
                keyword = arguments.get("keyword", "")
                max_results = arguments.get("max_results", 10)
                
                # Map category to tags
                include_tags = None
                if category != "All":
                    include_tags = [category]
                
                # Get dynamic tools from Sonarr OpenAPI
                dynamic_tools = openai_tools_service.get_tools(
                    capabilities=[keyword] if keyword else None,
                    include_tags=include_tags,
                    max_tools=max_results
                )
                
                # Format the response
                tool_list = []
                for t in dynamic_tools:
                    tool_list.append({
                        "name": t["function"]["name"],
                        "description": t["function"]["description"]
                    })
                
                return {"tools": tool_list}
                
            # Handle the get_tool_schema meta-tool
            elif tool_name == "get_tool_schema":
                requested_tool = arguments.get("tool_name")
                if not requested_tool:
                    return {"error": "Missing tool_name parameter"}
                
                # First check predefined tools
                predefined_tool = next((t for t in SONARR_TOOLS if t["name"] == requested_tool), None)
                if predefined_tool:
                    return {
                        "name": predefined_tool["name"],
                        "description": predefined_tool["description"],
                        "parameters": predefined_tool["input_schema"],
                        "returns": predefined_tool["output_schema"]
                    }
                
                # If not found, check dynamic tools
                dynamic_tools = openai_tools_service.get_tools()
                for t in dynamic_tools:
                    if t["function"]["name"] == requested_tool:
                        return {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"],
                            "returns": {
                                "type": "object",
                                "description": "Response from Sonarr API"
                            }
                        }
                
                return {"error": f"Tool '{requested_tool}' not found"}
            
            # Map tool names to Sonarr operations for OpenAI endpoint
            elif tool_name == "search_series":
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
        
        # If not a predefined tool, try to execute it as a dynamic OpenAI tool
        result = openai_tools_service.execute_tool(tool_name, arguments)
        
        # Check if there was an error
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling tool: {str(e)}")

@router.get("/api/v1/openai-tools")
async def get_openai_tools(
    capabilities: Optional[List[str]] = None,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    max_tools: Optional[int] = None
):
    """
    Get tools in OpenAI function calling format.
    
    This endpoint returns tools in the format expected by OpenAI's function calling API.
    
    Args:
        capabilities: Filter tools by these capability keywords
        include_tags: Only include operations with these tags
        exclude_tags: Exclude operations with these tags
        max_tools: Maximum number of tools to include
    """
    # Get dynamic tools from Sonarr OpenAPI
    dynamic_tools = openai_tools_service.get_tools(
        capabilities=capabilities,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        max_tools=max_tools
    )
    
    # Convert predefined tools to OpenAI function calling format
    predefined_tools = []
    for tool in SONARR_TOOLS:
        predefined_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        })
    
    # Combine both sets of tools
    all_tools = predefined_tools + dynamic_tools
    
    return all_tools