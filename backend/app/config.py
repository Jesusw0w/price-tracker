import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_root = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_root / ".env", env_prefix="PT_")

    database_url: str
    refresh_cooldown_minutes: int = 30
    max_trackers: int = 100


def _load_settings() -> Settings:
    # Fetch credentials from ssm
    if name := os.environ.get("PT_DATABASE_URL_PARAM"):
        import boto3  # type: ignore[import-not-found]

        ssm = boto3.client("ssm")
        url = ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
        return Settings(database_url=url)
    return Settings()  # type: ignore[call-arg]


settings = _load_settings()
