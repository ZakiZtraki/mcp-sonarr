import json
import yaml
import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Get the OpenAPI schema as a dictionary
openapi_schema = app.openapi()

# Print all paths for debugging
print("Available paths in OpenAPI schema:")
for path in openapi_schema["paths"]:
    print(f"  {path}")

# Add security schemes
openapi_schema["components"] = openapi_schema.get("components", {})
openapi_schema["components"]["securitySchemes"] = {
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
}

# Define paths that should not require authentication
public_paths = [
    "/api-key",         # API key retrieval endpoint
    "/",                # Root endpoint
    "/test",            # Root test endpoint
    "/mcp/test",        # Legacy test endpoint
    "/api/v1/tools",    # OpenAI tools listing endpoint
    "/api/v1/schema",   # OpenAI schema endpoint
    "/mcp_list_tools",  # Legacy MCP tool listing endpoint
    "/mcp_tool_schema", # Legacy MCP tool schema endpoint
    "/openapi.yaml",    # OpenAPI YAML specification
    "/openapi.json"     # OpenAPI JSON specification
]

# Add security requirement to paths (except public ones)
for path in openapi_schema["paths"]:
    for method in openapi_schema["paths"][path]:
        # Skip security for public paths
        if path in public_paths:
            # Remove security if it exists
            if "security" in openapi_schema["paths"][path][method]:
                del openapi_schema["paths"][path][method]["security"]
        else:
            # Add security for protected paths
            openapi_schema["paths"][path][method]["security"] = [{"bearerAuth": []}]

# Ensure the static directories exist
os.makedirs("static/.well-known", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Save as JSON in both locations
with open("static/.well-known/openapi.json", "w") as f:
    json.dump(openapi_schema, f, indent=2)

with open("static/openapi.json", "w") as f:
    json.dump(openapi_schema, f, indent=2)

# Save as YAML in both locations
with open("static/.well-known/openapi.yaml", "w") as f:
    yaml.dump(openapi_schema, f, sort_keys=False)

with open("static/openapi.yaml", "w") as f:
    yaml.dump(openapi_schema, f, sort_keys=False)

print("OpenAPI schema generated successfully in both locations!")
