import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import HTTPException

from app.schemas.contracts import WeatherRead

WEATHER_LABELS = {
    0: ("Clear", "☀️"),
    1: ("Mostly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Cloudy", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Foggy", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    61: ("Light rain", "🌦️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"),
    82: ("Heavy showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm", "⛈️"),
    99: ("Thunderstorm", "⛈️"),
}


@dataclass(frozen=True)
class WeatherLocation:
    key: Literal["home", "school"]
    name: str
    query: str


@lru_cache(maxsize=16)
def resolve_location(query: str) -> tuple[float, float, str]:
    params = urlencode({"name": query, "count": 1, "language": "en", "countryCode": "US"})
    try:
        with urlopen(
            f"https://geocoding-api.open-meteo.com/v1/search?{params}", timeout=5
        ) as response:
            payload = json.load(response)
        result = payload["results"][0]
        location_name = str(result["name"])
        admin = str(result.get("admin1", ""))
        if admin and admin != location_name:
            location_name = f"{location_name}, {admin}"
        return float(result["latitude"]), float(result["longitude"]), location_name
    except (IndexError, OSError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=503, detail=f"Could not find the configured weather location: {query}"
        ) from error


def current_weather(location: WeatherLocation) -> WeatherRead:
    latitude, longitude, resolved_name = resolve_location(location.query)
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": 1,
        }
    )
    try:
        with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=5) as response:
            payload = json.load(response)
        code = int(payload["current"]["weather_code"])
        label, emoji = WEATHER_LABELS.get(code, ("Changing weather", "🌤️"))
        return WeatherRead(
            key=location.key,
            name=location.name,
            location=resolved_name,
            temperature=round(float(payload["current"]["temperature_2m"])),
            high=round(float(payload["daily"]["temperature_2m_max"][0])),
            low=round(float(payload["daily"]["temperature_2m_min"][0])),
            weather_code=code,
            label=label,
            emoji=emoji,
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Weather is temporarily unavailable") from error


def configured_weather(locations: list[WeatherLocation]) -> list[WeatherRead]:
    return [current_weather(location) for location in locations]
