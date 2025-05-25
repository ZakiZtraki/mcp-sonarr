from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import get_or_create_api_key

# Security scheme
security = HTTPBearer()

# Get the API key
API_KEY = get_or_create_api_key()

# Dependency for API key validation
async def validate_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Dependency to check if request is from localhost
async def ensure_localhost(request: Request):
    client_host = request.client.host
    if client_host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only accessible from localhost"
        )
    return True
