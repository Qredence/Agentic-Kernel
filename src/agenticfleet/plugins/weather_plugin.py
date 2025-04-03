"""Weather Plugin for Semantic Kernel integration.

This is a placeholder plugin that demonstrates the basic structure of a Semantic Kernel plugin.
It will be replaced or enhanced with actual functionality in future iterations.
"""
from semantic_kernel.functions import kernel_function

class WeatherPlugin:
    """A simple plugin that provides weather information for cities.
    
    This is a placeholder implementation that returns static responses.
    In a real implementation, this would connect to a weather service API.
    """
    
    @kernel_function(
        name="get_weather",
        description="Gets the weather for a city"
    )
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