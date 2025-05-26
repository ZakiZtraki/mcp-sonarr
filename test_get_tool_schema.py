#!/usr/bin/env python3
"""
Test script for the get_tool_schema tool.
"""
import json
import argparse
import httpx

def test_get_tool_schema(base_url, tool_name, api_key=None):
    """
    Test the get_tool_schema tool.
    """
    # Prepare the request
    url = f"{base_url}/mcp_call_tool"
    data = {
        "tool_name": "get_tool_schema",
        "arguments": {
            "tool_name": tool_name
        }
    }
    
    # Prepare headers with API key if provided
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    print(f"Sending request to {url}")
    print(f"Request data: {json.dumps(data, indent=2)}")
    if api_key:
        print(f"Using API key: {api_key[:4]}...{api_key[-4:]}")
    
    # Make the request
    try:
        response = httpx.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Print the result
        print(f"\nResponse status code: {response.status_code}")
        
        # Save the result to a file
        output_file = "tool_schema_result.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\nResult saved to {output_file}")
        
        return result
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"\nError: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Test the get_tool_schema tool")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the MCP server")
    parser.add_argument("--tool-name", default="put__api_v3_episode_monitor", help="Name of the tool to get the schema for")
    parser.add_argument("--api-key", help="API key for authentication")
    
    args = parser.parse_args()
    
    # Test get_tool_schema
    test_get_tool_schema(args.url, args.tool_name, args.api_key)

if __name__ == "__main__":
    main()