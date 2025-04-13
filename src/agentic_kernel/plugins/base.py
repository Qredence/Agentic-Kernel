"""Base plugin class for Agentic Kernel.

This module defines the base class for all plugins in the Agentic Kernel system,
with enhanced support for A2A (Agent-to-Agent) capability advertisement and discovery.
"""

from typing import Any, Dict, List, Optional, Set


class BasePlugin:
    """Base class for all plugins in Agentic Kernel.

    This class provides the foundation for creating plugins that can be used
    by agents in the system. Plugins can advertise their capabilities through
    the A2A capability system, allowing agents to discover and use them.

    Attributes:
        name: The name of the plugin
        description: A description of what the plugin does
        config: Configuration dictionary for the plugin
        version: Version of the plugin
        a2a_capability_types: Set of A2A capability types supported by the plugin
    """

    def __init__(
        self, 
        name: str, 
        description: str, 
        config: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0"
    ):
        """Initialize the base plugin.

        Args:
            name: The name of the plugin.
            description: A description of what the plugin does.
            config: Optional configuration dictionary.
            version: Version of the plugin.
        """
        self.name = name
        self.description = description
        self.config = config or {}
        self.version = version

        # A2A capability types that this plugin can provide
        self.a2a_capability_types: Set[str] = set()

    def validate_config(self) -> bool:
        """Validate the plugin configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        return True

    def get_capabilities(self) -> Dict[str, str]:
        """Get a dictionary of plugin capabilities.

        This method should be overridden by subclasses to provide information
        about the capabilities offered by the plugin. These capabilities will
        be advertised through the A2A capability registry.

        Returns:
            Dict[str, str]: A dictionary mapping capability names to descriptions.
        """
        return {}

    def get_a2a_capability_types(self) -> Set[str]:
        """Get the A2A capability types supported by this plugin.

        Returns:
            Set[str]: Set of A2A capability type names
        """
        return self.a2a_capability_types

    def set_a2a_capability_types(self, capability_types: Set[str]) -> None:
        """Set the A2A capability types supported by this plugin.

        Args:
            capability_types: Set of A2A capability type names
        """
        self.a2a_capability_types = capability_types

    def get_dependencies(self) -> List[str]:
        """Get the dependencies of this plugin.

        Returns:
            List[str]: List of plugin names that this plugin depends on
        """
        return []

    def initialize(self) -> None:
        """Initialize the plugin. Called after configuration is set."""
        pass

    def cleanup(self) -> None:
        """Clean up any resources used by the plugin."""
        pass
