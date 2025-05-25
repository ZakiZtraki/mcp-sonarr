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
async def root():
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
