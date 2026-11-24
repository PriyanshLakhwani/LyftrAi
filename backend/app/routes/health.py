from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..config import settings
from ..database import engine

router = APIRouter()


@router.get("/health", response_model=dict)
async def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return JSONResponse(
            content={
                "status": "ok",
                "database": "connected",
                "keys_configured": len(settings.api_keys_list),
                "cache_enabled": True,
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "database unavailable",
                "error": str(e),
            },
        )