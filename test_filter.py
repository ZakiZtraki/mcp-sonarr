#!/usr/bin/env python3
"""
Test script for the filter_tools_by_capability function.
"""
from app.services.openai_tools_service import openai_tools_service
from app.core.openai_tools import filter_tools_by_capability

def main():
    # Get all Series tools
    tools = openai_tools_service.get_tools(include_tags=['Series'])
    print(f"Found {len(tools)} Series tools")
    
    # Filter by keyword
    keyword = "monitor"
    filtered = filter_tools_by_capability(tools, [keyword])
    print(f"Found {len(filtered)} tools with keyword '{keyword}':")
    
    for t in filtered:
        print(f"- {t['function']['name']}: {t['function']['description']}")
    
    # Try with a different keyword
    keyword = "episode"
    filtered = filter_tools_by_capability(tools, [keyword])
    print(f"\nFound {len(filtered)} tools with keyword '{keyword}':")
    
    for t in filtered:
        print(f"- {t['function']['name']}: {t['function']['description']}")

if __name__ == "__main__":
    main()