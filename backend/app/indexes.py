"""Definizione e gestione centralizzata degli indici MongoDB di ScentBase.

Gli indici sono creati esplicitamente tramite gli script del progetto e non
all'avvio di FastAPI. In questo modo è possibile confrontare in maniera
riproducibile le query con e senza gli indici gestiti.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.database import Database


PERFUMES_COLLECTION = "perfumes"
MONGODB_ID_INDEX_NAME = "_id_"


@dataclass(frozen=True)
class ManagedIndex:
    """Descrive un indice MongoDB gestito dal progetto."""

    name: str
    keys: tuple[tuple[str, int], ...]
    unique: bool = False
    partial_filter_expression: dict[str, Any] | None = None

    def to_index_model(self) -> IndexModel:
        """Converte la definizione in un ``IndexModel`` PyMongo."""
        options: dict[str, Any] = {
            "name": self.name,
            "unique": self.unique,
        }

        if self.partial_filter_expression is not None:
            options["partialFilterExpression"] = self.partial_filter_expression

        return IndexModel(list(self.keys), **options)

    def to_serializable_dict(self) -> dict[str, Any]:
        """Restituisce una rappresentazione adatta a JSON e report."""
        return {
            "name": self.name,
            "keys": [
                {
                    "field": field,
                    "direction": direction,
                }
                for field, direction in self.keys
            ],
            "unique": self.unique,
            "partial_filter_expression": self.partial_filter_expression,
        }


MANAGED_INDEXES: tuple[ManagedIndex, ...] = (
    ManagedIndex(
        name="uq_perfumes_source_url",
        keys=(("source_url", ASCENDING),),
        unique=True,
        partial_filter_expression={
            "source_url": {
                "$type": "string",
            },
        },
    ),
    ManagedIndex(
        name="idx_perfumes_brand_rating",
        keys=(
            ("brand_id", ASCENDING),
            ("rating", DESCENDING),
            ("_id", ASCENDING),
        ),
    ),
    ManagedIndex(
        name="idx_perfumes_gender_rating_votes",
        keys=(
            ("gender", ASCENDING),
            ("rating", DESCENDING),
            ("votes", DESCENDING),
            ("_id", ASCENDING),
        ),
    ),
    ManagedIndex(
        name="idx_perfumes_rating_votes",
        keys=(
            ("rating", DESCENDING),
            ("votes", DESCENDING),
            ("_id", ASCENDING),
        ),
    ),
    ManagedIndex(
        name="idx_perfumes_all_note_ids",
        keys=(
            ("all_note_ids", ASCENDING),
            ("_id", ASCENDING),
        ),
    ),
    ManagedIndex(
        name="idx_perfumes_accord_ids",
        keys=(
            ("accord_ids", ASCENDING),
            ("_id", ASCENDING),
        ),
    ),
)


def get_managed_index_names() -> tuple[str, ...]:
    """Restituisce i nomi degli indici gestiti, in ordine stabile."""
    return tuple(index.name for index in MANAGED_INDEXES)


def get_managed_index_definitions() -> list[dict[str, Any]]:
    """Restituisce le definizioni serializzabili degli indici gestiti."""
    return [index.to_serializable_dict() for index in MANAGED_INDEXES]


def create_managed_indexes(database: Database) -> list[str]:
    """Crea gli indici gestiti sulla collection ``perfumes``.

    L'operazione è idempotente quando un indice con lo stesso nome, le stesse
    chiavi e le stesse opzioni è già presente. MongoDB segnala invece
    esplicitamente eventuali conflitti di configurazione, evitando di
    nascondere una definizione non coerente.
    """
    collection = database[PERFUMES_COLLECTION]
    models = [index.to_index_model() for index in MANAGED_INDEXES]
    return collection.create_indexes(models)


def drop_managed_indexes(database: Database) -> list[str]:
    """Elimina soltanto gli indici gestiti dal progetto.

    L'indice ``_id_`` e gli eventuali indici creati esternamente non vengono
    modificati.
    """
    collection = database[PERFUMES_COLLECTION]
    existing_names = set(collection.index_information())
    dropped_names: list[str] = []

    for index_name in get_managed_index_names():
        if index_name not in existing_names:
            continue

        collection.drop_index(index_name)
        dropped_names.append(index_name)

    return dropped_names


def list_collection_indexes(database: Database) -> list[dict[str, Any]]:
    """Elenca gli indici della collection in un formato stabile e serializzabile."""
    collection = database[PERFUMES_COLLECTION]
    indexes: list[dict[str, Any]] = []

    for index_document in collection.list_indexes():
        keys = [
            {
                "field": field,
                "direction": direction,
            }
            for field, direction in index_document["key"].items()
        ]

        indexes.append(
            {
                "name": index_document["name"],
                "keys": keys,
                "unique": bool(index_document.get("unique", False)),
                "partial_filter_expression": index_document.get(
                    "partialFilterExpression"
                ),
            }
        )

    return sorted(indexes, key=lambda item: item["name"])
