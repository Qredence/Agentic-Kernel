"""Standardized interfaces for agent-tool integration.

This module defines the standardized interfaces for agent-tool integration,
including base classes for tools, tool providers, and tool registries.
These interfaces enable agents to discover and use tools in a consistent
manner, regardless of the tool's implementation details.
"""

import abc
import inspect
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories for classifying tools."""
    
    DATA_PROCESSING = "data_processing"
    FILE_OPERATIONS = "file_operations"
    WEB_INTERACTION = "web_interaction"
    COMMUNICATION = "communication"
    COMPUTATION = "computation"
    SYSTEM = "system"
    UTILITY = "utility"
    EXTERNAL_API = "external_api"
    OTHER = "other"


class ToolCapability(Enum):
    """Capabilities that tools can provide."""
    
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    FILE_ACCESS = "file_access"
    DATABASE = "database"
    API_ACCESS = "api_access"
    COMPUTATION = "computation"
    VISUALIZATION = "visualization"
    TRANSFORMATION = "transformation"


class ToolMetadata:
    """Metadata for a tool."""
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        author: str = "",
        categories: list[ToolCategory] | None = None,
        capabilities: list[ToolCapability] | None = None,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        examples: list[dict[str, Any]] | None = None,
        documentation_url: str = "",
        is_async: bool = False,
    ):
        """Initialize tool metadata.
        
        Args:
            name: The name of the tool
            description: A description of what the tool does
            version: The version of the tool
            author: The author or organization that created the tool
            categories: Categories that the tool belongs to
            capabilities: Capabilities that the tool provides
            input_schema: JSON schema for the tool's input
            output_schema: JSON schema for the tool's output
            examples: Example inputs and outputs for the tool
            documentation_url: URL to the tool's documentation
            is_async: Whether the tool is asynchronous
        """
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.categories = categories or []
        self.capabilities = capabilities or []
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}
        self.examples = examples or []
        self.documentation_url = documentation_url
        self.is_async = is_async
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the metadata to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "categories": [c.value for c in self.categories],
            "capabilities": [c.value for c in self.capabilities],
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": self.examples,
            "documentation_url": self.documentation_url,
            "is_async": self.is_async,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolMetadata":
        """Create a ToolMetadata instance from a dictionary."""
        categories = [ToolCategory(c) for c in data.get("categories", [])]
        capabilities = [ToolCapability(c) for c in data.get("capabilities", [])]
        
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            categories=categories,
            capabilities=capabilities,
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            examples=data.get("examples", []),
            documentation_url=data.get("documentation_url", ""),
            is_async=data.get("is_async", False),
        )


class BaseTool(abc.ABC):
    """Base class for all tools.
    
    All tools should inherit from this class and implement the required methods.
    """
    
    @abc.abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Get the tool's metadata.
        
        Returns:
            The tool's metadata
        """
        pass
    
    @abc.abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments.
        
        Args:
            **kwargs: Arguments to pass to the tool
            
        Returns:
            The result of executing the tool
        """
        pass
    
    async def execute_async(self, **kwargs: Any) -> Any:
        """Execute the tool asynchronously.
        
        By default, this calls the synchronous execute method. Tools that are
        inherently asynchronous should override this method.
        
        Args:
            **kwargs: Arguments to pass to the tool
            
        Returns:
            The result of executing the tool
        """
        return self.execute(**kwargs)
    
    def validate_input(self, **kwargs: Any) -> bool:
        """Validate the input arguments.
        
        Args:
            **kwargs: Arguments to validate
            
        Returns:
            True if the arguments are valid, False otherwise
        """
        # Default implementation does no validation
        return True
    
    def get_input_schema(self) -> dict[str, Any]:
        """Get the JSON schema for the tool's input.
        
        Returns:
            The input schema
        """
        return self.get_metadata().input_schema
    
    def get_output_schema(self) -> dict[str, Any]:
        """Get the JSON schema for the tool's output.
        
        Returns:
            The output schema
        """
        return self.get_metadata().output_schema


class FunctionTool(BaseTool):
    """A tool that wraps a function."""
    
    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
        categories: list[ToolCategory] | None = None,
        capabilities: list[ToolCapability] | None = None,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
    ):
        """Initialize a function tool.
        
        Args:
            func: The function to wrap
            name: The name of the tool (defaults to the function name)
            description: A description of what the tool does (defaults to the function docstring)
            categories: Categories that the tool belongs to
            capabilities: Capabilities that the tool provides
            input_schema: JSON schema for the tool's input
            output_schema: JSON schema for the tool's output
        """
        self.func = func
        self._name = name or func.__name__
        self._description = description or (inspect.getdoc(func) or "").strip()
        self._categories = categories or []
        self._capabilities = capabilities or []
        self._input_schema = input_schema or {}
        self._output_schema = output_schema or {}
        self._is_async = inspect.iscoroutinefunction(func)
    
    def get_metadata(self) -> ToolMetadata:
        """Get the tool's metadata."""
        return ToolMetadata(
            name=self._name,
            description=self._description,
            categories=self._categories,
            capabilities=self._capabilities,
            input_schema=self._input_schema,
            output_schema=self._output_schema,
            is_async=self._is_async,
        )
    
    def execute(self, **kwargs: Any) -> Any:
        """Execute the wrapped function."""
        if self._is_async:
            raise ValueError(
                f"Tool {self._name} is async and should be called with execute_async",
            )
        return self.func(**kwargs)
    
    async def execute_async(self, **kwargs: Any) -> Any:
        """Execute the wrapped function asynchronously."""
        if not self._is_async:
            return self.execute(**kwargs)
        return await self.func(**kwargs)


class ToolRegistry(abc.ABC):
    """Base class for tool registries.
    
    Tool registries manage collections of tools and provide methods for
    discovering and accessing them.
    """
    
    @abc.abstractmethod
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the registry.
        
        Args:
            tool: The tool to register
        """
        pass
    
    @abc.abstractmethod
    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool from the registry.
        
        Args:
            tool_name: The name of the tool to unregister
        """
        pass
    
    @abc.abstractmethod
    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool by name.
        
        Args:
            tool_name: The name of the tool
            
        Returns:
            The tool if found, None otherwise
        """
        pass
    
    @abc.abstractmethod
    def list_tools(self) -> list[ToolMetadata]:
        """List all registered tools.
        
        Returns:
            List of tool metadata
        """
        pass
    
    @abc.abstractmethod
    def find_tools(
        self,
        categories: list[ToolCategory] | None = None,
        capabilities: list[ToolCapability] | None = None,
        name_contains: str | None = None,
    ) -> list[ToolMetadata]:
        """Find tools matching the given criteria.
        
        Args:
            categories: Filter by categories
            capabilities: Filter by capabilities
            name_contains: Filter by name containing this string
            
        Returns:
            List of matching tool metadata
        """
        pass


class StandardToolRegistry(ToolRegistry):
    """Standard implementation of a tool registry."""
    
    def __init__(self):
        """Initialize the registry."""
        self.tools: dict[str, BaseTool] = {}
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the registry."""
        metadata = tool.get_metadata()
        self.tools[metadata.name] = tool
        logger.info(f"Registered tool: {metadata.name}")
    
    def register_function(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
        categories: list[ToolCategory] | None = None,
        capabilities: list[ToolCapability] | None = None,
    ) -> None:
        """Register a function as a tool.
        
        Args:
            func: The function to register
            name: The name of the tool (defaults to the function name)
            description: A description of what the tool does (defaults to the function docstring)
            categories: Categories that the tool belongs to
            capabilities: Capabilities that the tool provides
        """
        tool = FunctionTool(
            func=func,
            name=name,
            description=description,
            categories=categories,
            capabilities=capabilities,
        )
        self.register_tool(tool)
    
    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool from the registry."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> list[ToolMetadata]:
        """List all registered tools."""
        return [tool.get_metadata() for tool in self.tools.values()]
    
    def find_tools(
        self,
        categories: list[ToolCategory] | None = None,
        capabilities: list[ToolCapability] | None = None,
        name_contains: str | None = None,
    ) -> list[ToolMetadata]:
        """Find tools matching the given criteria."""
        results = []
        
        for tool in self.tools.values():
            metadata = tool.get_metadata()
            
            # Check categories
            if categories and not any(c in metadata.categories for c in categories):
                continue
            
            # Check capabilities
            if capabilities and not any(c in metadata.capabilities for c in capabilities):
                continue
            
            # Check name
            if name_contains and name_contains.lower() not in metadata.name.lower():
                continue
            
            results.append(metadata)
        
        return results
    
    def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool by name.
        
        Args:
            tool_name: The name of the tool
            **kwargs: Arguments to pass to the tool
            
        Returns:
            The result of executing the tool
            
        Raises:
            ValueError: If the tool is not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            raise
    
    async def execute_tool_async(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool asynchronously.
        
        Args:
            tool_name: The name of the tool
            **kwargs: Arguments to pass to the tool
            
        Returns:
            The result of executing the tool
            
        Raises:
            ValueError: If the tool is not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        try:
            return await tool.execute_async(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            raise


# Global registry instance for convenience
global_tool_registry = StandardToolRegistry()


def register_tool(tool: BaseTool) -> None:
    """Register a tool with the global registry."""
    global_tool_registry.register_tool(tool)


def register_function(
    func: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    categories: list[ToolCategory] | None = None,
    capabilities: list[ToolCapability] | None = None,
) -> Callable | Callable[[Callable], Callable]:
    """Register a function as a tool with the global registry.
    
    This can be used as a decorator:
    
    @register_function
    def my_tool():
        ...
    
    Or with arguments:
    
    @register_function(name="my_custom_name", description="Does something cool")
    def my_tool():
        ...
    
    Args:
        func: The function to register
        name: The name of the tool (defaults to the function name)
        description: A description of what the tool does (defaults to the function docstring)
        categories: Categories that the tool belongs to
        capabilities: Capabilities that the tool provides
        
    Returns:
        The original function (when used as a decorator)
    """
    def decorator(f: Callable) -> Callable:
        tool = FunctionTool(
            func=f,
            name=name,
            description=description,
            categories=categories,
            capabilities=capabilities,
        )
        register_tool(tool)
        return f
    
    if func is None:
        return decorator
    
    return decorator(func)