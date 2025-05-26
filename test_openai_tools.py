#!/usr/bin/env python3
"""
Test script for OpenAI tools integration with Sonarr API.
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

def main():
    parser = argparse.ArgumentParser(description="Test OpenAI tools integration with Sonarr API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the MCP server")
    parser.add_argument("--capabilities", nargs="+", help="Filter tools by these capability keywords")
    parser.add_argument("--include-tags", nargs="+", help="Only include operations with these tags")
    parser.add_argument("--exclude-tags", nargs="+", help="Exclude operations with these tags")
    parser.add_argument("--max-tools", type=int, help="Maximum number of tools to include")
    parser.add_argument("--output", help="Output file for tools JSON")
    
    args = parser.parse_args()
    
    try:
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

if __name__ == "__main__":
    main()