import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_root = Path(__file__).parent.parent


_SSM_FIELDS = ("database_url", "api_token")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_root / ".env", env_prefix="PT_")

    database_url: str
    api_token: SecretStr = Field(min_length=32)
    owner_sub: str = ""  # Cognito sub that /mcp acts as; empty turns /mcp off
    cognito_domain: str  # e.g. <prefix>.auth.eu-west-1.amazoncognito.com
    cognito_client_id: str
    public_url: str
    session_days: int = 14
    refresh_cooldown_minutes: int = 30
    max_trackers: int = 100  # per user


def _load_settings() -> Settings:

    params = {
        field: name
        for field in _SSM_FIELDS
        if (name := os.environ.get(f"PT_{field.upper()}_PARAM"))
    }
    if not params:
        return Settings()  # type: ignore[call-arg]

    import boto3  # type: ignore[import-not-found]

    ssm = boto3.client("ssm")
    found = ssm.get_parameters(Names=list(params.values()), WithDecryption=True)
    values = {p["Name"]: p["Value"] for p in found["Parameters"]}

    return Settings(**{field: values[name] for field, name in params.items()})


settings = _load_settings()
