"""Endpoint di lettura, ricerca e CRUD per la collection MongoDB ``perfumes``.

Il router espone gli endpoint di consultazione e le operazioni di creazione,
sostituzione ed eliminazione dei profumi. L'endpoint ``GET /perfumes`` supporta
inoltre filtri combinabili, ordinamento e paginazione.

L'endpoint ``GET /perfumes/{perfume_id}/details`` utilizza una MongoDB
Aggregation Pipeline per espandere i riferimenti verso brand, note, accordi
e profumieri.

L'endpoint ``GET /perfumes/{perfume_id}/similar`` utilizza una MongoDB
Aggregation Pipeline per confrontare note e accordi e restituire i profumi
maggiormente simili.

I riferimenti verso brand, note, accordi e profumieri vengono validati prima
di scrivere nel database, perché MongoDB non applica automaticamente vincoli
di foreign key tra collection.
"""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from backend.app.database import get_database
from backend.app.schemas.perfumes import PerfumeCreate, PerfumeUpdate
from backend.app.serializers import serialize_document, serialize_documents
from backend.app.services.aggregations import build_perfume_details_pipeline
from backend.app.services.similarity import (
    ACCORD_SIMILARITY_WEIGHT,
    NOTE_SIMILARITY_WEIGHT,
    build_similar_perfumes_pipeline,
)


router = APIRouter(prefix="/perfumes", tags=["perfumes"])

MANUAL_PERFUME_ID_PREFIX = "manual_perfume_"

SortField = Literal["name", "year", "rating", "votes"]
SortOrder = Literal["asc", "desc"]
GenderFilter = Literal["men", "women", "unisex"]


def unique_preserve_order(values: list[str]) -> list[str]:
    """Rimuove eventuali duplicati mantenendo l'ordine originale."""
    return list(dict.fromkeys(values))


def normalize_search_text(value: str, parameter_name: str) -> str:
    """Normalizza un filtro testuale e rifiuta valori composti da soli spazi."""
    normalized_value = value.strip()

    if not normalized_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Query parameter '{parameter_name}' cannot be blank",
        )

    return normalized_value


def partial_case_insensitive_match(value: str) -> dict[str, Any]:
    """Costruisce una ricerca parziale sicura e tollerante ai separatori.

    Spazi, trattini e underscore sono considerati equivalenti, mentre tutti gli
    altri caratteri inseriti dall'utente vengono trattati letteralmente.
    """
    search_terms = [
        term
        for term in re.split(r"[-_\s]+", value)
        if term
    ]
    pattern = (
        r"[-_\s]+".join(re.escape(term) for term in search_terms)
        if search_terms
        else re.escape(value)
    )

    return {
        "$regex": pattern,
        "$options": "i",
    }


def find_reference_ids_by_name(
    collection_name: str,
    search_value: str,
) -> list[str]:
    """Trova gli ``_id`` i cui nomi corrispondono al filtro testuale.

    La ricerca è parziale e case-insensitive. Un elenco vuoto viene mantenuto
    nella query principale tramite ``$in: []``, producendo correttamente zero
    risultati senza generare un errore HTTP.
    """
    db = get_database()
    cursor = db[collection_name].find(
        {"name": partial_case_insensitive_match(search_value)},
        {"_id": 1},
    )

    return [document["_id"] for document in cursor]


def build_perfume_search_query(
    *,
    name: str | None,
    brand: str | None,
    gender: GenderFilter | None,
    year_min: int | None,
    year_max: int | None,
    rating_min: float | None,
    rating_max: float | None,
    votes_min: int | None,
    note: str | None,
    accord: str | None,
    perfumer: str | None,
) -> dict[str, Any]:
    """Costruisce la query MongoDB applicando tutti i filtri con logica AND."""
    query: dict[str, Any] = {}

    if name is not None:
        normalized_name = normalize_search_text(name, "name")
        query["name"] = partial_case_insensitive_match(normalized_name)

    if brand is not None:
        normalized_brand = normalize_search_text(brand, "brand")
        brand_ids = find_reference_ids_by_name("brands", normalized_brand)
        query["brand_id"] = {"$in": brand_ids}

    if gender is not None:
        query["gender"] = gender

    if year_min is not None or year_max is not None:
        year_filter: dict[str, int] = {}

        if year_min is not None:
            year_filter["$gte"] = year_min

        if year_max is not None:
            year_filter["$lte"] = year_max

        query["year"] = year_filter

    if rating_min is not None or rating_max is not None:
        rating_filter: dict[str, float] = {}

        if rating_min is not None:
            rating_filter["$gte"] = rating_min

        if rating_max is not None:
            rating_filter["$lte"] = rating_max

        query["rating"] = rating_filter

    if votes_min is not None:
        query["votes"] = {"$gte": votes_min}

    if note is not None:
        normalized_note = normalize_search_text(note, "note")
        note_ids = find_reference_ids_by_name("notes", normalized_note)
        query["all_note_ids"] = {"$in": note_ids}

    if accord is not None:
        normalized_accord = normalize_search_text(accord, "accord")
        accord_ids = find_reference_ids_by_name("accords", normalized_accord)
        query["accord_ids"] = {"$in": accord_ids}

    if perfumer is not None:
        normalized_perfumer = normalize_search_text(perfumer, "perfumer")
        perfumer_ids = find_reference_ids_by_name(
            "perfumers",
            normalized_perfumer,
        )
        query["perfumer_ids"] = {"$in": perfumer_ids}

    return query


def validate_search_ranges(
    *,
    year_min: int | None,
    year_max: int | None,
    rating_min: float | None,
    rating_max: float | None,
) -> None:
    """Verifica la coerenza degli intervalli ricevuti nella query string."""
    if year_min is not None and year_max is not None and year_min > year_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="year_min cannot be greater than year_max",
        )

    if (
        rating_min is not None
        and rating_max is not None
        and rating_min > rating_max
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rating_min cannot be greater than rating_max",
        )


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
    name: str | None = Query(default=None, min_length=1, max_length=300),
    brand: str | None = Query(default=None, min_length=1, max_length=300),
    gender: GenderFilter | None = Query(default=None),
    year_min: int | None = Query(default=None, ge=0, le=2100),
    year_max: int | None = Query(default=None, ge=0, le=2100),
    rating_min: float | None = Query(default=None, ge=0, le=5),
    rating_max: float | None = Query(default=None, ge=0, le=5),
    votes_min: int | None = Query(default=None, ge=0),
    note: str | None = Query(default=None, min_length=1, max_length=300),
    accord: str | None = Query(default=None, min_length=1, max_length=300),
    perfumer: str | None = Query(default=None, min_length=1, max_length=300),
    sort_by: SortField | None = Query(default=None),
    sort_order: SortOrder = Query(default="asc"),
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Restituisce profumi filtrati, ordinati e paginati.

    Tutti i filtri specificati vengono combinati con logica AND. I filtri per
    brand, nota, accordo e profumiere sono risolti attraverso le rispettive
    collection, mantenendo nel risultato i riferimenti come identificativi.
    """
    validate_search_ranges(
        year_min=year_min,
        year_max=year_max,
        rating_min=rating_min,
        rating_max=rating_max,
    )

    query = build_perfume_search_query(
        name=name,
        brand=brand,
        gender=gender,
        year_min=year_min,
        year_max=year_max,
        rating_min=rating_min,
        rating_max=rating_max,
        votes_min=votes_min,
        note=note,
        accord=accord,
        perfumer=perfumer,
    )

    db = get_database()
    collection = db["perfumes"]

    sort_field = sort_by or "_id"
    sort_direction = ASCENDING if sort_order == "asc" else DESCENDING

    cursor = (
        collection.find(query)
        .sort(sort_field, sort_direction)
        .skip(skip)
        .limit(limit)
    )

    items = serialize_documents(list(cursor))

    return {
        "items": items,
        "limit": limit,
        "skip": skip,
        "total": collection.count_documents(query),
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


@router.get("/{perfume_id}/similar")
def get_similar_perfumes(
    perfume_id: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """Restituisce i profumi più simili per note e accordi condivisi.

    La similarità viene calcolata tramite indice di Jaccard, assegnando un peso
    del 70% alle note e del 30% agli accordi. Il profumo sorgente e i candidati
    con score uguale a zero vengono esclusi.
    """
    db = get_database()
    collection = db["perfumes"]

    source_perfume = collection.find_one(
        {"_id": perfume_id},
        {
            "_id": 1,
            "all_note_ids": 1,
            "accord_ids": 1,
        },
    )

    if source_perfume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfume not found",
        )

    source_note_ids = unique_preserve_order(
        source_perfume.get("all_note_ids") or []
    )
    source_accord_ids = unique_preserve_order(
        source_perfume.get("accord_ids") or []
    )

    pipeline = build_similar_perfumes_pipeline(
        source_perfume_id=perfume_id,
        source_note_ids=source_note_ids,
        source_accord_ids=source_accord_ids,
        limit=limit,
    )

    items = serialize_documents(
        list(collection.aggregate(pipeline))
    )

    return {
        "source_perfume_id": perfume_id,
        "note_weight": NOTE_SIMILARITY_WEIGHT,
        "accord_weight": ACCORD_SIMILARITY_WEIGHT,
        "limit": limit,
        "items": items,
    }


@router.get("/{perfume_id}/details")
def get_perfume_details(perfume_id: str) -> dict[str, Any]:
    """Restituisce un profumo con tutti i riferimenti espansi.

    La query utilizza una MongoDB Aggregation Pipeline con ``$lookup`` verso
    brand, note, accordi e profumieri. Gli identificativi originali vengono
    mantenuti insieme ai documenti collegati.
    """
    db = get_database()

    pipeline = build_perfume_details_pipeline(perfume_id)

    perfume = next(
        db["perfumes"].aggregate(pipeline),
        None,
    )

    serialized_perfume = serialize_document(perfume)

    if serialized_perfume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfume not found",
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
