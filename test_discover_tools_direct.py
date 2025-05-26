#!/usr/bin/env python3
"""
Test script for the discover_tools function directly.
"""
import json
from app.services.openai_tools_service import openai_tools_service

def test_discover_tools(category="Series", keyword="", max_results=5):
    """
    Test the discover_tools function directly.
    """
    # Map category to tags
    include_tags = None
    if category != "All":
        include_tags = [category]
    
    # Get dynamic tools from Sonarr OpenAPI
    capabilities = [keyword] if keyword else []
    print(f"Using capabilities: {capabilities}")
    
    dynamic_tools = openai_tools_service.get_tools(
        capabilities=capabilities,
        include_tags=include_tags,
        max_tools=max_results
    )
    
    # Format the response
    tool_list = []
    for t in dynamic_tools:
        tool_list.append({
            "name": t["function"]["name"],
            "description": t["function"]["description"]
        })
    
    return {"tools": tool_list}

def main():
    # Test with different combinations
    print("\n=== Testing with Series category and monitor keyword ===")
    result1 = test_discover_tools(category="Series", keyword="monitor", max_results=5)
    print(f"Found {len(result1['tools'])} tools")
    
    print("\n=== Testing with Series category and episode keyword ===")
    result2 = test_discover_tools(category="Series", keyword="episode", max_results=5)
    print(f"Found {len(result2['tools'])} tools")
    
    print("\n=== Testing with Series category and no keyword ===")
    result3 = test_discover_tools(category="Series", keyword="", max_results=5)
    print(f"Found {len(result3['tools'])} tools")
    
    # Print details of the first result
    print("\n=== Details of tools with monitor keyword ===")
    for i, tool in enumerate(result1["tools"]):
        print(f"{i+1}. {tool['name']}: {tool['description'][:60]}...")
    
    # Save the result to a file
    with open("discover_tools_result.json", "w") as f:
        json.dump(result1, f, indent=2)
    
    print(f"Result saved to discover_tools_result.json")
    
    # Return the first result
    return result1

if __name__ == "__main__":
    main()