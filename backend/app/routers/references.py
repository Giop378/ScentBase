"""Endpoint di sola lettura per i riferimenti usati dall'interfaccia."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.database import get_database
from backend.app.serializers import serialize_documents


router = APIRouter(prefix="/references", tags=["references"])


@router.get("/catalog")
def get_catalog_references() -> dict[str, list[dict[str, Any]]]:
    """Restituisce i dati leggeri necessari a presentare le card del catalogo.

    Brand e accordi vengono caricati con una sola richiesta e riutilizzati dal
    frontend. In questo modo si evitano richieste N+1 per ogni profumo, mentre
    gli identificativi presenti nei documenti MongoDB restano invariati.
    """
    db = get_database()

    brands = serialize_documents(
        list(
            db["brands"].find(
                {},
                {"_id": 1, "name": 1},
            ).sort("name", 1)
        )
    )
    accords = serialize_documents(
        list(
            db["accords"].find(
                {},
                {"_id": 1, "name": 1, "color_hex": 1},
            ).sort("name", 1)
        )
    )

    return {
        "brands": brands,
        "accords": accords,
    }
