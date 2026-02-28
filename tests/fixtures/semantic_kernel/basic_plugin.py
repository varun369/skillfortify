"""Basic Semantic Kernel plugin with @kernel_function decorators.

Fixture for testing the SemanticKernelParser against a simple plugin class
with decorated methods, standard imports, and URL references.
"""

from semantic_kernel.functions import kernel_function
import requests


class WeatherPlugin:
    """Plugin that fetches weather data from an external API."""

    @kernel_function(description="Get current weather for a city")
    def get_weather(self, city: str) -> str:
        """Return weather data for the given city name."""
        response = requests.get(f"https://api.weather.com/v2/current/{city}")
        return response.text

    @kernel_function(description="Get 5-day forecast")
    def get_forecast(self, city: str, days: int = 5) -> str:
        """Return multi-day weather forecast."""
        response = requests.get(
            f"https://api.weather.com/v2/forecast/{city}?days={days}"
        )
        return response.json()
