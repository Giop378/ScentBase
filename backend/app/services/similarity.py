"""Aggregation Pipeline per la ricerca dei profumi simili.

La similarità viene calcolata interamente da MongoDB confrontando gli insiemi
delle note e degli accordi. Il modulo costruisce la pipeline senza accedere
direttamente al database e senza dipendere da FastAPI.
"""

from __future__ import annotations

from typing import Any


Pipeline = list[dict[str, Any]]

NOTE_SIMILARITY_WEIGHT = 0.7
ACCORD_SIMILARITY_WEIGHT = 0.3


def _ordered_documents(
    id_array_field: str,
    lookup_result_field: str,
) -> dict[str, Any]:
    """Ricostruisce i documenti collegati rispettando l'ordine degli ID."""
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


def _ordered_shared_ids(
    source_ids: list[str],
    intersection_field: str,
) -> dict[str, Any]:
    """Ordina gli ID condivisi secondo l'ordine del profumo sorgente."""
    return {
        "$filter": {
            "input": source_ids,
            "as": "reference_id",
            "cond": {
                "$in": [
                    "$$reference_id",
                    f"${intersection_field}",
                ],
            },
        },
    }


def _jaccard_similarity(
    shared_ids_field: str,
    union_ids_field: str,
) -> dict[str, Any]:
    """Calcola Jaccard, restituendo zero quando l'unione è vuota."""
    return {
        "$cond": [
            {
                "$gt": [
                    {
                        "$size": f"${union_ids_field}",
                    },
                    0,
                ],
            },
            {
                "$divide": [
                    {
                        "$size": f"${shared_ids_field}",
                    },
                    {
                        "$size": f"${union_ids_field}",
                    },
                ],
            },
            0,
        ],
    }


def build_similar_perfumes_pipeline(
    *,
    source_perfume_id: str,
    source_note_ids: list[str],
    source_accord_ids: list[str],
    limit: int,
) -> Pipeline:
    """Costruisce la pipeline per individuare i profumi più simili.

    I candidati vengono preselezionati quando condividono almeno una nota o un
    accordo con il profumo sorgente. La classifica usa Jaccard sulle note e
    sugli accordi, combinando le due componenti con pesi 0.7 e 0.3.
    """
    source_note_ids = list(dict.fromkeys(source_note_ids))
    source_accord_ids = list(dict.fromkeys(source_accord_ids))

    return [
        {
            "$match": {
                "_id": {
                    "$ne": source_perfume_id,
                },
                "$or": [
                    {
                        "all_note_ids": {
                            "$in": source_note_ids,
                        },
                    },
                    {
                        "accord_ids": {
                            "$in": source_accord_ids,
                        },
                    },
                ],
            },
        },
        {
            "$set": {
                "_candidate_note_ids": {
                    "$ifNull": [
                        "$all_note_ids",
                        [],
                    ],
                },
                "_candidate_accord_ids": {
                    "$ifNull": [
                        "$accord_ids",
                        [],
                    ],
                },
            },
        },
        {
            "$set": {
                "_shared_note_id_set": {
                    "$setIntersection": [
                        source_note_ids,
                        "$_candidate_note_ids",
                    ],
                },
                "_shared_accord_id_set": {
                    "$setIntersection": [
                        source_accord_ids,
                        "$_candidate_accord_ids",
                    ],
                },
                "_note_union_ids": {
                    "$setUnion": [
                        source_note_ids,
                        "$_candidate_note_ids",
                    ],
                },
                "_accord_union_ids": {
                    "$setUnion": [
                        source_accord_ids,
                        "$_candidate_accord_ids",
                    ],
                },
            },
        },
        {
            "$set": {
                "shared_note_ids": _ordered_shared_ids(
                    source_note_ids,
                    "_shared_note_id_set",
                ),
                "shared_accord_ids": _ordered_shared_ids(
                    source_accord_ids,
                    "_shared_accord_id_set",
                ),
            },
        },
        {
            "$set": {
                "_note_similarity": _jaccard_similarity(
                    "shared_note_ids",
                    "_note_union_ids",
                ),
                "_accord_similarity": _jaccard_similarity(
                    "shared_accord_ids",
                    "_accord_union_ids",
                ),
            },
        },
        {
            "$set": {
                "_similarity_score": {
                    "$add": [
                        {
                            "$multiply": [
                                "$_note_similarity",
                                NOTE_SIMILARITY_WEIGHT,
                            ],
                        },
                        {
                            "$multiply": [
                                "$_accord_similarity",
                                ACCORD_SIMILARITY_WEIGHT,
                            ],
                        },
                    ],
                },
            },
        },
        {
            "$match": {
                "_similarity_score": {
                    "$gt": 0,
                },
            },
        },
        {
            "$sort": {
                "_similarity_score": -1,
                "rating": -1,
                "votes": -1,
                "_id": 1,
            },
        },
        {
            "$limit": limit,
        },
        {
            "$set": {
                "note_similarity": {
                    "$round": [
                        "$_note_similarity",
                        6,
                    ],
                },
                "accord_similarity": {
                    "$round": [
                        "$_accord_similarity",
                        6,
                    ],
                },
                "similarity_score": {
                    "$round": [
                        "$_similarity_score",
                        6,
                    ],
                },
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
                "localField": "shared_note_ids",
                "foreignField": "_id",
                "as": "_shared_note_documents",
            },
        },
        {
            "$lookup": {
                "from": "accords",
                "localField": "shared_accord_ids",
                "foreignField": "_id",
                "as": "_shared_accord_documents",
            },
        },
        {
            "$set": {
                "brand": _first_document_or_none(
                    "_brand_documents",
                ),
                "shared_notes": _ordered_documents(
                    "shared_note_ids",
                    "_shared_note_documents",
                ),
                "shared_accords": _ordered_documents(
                    "shared_accord_ids",
                    "_shared_accord_documents",
                ),
            },
        },
        {
            "$project": {
                "_candidate_note_ids": 0,
                "_candidate_accord_ids": 0,
                "_shared_note_id_set": 0,
                "_shared_accord_id_set": 0,
                "_note_union_ids": 0,
                "_accord_union_ids": 0,
                "_note_similarity": 0,
                "_accord_similarity": 0,
                "_similarity_score": 0,
                "_brand_documents": 0,
                "_shared_note_documents": 0,
                "_shared_accord_documents": 0,
            },
        },
    ]