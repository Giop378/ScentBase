"""Endpoint statistici basati su MongoDB Aggregation Pipeline."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backend.app.database import get_database
from backend.app.serializers import serialize_documents
from backend.app.services.aggregations import (
    build_brand_statistics_pipeline,
    build_note_statistics_pipeline,
    build_top_perfumes_pipeline,
)


router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
)


@router.get("/top-perfumes")
def get_top_perfumes(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    min_votes: int = Query(
        default=100,
        ge=0,
    ),
) -> dict[str, Any]:
    """Restituisce i profumi meglio valutati sopra una soglia di voti."""
    db = get_database()

    pipeline = build_top_perfumes_pipeline(
        limit=limit,
        min_votes=min_votes,
    )

    items = serialize_documents(
        list(
            db["perfumes"].aggregate(pipeline)
        )
    )

    return {
        "items": items,
        "limit": limit,
        "min_votes": min_votes,
    }


@router.get("/brands")
def get_brand_statistics(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
) -> dict[str, Any]:
    """Restituisce conteggio e rating medio dei profumi per brand."""
    db = get_database()

    pipeline = build_brand_statistics_pipeline(limit)

    items = serialize_documents(
        list(
            db["perfumes"].aggregate(pipeline)
        )
    )

    return {
        "items": items,
        "limit": limit,
    }


@router.get("/notes")
def get_note_statistics(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
) -> dict[str, Any]:
    """Restituisce le note presenti nel maggior numero di profumi."""
    db = get_database()

    pipeline = build_note_statistics_pipeline(limit)

    items = serialize_documents(
        list(
            db["perfumes"].aggregate(pipeline)
        )
    )

    return {
        "items": items,
        "limit": limit,
    }