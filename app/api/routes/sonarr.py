from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import validate_token
from app.models.api import SonarrQueryModel, TextResponse, JsonResponse, StatusResponse, OperationParamsResponse
from app.services.sonarr_service import sonarr_service

router = APIRouter(prefix="/mcp", tags=["sonarr"])

@router.post("/sonarr-query", response_model=TextResponse)
async def sonarr_query(request: SonarrQueryModel, api_key: str = Depends(validate_token)):
    intent = request.intent.lower()
    result = sonarr_service.call_sonarr_operation(intent, {"input": request.input})
    return {"type": "text", "content": str(result)}

@router.get("/sonarr-capabilities", response_model=JsonResponse)
async def list_sonarr_capabilities(api_key: str = Depends(validate_token)):
    commands = sonarr_service.extract_sonarr_commands()
    return {"type": "json", "commands": [cmd.dict() for cmd in commands]}

@router.get("/sonarr-help", response_model=TextResponse)
async def sonarr_help(api_key: str = Depends(validate_token)):
    commands = sonarr_service.extract_sonarr_commands()
    lines = [
        f"- **{cmd.operationId}** ({cmd.method} {cmd.path}): {cmd.summary or 'No description'}"
        for cmd in commands
    ]
    return {"type": "text", "content": "\n".join(lines)}

@router.get("/sonarr-operation-params/{operation_id}", response_model=OperationParamsResponse)
async def get_required_params(operation_id: str, api_key: str = Depends(validate_token)):
    params = sonarr_service.get_operation_parameters(operation_id)
    return {"operationId": operation_id, "parameters": params}

@router.get("/sonarr-status", response_model=StatusResponse)
async def get_sonarr_status(api_key: str = Depends(validate_token)):
    """Check if the Sonarr API is accessible and the API key is valid."""
    if sonarr_service.validate_api_key():
        return {"status": "ok", "message": "Sonarr API is accessible and API key is valid."}
    else:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key or Sonarr server is not accessible."
        )
