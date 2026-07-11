from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.database import get_database
from backend.app.serializers import serialize_document, serialize_documents

router = APIRouter(prefix="/perfumes", tags=["perfumes"])


@router.get("")
def get_perfumes(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    db = get_database()
    collection = db["perfumes"]

    cursor = collection.find({}).sort("_id", 1).skip(skip).limit(limit)
    items = serialize_documents(list(cursor))

    return {
        "items": items,
        "limit": limit,
        "skip": skip,
        "total": collection.count_documents({}),
    }


@router.get("/{perfume_id}")
def get_perfume_by_id(perfume_id: str) -> dict[str, Any]:
    db = get_database()

    perfume = db["perfumes"].find_one({"_id": perfume_id})

    if perfume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfume not found",
        )

    serialized_perfume = serialize_document(perfume)
    if serialized_perfume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfume not found",
        )

    return serialized_perfume