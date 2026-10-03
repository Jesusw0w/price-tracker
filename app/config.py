from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_root = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Real env vars win over .env, so Lambda config needs no file
    model_config = SettingsConfigDict(env_file=_root / ".env", env_prefix="PT_")

    database_url: str
    data_dir: Path = _root / "app" / "data"


settings = Settings()  # type: ignore[call-arg]  # mypy cannot see fields filled from env

historical_data_path = settings.data_dir / "gpu_data.csv"
tracked_path = settings.data_dir / "tracked.json"
