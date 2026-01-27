# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Sonarr is a Model Context Protocol (MCP) server that allows AI assistants (Claude, ChatGPT) to control a Sonarr instance for TV series management. It provides both stdio transport (for local MCP clients like Claude Desktop) and HTTP transport (for remote access).

## Build and Run Commands

```bash
# Install dependencies (development)
pip install -e ".[dev]"

# Run HTTP server (remote access, default port 8080)
python -m mcp_sonarr.http_server

# Run stdio server (local MCP client)
mcp-sonarr

# Run tests
pytest

# Run single test file
pytest tests/test_client.py

# Run specific test
pytest tests/test_client.py::TestSonarrClient::test_get_system_status

# Linting
ruff check .
black --check .

# Format code
black .
```

## Docker Commands

```bash
# Build and run with docker-compose
docker-compose up -d

# Rebuild after changes
docker-compose up -d --build

# View logs
docker-compose logs -f
```

## Architecture

The codebase has three main components:

1. **`sonarr_client.py`** - Async HTTP client wrapping Sonarr's v3 API. Uses httpx for requests and pydantic for configuration. All API methods are async and follow the pattern `_get`, `_post`, `_put`, `_delete` for HTTP operations.

2. **`server.py`** - MCP server implementation using stdio transport. Defines all available tools via the `@server.list_tools()` decorator and handles tool execution in `@server.call_tool()`. The `_execute_tool()` function routes tool calls to the appropriate client methods.

3. **`http_server.py`** - Starlette-based HTTP server providing REST endpoints and MCP JSON-RPC over HTTP. Imports and reuses tool definitions from `server.py`. Supports optional Bearer token authentication via `MCP_AUTH_TOKEN` environment variable.

## Key Patterns

- Tools are defined with JSON schemas in `list_tools()` and executed in `_execute_tool()` - both in `server.py`
- The Sonarr client is lazily initialized via `get_client()` using environment variables
- HTTP server reuses `list_tools` and `_execute_tool` from the stdio server module
- All Sonarr API responses are simplified/transformed before returning to reduce noise

## Environment Variables

- `SONARR_URL` (required) - Sonarr instance URL
- `SONARR_API_KEY` (required) - Sonarr API key
- `MCP_AUTH_TOKEN` (optional) - Bearer token for HTTP server auth
- `MCP_HOST` (default: 0.0.0.0) - HTTP server bind address
- `MCP_PORT` (default: 8080) - HTTP server port

## Testing

Tests use pytest-asyncio with mocked HTTP calls. The `@pytest.mark.asyncio` decorator is required for async tests. Fixtures provide `SonarrConfig` and `SonarrClient` instances.
