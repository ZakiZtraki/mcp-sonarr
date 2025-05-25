from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union

class SonarrQueryModel(BaseModel):
    """Model for Sonarr query requests."""
    intent: str
    input: Optional[str] = None
    user_id: Optional[str] = None

class TextResponse(BaseModel):
    """Model for text responses."""
    type: str = "text"
    content: str

class JsonResponse(BaseModel):
    """Model for JSON responses."""
    type: str = "json"
    commands: List[Dict[str, Any]]

class StatusResponse(BaseModel):
    """Model for status responses."""
    status: str
    message: str

class OperationParamsResponse(BaseModel):
    """Model for operation parameters responses."""
    operationId: str
    parameters: List[Dict[str, Any]]

class WelcomeResponse(BaseModel):
    """Model for welcome message response."""
    message: str

class ApiKeyResponse(BaseModel):
    """Model for API key response."""
    api_key: str
