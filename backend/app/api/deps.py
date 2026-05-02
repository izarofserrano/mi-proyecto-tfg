from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.db.session import get_db

__all__ = ["get_db", "verify_api_key"]

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Validates X-API-Key header when API_KEY is configured. No-op when empty."""
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="API key inválida o ausente.")
