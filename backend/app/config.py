from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_root = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_root / ".env", env_prefix="PT_")

    database_url: str


settings = Settings()  # type: ignore[call-arg]  # mypy cannot see fields filled from env
