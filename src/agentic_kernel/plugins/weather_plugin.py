"""Weather Plugin for Semantic Kernel integration.

This is a placeholder plugin that demonstrates the basic structure of a Semantic Kernel plugin.
It will be replaced or enhanced with actual functionality in future iterations.
"""

from typing import Dict, Any, Optional

from semantic_kernel.functions import kernel_function
from agentic_kernel.plugins.base import BasePlugin


class WeatherPlugin(BasePlugin):
    """A simple plugin that provides weather information for cities.

    This is a placeholder implementation that returns static responses.
    In a real implementation, this would connect to a weather service API.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the WeatherPlugin.

        Args:
            config: Optional configuration dictionary.
        """
        super().__init__(
            name="weather",
            description="A plugin that provides weather information for cities",
            config=config,
        )

    def validate_config(self) -> bool:
        """Validate the plugin configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        return True

    def get_capabilities(self) -> Dict[str, Any]:
        """Get the plugin capabilities.

        Returns:
            Dict[str, Any]: Dictionary of plugin capabilities.
        """
        return {
            "get_weather": {
                "description": "Gets the weather for a city",
                "parameters": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city to get weather for",
                    }
                },
            }
        }

    def initialize(self) -> None:
        """Initialize the plugin. No special initialization needed."""
        pass

    def cleanup(self) -> None:
        """Clean up the plugin. No special cleanup needed."""
        pass

    @kernel_function(name="get_weather", description="Gets the weather for a city")
    def get_weather(self, city: str) -> str:
        """Retrieves the weather for a given city.

        Args:
            city (str): The name of the city to get weather for.

        Returns:
            str: A description of the weather in the city.
        """
        if "paris" in city.lower():
            return f"The weather in {city} is 20°C and sunny."
        elif "london" in city.lower():
            return f"The weather in {city} is 15°C and cloudy."
        else:
            return f"Sorry, I don't have the weather for {city}."
