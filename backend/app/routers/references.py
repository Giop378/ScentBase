"""Endpoint di sola lettura per i riferimenti usati dall'interfaccia."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.database import get_database
from backend.app.serializers import serialize_documents


router = APIRouter(prefix="/references", tags=["references"])


def _lightweight_references(
    collection_name: str,
    projection: dict[str, int],
) -> list[dict[str, Any]]:
    """Restituisce riferimenti ordinati e limitati ai campi utili alla UI."""
    db = get_database()
    return serialize_documents(
        list(
            db[collection_name].find({}, projection).sort("name", 1)
        )
    )


@router.get("/catalog")
def get_catalog_references() -> dict[str, list[dict[str, Any]]]:
    """Restituisce i riferimenti necessari a card, filtri e form CRUD.

    Il frontend mostra nomi leggibili ma conserva e invia gli identificativi
    originali. Tutte le collection collegate vengono caricate con una sola
    richiesta, evitando query N+1 e l'inserimento manuale di ID tecnici.
    """
    return {
        "brands": _lightweight_references(
            "brands",
            {"_id": 1, "name": 1},
        ),
        "notes": _lightweight_references(
            "notes",
            {"_id": 1, "name": 1},
        ),
        "accords": _lightweight_references(
            "accords",
            {"_id": 1, "name": 1, "color_hex": 1},
        ),
        "perfumers": _lightweight_references(
            "perfumers",
            {"_id": 1, "name": 1},
        ),
    }
