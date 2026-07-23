"""Aggregation Pipeline MongoDB utilizzate dal backend ScentBase.

Il modulo contiene funzioni che costruiscono pipeline senza accedere
direttamente al database e senza dipendere da FastAPI.
"""

from __future__ import annotations

from typing import Any


Pipeline = list[dict[str, Any]]


def _ordered_documents(
    id_array_field: str,
    lookup_result_field: str,
) -> dict[str, Any]:
    """Ricostruisce i documenti collegati rispettando l'ordine degli ID.

    ``$lookup`` non garantisce che i documenti restituiti seguano l'ordine
    dell'array di identificativi presente nel profumo. La funzione percorre
    quindi l'array originale e seleziona, per ogni ID, il documento collegato.

    Campi mancanti o nulli vengono trattati come array vuoti. Eventuali
    riferimenti senza corrispondenza vengono esclusi dal risultato espanso.
    """
    return {
        "$filter": {
            "input": {
                "$map": {
                    "input": {
                        "$ifNull": [
                            f"${id_array_field}",
                            [],
                        ],
                    },
                    "as": "reference_id",
                    "in": {
                        "$arrayElemAt": [
                            {
                                "$filter": {
                                    "input": {
                                        "$ifNull": [
                                            f"${lookup_result_field}",
                                            [],
                                        ],
                                    },
                                    "as": "linked_document",
                                    "cond": {
                                        "$eq": [
                                            "$$linked_document._id",
                                            "$$reference_id",
                                        ],
                                    },
                                },
                            },
                            0,
                        ],
                    },
                },
            },
            "as": "linked_document",
            "cond": {
                "$ne": [
                    "$$linked_document",
                    None,
                ],
            },
        },
    }


def _first_document_or_none(
    lookup_result_field: str,
) -> dict[str, Any]:
    """Restituisce il primo documento di un lookup oppure ``null``."""
    return {
        "$ifNull": [
            {
                "$arrayElemAt": [
                    f"${lookup_result_field}",
                    0,
                ],
            },
            None,
        ],
    }


def _perfume_card_reference_stages() -> Pipeline:
    """Espande i riferimenti necessari alle card senza introdurre query N+1."""
    return [
        {
            "$lookup": {
                "from": "brands",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "_brand_documents",
            },
        },
        {
            "$lookup": {
                "from": "accords",
                "localField": "accord_ids",
                "foreignField": "_id",
                "as": "_accord_documents",
            },
        },
        {
            "$set": {
                "brand": _first_document_or_none(
                    "_brand_documents"
                ),
                "accords": _ordered_documents(
                    "accord_ids",
                    "_accord_documents",
                ),
            },
        },
        {
            "$project": {
                "_brand_documents": 0,
                "_accord_documents": 0,
            },
        },
    ]


def build_perfume_details_pipeline(perfume_id: str) -> Pipeline:
    """Costruisce la pipeline per il dettaglio completo di un profumo."""
    return [
        {
            "$match": {
                "_id": perfume_id,
            },
        },
        {
            "$lookup": {
                "from": "brands",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "_brand_documents",
            },
        },
        {
            "$lookup": {
                "from": "notes",
                "localField": "all_note_ids",
                "foreignField": "_id",
                "as": "_note_documents",
            },
        },
        {
            "$lookup": {
                "from": "accords",
                "localField": "accord_ids",
                "foreignField": "_id",
                "as": "_accord_documents",
            },
        },
        {
            "$lookup": {
                "from": "perfumers",
                "localField": "perfumer_ids",
                "foreignField": "_id",
                "as": "_perfumer_documents",
            },
        },
        {
            "$set": {
                "brand": _first_document_or_none(
                    "_brand_documents"
                ),
                "top_notes": _ordered_documents(
                    "top_note_ids",
                    "_note_documents",
                ),
                "middle_notes": _ordered_documents(
                    "middle_note_ids",
                    "_note_documents",
                ),
                "base_notes": _ordered_documents(
                    "base_note_ids",
                    "_note_documents",
                ),
                "accords": _ordered_documents(
                    "accord_ids",
                    "_accord_documents",
                ),
                "perfumers": _ordered_documents(
                    "perfumer_ids",
                    "_perfumer_documents",
                ),
            },
        },
        {
            "$project": {
                "_brand_documents": 0,
                "_note_documents": 0,
                "_accord_documents": 0,
                "_perfumer_documents": 0,
            },
        },
    ]


def build_top_perfumes_pipeline(
    *,
    limit: int,
    min_votes: int,
) -> Pipeline:
    """Costruisce la classifica dei profumi meglio valutati."""
    return [
        {
            "$match": {
                "rating": {
                    "$ne": None,
                },
                "votes": {
                    "$gte": min_votes,
                },
            },
        },
        {
            "$sort": {
                "rating": -1,
                "votes": -1,
                "_id": 1,
            },
        },
        {
            "$limit": limit,
        },
        *_perfume_card_reference_stages(),
    ]


def build_brand_statistics_pipeline(limit: int) -> Pipeline:
    """Costruisce conteggio e rating medio dei profumi per brand."""
    return [
        {
            "$group": {
                "_id": "$brand_id",
                "perfume_count": {
                    "$sum": 1,
                },
                "rated_perfume_count": {
                    "$sum": {
                        "$cond": [
                            {
                                "$ne": [
                                    {
                                        "$ifNull": [
                                            "$rating",
                                            None,
                                        ],
                                    },
                                    None,
                                ],
                            },
                            1,
                            0,
                        ],
                    },
                },
                "average_rating": {
                    "$avg": "$rating",
                },
            },
        },
        {
            "$lookup": {
                "from": "brands",
                "localField": "_id",
                "foreignField": "_id",
                "as": "_brand_documents",
            },
        },
        {
            "$set": {
                "brand": _first_document_or_none(
                    "_brand_documents"
                ),
            },
        },
        {
            "$sort": {
                "average_rating": -1,
                "perfume_count": -1,
                "_id": 1,
            },
        },
        {
            "$limit": limit,
        },
        {
            "$project": {
                "_id": 0,
                "_brand_documents": 0,
            },
        },
    ]


def build_note_statistics_pipeline(limit: int) -> Pipeline:
    """Costruisce la classifica delle note presenti in più profumi."""
    return [
        {
            "$project": {
                "all_note_ids": {
                    "$ifNull": [
                        "$all_note_ids",
                        [],
                    ],
                },
            },
        },
        {
            "$unwind": "$all_note_ids",
        },
        {
            "$group": {
                "_id": "$all_note_ids",
                "perfume_count": {
                    "$sum": 1,
                },
            },
        },
        {
            "$lookup": {
                "from": "notes",
                "localField": "_id",
                "foreignField": "_id",
                "as": "_note_documents",
            },
        },
        {
            "$set": {
                "note": _first_document_or_none(
                    "_note_documents"
                ),
            },
        },
        {
            "$sort": {
                "perfume_count": -1,
                "_id": 1,
            },
        },
        {
            "$limit": limit,
        },
        {
            "$project": {
                "_id": 0,
                "_note_documents": 0,
            },
        },
    ]
