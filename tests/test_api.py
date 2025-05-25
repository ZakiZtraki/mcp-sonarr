from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint returns the welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Sonarr MCP API"}

# Add more tests as needed
