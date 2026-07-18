"""Test di integrazione per la ricerca dei profumi simili."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pymongo.database import Database


TemporaryPerfumeInserter = Callable[[list[dict[str, Any]]], None]


@pytest.fixture
def insert_temporary_perfumes(
    test_database: Database,
) -> Generator[TemporaryPerfumeInserter, None, None]:
    """Inserisce profumi temporanei e li elimina al termine del test."""
    inserted_ids: list[str] = []

    def insert(documents: list[dict[str, Any]]) -> None:
        if not documents:
            return

        test_database["perfumes"].insert_many(documents)
        inserted_ids.extend(document["_id"] for document in documents)

    try:
        yield insert
    finally:
        if inserted_ids:
            test_database["perfumes"].delete_many(
                {
                    "_id": {
                        "$in": inserted_ids,
                    },
                }
            )


def build_test_perfume(
    perfume_id: str,
    *,
    name: str,
    rating: float | None = 4.0,
    votes: int = 100,
    note_ids: list[str] | None = None,
    accord_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Costruisce un documento minimale valido per i test di similarità."""
    normalized_note_ids = note_ids or []
    normalized_accord_ids = accord_ids or []

    return {
        "_id": perfume_id,
        "name": name,
        "brand_id": "brand_test_house",
        "gender": "unisex",
        "rating": rating,
        "votes": votes,
        "year": 2024,
        "top_note_ids": normalized_note_ids,
        "middle_note_ids": [],
        "base_note_ids": [],
        "all_note_ids": normalized_note_ids,
        "accord_ids": normalized_accord_ids,
        "perfumer_ids": [],
    }


def item_ids(response_body: dict[str, Any]) -> list[str]:
    """Restituisce gli identificativi dei profumi presenti nella risposta."""
    return [item["_id"] for item in response_body["items"]]


def item_by_id(
    response_body: dict[str, Any],
    perfume_id: str,
) -> dict[str, Any]:
    """Recupera un risultato tramite identificativo."""
    return next(
        item
        for item in response_body["items"]
        if item["_id"] == perfume_id
    )


def test_similar_perfumes_return_expected_metadata_and_items(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/similar"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["source_perfume_id"] == "perfume_vanilla_woods"
    assert body["note_weight"] == pytest.approx(0.7)
    assert body["accord_weight"] == pytest.approx(0.3)
    assert body["limit"] == 10

    assert item_ids(body) == [
        "perfume_vanilla_night",
        "perfume_woody_trail",
        "perfume_sweet_rose",
    ]


def test_similar_perfumes_calculate_weighted_jaccard_score(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/similar"
    )

    assert response.status_code == 200

    vanilla_night = item_by_id(
        response.json(),
        "perfume_vanilla_night",
    )

    assert vanilla_night["note_similarity"] == pytest.approx(0.5)
    assert vanilla_night["accord_similarity"] == pytest.approx(0.5)
    assert vanilla_night["similarity_score"] == pytest.approx(0.5)

    sweet_rose = item_by_id(
        response.json(),
        "perfume_sweet_rose",
    )

    assert sweet_rose["note_similarity"] == pytest.approx(
        1 / 3,
        abs=1e-6,
    )
    assert sweet_rose["accord_similarity"] == pytest.approx(
        1 / 3,
        abs=1e-6,
    )
    assert sweet_rose["similarity_score"] == pytest.approx(
        1 / 3,
        abs=1e-6,
    )


def test_similar_perfumes_return_shared_ids_and_expanded_documents(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/similar"
    )

    assert response.status_code == 200

    vanilla_night = item_by_id(
        response.json(),
        "perfume_vanilla_night",
    )

    assert vanilla_night["shared_note_ids"] == [
        "note_vanilla",
    ]
    assert vanilla_night["shared_accord_ids"] == [
        "accord_sweet",
    ]

    assert [
        note["_id"]
        for note in vanilla_night["shared_notes"]
    ] == [
        "note_vanilla",
    ]

    assert [
        accord["_id"]
        for accord in vanilla_night["shared_accords"]
    ] == [
        "accord_sweet",
    ]

    assert vanilla_night["brand"] == {
        "_id": "brand_guerlain",
        "name": "Guerlain",
        "country": "France",
    }


def test_similar_perfumes_exclude_source_perfume(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/similar"
    )

    assert response.status_code == 200
    assert "perfume_vanilla_woods" not in item_ids(response.json())


def test_similar_perfumes_use_rating_to_break_score_ties(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/similar"
    )

    assert response.status_code == 200

    body = response.json()
    first_item = body["items"][0]
    second_item = body["items"][1]

    assert first_item["similarity_score"] == pytest.approx(0.5)
    assert second_item["similarity_score"] == pytest.approx(0.5)
    assert first_item["_id"] == "perfume_vanilla_night"
    assert second_item["_id"] == "perfume_woody_trail"
    assert first_item["rating"] > second_item["rating"]


def test_similar_perfumes_respect_limit(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/similar",
        params={
            "limit": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["limit"] == 1
    assert item_ids(body) == [
        "perfume_vanilla_night",
    ]


@pytest.mark.parametrize("invalid_limit", [0, 51])
def test_similar_perfumes_reject_invalid_limit(
    api_client: TestClient,
    invalid_limit: int,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/similar",
        params={
            "limit": invalid_limit,
        },
    )

    assert response.status_code == 422


def test_similar_perfumes_return_404_for_unknown_source(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_does_not_exist/similar"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found"


def test_similar_perfumes_return_empty_list_for_source_without_data(
    api_client: TestClient,
    insert_temporary_perfumes: TemporaryPerfumeInserter,
) -> None:
    source_id = "perfume_without_similarity_data"

    insert_temporary_perfumes(
        [
            build_test_perfume(
                source_id,
                name="Without Similarity Data",
                note_ids=[],
                accord_ids=[],
            )
        ]
    )

    response = api_client.get(
        f"/perfumes/{source_id}/similar"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_similar_perfumes_exclude_candidates_without_shared_elements(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_citrus_dawn/similar"
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_similar_perfumes_handle_note_only_similarity(
    api_client: TestClient,
    insert_temporary_perfumes: TemporaryPerfumeInserter,
) -> None:
    candidate_id = "perfume_citrus_echo"

    insert_temporary_perfumes(
        [
            build_test_perfume(
                candidate_id,
                name="Citrus Echo",
                note_ids=["note_bergamot"],
                accord_ids=[],
            )
        ]
    )

    response = api_client.get(
        "/perfumes/perfume_citrus_dawn/similar"
    )

    assert response.status_code == 200

    candidate = item_by_id(response.json(), candidate_id)

    assert candidate["note_similarity"] == pytest.approx(1.0)
    assert candidate["accord_similarity"] == pytest.approx(0.0)
    assert candidate["similarity_score"] == pytest.approx(0.7)


def test_similar_perfumes_handle_accord_only_similarity(
    api_client: TestClient,
    insert_temporary_perfumes: TemporaryPerfumeInserter,
) -> None:
    source_id = "perfume_accord_only_source"

    insert_temporary_perfumes(
        [
            build_test_perfume(
                source_id,
                name="Accord Only Source",
                note_ids=[],
                accord_ids=["accord_woody"],
            )
        ]
    )

    response = api_client.get(
        f"/perfumes/{source_id}/similar"
    )

    assert response.status_code == 200

    woody_trail = item_by_id(
        response.json(),
        "perfume_woody_trail",
    )

    assert woody_trail["note_similarity"] == pytest.approx(0.0)
    assert woody_trail["accord_similarity"] == pytest.approx(1.0)
    assert woody_trail["similarity_score"] == pytest.approx(0.3)


def test_similar_perfumes_use_id_as_final_tie_breaker(
    api_client: TestClient,
    insert_temporary_perfumes: TemporaryPerfumeInserter,
) -> None:
    source_id = "perfume_tie_source"

    insert_temporary_perfumes(
        [
            build_test_perfume(
                source_id,
                name="Tie Source",
                note_ids=["note_jasmine"],
                accord_ids=[],
            ),
            build_test_perfume(
                "perfume_tie_a",
                name="Tie A",
                rating=5.0,
                votes=999,
                note_ids=["note_jasmine"],
                accord_ids=[],
            ),
            build_test_perfume(
                "perfume_tie_b",
                name="Tie B",
                rating=5.0,
                votes=999,
                note_ids=["note_jasmine"],
                accord_ids=[],
            ),
        ]
    )

    response = api_client.get(
        f"/perfumes/{source_id}/similar"
    )

    assert response.status_code == 200
    assert item_ids(response.json())[:2] == [
        "perfume_tie_a",
        "perfume_tie_b",
    ]