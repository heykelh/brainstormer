from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    anthropic_api_key: str = ""
    github_token: str = ""
    ntfy_topic: str = ""

    brainstormer_model: str = "claude-haiku-5-5"
    brainstormer_lookback_days: int = 14
    brainstormer_digest_size: int = 5
    brainstormer_founder_profile: str = "Développeur solo, stack Python."

    db_path: Path = ROOT / "data" / "brainstormer.db"
    reports_dir: Path = ROOT / "reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
