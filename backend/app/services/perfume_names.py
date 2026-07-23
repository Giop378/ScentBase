"""Regole applicative per riconoscere profumi realmente duplicati."""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, status

from backend.app.database import get_database


REFERENCE_FIELDS = (
    "top_note_ids",
    "middle_note_ids",
    "base_note_ids",
    "accord_ids",
    "perfumer_ids",
)


def _normalize_name(value: object) -> str:
    """Normalizza solo ciò che non modifica il significato del nome."""
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _normalized_references(document: dict[str, Any], field: str) -> tuple[str, ...]:
    """Confronta gli stessi riferimenti indipendentemente dall'ordine."""
    return tuple(sorted(set(document.get(field) or [])))


def perfume_identity(document: dict[str, Any]) -> tuple[Any, ...]:
    """Costruisce la firma dei dati che identificano una fragranza.

    Rating, voti e URL sorgente non fanno parte della firma: possono cambiare
    nel tempo senza trasformare il profumo in una fragranza differente.
    """
    return (
        _normalize_name(document.get("name")),
        document.get("brand_id"),
        str(document.get("gender") or "").casefold(),
        document.get("year"),
        *(
            _normalized_references(document, field)
            for field in REFERENCE_FIELDS
        ),
    )


def ensure_no_duplicate_perfume(document: dict[str, Any]) -> None:
    """Rifiuta solo un profumo con la stessa firma applicativa.

    La ricerca del nome è esatta ma case-insensitive. Un profumo con lo stesso
    nome resta quindi ammesso quando differisce per brand, genere, anno, note,
    accordi o profumieri, come nel caso di una variante o riformulazione.
    """
    name = re.sub(r"\s+", " ", str(document.get("name") or "")).strip()
    query = {
        "name": {
            "$regex": f"^{re.escape(name)}$",
            "$options": "i",
        },
        "brand_id": document.get("brand_id"),
        "gender": document.get("gender"),
        "year": document.get("year"),
    }

    projection = {
        "name": 1,
        "brand_id": 1,
        "gender": 1,
        "year": 1,
        **{field: 1 for field in REFERENCE_FIELDS},
    }
    expected_identity = perfume_identity(document)

    for existing_perfume in get_database()["perfumes"].find(query, projection):
        if perfume_identity(existing_perfume) == expected_identity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An identical perfume already exists",
            )
