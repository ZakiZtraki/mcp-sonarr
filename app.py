from fastapi import FastAPI, Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uuid
import secrets
from sonarr import router as sonarr_router

# Initialize FastAPI app
app = FastAPI(
    title="Sonarr MCP API",
    description="API for interacting with Sonarr through MCP",
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

# Security scheme
security = HTTPBearer()

# Function to generate a secure API key
def generate_api_key():
    """Generate a secure API key using a combination of UUID and random bytes."""
    # Create a base using UUID4 (random UUID)
    uuid_part = str(uuid.uuid4()).replace('-', '')
    # Add some additional randomness with secrets
    random_part = secrets.token_hex(8)
    # Combine them
    return f"{uuid_part}{random_part}"

# API key from environment variable with auto-generated fallback
API_KEY_FILE = ".api_key"

# Check if API key is in environment variable
API_KEY = os.getenv("MCP_API_KEY")

# If not in environment, check if we have a saved key
if not API_KEY and os.path.exists(API_KEY_FILE):
    try:
        with open(API_KEY_FILE, "r") as f:
            API_KEY = f.read().strip()
    except Exception as e:
        print(f"Error reading API key file: {e}")

# If still no API key, generate one and save it
if not API_KEY:
    API_KEY = generate_api_key()
    try:
        with open(API_KEY_FILE, "w") as f:
            f.write(API_KEY)
        print(f"Generated new API key: {API_KEY}")
        print(f"This key has been saved to {API_KEY_FILE}")
    except Exception as e:
        print(f"Warning: Could not save API key to file: {e}")
        print(f"Your API key is: {API_KEY}")
        print("Please save this key as it will be required for authentication.")

# Dependency for API key validation
async def validate_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Include the Sonarr router
app.include_router(sonarr_router, dependencies=[Depends(validate_token)])

# Mount static files
app.mount("/.well-known", StaticFiles(directory="static/.well-known"), name="well-known")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint
@app.get(
    "/", 
    dependencies=[],
    summary="API Welcome Page",
    description="Welcome page for the Sonarr MCP API. This endpoint does not require authentication.",
    response_description="Welcome message",
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

# API key retrieval endpoint (only accessible from localhost)
@app.get(
    "/api-key", 
    dependencies=[],
    summary="Retrieve API Key",
    description="Retrieves the current API key. This endpoint is only accessible from localhost for security reasons.",
    response_description="Returns the API key that should be used for authentication",
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
async def get_api_key_endpoint(request: Request):
    client_host = request.client.host
    if client_host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only accessible from localhost"
        )
    return {"api_key": API_KEY}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)