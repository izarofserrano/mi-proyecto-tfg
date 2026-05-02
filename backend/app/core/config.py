from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./tfg.db"
    upload_dir: str = str(Path(tempfile.gettempdir()) / "tfg_uploads")
    api_key: str = ""  # empty = auth disabled (development mode)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
