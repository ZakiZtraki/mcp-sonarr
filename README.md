# Sonarr MCP Assistant

This is a FastAPI application that provides an API for interacting with Sonarr through an MCP server. It includes an AI plugin configuration for integration with AI assistants.

## Project Structure

The project has been refactored to follow a more modular and maintainable structure:

```
mcp-sonarr/
│
├── app/                              # Main application package
│   ├── __init__.py                   # Package initializer
│   ├── main.py                       # Application entry point
│   ├── config/                       # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py               # Application settings and environment variables
│   │   └── security.py               # Security and authentication logic
│   │
│   ├── api/                          # API routes and endpoints
│   │   ├── __init__.py
│   │   ├── routes/                   # Route definitions
│   │   │   ├── __init__.py
│   │   │   ├── sonarr.py             # Sonarr-specific routes
│   │   │   └── system.py             # System and authentication routes
│   │   │
│   │   └── dependencies.py           # Shared API dependencies
│   │
│   ├── core/                         # Core application logic
│   │   ├── __init__.py
│   │   ├── security.py               # Security utilities
│   │   └── utils.py                  # General utilities
│   │
│   ├── services/                     # Service layer
│   │   ├── __init__.py
│   │   └── sonarr_service.py         # Sonarr API interaction logic
│   │
│   └── models/                       # Data models
│       ├── __init__.py
│       ├── sonarr.py                 # Sonarr-specific models
│       └── api.py                    # API request/response models
│
├── static/                           # Static files
│   └── .well-known/
│       ├── ai-plugin.json
│       ├── openapi.json
│       └── openapi.yaml
│
├── scripts/                          # Utility scripts
│   └── generate_openapi.py           # Script to generate OpenAPI schema
│
├── tests/                            # Tests directory
│   ├── __init__.py
│   ├── test_api.py
│   └── test_sonarr_service.py
│
├── .env.example                      # Example environment file
├── .gitignore                        # Git ignore file
├── README.md                         # Project documentation
├── requirements.txt                  # Project dependencies
├── Dockerfile                        # Docker configuration
├── docker-compose.yaml               # Docker Compose configuration
└── run.py                            # Convenience script to run the application
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- A Sonarr instance with API access
- Git (optional, for cloning the repository)

### Installation

1. **Clone or download the repository**:

   Using Git:
   ```bash
   git clone https://github.com/ZakiZtraki/mcp-sonarr.git
   cd mcp-sonarr
   ```

   Alternatively, you can download the ZIP file from GitHub and extract it.

2. **Set up a virtual environment** (recommended):

   On Linux/macOS:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

   On Windows:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** as described in the sections below.

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

3. **From the API**: You can also retrieve the current API key (only accessible from localhost):

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

### Standard Method

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:

   ```bash
   python run.py
   ```

   Or directly with uvicorn:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Generate the OpenAPI schema:

   ```bash
   python scripts/generate_openapi.py
   ```

### Using Docker Compose (Recommended)

For the easiest deployment, you can use Docker Compose:

1. Make sure you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

2. Create a `.env` file with your Sonarr API settings:

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file with your actual Sonarr API key and URL.

3. Start the application using Docker Compose:

   ```bash
   docker compose up -d
   ```

   This will build the Docker image and start the container in detached mode.

4. Check the logs to see the auto-generated API key (if you didn't specify one):

   ```bash
   docker compose logs
   ```

5. To stop the application:

   ```bash
   docker compose down
   ```

## API Endpoints

### OpenAI Plugin Endpoints
- `/.well-known/ai-plugin.json`: Plugin manifest
- `/openapi.yaml` or `/openapi.json`: API specification
- `/api/v1/tools`: List available tools
- `/api/v1/schema`: Get tool schemas
- `/api/v1/call`: Call a specific tool
- `/test`: Test endpoint (no authentication required)

### Legacy Endpoints
- `POST /mcp/sonarr-query`: Query Sonarr with an intent
- `GET /mcp/sonarr-capabilities`: List available Sonarr capabilities
- `GET /mcp/sonarr-help`: Get help information for Sonarr commands
- `GET /mcp/sonarr-operation-params/{operation_id}`: Get parameters for a specific operation
- `GET /mcp/sonarr-status`: Check if the Sonarr API is accessible and the API key is valid
- `/mcp_list_tools`: Legacy MCP tool listing endpoint
- `/mcp_tool_schema`: Legacy MCP tool schema endpoint
- `/mcp_call_tool`: Legacy MCP tool call endpoint

## AI Plugin Configuration

The AI plugin configuration is located at `static/.well-known/ai-plugin.json`. It uses service_http authentication with a bearer token.

### OpenAI Plugin Integration

The plugin supports direct tool calls to the root endpoint (`/`). OpenAI can send tool calls in the following format:

```json
{
  "name": "search_series",
  "arguments": {
    "title": "Breaking Bad"
  }
}
```

Available tools:
- `search_series`: Search for TV series by title
- `get_series`: Get details about a specific TV series by ID
- `add_series`: Add a new TV series to Sonarr
- `get_calendar`: Get upcoming episodes from the Sonarr calendar

To use the plugin with an AI assistant, you need to:

1. Host the application on a publicly accessible server
2. Configure the AI assistant to use the plugin
3. Provide the API key when prompted by the AI assistant

### Disclaimer: AI Assistant Access and User Responsibility

**IMPORTANT: Please read this section carefully before using this integration.**

By using this MCP server integration with AI assistants, you acknowledge and agree to the following:

1. **Access Level**: This integration grants AI assistants the ability to interact with your Sonarr instance through the API. This includes the ability to:
   - View your media library and download history
   - Add, modify, or delete series from your library
   - Trigger searches and downloads
   - Access system information from your Sonarr instance

2. **User Responsibility**: 
   - You are solely responsible for the installation, configuration, and use of this MCP server
   - You should only provide API access to AI assistants you trust
   - You should regularly monitor the actions performed through this integration
   - Consider using a Sonarr API key with limited permissions if possible

3. **Security Considerations**:
   - Exposing this service to the internet carries inherent security risks
   - Always use strong, unique API keys and proper authentication
   - Consider implementing additional security measures like a reverse proxy with authentication

4. **Liability Limitation**:
   - The developers of this integration are not responsible for any unexpected behavior, data loss, or security issues that may arise from its use
   - Use this integration at your own risk
   - Test in a non-production environment before deploying to your main Sonarr instance

5. **Privacy Implications**:
   - Be aware that when using AI assistants with this integration, information about your media library may be processed by the AI service
   - Review the privacy policy of any AI assistant you connect to this integration

## Development

### Running Tests

To run the tests:

```bash
pytest
```

### Generating OpenAPI Schema

To generate the OpenAPI schema:

```bash
python scripts/generate_openapi.py
```

## Troubleshooting

### Common Issues

1. **"Error: SONARR_API_KEY environment variable is not set"**
   - Make sure you've set the SONARR_API_KEY environment variable or added it to your .env file
   - Verify that your .env file is in the correct location (project root)

2. **"Error: SONARR_API_URL environment variable is not set"**
   - Make sure you've set the SONARR_API_URL environment variable or added it to your .env file
   - The URL should include the full path to the API (e.g., https://sonarr.example.com/api)

3. **"API key validation failed"**
   - Verify that your Sonarr instance is running and accessible
   - Check that the API key is correct and has the necessary permissions in Sonarr
   - Ensure there are no network issues preventing access to your Sonarr instance

4. **"This endpoint is only accessible from localhost"**
   - The /api-key endpoint is restricted to localhost for security reasons
   - Access this endpoint only from the same machine where the server is running

### Getting Help

If you encounter issues not covered here, please:
1. Check the application logs for more detailed error messages
2. Open an issue on the GitHub repository with details about your problem
3. Include relevant error messages and your environment configuration (without sensitive information)