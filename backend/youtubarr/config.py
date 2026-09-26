from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YOUTUBARR_", extra="ignore")

    config_dir: Path = Path("/config")
    library_dir: Path = Path("/library")
    cache_dir: Path = Path("/cache")
    virtual_mount: Path = Path("/mnt/youtubarr")
    host: str = "0.0.0.0"
    port: int = 8788
    public_base_url: str = ""
    session_days: int = 30
    cache_max_gb: int = 20
    cache_ttl_hours: int = 24
    worker_count: int = 2
    log_level: str = "INFO"
    max_video_height: int = 1080

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.config_dir / 'youtubarr.db'}"

    @property
    def web_dir(self) -> Path:
        return Path(__file__).resolve().parent / "web"


settings = Settings()
