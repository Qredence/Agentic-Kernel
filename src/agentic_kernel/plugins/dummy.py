"""Dummy plugin for testing purposes."""

from typing import Dict, Any, Optional

from .base import BasePlugin


class DummyPlugin(BasePlugin):
    """A dummy plugin for testing purposes."""

    def __init__(
        self,
        name: str = "dummy",
        description: str = "A dummy plugin for testing",
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the dummy plugin.

        Args:
            name: The name of the plugin
            description: A description of what the plugin does
            config: Optional configuration dictionary
        """
        super().__init__(name, description, config)
        self.calls: Dict[str, int] = {}

    def validate_config(self) -> bool:
        """Validate the plugin configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        # Dummy plugin accepts any configuration
        return True

    def get_capabilities(self) -> Dict[str, Any]:
        """Get the plugin's capabilities.

        Returns:
            Dictionary describing the plugin's capabilities
        """
        return {
            "functions": [
                {
                    "name": "dummy_function",
                    "description": "A dummy function that does nothing",
                    "parameters": {},
                }
            ]
        }

    async def initialize(self) -> None:
        """Initialize the plugin."""
        self.calls["initialize"] = self.calls.get("initialize", 0) + 1

    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.calls["cleanup"] = self.calls.get("cleanup", 0) + 1

    def dummy_function(self) -> str:
        """A dummy function that does nothing.

        Returns:
            A dummy response
        """
        self.calls["dummy_function"] = self.calls.get("dummy_function", 0) + 1
        return "This is a dummy response"
