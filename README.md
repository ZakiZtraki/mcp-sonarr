# MCP Sonarr Server

A Model Context Protocol (MCP) server that enables AI assistants like Claude and ChatGPT to control your Sonarr instance. Manage your TV series library, search for shows, monitor downloads, and get statistics through natural language.

## Features

- **Series Management**: Search, add, update, and delete TV series
- **Episode Management**: View episodes, track downloads, manage files
- **Download Queue**: Monitor and manage current downloads
- **Calendar**: View upcoming episodes
- **Statistics**: Get comprehensive library statistics
- **System Status**: Health checks, disk space, and configuration info
- **Remote Access**: HTTP API for integration with Claude/ChatGPT
- **Docker Support**: Easy deployment with Docker and docker-compose

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/ZakiZtraki/mcp-sonarr.git
cd mcp-sonarr
```

2. Create your environment file:
```bash
cp .env.example .env
```

3. Edit `.env` with your Sonarr details:
```env
SONARR_URL=https://sonarr.zenmedia.live
SONARR_API_KEY=your-api-key-here
MCP_AUTH_TOKEN=your-secure-token  # Optional but recommended
```

4. Start the server:
```bash
docker-compose up -d
```

The MCP server will be available at `http://localhost:8080`.

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/ZakiZtraki/mcp-sonarr.git
cd mcp-sonarr
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set environment variables:
```bash
export SONARR_URL=https://sonarr.zenmedia.live
export SONARR_API_KEY=your-api-key-here
```

4. Run the server:
```bash
# For HTTP server (remote access)
python -m mcp_sonarr.http_server

# For stdio server (local MCP client)
mcp-sonarr
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SONARR_URL` | Yes | URL of your Sonarr instance |
| `SONARR_API_KEY` | Yes | Sonarr API key (Settings -> General -> API Key) |
| `MCP_AUTH_TOKEN` | No | Simple Bearer token for API authentication |
| `MCP_HOST` | No | Server host (default: `0.0.0.0`) |
| `MCP_PORT` | No | Server port (default: `8080`) |

#### OAuth 2.0 Configuration (for ChatGPT)

| Variable | Required | Description |
|----------|----------|-------------|
| `OAUTH_CLIENT_ID` | For OAuth | OAuth client ID (provide to ChatGPT) |
| `OAUTH_CLIENT_SECRET` | For OAuth | OAuth client secret (provide to ChatGPT) |
| `OAUTH_AUTH_PASSWORD` | For OAuth | Password for the authorization form |
| `OAUTH_JWT_SECRET` | No | Secret for signing JWTs (auto-generated if not set) |
| `OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token expiry in minutes (default: `60`) |

## Integration with AI Assistants

### Claude Desktop

Add to your Claude Desktop configuration (`~/.config/claude/claude_desktop_config.json` on Linux/Mac or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "sonarr": {
      "command": "mcp-sonarr",
      "env": {
        "SONARR_URL": "https://sonarr.zenmedia.live",
        "SONARR_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Claude (Remote MCP Server)

For Claude with remote MCP server support, configure the HTTP endpoint:

```json
{
  "mcpServers": {
    "sonarr": {
      "type": "http",
      "url": "https://your-mcp-server.com/mcp",
      "headers": {
        "Authorization": "Bearer your-auth-token"
      }
    }
  }
}
```

### ChatGPT (with OAuth Authentication)

ChatGPT supports OAuth 2.0 for authenticating with MCP servers. Here's how to set it up:

#### 1. Configure OAuth on Your Server

Set these environment variables on your MCP server:

```env
# Generate secure values for these
OAUTH_CLIENT_ID=my-chatgpt-client
OAUTH_CLIENT_SECRET=your-super-secret-value-here
OAUTH_AUTH_PASSWORD=your-authorization-password
```

#### 2. Configure ChatGPT Custom Action

In ChatGPT, create a new GPT or edit an existing one:

1. Go to **Configure** → **Actions** → **Create new action**
2. Set the **Authentication** type to **OAuth**
3. Enter the following OAuth settings:
   - **Client ID**: Your `OAUTH_CLIENT_ID` value
   - **Client Secret**: Your `OAUTH_CLIENT_SECRET` value
   - **Authorization URL**: `https://your-mcp-server.com/oauth/authorize`
   - **Token URL**: `https://your-mcp-server.com/oauth/token`
   - **Scope**: `full` (or leave empty)

4. Import the OpenAPI schema from your server, or manually configure the MCP endpoint:
   - **Server URL**: `https://your-mcp-server.com`

#### 3. Authorize Access

When ChatGPT tries to use your MCP server for the first time:
1. You'll be redirected to the authorization page
2. Enter your `OAUTH_AUTH_PASSWORD`
3. Click **Authorize**
4. ChatGPT will receive an access token and can now call your MCP tools

The OAuth flow follows the standard Authorization Code grant type, which ChatGPT handles automatically.

### ChatGPT (Simple Bearer Token)

For simpler setups without OAuth, you can use a Bearer token:

1. Set `MCP_AUTH_TOKEN=your-secure-token` on your server
2. In ChatGPT, configure the action with **API Key** authentication
3. Set the header to `Authorization: Bearer your-secure-token`

## Available Tools

### System & Statistics

| Tool | Description |
|------|-------------|
| `sonarr_system_status` | Get Sonarr system information |
| `sonarr_health_check` | Check for any issues |
| `sonarr_get_statistics` | Get comprehensive library statistics |
| `sonarr_get_disk_space` | View disk space for root folders |
| `sonarr_get_root_folders` | List configured root folders |
| `sonarr_get_quality_profiles` | List quality profiles |
| `sonarr_get_tags` | List all tags |

### Series Management

| Tool | Description |
|------|-------------|
| `sonarr_get_all_series` | List all series in library |
| `sonarr_get_series` | Get details for a specific series |
| `sonarr_search_new_series` | Search for series to add |
| `sonarr_add_series` | Add a new series |
| `sonarr_delete_series` | Remove a series |

### Episodes

| Tool | Description |
|------|-------------|
| `sonarr_get_episodes` | List episodes for a series |
| `sonarr_get_episode_files` | List downloaded files for a series |

### Calendar & Queue

| Tool | Description |
|------|-------------|
| `sonarr_get_calendar` | View upcoming episodes |
| `sonarr_get_queue` | View download queue |
| `sonarr_delete_queue_item` | Remove item from queue |

### History & Wanted

| Tool | Description |
|------|-------------|
| `sonarr_get_history` | View download history |
| `sonarr_get_missing_episodes` | List missing episodes |

### Commands

| Tool | Description |
|------|-------------|
| `sonarr_search_series` | Search for all episodes of a series |
| `sonarr_search_season` | Search for a specific season |
| `sonarr_refresh_series` | Refresh series metadata |
| `sonarr_rescan_series` | Rescan disk for files |
| `sonarr_rss_sync` | Trigger RSS sync |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/info` | GET | Server information |
| `/mcp` | POST | MCP Streamable HTTP endpoint (for ChatGPT/Claude) |
| `/oauth/authorize` | GET, POST | OAuth 2.0 authorization endpoint |
| `/oauth/token` | POST | OAuth 2.0 token endpoint |
| `/.well-known/oauth-authorization-server` | GET | OAuth 2.0 server metadata |

The `/mcp` endpoint implements the full MCP protocol over HTTP, supporting:
- `initialize` - Initialize the MCP session
- `tools/list` - List available tools
- `tools/call` - Execute a tool

## Example Usage

### Get Library Statistics
```
"Hey Claude, can you show me my Sonarr library statistics?"
```

### Search and Add a Series
```
"Search for 'Breaking Bad' on Sonarr and add it to my library"
```

### Check Download Queue
```
"What's currently downloading in Sonarr?"
```

### View Upcoming Episodes
```
"What episodes are coming up this week?"
```

### Find Missing Episodes
```
"Show me which episodes are missing from my library"
```

## Security Considerations

1. **Use HTTPS**: Always deploy behind a reverse proxy with TLS
2. **Enable Authentication**: Use OAuth (`OAUTH_*` variables) or simple Bearer token (`MCP_AUTH_TOKEN`)
3. **Strong Secrets**: Use long, random values for `OAUTH_CLIENT_SECRET` and `OAUTH_AUTH_PASSWORD`
4. **Firewall**: Limit access to trusted networks/IPs
5. **API Key Security**: Never expose your Sonarr API key publicly
6. **Token Expiry**: Adjust `OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES` based on your security requirements

## Deployment with Traefik

Example `docker-compose.yml` for Traefik:

```yaml
version: '3.8'

services:
  mcp-sonarr:
    build: .
    environment:
      - SONARR_URL=https://sonarr.zenmedia.live
      - SONARR_API_KEY=${SONARR_API_KEY}
      - MCP_AUTH_TOKEN=${MCP_AUTH_TOKEN}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-sonarr.rule=Host(`mcp-sonarr.yourdomain.com`)"
      - "traefik.http.routers.mcp-sonarr.entrypoints=websecure"
      - "traefik.http.routers.mcp-sonarr.tls.certresolver=letsencrypt"
    networks:
      - traefik

networks:
  traefik:
    external: true
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/ZakiZtraki/mcp-sonarr.git
cd mcp-sonarr

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Project Structure

```
mcp-sonarr/
├── src/
│   └── mcp_sonarr/
│       ├── __init__.py
│       ├── server.py        # MCP server (stdio transport)
│       ├── http_server.py   # HTTP server (remote access)
│       ├── sonarr_client.py # Sonarr API client
│       └── auth.py          # OAuth 2.0 authentication
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

- **Issues**: [GitHub Issues](https://github.com/ZakiZtraki/mcp-sonarr/issues)
- **Sonarr API Docs**: [Sonarr Wiki](https://wiki.servarr.com/sonarr/api)
- **MCP Specification**: [MCP Docs](https://modelcontextprotocol.io/)
