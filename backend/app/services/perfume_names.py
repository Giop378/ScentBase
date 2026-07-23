"""Regole applicative relative ai nomi dei profumi."""

from __future__ import annotations

import re

from fastapi import HTTPException, status

from backend.app.database import get_database


def ensure_unique_perfume_name(name: str) -> None:
    """Impedisce la creazione di nomi duplicati ignorando le maiuscole.

    Il nome ricevuto è già stato ripulito dal modello Pydantic: gli spazi
    iniziali e finali sono rimossi e le sequenze di spazi sono collassate.
    La regex è ancorata, quindi il confronto resta esatto e non parziale.
    """
    existing_perfume = get_database()["perfumes"].find_one(
        {
            "name": {
                "$regex": f"^{re.escape(name)}$",
                "$options": "i",
            }
        },
        {"_id": 1},
    )

    if existing_perfume is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A perfume with this name already exists",
        )
