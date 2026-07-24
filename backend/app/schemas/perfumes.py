"""Schemi Pydantic per la creazione e la modifica dei profumi.

I modelli definiti in questo modulo validano i payload ricevuti dagli endpoint
CRUD della collection MongoDB ``perfumes``.

I campi ``_id`` e ``all_note_ids`` non sono esposti nei payload:

* ``_id`` viene generato dal backend;
* ``all_note_ids`` viene calcolato dal backend unendo le note di testa,
  cuore e fondo.
"""

from __future__ import annotations

import re
from typing import Annotated, ClassVar, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)


# Stringa obbligatoria usata per il nome del profumo.
NonEmptyText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=300,
    ),
]

# Identificativo stringa delle collection collegate.
ReferenceId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


def clean_display_text(value: str) -> str:
    """Applica la stessa pulizia testuale usata dalla pipeline ETL.

    La funzione mantiene maiuscole, minuscole e caratteri leggibili originali,
    ma normalizza NBSP, virgolette esterne e sequenze di spazi.
    """
    normalized = value.replace("\u00a0", " ").strip()
    normalized = normalized.strip("'\"`“”‘’ ")
    return re.sub(r"\s+", " ", normalized)


class PerfumePayload(BaseModel):
    """Campi scrivibili di un documento della collection ``perfumes``."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "ScentBase CRUD Test",
                "brand_id": "brand_example",
                "gender": "unisex",
                "rating": 4.2,
                "votes": 10,
                "year": 2026,
                "top_note_ids": ["note_bergamot"],
                "middle_note_ids": ["note_jasmine"],
                "base_note_ids": ["note_vanilla"],
                "accord_ids": ["accord_citrus", "accord_sweet"],
                "perfumer_ids": ["perfumer_example"],
                "source_url": "https://example.com/scentbase-crud-test",
            }
        },
    )

    REFERENCE_ARRAY_FIELDS: ClassVar[tuple[str, ...]] = (
        "top_note_ids",
        "middle_note_ids",
        "base_note_ids",
        "accord_ids",
        "perfumer_ids",
    )

    name: NonEmptyText = Field(
        description="Nome leggibile del profumo.",
    )
    brand_id: ReferenceId = Field(
        description="Identificativo di un documento esistente in brands.",
    )
    gender: Literal["men", "women", "unisex"] = Field(
        description="Genere ammesso dal modello documentale.",
    )

    rating: float | None = Field(
        default=None,
        ge=0,
        le=5,
        description="Valutazione media compresa tra 0 e 5.",
    )
    votes: int | None = Field(
        default=None,
        ge=0,
        description="Numero di valutazioni, se disponibile.",
    )
    year: int | None = Field(
        default=None,
        ge=0,
        le=2100,
        description="Anno di rilascio, se disponibile.",
    )

    top_note_ids: list[ReferenceId] = Field(
        default_factory=list,
        description="Identificativi delle note di testa.",
    )
    middle_note_ids: list[ReferenceId] = Field(
        default_factory=list,
        description="Identificativi delle note di cuore.",
    )
    base_note_ids: list[ReferenceId] = Field(
        default_factory=list,
        description="Identificativi delle note di fondo.",
    )
    accord_ids: list[ReferenceId] = Field(
        default_factory=list,
        description="Identificativi degli accordi principali.",
    )
    perfumer_ids: list[ReferenceId] = Field(
        default_factory=list,
        description="Identificativi dei profumieri associati.",
    )

    source_url: AnyHttpUrl | None = Field(
        default=None,
        description=(
            "URL sorgente opzionale per i profumi creati manualmente. "
            "Quando presente, l'unicità viene controllata dal backend."
        ),
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        """Normalizza il nome come ``clean_text`` della pipeline ETL."""
        if isinstance(value, str):
            return clean_display_text(value)
        return value

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, value: object) -> object:
        """Normalizza il genere prima della verifica dei valori ammessi."""
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator(
        "top_note_ids",
        "middle_note_ids",
        "base_note_ids",
        "accord_ids",
        "perfumer_ids",
        mode="after",
    )
    @classmethod
    def remove_duplicate_references(cls, values: list[str]) -> list[str]:
        """Rimuove gli identificativi duplicati preservando l'ordine."""
        return list(dict.fromkeys(values))


class PerfumeCreate(PerfumePayload):
    """Payload completo accettato da ``POST /perfumes``."""


class PerfumeUpdate(PerfumePayload):
    """Payload completo accettato da ``PUT /perfumes/{perfume_id}``."""
