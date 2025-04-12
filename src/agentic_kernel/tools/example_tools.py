"""Example tool implementations using the standardized tool interfaces.

This module provides example implementations of tools using the standardized
tool interfaces defined in tool_interface.py. These examples demonstrate
how to create and register tools for use by agents.
"""

import logging
import os
from typing import Any

import requests

from .tool_interface import (
    BaseTool,
    FunctionTool,
    ToolCapability,
    ToolCategory,
    ToolMetadata,
    register_function,
    register_tool,
)

logger = logging.getLogger(__name__)


class FileReadTool(BaseTool):
    """Tool for reading files from the filesystem."""
    
    def get_metadata(self) -> ToolMetadata:
        """Get the tool's metadata."""
        return ToolMetadata(
            name="file_read",
            description="Read the contents of a file from the filesystem",
            version="1.0.0",
            author="Agentic Kernel Team",
            categories=[ToolCategory.FILE_OPERATIONS],
            capabilities=[ToolCapability.READ, ToolCapability.FILE_ACCESS],
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Encoding to use when reading the file",
                        "default": "utf-8",
                    },
                },
                "required": ["path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Contents of the file",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the file that was read",
                    },
                    "size": {
                        "type": "integer",
                        "description": "Size of the file in bytes",
                    },
                },
            },
            examples=[
                {
                    "input": {"path": "/path/to/file.txt"},
                    "output": {
                        "content": "Example file content",
                        "path": "/path/to/file.txt",
                        "size": 20,
                    },
                },
            ],
        )
    
    def validate_input(self, **kwargs: Any) -> bool:
        """Validate the input arguments."""
        if "path" not in kwargs:
            return False
        
        path = kwargs["path"]
        if not os.path.exists(path):
            return False
        
        if not os.path.isfile(path):
            return False
        
        return True
    
    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""
        path = kwargs["path"]
        encoding = kwargs.get("encoding", "utf-8")
        
        if not self.validate_input(**kwargs):
            raise ValueError(f"Invalid input: File not found or not accessible: {path}")
        
        try:
            with open(path, encoding=encoding) as f:
                content = f.read()
            
            size = os.path.getsize(path)
            
            return {
                "content": content,
                "path": path,
                "size": size,
            }
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}", exc_info=True)
            raise


class WebFetchTool(BaseTool):
    """Tool for fetching data from web URLs."""
    
    def get_metadata(self) -> ToolMetadata:
        """Get the tool's metadata."""
        return ToolMetadata(
            name="web_fetch",
            description="Fetch data from a web URL",
            version="1.0.0",
            author="Agentic Kernel Team",
            categories=[ToolCategory.WEB_INTERACTION],
            capabilities=[ToolCapability.READ, ToolCapability.NETWORK],
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch data from",
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers to include in the request",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Request timeout in seconds",
                        "default": 10,
                    },
                },
                "required": ["url"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content of the response",
                    },
                    "status_code": {
                        "type": "integer",
                        "description": "HTTP status code",
                    },
                    "headers": {
                        "type": "object",
                        "description": "Response headers",
                    },
                },
            },
            examples=[
                {
                    "input": {"url": "https://example.com"},
                    "output": {
                        "content": "<html>Example content</html>",
                        "status_code": 200,
                        "headers": {"content-type": "text/html"},
                    },
                },
            ],
        )
    
    def validate_input(self, **kwargs: Any) -> bool:
        """Validate the input arguments."""
        if "url" not in kwargs:
            return False
        
        url = kwargs["url"]
        if not url.startswith(("http://", "https://")):
            return False
        
        return True
    
    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""
        url = kwargs["url"]
        headers = kwargs.get("headers", {})
        timeout = kwargs.get("timeout", 10)
        
        if not self.validate_input(**kwargs):
            raise ValueError(f"Invalid input: URL must start with http:// or https://: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            
            return {
                "content": response.text,
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}", exc_info=True)
            raise


# Example of using the FunctionTool class to wrap a function
def calculate_statistics(numbers: list[float]) -> dict[str, float]:
    """Calculate basic statistics for a list of numbers.
    
    Args:
        numbers: List of numbers to calculate statistics for
        
    Returns:
        Dictionary containing the calculated statistics
    """
    if not numbers:
        return {
            "count": 0,
            "sum": 0,
            "mean": 0,
            "min": 0,
            "max": 0,
        }
    
    return {
        "count": len(numbers),
        "sum": sum(numbers),
        "mean": sum(numbers) / len(numbers),
        "min": min(numbers),
        "max": max(numbers),
    }


# Example of using the register_function decorator
@register_function(
    name="string_operations",
    description="Perform various operations on strings",
    categories=[ToolCategory.DATA_PROCESSING],
    capabilities=[ToolCapability.TRANSFORMATION],
)
def string_operations(
    text: str,
    operation: str = "length",
    additional_args: dict[str, Any] | None = None,
) -> Any:
    """Perform various operations on strings.
    
    Args:
        text: The input text to operate on
        operation: The operation to perform (length, reverse, uppercase, lowercase)
        additional_args: Additional arguments for the operation
        
    Returns:
        The result of the operation
    """
    additional_args = additional_args or {}
    
    if operation == "length":
        return len(text)
    if operation == "reverse":
        return text[::-1]
    if operation == "uppercase":
        return text.upper()
    if operation == "lowercase":
        return text.lower()
    if operation == "split":
        delimiter = additional_args.get("delimiter", " ")
        return text.split(delimiter)
    if operation == "join":
        parts = additional_args.get("parts", [])
        delimiter = additional_args.get("delimiter", " ")
        return delimiter.join(parts)
    raise ValueError(f"Unknown operation: {operation}")


# Register the example tools
def register_example_tools():
    """Register the example tools with the global registry."""
    # Register the class-based tools
    register_tool(FileReadTool())
    register_tool(WebFetchTool())
    
    # Register the function-based tool
    stats_tool = FunctionTool(
        func=calculate_statistics,
        name="calculate_statistics",
        description="Calculate basic statistics for a list of numbers",
        categories=[ToolCategory.COMPUTATION, ToolCategory.DATA_PROCESSING],
        capabilities=[ToolCategory.COMPUTATION],
    )
    register_tool(stats_tool)
    
    # Note: string_operations is already registered via the decorator
    
    logger.info("Registered example tools")


# Register the example tools when this module is imported
register_example_tools()