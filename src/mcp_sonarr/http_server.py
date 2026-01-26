"""HTTP/SSE Transport for MCP Server - Enables remote access for Claude/ChatGPT."""

import os
import json
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

import uvicorn
from dotenv import load_dotenv

from .sonarr_client import SonarrClient, SonarrConfig
from .server import list_tools, _execute_tool, get_client

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server info
SERVER_NAME = "mcp-sonarr"
SERVER_VERSION = "1.0.0"


def get_auth_token() -> Optional[str]:
    """Get the authentication token from environment."""
    return os.getenv("MCP_AUTH_TOKEN")


def verify_auth(request: Request) -> bool:
    """Verify the authentication token."""
    auth_token = get_auth_token()
    if not auth_token:
        return True  # No auth configured

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return token == auth_token

    return False


# ==================== Endpoints ====================

async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    try:
        client = get_client()
        status = await client.get_system_status()
        return JSONResponse({
            "status": "healthy",
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "sonarr_version": status.get("version"),
        })
    except Exception as e:
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)},
            status_code=503,
        )


async def server_info(request: Request) -> JSONResponse:
    """Get server information (MCP initialize equivalent)."""
    if not verify_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return JSONResponse({
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
        },
    })


async def tools_list(request: Request) -> JSONResponse:
    """List available tools."""
    if not verify_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    tools = await list_tools()
    return JSONResponse({
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }
            for tool in tools
        ]
    })


async def tools_call(request: Request) -> JSONResponse:
    """Call a tool."""
    if not verify_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        body = await request.json()
        tool_name = body.get("name")
        arguments = body.get("arguments", {})

        if not tool_name:
            return JSONResponse(
                {"error": "Missing 'name' field"},
                status_code=400,
            )

        client = get_client()
        result = await _execute_tool(client, tool_name, arguments)

        return JSONResponse({
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, default=str),
                }
            ],
        })

    except ValueError as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=400,
        )
    except Exception as e:
        logger.exception("Error calling tool")
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
        )


async def mcp_messages(request: Request) -> Response:
    """
    Handle MCP messages over HTTP (SSE transport).
    This endpoint implements the Streamable HTTP transport for MCP.
    """
    if not verify_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        msg_id = body.get("id")

        result = None

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "capabilities": {
                    "tools": {},
                },
            }

        elif method == "tools/list":
            tools = await list_tools()
            result = {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                    }
                    for tool in tools
                ]
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            client = get_client()
            tool_result = await _execute_tool(client, tool_name, arguments)
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tool_result, indent=2, default=str),
                    }
                ],
            }

        elif method == "notifications/initialized":
            # Client initialized notification - no response needed
            return Response(status_code=204)

        else:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                },
                status_code=400,
            )

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        })

    except Exception as e:
        logger.exception("Error processing MCP message")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in dir() else None,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            },
            status_code=500,
        )


async def sse_endpoint(request: Request) -> StreamingResponse:
    """SSE endpoint for MCP transport."""
    if not verify_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    async def event_generator():
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'server': SERVER_NAME})}\n\n"

        # Keep connection alive
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# OpenAPI schema for documentation
async def openapi_schema(request: Request) -> JSONResponse:
    """Return OpenAPI schema for the MCP server."""
    tools = await list_tools()

    paths = {
        "/health": {
            "get": {
                "summary": "Health Check",
                "description": "Check server health and Sonarr connection",
                "responses": {"200": {"description": "Server is healthy"}},
            }
        },
        "/info": {
            "get": {
                "summary": "Server Info",
                "description": "Get MCP server information",
                "responses": {"200": {"description": "Server information"}},
            }
        },
        "/tools": {
            "get": {
                "summary": "List Tools",
                "description": "List all available MCP tools",
                "responses": {"200": {"description": "List of tools"}},
            }
        },
        "/tools/call": {
            "post": {
                "summary": "Call Tool",
                "description": "Execute an MCP tool",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "arguments": {"type": "object"},
                                },
                                "required": ["name"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "Tool execution result"}},
            }
        },
        "/mcp": {
            "post": {
                "summary": "MCP Messages",
                "description": "Handle MCP JSON-RPC messages",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "jsonrpc": {"type": "string"},
                                    "method": {"type": "string"},
                                    "params": {"type": "object"},
                                    "id": {"type": ["string", "integer"]},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "MCP response"}},
            }
        },
    }

    return JSONResponse({
        "openapi": "3.1.0",
        "info": {
            "title": "MCP Sonarr Server",
            "description": "MCP Server for controlling Sonarr via AI assistants",
            "version": SERVER_VERSION,
        },
        "servers": [
            {"url": "/", "description": "Current server"}
        ],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                }
            }
        },
    })


# ==================== Application Setup ====================

routes = [
    Route("/", endpoint=server_info, methods=["GET"]),
    Route("/health", endpoint=health, methods=["GET"]),
    Route("/info", endpoint=server_info, methods=["GET"]),
    Route("/tools", endpoint=tools_list, methods=["GET"]),
    Route("/tools/call", endpoint=tools_call, methods=["POST"]),
    Route("/mcp", endpoint=mcp_messages, methods=["POST"]),
    Route("/sse", endpoint=sse_endpoint, methods=["GET"]),
    Route("/openapi.json", endpoint=openapi_schema, methods=["GET"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(routes=routes, middleware=middleware)


def main():
    """Run the HTTP server."""
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8080"))

    logger.info(f"Starting MCP Sonarr HTTP server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
