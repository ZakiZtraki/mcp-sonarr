#!/usr/bin/env python3
"""
Test script for OpenAI tools integration with Sonarr API - Clean version.
"""
import json
import httpx
import argparse
from typing import Dict, Any, List, Optional

def get_openai_tools(base_url: str, 
                    capabilities: Optional[List[str]] = None,
                    include_tags: Optional[List[str]] = None,
                    exclude_tags: Optional[List[str]] = None,
                    max_tools: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get OpenAI tools from the MCP server.
    """
    params = {}
    if capabilities:
        params["capabilities"] = capabilities
    if include_tags:
        params["include_tags"] = include_tags
    if exclude_tags:
        params["exclude_tags"] = exclude_tags
    if max_tools:
        params["max_tools"] = max_tools
    
    resp = httpx.get(f"{base_url}/api/v1/openai-tools", params=params)
    resp.raise_for_status()
    return resp.json()

def call_tool(base_url: str, tool_name: str, arguments: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Call a tool on the MCP server.
    """
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    data = {
        "tool_name": tool_name,
        "arguments": arguments
    }
    
    resp = httpx.post(f"{base_url}/api/v1/call", json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser(description="Test OpenAI tools integration with Sonarr API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the MCP server")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--capabilities", nargs="+", help="Filter tools by these capability keywords")
    parser.add_argument("--include-tags", nargs="+", help="Only include operations with these tags")
    parser.add_argument("--exclude-tags", nargs="+", help="Exclude operations with these tags")
    parser.add_argument("--max-tools", type=int, help="Maximum number of tools to include")
    parser.add_argument("--output", help="Output file for tools JSON")
    parser.add_argument("--call", help="Call a specific tool")
    parser.add_argument("--args", help="JSON string of arguments for the tool call")
    
    args = parser.parse_args()
    
    try:
        # If we're calling a tool
        if args.call:
            tool_arguments = {}
            if args.args:
                tool_arguments = json.loads(args.args)
            
            print(f"Calling tool '{args.call}' with arguments: {tool_arguments}")
            result = call_tool(args.url, args.call, tool_arguments, args.api_key)
            print(json.dumps(result, indent=2))
            return
        
        # Otherwise, get the tools
        tools = get_openai_tools(
            args.url,
            capabilities=args.capabilities,
            include_tags=args.include_tags,
            exclude_tags=args.exclude_tags,
            max_tools=args.max_tools
        )
        
        print(f"Retrieved {len(tools)} tools")
        
        # Print a summary of the tools
        for i, tool in enumerate(tools):
            print(f"{i+1}. {tool['function']['name']}: {tool['function']['description'][:60]}...")
        
        # Save to file if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(tools, f, indent=2)
            print(f"Saved tools to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, "response") and hasattr(e.response, "text"):
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    main()