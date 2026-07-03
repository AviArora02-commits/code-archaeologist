"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Code Archaeologist"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./code_archaeologist.db"
    sqlite_path: str = "./code_archaeologist.db"
    clone_dir: str = "./repos"
    cognee_mode: Literal["local", "cloud"] = "local"
    cognee_cloud_url: str = ""
    cognee_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "gemini"
    llm_model: str = "gemini/gemini-2.0-flash-exp"
    openai_api_key: str = ""
    github_token: str = ""
    github_api_base: str = "https://api.github.com"
    cors_origins: str = "http://localhost:3000"
    max_files: int = Field(default=50, ge=1)
    max_file_size_kb: int = Field(default=512, ge=1)
    clone_depth: int = Field(default=50, ge=1)
    dry_run_cost_per_chunk: float = 0.002

    # Expert knowledge notifications (optional)
    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notify_email_from: str = ""
    notify_email_to: str = ""

    # Open-source Cognee (local SDK) storage paths
    data_root_directory: str = ""
    system_root_directory: str = ""

    @model_validator(mode="after")
    def use_persistent_volume(self) -> "Settings":
        data_dir = Path("/data")
        if data_dir.is_dir() and self.sqlite_path.startswith("."):
            self.sqlite_path = str(data_dir / "code_archaeologist.db")
            self.clone_dir = str(data_dir / "repos")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
