import requests
from strands import tool, Agent
from strands.models.ollama import OllamaModel

URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight showers",
    81: "Moderate showers",
    82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


class Weather:
    def __init__(self) -> None:
        return

    def get_geocode(self, city: str = "Reno") -> tuple[float, float]:
        """Return the latitude and longitude of a given city."""
        params = {"name": city, "count": 1}
        response = requests.get(GEOCODING_URL, params=params, timeout=10)

        if not response.ok:
            raise Exception(f"Geocoding failed: {response.status_code}")

        results = response.json().get("results", [])
        if not results:
            raise Exception(f"No geocoding result found for {city}")

        result = results[0]
        return result["latitude"], result["longitude"]

    @tool
    def get_current_weather(self, city: str = "Reno") -> dict:
        """Get the current weather in a city."""
        latitude, longitude = self.get_geocode(city=city)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["temperature_2m", "wind_speed_10m", "precipitation", "weather_code"],
            "temperature_unit": "fahrenheit",
        }

        response = requests.get(URL, params=params, timeout=10)
        if not response.ok:
            raise Exception(f"Failed to fetch weather data: {response.status_code}")

        weather_current = response.json()["current"]
        weather_current["weather_code"] = WMO_CODES[int(weather_current["weather_code"])]
        weather_current["city"] = city
        return weather_current

    @tool
    def get_forecast(self, city: str = "Reno", days: int = 7):
        """Get the forecast for a certain number of days in a city."""
        latitude, longitude = self.get_geocode(city=city)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "weather_code"],
            "temperature_unit": "fahrenheit",
            "forecast_days": days,
        }

        response = requests.get(URL, params=params, timeout=10)
        if not response.ok:
            raise Exception(f"Failed to fetch forecast data: {response.status_code}")

        results = response.json()["daily"]
        results["city"] = city
        results["weather_code"] = [WMO_CODES[int(code)] for code in results.get("weather_code", [])]
        return results

    @tool
    def get_weather_summary(self, city: str = "Reno", days: int = 3) -> dict:
        """Return a compact current + forecast snapshot for a city."""
        current = self.get_current_weather(self, city)
        forecast = self.get_forecast(self, city=city, days=days)
        return {
            "city": city,
            "current": current,
            "forecast": {
                "dates": forecast.get("time", []),
                "highs": forecast.get("temperature_2m_max", []),
                "lows": forecast.get("temperature_2m_min", []),
                "precipitation": forecast.get("precipitation_sum", []),
                "conditions": forecast.get("weather_code", []),
            },
        }

    @tool
    def get_forecast_summary(self, city: str = "Reno", days: int = 3) -> str:
        """Return a human-readable forecast summary for the next few days."""
        forecast = self.get_forecast(self, city=city, days=days)
        lines = [f"Forecast for {city}:"]
        for day, high, low, precipitation, condition in zip(
            forecast.get("time", []),
            forecast.get("temperature_2m_max", []),
            forecast.get("temperature_2m_min", []),
            forecast.get("precipitation_sum", []),
            forecast.get("weather_code", []),
        ):
            lines.append(f"- {day}: high {high}°F, low {low}°F, precipitation {precipitation}, {condition}")
        return "\n".join(lines)

    def list_weather_tools(self) -> list:
        return [self.get_current_weather, self.get_forecast, self.get_weather_summary, self.get_forecast_summary]


@tool
def use_weather_tools(message: str) -> str:
    """Use the weather tools to get current weather or forecasts for a city."""
    weather = Weather()

    model = OllamaModel(
        model_id='qwen2.5:1.5b',
        host="http://localhost:11434",
    )

    agent = Agent(
        model=model,
        tools=weather.list_weather_tools(),
        system_prompt="You are a helpful assistant that provides weather information. Use the available tools to fetch current weather data or forecasts for a given city.",
    )

    response = agent(message)
    try:
        return response.message["content"][0]["text"]  # type: ignore
    except (KeyError, IndexError):
        return "I'm sorry, I couldn't retrieve the information."
