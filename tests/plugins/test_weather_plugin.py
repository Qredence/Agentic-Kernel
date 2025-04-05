"""Tests for the WeatherPlugin."""
import pytest
from agentic_kernel.plugins.weather_plugin import WeatherPlugin

@pytest.fixture
def weather_plugin():
    """Fixture to create a WeatherPlugin instance."""
    return WeatherPlugin()

def test_weather_plugin_paris(weather_plugin):
    """Test that the plugin returns expected weather for Paris."""
    result = weather_plugin.get_weather("Paris")
    assert "Paris" in result
    assert "20°C" in result
    assert "sunny" in result

def test_weather_plugin_london(weather_plugin):
    """Test that the plugin returns expected weather for London."""
    result = weather_plugin.get_weather("London")
    assert "London" in result
    assert "15°C" in result
    assert "cloudy" in result

def test_weather_plugin_unknown_city(weather_plugin):
    """Test that the plugin handles unknown cities appropriately."""
    city = "UnknownCity"
    result = weather_plugin.get_weather(city)
    assert city in result
    assert "Sorry" in result
    assert "don't have the weather" in result

def test_weather_plugin_case_insensitive(weather_plugin):
    """Test that the city matching is case insensitive."""
    result = weather_plugin.get_weather("PARIS")
    assert "PARIS" in result
    assert "20°C" in result
    assert "sunny" in result 