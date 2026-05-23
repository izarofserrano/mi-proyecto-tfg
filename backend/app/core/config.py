from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./tfg.db"
    upload_dir: str = str(Path(tempfile.gettempdir()) / "tfg_uploads")
    api_key: str = ""  # empty = auth disabled (development mode)

    # LLM fallback — opcional, solo se usa si usar_llm_fallback=True
    usar_llm_fallback: bool = False  # default False para no requerir API key
    proveedor_llm: str = "ninguno"   # "gemini", "anthropic", "openai", "ninguno"
    llm_api_key: str = ""            # API key del proveedor LLM

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
