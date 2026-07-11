from __future__ import annotations

from fastapi import APIRouter

from backend.app.database import get_database

router = APIRouter(prefix="/collections", tags=["collections"])

COLLECTION_NAMES = ("perfumes", "brands", "notes", "accords", "perfumers")


@router.get("/counts")
def get_collection_counts() -> dict[str, int]:
    db = get_database()

    return {
        collection_name: db[collection_name].count_documents({})
        for collection_name in COLLECTION_NAMES
    }