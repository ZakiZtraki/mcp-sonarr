#!/usr/bin/env python3
"""
Script to search for tools in the Sonarr API.
"""
from app.services.openai_tools_service import openai_tools_service

def search_tools(search_term):
    """
    Search for tools containing the search term in their name or description.
    """
    # Get all tools
    tools = openai_tools_service.get_tools()
    print(f"Found {len(tools)} total tools")
    
    # Search for tools containing the search term
    matching_tools = []
    for tool in tools:
        name = tool["function"]["name"].lower()
        description = tool["function"]["description"].lower()
        
        # Get parameters as a string
        parameters_str = ""
        if "parameters" in tool["function"]:
            parameters = tool["function"]["parameters"]
            if "properties" in parameters:
                for prop_name, prop_value in parameters["properties"].items():
                    parameters_str += f"{prop_name} "
                    if "description" in prop_value:
                        parameters_str += f"{prop_value['description']} "
        
        parameters_str = parameters_str.lower()
        
        # Check if the search term is in the name, description, or parameters
        if (search_term.lower() in name or 
            search_term.lower() in description or 
            search_term.lower() in parameters_str):
            matching_tools.append(tool)
    
    # Print the matching tools
    print(f"Found {len(matching_tools)} tools matching '{search_term}':")
    for i, tool in enumerate(matching_tools):
        # Extract the tag from the description (format: "... (Tag: TagName)")
        tag = "Unknown"
        description = tool['function']['description']
        if "(Tag:" in description:
            tag = description.split("(Tag:")[1].split(")")[0].strip()
        
        print(f"{i+1}. {tool['function']['name']}: {description} [Tag: {tag}]")
        
        # Print parameters if they contain the search term
        if "parameters" in tool["function"]:
            parameters = tool["function"]["parameters"]
            if "properties" in parameters:
                for prop_name, prop_value in parameters["properties"].items():
                    if "description" in prop_value and search_term.lower() in prop_value["description"].lower():
                        print(f"   - Parameter: {prop_name}: {prop_value['description']}")
    
    return matching_tools

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
    else:
        search_term = "monitor"
    
    search_tools(search_term)