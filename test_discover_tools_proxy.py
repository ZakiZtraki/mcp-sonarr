#!/usr/bin/env python3
"""
Test script for the discover_tools tool through the reverse proxy.
"""
import json
import argparse
import httpx

def test_discover_tools(base_url, category="Series", keyword="monitor", max_results=5, api_key=None):
    """
    Test the discover_tools tool through the reverse proxy.
    """
    # Prepare the request
    url = f"{base_url}/mcp_call_tool"
    data = {
        "tool_name": "discover_tools",
        "arguments": {
            "category": category,
            "keyword": keyword,
            "max_results": max_results
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
        print(f"Found {len(result.get('tools', []))} tools:")
        
        for i, tool in enumerate(result.get("tools", [])):
            print(f"{i+1}. {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:60]}...")
        
        # Save the result to a file
        output_file = "discover_tools_proxy_result.json"
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
    parser = argparse.ArgumentParser(description="Test the discover_tools tool through the reverse proxy")
    parser.add_argument("--url", default="https://mcp-sonarr.zakitraki.com", help="Base URL of the MCP server")
    parser.add_argument("--category", default="All", help="Category of tools to discover")
    parser.add_argument("--keyword", default="monitor", help="Keyword to search for in tool names and descriptions")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of tools to return")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--local", action="store_true", help="Try local server if remote fails")
    
    args = parser.parse_args()
    
    # Test discover_tools with the provided URL
    result = test_discover_tools(args.url, args.category, args.keyword, args.max_results, args.api_key)
    
    # If the remote test failed and --local is specified, try with a local server
    if result is None and args.local:
        print("\n\nRemote server test failed. Trying local server...")
        local_url = "http://localhost:8000"
        
        # Start the local server if it's not already running
        import subprocess
        import time
        import os
        import signal
        
        # Check if the server is already running
        try:
            httpx.get(f"{local_url}/ping", timeout=1)
            print("Local server is already running")
        except:
            print("Starting local server...")
            server_process = subprocess.Popen(
                ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd="/root/mcp-sonarr",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for the server to start
            time.sleep(5)
            
            try:
                # Test with the local server
                test_discover_tools(local_url, args.category, args.keyword, args.max_results)
            finally:
                # Stop the server
                if 'server_process' in locals():
                    print("Stopping local server...")
                    os.kill(server_process.pid, signal.SIGTERM)
                    server_process.wait()

if __name__ == "__main__":
    main()