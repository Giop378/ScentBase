from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.app.config import MONGO_DATABASE
from backend.app.database import check_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    if not check_connection():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB connection failed",
        )

    return {
        "status": "ok",
        "mongodb": "connected",
        "database": MONGO_DATABASE,
    }