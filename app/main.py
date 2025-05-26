from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.api.routes import sonarr, system, mcp

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_sonarr")
logger.info("Starting MCP Sonarr Plugin")

# Initialize FastAPI app
app = FastAPI(
    title="MCP Sonarr Plugin",
    description="""
    Plugin for managing Sonarr media library through Media Control Protocol.
    
    ## MCP Protocol Support
    
    This server implements the Model Context Protocol (MCP) for integration with OpenAI and other MCP clients.
    
    - The root endpoint (`/`) handles MCP protocol messages using JSON-RPC 2.0
    - Supports MCP initialization, tools/list, and tools/call methods
    - Compatible with OpenAI's MCP client in the Playground
    
    ## Available Endpoints
    
    ### OpenAI Plugin Endpoints
    - `/.well-known/ai-plugin.json`: Plugin manifest
    - `/openapi.yaml` or `/openapi.json`: API specification
    - `/api/v1/tools`: List available tools
    - `/api/v1/schema`: Get tool schemas
    - `/api/v1/call`: Call a specific tool
    - `/test`: Test endpoint (no authentication required)
    
    ### Legacy Endpoints
    - `/mcp/sonarr-status`: Check if Sonarr is accessible
    - `/mcp/sonarr-query`: Execute Sonarr operations
    - `/mcp/sonarr-capabilities`: List available Sonarr operations
    - `/mcp/sonarr-help`: Get help on using Sonarr operations
    - `/mcp/test`: Test endpoint (no authentication required)
    
    All endpoints except `/test` and `/mcp/test` require authentication with a Bearer token.
    """,
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(system.router)
app.include_router(sonarr.router)
app.include_router(mcp.router)

# Root-level test endpoint
@app.get("/test")
async def test_endpoint():
    """A simple test endpoint that doesn't require authentication."""
    return JSONResponse(
        content={"status": "ok", "message": "Test endpoint is working."},
        status_code=200
    )

# Mount static files
app.mount("/.well-known", StaticFiles(directory="static/.well-known"), name="well-known")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve OpenAPI files at root level
@app.get("/openapi.yaml")
async def get_openapi_yaml():
    """Serve the OpenAPI YAML specification."""
    from fastapi.responses import FileResponse
    return FileResponse("static/openapi.yaml")

@app.get("/openapi.json")
async def get_openapi_json():
    """Serve the OpenAPI JSON specification."""
    from fastapi.responses import FileResponse
    return FileResponse("static/openapi.json")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
