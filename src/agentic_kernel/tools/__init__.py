"""Tools module for the Agentic Kernel system."""

from typing import Dict, Any, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """Registry for MCP tools that can be used by agents."""

    def __init__(self):
        """Initialize the MCP tool registry."""
        self.tools: Dict[str, Callable] = {}
        self.tool_descriptions: Dict[str, str] = {}

    def register_tool(self, name: str, tool: Callable, description: str = "") -> None:
        """Register a tool with the registry.

        Args:
            name: The name of the tool
            tool: The tool function
            description: Optional description of what the tool does
        """
        self.tools[name] = tool
        self.tool_descriptions[name] = description
        logger.info(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name.

        Args:
            name: The name of the tool

        Returns:
            The tool function if found, None otherwise
        """
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools.

        Returns:
            List of dictionaries containing tool names and descriptions
        """
        return [
            {"name": name, "description": self.tool_descriptions[name]}
            for name in self.tools
        ]

    def execute_tool(self, name: str, **kwargs: Any) -> Any:
        """Execute a tool by name.

        Args:
            name: The name of the tool
            **kwargs: Arguments to pass to the tool

        Returns:
            The result of executing the tool

        Raises:
            ValueError: If the tool is not found
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        try:
            return tool(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            raise
