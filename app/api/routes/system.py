from fastapi import APIRouter, Depends, Request
from app.api.dependencies import validate_token, ensure_localhost, API_KEY
from app.models.api import WelcomeResponse, ApiKeyResponse

router = APIRouter()

@router.get(
    "/", 
    dependencies=[],
    summary="API Welcome Page",
    description="Welcome page for the Sonarr MCP API. This endpoint does not require authentication.",
    response_description="Welcome message",
    response_model=WelcomeResponse,
    responses={
        200: {
            "description": "Welcome message",
            "content": {
                "application/json": {
                    "example": {"message": "Welcome to Sonarr MCP API"}
                }
            }
        }
    }
)
async def root_get():
    return {"message": "Welcome to Sonarr MCP API"}

@router.post(
    "/", 
    dependencies=[],
    summary="API Welcome Page and MCP Protocol Endpoint",
    description="Handles both simple welcome requests and MCP protocol messages.",
    response_description="Welcome message or MCP protocol response",
    responses={
        200: {
            "description": "Welcome message or MCP protocol response",
            "content": {
                "application/json": {
                    "example": {"message": "Welcome to Sonarr MCP API"}
                }
            }
        }
    }
)
async def root_post(request: Request):
    # Import necessary modules
    import logging
    import json
    import httpx
    from fastapi.responses import JSONResponse
    from app.services.sonarr_service import sonarr_service
    from app.core.mcp_protocol import process_mcp_message
    
    logger = logging.getLogger("uvicorn")
    
    try:
        body = await request.json()
        logger.info(f"POST / request body: {body}")
        
        # Check if this is an MCP protocol message (has jsonrpc field)
        if "jsonrpc" in body and body.get("jsonrpc") == "2.0":
            # Process as MCP protocol message
            response = process_mcp_message(body, sonarr_service)
            if response:
                logger.info(f"MCP response: {response}")
                return JSONResponse(content=response)
            else:
                # This was a notification that doesn't require a response
                return JSONResponse(content={"message": "Notification received"})
        
        # If this is a direct tool call (OpenAI plugin format), handle it
        elif "name" in body and "arguments" in body:
            # Extract tool name and arguments
            tool_name = body["name"]
            arguments = body["arguments"]
            logger.info(f"Handling direct tool call: {tool_name} with arguments: {arguments}")
            
            # Validate API key before proceeding
            if not sonarr_service.validate_api_key():
                return JSONResponse(
                    content={"error": "Invalid API key or Sonarr server is not accessible."},
                    status_code=401
                )
            
            # Map tool names to direct API calls
            if tool_name == "search_series":
                title = arguments.get("title", "")
                if not title:
                    return JSONResponse(
                        content={"error": "Missing required parameter: title"},
                        status_code=400
                    )
                
                try:
                    # Call Sonarr API directly
                    resp = httpx.get(
                        f"{sonarr_service.api_url}/v3/series/lookup",
                        params={"term": title},
                        headers=sonarr_service.headers,
                        timeout=10
                    )
                    resp.raise_for_status()
                    return JSONResponse(content=resp.json())
                except Exception as e:
                    logger.error(f"Error searching series: {str(e)}")
                    return JSONResponse(
                        content={"error": f"Error searching series: {str(e)}"},
                        status_code=500
                    )
                
            elif tool_name == "get_series":
                series_id = arguments.get("id")
                if not series_id:
                    return JSONResponse(
                        content={"error": "Missing required parameter: id"},
                        status_code=400
                    )
                
                try:
                    # Call Sonarr API directly
                    resp = httpx.get(
                        f"{sonarr_service.api_url}/v3/series/{series_id}",
                        headers=sonarr_service.headers,
                        timeout=10
                    )
                    resp.raise_for_status()
                    return JSONResponse(content=resp.json())
                except Exception as e:
                    logger.error(f"Error getting series: {str(e)}")
                    return JSONResponse(
                        content={"error": f"Error getting series: {str(e)}"},
                        status_code=500
                    )
                
            elif tool_name == "add_series":
                # Required parameters for adding a series
                required_params = ["tvdb_id", "title", "quality_profile_id", "root_folder_path"]
                for param in required_params:
                    if param not in arguments:
                        return JSONResponse(
                            content={"error": f"Missing required parameter: {param}"},
                            status_code=400
                        )
                
                try:
                    # Call Sonarr API directly
                    resp = httpx.post(
                        f"{sonarr_service.api_url}/v3/series",
                        json=arguments,
                        headers=sonarr_service.headers,
                        timeout=10
                    )
                    resp.raise_for_status()
                    return JSONResponse(content=resp.json())
                except Exception as e:
                    logger.error(f"Error adding series: {str(e)}")
                    return JSONResponse(
                        content={"error": f"Error adding series: {str(e)}"},
                        status_code=500
                    )
                
            elif tool_name == "get_calendar":
                try:
                    # Build query parameters
                    params = {}
                    if "start_date" in arguments:
                        params["start"] = arguments["start_date"]
                    if "end_date" in arguments:
                        params["end"] = arguments["end_date"]
                    
                    # Call Sonarr API directly
                    resp = httpx.get(
                        f"{sonarr_service.api_url}/v3/calendar",
                        params=params,
                        headers=sonarr_service.headers,
                        timeout=10
                    )
                    resp.raise_for_status()
                    return JSONResponse(content=resp.json())
                except Exception as e:
                    logger.error(f"Error getting calendar: {str(e)}")
                    return JSONResponse(
                        content={"error": f"Error getting calendar: {str(e)}"},
                        status_code=500
                    )
                
            else:
                logger.error(f"Unknown tool: {tool_name}")
                return JSONResponse(
                    content={"error": f"Unknown tool: {tool_name}"},
                    status_code=404
                )
    except Exception as e:
        logger.error(f"Error processing POST request: {str(e)}")
    
    # Default response for non-MCP requests
    return {"message": "Welcome to Sonarr MCP API"}

@router.get(
    "/api-key", 
    dependencies=[Depends(ensure_localhost)],
    summary="Retrieve API Key",
    description="Retrieves the current API key. This endpoint is only accessible from localhost for security reasons.",
    response_description="Returns the API key that should be used for authentication",
    response_model=ApiKeyResponse,
    responses={
        200: {
            "description": "The current API key",
            "content": {
                "application/json": {
                    "example": {"api_key": "example1234567890abcdef"}
                }
            }
        },
        403: {
            "description": "Access denied - endpoint only accessible from localhost"
        }
    }
)
async def get_api_key_endpoint():
    return {"api_key": API_KEY}
