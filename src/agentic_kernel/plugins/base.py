"""Base plugin class for Agentic Kernel."""

from typing import Any, Dict, Optional


class BasePlugin:
    """Base class for all plugins in Agentic Kernel."""

    def __init__(
        self, name: str, description: str, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the base plugin.

        Args:
            name: The name of the plugin.
            description: A description of what the plugin does.
            config: Optional configuration dictionary.
        """
        self.name = name
        self.description = description
        self.config = config or {}

    def validate_config(self) -> bool:
        """Validate the plugin configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        return True

    def get_capabilities(self) -> Dict[str, str]:
        """Get a dictionary of plugin capabilities.

        Returns:
            Dict[str, str]: A dictionary mapping capability names to descriptions.
        """
        return {}

    def initialize(self) -> None:
        """Initialize the plugin. Called after configuration is set."""
        pass

    def cleanup(self) -> None:
        """Clean up any resources used by the plugin."""
        pass
