#!/usr/bin/env python3
"""
Generate OpenAPI schema for the MCP Sonarr Plugin - Clean version.
"""
import os
import json
import yaml
from pathlib import Path

# Import the FastAPI app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main_clean import app

# Get the OpenAPI schema
openapi_schema = app.openapi()

# Add security schemes
openapi_schema["components"]["securitySchemes"] = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
}

# Define paths that should not require authentication
public_paths = [
    "/api-key",             # API key retrieval endpoint
    "/",                    # Root endpoint
    "/test",                # Root test endpoint
    "/api/v1/tools",        # OpenAI tools listing endpoint
    "/api/v1/schema",       # OpenAI schema endpoint
    "/api/v1/openai-tools", # OpenAI function calling format tools
    "/openapi.yaml",        # OpenAPI YAML specification
    "/openapi.json"         # OpenAPI JSON specification
]

# Add security requirement to paths (except public ones)
for path in openapi_schema["paths"]:
    for method in openapi_schema["paths"][path]:
        if path not in public_paths:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

# Create the static directory if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# Create the .well-known directory if it doesn't exist
well_known_dir = static_dir / ".well-known"
well_known_dir.mkdir(exist_ok=True)

# Write the OpenAPI schema to a JSON file
with open(static_dir / "openapi.json", "w") as f:
    json.dump(openapi_schema, f, indent=2)

# Write the OpenAPI schema to a YAML file
with open(static_dir / "openapi.yaml", "w") as f:
    yaml.dump(openapi_schema, f, sort_keys=False)

# Create the ai-plugin.json file
ai_plugin = {
    "schema_version": "v1",
    "name_for_human": "Sonarr Plugin",
    "name_for_model": "sonarr",
    "description_for_human": "Plugin for managing your Sonarr media library.",
    "description_for_model": "Plugin for managing Sonarr media library. Use this plugin to search for TV series, add them to your library, and manage your media collection.",
    "auth": {
        "type": "service_http",
        "authorization_type": "bearer"
    },
    "api": {
        "type": "openapi",
        "url": "https://your-server-url/openapi.json"
    },
    "logo_url": "https://your-server-url/static/logo.png",
    "contact_email": "contact@example.com",
    "legal_info_url": "https://example.com/legal"
}

# Write the ai-plugin.json file
with open(well_known_dir / "ai-plugin.json", "w") as f:
    json.dump(ai_plugin, f, indent=2)

print("OpenAPI schema generated successfully.")
print(f"JSON schema: {static_dir / 'openapi.json'}")
print(f"YAML schema: {static_dir / 'openapi.yaml'}")
print(f"AI Plugin manifest: {well_known_dir / 'ai-plugin.json'}")

# Create a simple logo file if it doesn't exist
logo_path = static_dir / "logo.png"
if not logo_path.exists():
    # This is a simple 1x1 transparent PNG
    transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x00\x00\x02\x00\x01\xe5\'\xde\xfc\x00\x00\x00\x00IEND\xaeB`\x82'
    with open(logo_path, "wb") as f:
        f.write(transparent_png)
    print(f"Created placeholder logo: {logo_path}")