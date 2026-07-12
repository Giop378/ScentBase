"""Endpoint di lettura e CRUD per la collection MongoDB ``perfumes``.

Il router mantiene gli endpoint di consultazione già presenti e aggiunge le
operazioni di creazione, sostituzione ed eliminazione dei profumi.

I riferimenti verso brand, note, accordi e profumieri vengono validati prima
di scrivere nel database, perché MongoDB non applica automaticamente vincoli
di foreign key tra collection.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from backend.app.database import get_database
from backend.app.schemas.perfumes import PerfumeCreate, PerfumeUpdate
from backend.app.serializers import serialize_document, serialize_documents


router = APIRouter(prefix="/perfumes", tags=["perfumes"])

MANUAL_PERFUME_ID_PREFIX = "manual_perfume_"


def unique_preserve_order(values: list[str]) -> list[str]:
    """Rimuove eventuali duplicati mantenendo l'ordine originale."""
    return list(dict.fromkeys(values))


def build_perfume_document(
    payload: PerfumeCreate | PerfumeUpdate,
) -> dict[str, Any]:
    """Converte il payload nel documento da salvare in MongoDB.

    ``_id`` non è incluso nei modelli Pydantic e viene gestito dal backend.
    ``all_note_ids`` viene sempre ricostruito a partire dalle tre categorie di
    note, evitando che il client possa inviare un valore incoerente.
    """
    document = payload.model_dump(mode="json")

    document["top_note_ids"] = unique_preserve_order(
        document["top_note_ids"]
    )
    document["middle_note_ids"] = unique_preserve_order(
        document["middle_note_ids"]
    )
    document["base_note_ids"] = unique_preserve_order(
        document["base_note_ids"]
    )
    document["accord_ids"] = unique_preserve_order(
        document["accord_ids"]
    )
    document["perfumer_ids"] = unique_preserve_order(
        document["perfumer_ids"]
    )

    document["all_note_ids"] = unique_preserve_order(
        document["top_note_ids"]
        + document["middle_note_ids"]
        + document["base_note_ids"]
    )

    return document


def find_missing_ids(
    collection_name: str,
    identifiers: list[str],
) -> list[str]:
    """Restituisce gli identificativi non presenti nella collection indicata."""
    if not identifiers:
        return []

    db = get_database()
    unique_identifiers = unique_preserve_order(identifiers)

    existing_ids = set(
        db[collection_name].distinct(
            "_id",
            {"_id": {"$in": unique_identifiers}},
        )
    )

    return [
        identifier
        for identifier in unique_identifiers
        if identifier not in existing_ids
    ]


def validate_references(document: dict[str, Any]) -> None:
    """Verifica che tutti i riferimenti del profumo siano validi."""
    db = get_database()
    missing_references: dict[str, list[str]] = {}

    brand_id = document["brand_id"]
    brand = db["brands"].find_one(
        {"_id": brand_id},
        {"_id": 1},
    )
    if brand is None:
        missing_references["brands"] = [brand_id]

    missing_notes = find_missing_ids(
        "notes",
        document["all_note_ids"],
    )
    if missing_notes:
        missing_references["notes"] = missing_notes

    missing_accords = find_missing_ids(
        "accords",
        document["accord_ids"],
    )
    if missing_accords:
        missing_references["accords"] = missing_accords

    missing_perfumers = find_missing_ids(
        "perfumers",
        document["perfumer_ids"],
    )
    if missing_perfumers:
        missing_references["perfumers"] = missing_perfumers

    if missing_references:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid collection references",
                "missing_references": missing_references,
            },
        )


def ensure_unique_source_url(
    source_url: str | None,
    *,
    excluded_perfume_id: str | None = None,
) -> None:
    """Controlla l'unicità di ``source_url`` quando il campo è presente."""
    if source_url is None:
        return

    db = get_database()
    query: dict[str, Any] = {"source_url": source_url}

    if excluded_perfume_id is not None:
        query["_id"] = {"$ne": excluded_perfume_id}

    existing_perfume = db["perfumes"].find_one(
        query,
        {"_id": 1},
    )

    if existing_perfume is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A perfume with this source_url already exists",
        )


def validate_imported_perfume_source_url(
    *,
    perfume_id: str,
    existing_source_url: str | None,
    requested_source_url: str | None,
) -> None:
    """Protegge il riferimento alla sorgente dei profumi importati dall'ETL.

    Gli identificativi ETL sono calcolati usando ``source_url``. Per questo un
    profumo importato deve conservare il proprio URL sorgente durante un PUT.
    I profumi creati manualmente, riconoscibili dal prefisso dell'identificativo,
    possono invece omettere, aggiungere o cambiare ``source_url``.
    """
    if perfume_id.startswith(MANUAL_PERFUME_ID_PREFIX):
        return

    if requested_source_url is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "source_url is required when updating a perfume imported "
                "through the ETL pipeline"
            ),
        )

    if existing_source_url != requested_source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "source_url cannot be changed for a perfume imported "
                "through the ETL pipeline"
            ),
        )


@router.get("")
def get_perfumes(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Restituisce una pagina di profumi ordinata per identificativo."""
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


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_perfume(payload: PerfumeCreate) -> dict[str, Any]:
    """Crea un nuovo profumo dopo aver validato struttura e riferimenti."""
    db = get_database()
    collection = db["perfumes"]

    document = build_perfume_document(payload)

    validate_references(document)
    ensure_unique_source_url(document.get("source_url"))

    document["_id"] = f"{MANUAL_PERFUME_ID_PREFIX}{uuid4().hex}"

    # Per i profumi manuali source_url è opzionale: se assente non viene
    # memorizzato come campo nullo nel documento MongoDB.
    if document.get("source_url") is None:
        document.pop("source_url", None)

    try:
        collection.insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A perfume with the same unique value already exists",
        ) from exc

    created_perfume = collection.find_one({"_id": document["_id"]})
    serialized_perfume = serialize_document(created_perfume)

    if serialized_perfume is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Created perfume could not be retrieved",
        )

    return serialized_perfume


@router.get("/{perfume_id}")
def get_perfume_by_id(perfume_id: str) -> dict[str, Any]:
    """Restituisce un profumo tramite il relativo identificativo."""
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


@router.put("/{perfume_id}")
def update_perfume(
    perfume_id: str,
    payload: PerfumeUpdate,
) -> dict[str, Any]:
    """Sostituisce i campi scrivibili di un profumo esistente."""
    db = get_database()
    collection = db["perfumes"]

    existing_perfume = collection.find_one(
        {"_id": perfume_id},
        {"_id": 1, "source_url": 1},
    )

    if existing_perfume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfume not found",
        )

    document = build_perfume_document(payload)
    requested_source_url = document.get("source_url")

    validate_imported_perfume_source_url(
        perfume_id=perfume_id,
        existing_source_url=existing_perfume.get("source_url"),
        requested_source_url=requested_source_url,
    )
    validate_references(document)
    ensure_unique_source_url(
        requested_source_url,
        excluded_perfume_id=perfume_id,
    )

    # PUT sostituisce tutti i campi scrivibili. Per un profumo manuale,
    # l'omissione di source_url comporta la rimozione del campo.
    source_url = document.pop("source_url", None)
    update_operations: dict[str, Any] = {"$set": document}

    if source_url is None:
        update_operations["$unset"] = {"source_url": ""}
    else:
        update_operations["$set"]["source_url"] = source_url

    try:
        updated_perfume = collection.find_one_and_update(
            {"_id": perfume_id},
            update_operations,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The update conflicts with an existing unique value",
        ) from exc

    serialized_perfume = serialize_document(updated_perfume)
    if serialized_perfume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfume not found",
        )

    return serialized_perfume


@router.delete(
    "/{perfume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_perfume(perfume_id: str) -> Response:
    """Elimina un profumo senza cancellare i documenti collegati."""
    db = get_database()

    result = db["perfumes"].delete_one({"_id": perfume_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfume not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
