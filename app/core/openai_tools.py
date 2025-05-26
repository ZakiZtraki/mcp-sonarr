"""
Utility module for converting Sonarr OpenAPI endpoints to OpenAI tool format.
"""
import re
from typing import Dict, Any, List, Optional, Set

def sanitize_parameter_name(name: str) -> str:
    """
    Sanitize parameter names to be compatible with OpenAI function calling.
    Replaces hyphens with underscores and ensures names are valid Python identifiers.
    """
    # Replace hyphens with underscores
    name = name.replace('-', '_')
    # Ensure it's a valid Python identifier
    if not name.isidentifier():
        # If it starts with a number, prefix with underscore
        if name[0].isdigit():
            name = f"_{name}"
        # Replace any invalid characters with underscores
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    return name

def openapi_type_to_jsonschema(openapi_type: str) -> str:
    """
    Convert OpenAPI types to JSON Schema types.
    """
    type_mapping = {
        "integer": "integer",
        "number": "number",
        "string": "string",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
    }
    return type_mapping.get(openapi_type, "string")

def extract_parameter_schema(parameter: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract parameter schema from OpenAPI parameter object.
    """
    schema = {}
    
    # Get the parameter schema
    param_schema = parameter.get("schema", {})
    
    # Set the type
    if "type" in param_schema:
        schema["type"] = openapi_type_to_jsonschema(param_schema["type"])
    
    # Add description
    if "description" in parameter:
        schema["description"] = parameter["description"]
    
    # Add enum values if present
    if "enum" in param_schema:
        schema["enum"] = param_schema["enum"]
    
    # Add format if present
    if "format" in param_schema:
        schema["format"] = param_schema["format"]
    
    # Add default value if present
    if "default" in param_schema:
        schema["default"] = param_schema["default"]
    
    # Handle array type
    if param_schema.get("type") == "array" and "items" in param_schema:
        schema["items"] = extract_parameter_schema({"schema": param_schema["items"]})
    
    return schema

def convert_path_to_tool(path: str, method: str, operation: Dict[str, Any], 
                         openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an OpenAPI path and operation to an OpenAI tool definition.
    
    Args:
        path: The OpenAPI path
        method: The HTTP method (get, post, put, delete)
        operation: The OpenAPI operation object
        openapi_spec: The complete OpenAPI specification
    
    Returns:
        An OpenAI tool definition
    """
    # Create a base tool definition
    operation_id = operation.get("operationId", f"{method}_{path}")
    
    # Clean up the operation ID to make it a valid function name
    function_name = sanitize_parameter_name(operation_id)
    
    # Get the summary or generate one
    summary = operation.get("summary", f"{method.upper()} {path}")
    
    # Get the description or use the summary
    description = operation.get("description", summary)
    
    # Get the tag for categorization
    tag = operation.get("tags", ["Sonarr"])[0]
    
    # Build the tool definition
    tool = {
        "type": "function",
        "function": {
            "name": function_name,
            "description": f"{description} (Tag: {tag})",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
    
    # Add path parameters
    path_params = [p for p in re.findall(r'{([^}]+)}', path)]
    
    # Process parameters
    for param in operation.get("parameters", []):
        param_name = sanitize_parameter_name(param["name"])
        param_schema = extract_parameter_schema(param)
        
        tool["function"]["parameters"]["properties"][param_name] = param_schema
        
        # Add to required list if parameter is required
        if param.get("required", False):
            tool["function"]["parameters"]["required"].append(param_name)
    
    # Process request body if present
    if "requestBody" in operation:
        content = operation["requestBody"].get("content", {})
        
        # Try to get JSON schema from request body
        json_content = content.get("application/json", {})
        if "schema" in json_content:
            body_schema = json_content["schema"]
            
            # If it's a reference, resolve it
            if "$ref" in body_schema:
                ref_path = body_schema["$ref"].split("/")
                ref_name = ref_path[-1]
                
                # Try to find the schema in components
                if "components" in openapi_spec and "schemas" in openapi_spec["components"]:
                    schema = openapi_spec["components"]["schemas"].get(ref_name, {})
                    
                    # Add properties from the referenced schema
                    if "properties" in schema:
                        for prop_name, prop_schema in schema["properties"].items():
                            sanitized_name = sanitize_parameter_name(prop_name)
                            
                            # Convert property schema to parameter schema
                            prop_param = {
                                "name": sanitized_name,
                                "schema": prop_schema,
                                "description": prop_schema.get("description", f"{prop_name} parameter")
                            }
                            
                            param_schema = extract_parameter_schema(prop_param)
                            tool["function"]["parameters"]["properties"][sanitized_name] = param_schema
                            
                            # Add to required list if property is required
                            if "required" in schema and prop_name in schema["required"]:
                                tool["function"]["parameters"]["required"].append(sanitized_name)
            
            # If it has direct properties
            elif "properties" in body_schema:
                for prop_name, prop_schema in body_schema["properties"].items():
                    sanitized_name = sanitize_parameter_name(prop_name)
                    
                    # Convert property schema to parameter schema
                    prop_param = {
                        "name": sanitized_name,
                        "schema": prop_schema,
                        "description": prop_schema.get("description", f"{prop_name} parameter")
                    }
                    
                    param_schema = extract_parameter_schema(prop_param)
                    tool["function"]["parameters"]["properties"][sanitized_name] = param_schema
                    
                    # Add to required list if property is required
                    if "required" in body_schema and prop_name in body_schema["required"]:
                        tool["function"]["parameters"]["required"].append(sanitized_name)
    
    return tool

def generate_openai_tools(openapi_spec: Dict[str, Any], 
                          include_tags: Optional[List[str]] = None,
                          exclude_tags: Optional[List[str]] = None,
                          max_tools: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Generate OpenAI tools from an OpenAPI specification.
    
    Args:
        openapi_spec: The OpenAPI specification
        include_tags: Only include operations with these tags
        exclude_tags: Exclude operations with these tags
        max_tools: Maximum number of tools to generate
    
    Returns:
        A list of OpenAI tool definitions
    """
    tools = []
    
    # Process each path and method
    for path, path_item in openapi_spec.get("paths", {}).items():
        for method, operation in path_item.items():
            # Skip if not a standard HTTP method
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue
            
            # Check tags
            tags = operation.get("tags", [])
            
            # Skip if not in include_tags (if specified)
            if include_tags and not any(tag in include_tags for tag in tags):
                continue
            
            # Skip if in exclude_tags
            if exclude_tags and any(tag in exclude_tags for tag in tags):
                continue
            
            # Convert to tool
            tool = convert_path_to_tool(path, method, operation, openapi_spec)
            tools.append(tool)
            
            # Stop if we've reached the maximum number of tools
            if max_tools and len(tools) >= max_tools:
                break
    
    return tools

def filter_tools_by_capability(tools: List[Dict[str, Any]], 
                               capabilities: List[str]) -> List[Dict[str, Any]]:
    """
    Filter tools by capability keywords.
    
    Args:
        tools: List of OpenAI tool definitions
        capabilities: List of capability keywords to filter by
    
    Returns:
        Filtered list of tools
    """
    # If no capabilities are specified, return all tools
    if not capabilities:
        return tools
        
    filtered_tools = []
    
    for tool in tools:
        description = tool["function"].get("description", "").lower()
        name = tool["function"].get("name", "").lower()
        
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
        
        # Check if any capability keyword is in the description, name, or parameters
        for cap in capabilities:
            cap_lower = cap.lower()
            if (cap_lower in description or 
                cap_lower in name or 
                cap_lower in parameters_str):
                filtered_tools.append(tool)
                break
    
    return filtered_tools

def get_sonarr_tools(openapi_spec: Dict[str, Any], 
                     capabilities: Optional[List[str]] = None,
                     include_tags: Optional[List[str]] = None,
                     exclude_tags: Optional[List[str]] = None,
                     max_tools: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get OpenAI tools for Sonarr API.
    
    Args:
        openapi_spec: The Sonarr OpenAPI specification
        capabilities: Filter tools by these capability keywords
        include_tags: Only include operations with these tags
        exclude_tags: Exclude operations with these tags
        max_tools: Maximum number of tools to generate
    
    Returns:
        A list of OpenAI tool definitions for Sonarr
    """
    # Generate all tools
    tools = generate_openai_tools(
        openapi_spec, 
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        max_tools=max_tools
    )
    
    # Filter by capabilities if specified
    if capabilities:
        tools = filter_tools_by_capability(tools, capabilities)
    
    return tools