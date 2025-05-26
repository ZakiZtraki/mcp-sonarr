"""
Routes for the MCP API - Clean version without legacy endpoints.
This file provides OpenAI function calling compatible endpoints for Sonarr API.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List, Optional
from app.api.dependencies import validate_token
from app.services.sonarr_service import sonarr_service
from app.services.openai_tools_service import openai_tools_service

router = APIRouter(tags=["mcp"])

# Define core tool schemas - these are the tools that will be initially exposed to the AI
CORE_TOOLS = [
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
    }
]

# OpenAI-compatible endpoints
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
    # Start with our core tools
    tools_list = [
        {
            "name": tool["name"],
            "description": tool["description"]
        }
        for tool in CORE_TOOLS
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
        # First check core tools
        tool = next((t for t in CORE_TOOLS if t["name"] == tool_name), None)
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
    tools_list = list(CORE_TOOLS)
    
    # Add dynamic tools if requested
    if dynamic:
        dynamic_tools = openai_tools_service.get_tools(
            capabilities=capabilities,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            max_tools=max_tools
        )
        
        # Convert dynamic tools to the same format as core tools
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
        
        # Handle core tools
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
            
            # First check core tools
            core_tool = next((t for t in CORE_TOOLS if t["name"] == requested_tool), None)
            if core_tool:
                return {
                    "name": core_tool["name"],
                    "description": core_tool["description"],
                    "parameters": core_tool["input_schema"],
                    "returns": core_tool["output_schema"]
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
            
        elif tool_name == "search_series":
            result = sonarr_service.call_sonarr_operation("search_series", {"term": arguments.get("title", "")})
            return result
        
        # Try to execute it as a dynamic OpenAI tool
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
    
    # Convert core tools to OpenAI function calling format
    core_tools = []
    for tool in CORE_TOOLS:
        core_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        })
    
    # Combine both sets of tools
    all_tools = core_tools + dynamic_tools
    
    return all_tools