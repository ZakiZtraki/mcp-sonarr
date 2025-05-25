# Sonarr MCP Assistant

This is a FastAPI application that provides an API for interacting with Sonarr through an MCP server. It includes an AI plugin configuration for integration with AI assistants.

## Authentication

The API uses Bearer token authentication. You need to include an API key in the `Authorization` header of your requests.

### Setting up API Keys

You have three options for setting up the API key:

1. **Environment Variable**: Set the `MCP_API_KEY` environment variable with your desired API key:

   ```bash
   export MCP_API_KEY=your-api-key-here
   ```

   Or on Windows:

   ```powershell
   $env:MCP_API_KEY = "your-api-key-here"
   ```

2. **Environment File**: Create a `.env` file in the project root with the following content:

   ```
   MCP_API_KEY=your-api-key-here
   ```

3. **Auto-generated Key**: If you don't set an API key, the application will automatically generate a secure key when it starts up. The key will be:
   - Displayed in the console output
   - Saved to a file named `.api_key` in the project root
   - Used consistently across application restarts (as long as the `.api_key` file exists)

### Retrieving the Auto-generated API Key

If you're using the auto-generated API key, you can retrieve it in several ways:

1. **From Console Output**: When the application starts, it will display the API key in the console.

2. **From the API Key File**: The key is saved in the `.api_key` file in the project root:

   ```bash
   cat .api_key
   ```

   Or on Windows:

   ```powershell
   Get-Content .api_key
   ```

3. **From the API**: You can also add an endpoint to retrieve the current API key (only accessible from localhost):

   ```bash
   curl http://localhost:8000/api-key
   ```

### Making Authenticated Requests

Include the API key in the `Authorization` header of your requests:

```bash
curl -H "Authorization: Bearer your-api-key-here" https://your-server/mcp/sonarr-status
```

## Sonarr API Configuration

The application also connects to a Sonarr instance. You need to configure the Sonarr API settings:

> **IMPORTANT**: Never commit your actual API keys or URLs to the repository. Always use environment variables or a `.env` file that is excluded from version control (add `.env` to your `.gitignore` file).

1. Set the following environment variables:

   ```bash
   export SONARR_API_KEY=your-sonarr-api-key
   export SONARR_API_URL=https://your-sonarr-instance/api
   ```

   Or on Windows:

   ```powershell
   $env:SONARR_API_KEY = "your-sonarr-api-key"
   $env:SONARR_API_URL = "https://your-sonarr-instance/api"
   ```

2. You can also add these to your `.env` file:

   ```
   SONARR_API_KEY=your-sonarr-api-key
   SONARR_API_URL=https://your-sonarr-instance/api
   ```

   A sample `.env.example` file is provided in the repository. You can copy it to create your own `.env` file:

   ```bash
   cp .env.example .env
   ```

   Then edit the `.env` file with your actual API key and URL.

## Running the Application

1. Install the required dependencies:

   ```bash
   pip install fastapi uvicorn httpx pydantic pydantic-settings python-dotenv
   ```

2. Run the application:

   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

3. Generate the OpenAPI schema:

   ```bash
   python generate_openapi.py
   ```

## AI Plugin Configuration

The AI plugin configuration is located at `static/.well-known/ai-plugin.json`. It uses service_http authentication with a bearer token.

To use the plugin with an AI assistant, you need to:

1. Host the application on a publicly accessible server
2. Configure the AI assistant to use the plugin
3. Provide the API key when prompted by the AI assistant

## API Endpoints

- `POST /mcp/sonarr-query`: Query Sonarr with an intent
- `GET /mcp/sonarr-capabilities`: List available Sonarr capabilities
- `GET /mcp/sonarr-help`: Get help information for Sonarr commands
- `GET /mcp/sonarr-operation-params/{operation_id}`: Get parameters for a specific operation
- `GET /mcp/sonarr-status`: Check if the Sonarr API is accessible and the API key is valid