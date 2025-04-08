"""Registry for managing MCP tool connections and sessions."""

import logging
from typing import Dict, List, Any, Optional

# Try importing MCP, but allow tests to run without it
try:
    from mcp import ClientSession

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = Any  # Type alias for tests

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """Registry for MCP tools and their handlers.

    Manages connections to different MCP servers and the tools they provide.
    """

    def __init__(self) -> None:
        """Initialize the MCPToolRegistry."""
        self.tools: Dict[str, List[Dict[str, Any]]] = {}
        self.sessions: Dict[str, ClientSession] = {}
        logger.info("MCPToolRegistry initialized.")

    def register_connection(
        self, name: str, tools: List[Dict[str, Any]], session: ClientSession
    ) -> None:
        """Register a new MCP connection with its tools.

        Args:
            name: The name of the connection (e.g., 'local-mcp').
            tools: A list of tool specifications provided by the connection.
            session: The MCP ClientSession object for this connection.
        """
        self.tools[name] = tools
        self.sessions[name] = session
        logger.info(f"Registered MCP connection '{name}' with {len(tools)} tools.")

    def unregister_connection(self, name: str) -> None:
        """Unregister an MCP connection.

        Args:
            name: The name of the connection to remove.
        """
        if name in self.tools:
            del self.tools[name]
        if name in self.sessions:
            del self.sessions[name]
        logger.info(f"Unregistered MCP connection '{name}'.")

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get a flattened list of all registered tools across all connections.

        Returns:
            A list of tool specification dictionaries.
        """
        all_tools = [tool for tools in self.tools.values() for tool in tools]
        logger.debug(
            f"Returning {len(all_tools)} tools from {len(self.sessions)} connections."
        )
        return all_tools

    def get_session_for_tool(
        self, tool_name: str
    ) -> Optional[tuple[str, ClientSession]]:
        """Find the connection name and session that can handle a specific tool.

        Args:
            tool_name: The name of the tool function (e.g., 'mcp_Neon_list_projects').

        Returns:
            A tuple containing the connection name and the ClientSession, or None if not found.
        """
        for connection_name, tools in self.tools.items():
            if any(t.get("function", {}).get("name") == tool_name for t in tools):
                logger.debug(
                    f"Found session '{connection_name}' for tool '{tool_name}'."
                )
                return connection_name, self.sessions[connection_name]

        logger.warning(f"No session found capable of handling tool '{tool_name}'.")
        return None

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool using its registered session.

        Args:
            tool_name: The name of the tool function to execute.
            arguments: The arguments to pass to the tool.

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If no session is found for the tool.
            Exception: If the tool execution fails.
        """
        session_info = self.get_session_for_tool(tool_name)
        if not session_info:
            raise ValueError(f"No session found for tool: {tool_name}")

        connection_name, session = session_info
        logger.info(f"Executing tool '{tool_name}' on connection '{connection_name}'")

        try:
            result = await session.call_tool(tool_name, arguments)
            logger.debug(f"Tool '{tool_name}' executed successfully")
            return result

        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
