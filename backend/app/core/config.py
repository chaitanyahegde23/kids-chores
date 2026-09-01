from functools import lru_cache

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Kids Chores API"
    app_env: str = "development"
    api_docs_enabled: bool = True
    database_url: str = "postgresql+psycopg://kids_chores:local-only@localhost:5433/kids_chores"
    household_timezone: str = "America/New_York"
    parent_pin: str = "2468"
    session_secret: str = "local-development-secret-change-me"
    parent_session_seconds: int = Field(default=43_200, ge=300, le=604_800)
    allowed_origin: str = "http://localhost:5174"
    weather_home_label: str = Field(default="Home", min_length=1, max_length=40)
    weather_home_location: str = Field(default="10001", min_length=2, max_length=120)
    weather_school_label: str = Field(default="School", min_length=1, max_length=40)
    weather_school_location: str = Field(default="10003", min_length=2, max_length=120)

    @field_validator(
        "weather_home_label",
        "weather_home_location",
        "weather_school_label",
        "weather_school_location",
    )
    @classmethod
    def trim_weather_location(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("parent_pin")
    @classmethod
    def validate_pin(cls, value: str, info: ValidationInfo) -> str:
        if len(value) != 4 or not value.isdigit():
            raise ValueError("PARENT_PIN must contain exactly four digits")
        if info.data.get("app_env") == "production" and value == "2468":
            raise ValueError("Production PARENT_PIN must not use the demo PIN")
        return value

    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: str, info: ValidationInfo) -> str:
        if len(value) < 24:
            raise ValueError("SESSION_SECRET must contain at least 24 characters")
        if info.data.get("app_env") == "production" and (
            value == "local-development-secret-change-me" or value.startswith("replace-with-")
        ):
            raise ValueError("Production SESSION_SECRET must not use a placeholder")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
