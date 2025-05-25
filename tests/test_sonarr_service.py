import pytest
from unittest.mock import patch, MagicMock
from app.services.sonarr_service import SonarrService
import json

@pytest.fixture
def mock_sonarr_service():
    with patch("app.services.sonarr_service.httpx") as mock_httpx:
        with patch("app.services.sonarr_service.settings") as mock_settings:
            # Configure the mock settings
            mock_settings.SONARR_API_KEY = "test_api_key"
            mock_settings.SONARR_API_URL = "https://test.sonarr.com/api"
            
            # Create the service which will use our mocked settings
            service = SonarrService()
            
            # Configure the mock HTTP responses
            mock_httpx.get.return_value = MagicMock()
            mock_httpx.get.return_value.raise_for_status = MagicMock()
            mock_httpx.get.return_value.json.return_value = {}
            
            yield service, mock_httpx

def test_validate_api_key(mock_sonarr_service):
    """Test that validate_api_key makes the correct API call."""
    service, mock_httpx = mock_sonarr_service
    result = service.validate_api_key()
    assert result is True
    mock_httpx.get.assert_called_once_with(
        "https://test.sonarr.com/api/system/status",
        headers={"X-Api-Key": "test_api_key"},
        timeout=10
    )

def test_validate_api_key_missing_key(mock_sonarr_service):
    """Test that validate_api_key returns False when API key is missing."""
    service, mock_httpx = mock_sonarr_service
    # Set API key to empty string
    service.api_key = ""
    result = service.validate_api_key()
    assert result is False
    # Ensure no HTTP request was made
    mock_httpx.get.assert_not_called()

def test_validate_api_key_missing_url(mock_sonarr_service):
    """Test that validate_api_key returns False when API URL is missing."""
    service, mock_httpx = mock_sonarr_service
    # Set API URL to empty string
    service.api_url = ""
    result = service.validate_api_key()
    assert result is False
    # Ensure no HTTP request was made
    mock_httpx.get.assert_not_called()

@patch("app.services.sonarr_service.load_sonarr_openapi")
def test_extract_sonarr_commands(mock_load_openapi, mock_sonarr_service):
    """Test that extract_sonarr_commands correctly parses the OpenAPI schema."""
    service, _ = mock_sonarr_service
    
    # Mock the OpenAPI schema
    mock_openapi = {
        "paths": {
            "/series": {
                "get": {
                    "operationId": "getSeries",
                    "summary": "Get all series",
                    "tags": ["Series"]
                }
            },
            "/series/{id}": {
                "get": {
                    "operationId": "getSeriesById",
                    "summary": "Get series by ID",
                    "tags": ["Series"]
                }
            }
        }
    }
    mock_load_openapi.return_value = mock_openapi
    
    commands = service.extract_sonarr_commands()
    assert len(commands) == 2
    assert commands[0].operationId == "getSeries"
    assert commands[0].method == "GET"
    assert commands[0].path == "/series"
    assert commands[0].summary == "Get all series"
    assert commands[0].tag == "Series"
    
    assert commands[1].operationId == "getSeriesById"
    assert commands[1].method == "GET"
    assert commands[1].path == "/series/{id}"
    assert commands[1].summary == "Get series by ID"
    assert commands[1].tag == "Series"

@patch("app.services.sonarr_service.load_sonarr_openapi")
def test_get_operation_parameters(mock_load_openapi, mock_sonarr_service):
    """Test that get_operation_parameters returns the correct parameters."""
    service, _ = mock_sonarr_service
    
    # Mock the OpenAPI schema
    mock_openapi = {
        "paths": {
            "/series/{id}": {
                "get": {
                    "operationId": "getSeriesById",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ]
                }
            }
        }
    }
    mock_load_openapi.return_value = mock_openapi
    
    params = service.get_operation_parameters("getSeriesById")
    assert len(params) == 1
    assert params[0]["name"] == "id"
    assert params[0]["in"] == "path"
    assert params[0]["required"] is True

# Add more tests as needed
