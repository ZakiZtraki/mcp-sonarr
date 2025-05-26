# MCP-Sonarr: Clean Version

This is the clean version of the MCP-Sonarr integration, focusing exclusively on OpenAI function calling format without legacy endpoints.

## Overview

This implementation provides a direct integration between Sonarr's API and OpenAI's function calling format. It dynamically converts Sonarr's OpenAPI schema to OpenAI-compatible tools, allowing an AI to discover and use the full range of Sonarr's API capabilities.

## Key Features

1. **Dynamic Tool Generation**: Tools are generated directly from Sonarr's OpenAPI schema, ensuring they stay up-to-date with the API.

2. **Progressive Discovery**: The AI can discover tools as needed through meta-tools, rather than loading all possible tools upfront.

3. **OpenAI Function Calling Format**: All tools are provided in OpenAI's function calling format for seamless integration.

4. **Security and Control**: Proper authentication and error handling ensure secure access to the Sonarr API.

## How It Works

1. **Initial Connection**: When an AI connects to the MCP server, it receives a limited set of core tools, including meta-tools for discovery.

2. **Tool Discovery**: The AI can use the `discover_tools` meta-tool to find additional tools based on categories or keywords.

3. **Schema Retrieval**: Once the AI discovers a tool, it can use the `get_tool_schema` meta-tool to get detailed information about the tool's parameters and return values.

4. **Tool Usage**: With the schema information, the AI can call the tool through the standard API endpoint.

## API Endpoints

- `/api/v1/tools`: List available tools
- `/api/v1/schema`: Get tool schemas
- `/api/v1/call`: Call a specific tool
- `/api/v1/openai-tools`: Get tools in OpenAI function calling format

## Core Tools

1. **discover_tools**: Discover additional Sonarr API tools based on specific needs or categories
2. **get_tool_schema**: Get the detailed schema for a specific tool by name
3. **search_series**: Search for TV series by title

## Usage

### Building and Running

```bash
# Build the Docker image
docker build -t mcp-sonarr:clean -f Dockerfile.clean .

# Run the container
docker run -p 8000:8000 -e SONARR_API_KEY=your_api_key -e SONARR_API_URL=http://your_sonarr_instance:8989 mcp-sonarr:clean
```

### Testing

```bash
# Get all available tools
./test_openai_tools_clean.py --url http://localhost:8000

# Get tools filtered by category
./test_openai_tools_clean.py --url http://localhost:8000 --include-tags Series

# Call a specific tool
./test_openai_tools_clean.py --url http://localhost:8000 --call discover_tools --args '{"category": "Series", "max_results": 5}'
```

## Integration with OpenAI

To use this with OpenAI:

1. Configure your OpenAI client to use the `/api/v1/openai-tools` endpoint to get the available tools.
2. The AI will start with the core tools and can discover additional tools as needed.
3. When the AI needs to use a tool, it will call the `/api/v1/call` endpoint with the tool name and arguments.

## Example Interaction Flow

1. **User**: "I want to see what quality profiles are available in Sonarr."

2. **AI**: (Checks its initial tools, doesn't find a specific quality profile tool)
   "Let me check what tools are available for managing quality profiles."
   (Calls `discover_tools` with category="Quality")

3. **Server**: Returns a list of quality-related tools, including `getQualityProfiles`.

4. **AI**: "I found a tool to get quality profiles. Let me get more details about it."
   (Calls `get_tool_schema` with tool_name="getQualityProfiles")

5. **Server**: Returns the detailed schema for the `getQualityProfiles` tool.

6. **AI**: "Now I can get the quality profiles for you."
   (Calls the `getQualityProfiles` tool)

7. **Server**: Returns the list of quality profiles.

8. **AI**: "Here are the quality profiles available in your Sonarr instance: [lists profiles]"