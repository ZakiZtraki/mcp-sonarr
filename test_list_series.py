#!/usr/bin/env python3
"""
Test script for the list_series tool.
"""
import json
import httpx
import argparse

def test_list_series(base_url: str):
    """
    Test the list_series tool.
    """
    # Prepare the request
    url = f"{base_url}/mcp_call_tool"
    data = {
        "tool_name": "list_series",
        "arguments": {}
    }
    
    # Make the request
    try:
        response = httpx.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        
        # Print the result
        print(f"Found {len(result)} series:")
        for i, series in enumerate(result):
            print(f"{i+1}. {series.get('title', 'Unknown')} ({series.get('year', 'Unknown')})")
        
        return result
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, "response") and hasattr(e.response, "text"):
            print(f"Response: {e.response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Test the list_series tool")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the MCP server")
    
    args = parser.parse_args()
    
    # Test list_series
    test_list_series(args.url)

if __name__ == "__main__":
    main()