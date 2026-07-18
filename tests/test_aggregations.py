"""Test di integrazione per JOIN e aggregazioni statistiche di ScentBase."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pymongo.database import Database


@pytest.fixture
def perfume_with_ordered_references(
    test_database: Database,
) -> Generator[str, None, None]:
    """Inserisce un profumo con più riferimenti ordinati."""
    perfume_id = "perfume_ordered_references"

    test_database["perfumes"].insert_one(
        {
            "_id": perfume_id,
            "name": "Ordered References",
            "brand_id": "brand_test_house",
            "gender": "unisex",
            "rating": 4.2,
            "votes": 120,
            "year": 2024,
            "top_note_ids": [
                "note_rose",
                "note_bergamot",
            ],
            "middle_note_ids": [
                "note_jasmine",
            ],
            "base_note_ids": [
                "note_sandalwood",
                "note_vanilla",
            ],
            "all_note_ids": [
                "note_rose",
                "note_bergamot",
                "note_jasmine",
                "note_sandalwood",
                "note_vanilla",
            ],
            "accord_ids": [
                "accord_woody",
                "accord_sweet",
                "accord_floral",
            ],
            "perfumer_ids": [
                "perfumer_test",
                "perfumer_alberto_morillas",
            ],
        }
    )

    try:
        yield perfume_id
    finally:
        test_database["perfumes"].delete_one(
            {
                "_id": perfume_id,
            }
        )


@pytest.fixture
def perfume_with_empty_references(
    test_database: Database,
) -> Generator[str, None, None]:
    """Inserisce un profumo privo di note, accordi e profumieri."""
    perfume_id = "perfume_empty_references"

    test_database["perfumes"].insert_one(
        {
            "_id": perfume_id,
            "name": "Empty References",
            "brand_id": "brand_test_house",
            "gender": "unisex",
            "rating": None,
            "votes": 0,
            "year": None,
            "top_note_ids": [],
            "middle_note_ids": [],
            "base_note_ids": [],
            "all_note_ids": [],
            "accord_ids": [],
            "perfumer_ids": [],
        }
    )

    try:
        yield perfume_id
    finally:
        test_database["perfumes"].delete_one(
            {
                "_id": perfume_id,
            }
        )


def item_names(
    response_body: dict[str, Any],
) -> list[str]:
    """Restituisce i nomi dei profumi nella risposta statistica."""
    return [
        item["name"]
        for item in response_body["items"]
    ]


def test_perfume_details_expands_all_references(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/details"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["_id"] == "perfume_vanilla_woods"

    assert body["brand"] == {
        "_id": "brand_dior",
        "name": "Dior",
        "country": "France",
    }

    assert [
        note["_id"]
        for note in body["top_notes"]
    ] == [
        "note_vanilla",
    ]

    assert body["middle_notes"] == []

    assert [
        note["_id"]
        for note in body["base_notes"]
    ] == [
        "note_sandalwood",
    ]

    assert [
        accord["_id"]
        for accord in body["accords"]
    ] == [
        "accord_sweet",
        "accord_woody",
    ]

    assert [
        perfumer["_id"]
        for perfumer in body["perfumers"]
    ] == [
        "perfumer_alberto_morillas",
    ]


def test_perfume_details_preserves_reference_order(
    api_client: TestClient,
    perfume_with_ordered_references: str,
) -> None:
    response = api_client.get(
        (
            "/perfumes/"
            f"{perfume_with_ordered_references}/details"
        )
    )

    assert response.status_code == 200

    body = response.json()

    assert [
        note["_id"]
        for note in body["top_notes"]
    ] == [
        "note_rose",
        "note_bergamot",
    ]

    assert [
        note["_id"]
        for note in body["middle_notes"]
    ] == [
        "note_jasmine",
    ]

    assert [
        note["_id"]
        for note in body["base_notes"]
    ] == [
        "note_sandalwood",
        "note_vanilla",
    ]

    assert [
        accord["_id"]
        for accord in body["accords"]
    ] == [
        "accord_woody",
        "accord_sweet",
        "accord_floral",
    ]

    assert [
        perfumer["_id"]
        for perfumer in body["perfumers"]
    ] == [
        "perfumer_test",
        "perfumer_alberto_morillas",
    ]


def test_perfume_details_keeps_original_reference_ids(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods/details"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["brand_id"] == "brand_dior"

    assert body["top_note_ids"] == [
        "note_vanilla",
    ]

    assert body["middle_note_ids"] == []

    assert body["base_note_ids"] == [
        "note_sandalwood",
    ]

    assert body["all_note_ids"] == [
        "note_vanilla",
        "note_sandalwood",
    ]

    assert body["accord_ids"] == [
        "accord_sweet",
        "accord_woody",
    ]

    assert body["perfumer_ids"] == [
        "perfumer_alberto_morillas",
    ]


def test_perfume_details_returns_empty_arrays(
    api_client: TestClient,
    perfume_with_empty_references: str,
) -> None:
    response = api_client.get(
        (
            "/perfumes/"
            f"{perfume_with_empty_references}/details"
        )
    )

    assert response.status_code == 200

    body = response.json()

    assert body["brand"]["_id"] == "brand_test_house"
    assert body["top_notes"] == []
    assert body["middle_notes"] == []
    assert body["base_notes"] == []
    assert body["accords"] == []
    assert body["perfumers"] == []


def test_perfume_details_returns_404_for_unknown_id(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_does_not_exist/details"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found"


def test_regular_perfume_endpoint_remains_unexpanded(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_vanilla_woods"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["brand_id"] == "brand_dior"
    assert "brand" not in body
    assert "top_notes" not in body
    assert "middle_notes" not in body
    assert "base_notes" not in body
    assert "accords" not in body
    assert "perfumers" not in body


def test_top_perfumes_are_sorted_by_rating_and_votes(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/statistics/top-perfumes"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["limit"] == 10
    assert body["min_votes"] == 100

    assert item_names(body) == [
        "Vanilla Night",
        "Citrus Dawn",
        "Vanilla Woods",
        "Woody Trail",
        "Sweet Rose",
    ]

    assert body["items"][0]["brand"]["name"] == "Guerlain"


def test_top_perfumes_applies_min_votes_and_limit(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/statistics/top-perfumes",
        params={
            "min_votes": 600,
            "limit": 2,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["limit"] == 2
    assert body["min_votes"] == 600

    assert item_names(body) == [
        "Vanilla Night",
        "Vanilla Woods",
    ]


def test_brand_statistics_return_counts_and_average_rating(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/statistics/brands"
    )

    assert response.status_code == 200

    body = response.json()

    items_by_brand = {
        item["brand"]["_id"]: item
        for item in body["items"]
    }

    assert [
        item["brand"]["_id"]
        for item in body["items"]
    ] == [
        "brand_dior",
        "brand_guerlain",
        "brand_test_house",
    ]

    dior = items_by_brand["brand_dior"]

    assert dior["perfume_count"] == 3
    assert dior["rated_perfume_count"] == 3
    assert dior["average_rating"] == pytest.approx(4.3)

    guerlain = items_by_brand["brand_guerlain"]

    assert guerlain["perfume_count"] == 2
    assert guerlain["rated_perfume_count"] == 2
    assert guerlain["average_rating"] == pytest.approx(4.1)

    test_house = items_by_brand["brand_test_house"]

    assert test_house["perfume_count"] == 2
    assert test_house["rated_perfume_count"] == 2
    assert test_house["average_rating"] == pytest.approx(3.9)


def test_brand_statistics_ignore_missing_ratings(
    api_client: TestClient,
    perfume_with_empty_references: str,
) -> None:
    response = api_client.get(
        "/statistics/brands"
    )

    assert response.status_code == 200

    test_house = next(
        item
        for item in response.json()["items"]
        if item["brand"]["_id"] == "brand_test_house"
    )

    assert test_house["perfume_count"] == 3
    assert test_house["rated_perfume_count"] == 2
    assert test_house["average_rating"] == pytest.approx(3.9)


def test_brand_statistics_respect_limit(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/statistics/brands",
        params={
            "limit": 2,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["limit"] == 2
    assert len(body["items"]) == 2

    assert [
        item["brand"]["_id"]
        for item in body["items"]
    ] == [
        "brand_dior",
        "brand_guerlain",
    ]


def test_note_statistics_return_frequency_and_order(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/statistics/notes"
    )

    assert response.status_code == 200

    body = response.json()

    counts_by_note = {
        item["note"]["_id"]: item["perfume_count"]
        for item in body["items"]
    }

    assert body["items"][0]["note"]["_id"] == "note_vanilla"
    assert body["items"][0]["perfume_count"] == 3

    assert counts_by_note == {
        "note_vanilla": 3,
        "note_rose": 2,
        "note_sandalwood": 2,
        "note_bergamot": 1,
        "note_jasmine": 1,
    }


@pytest.mark.parametrize(
    "endpoint",
    [
        "/statistics/top-perfumes",
        "/statistics/brands",
        "/statistics/notes",
    ],
)
@pytest.mark.parametrize(
    "invalid_limit",
    [
        0,
        101,
    ],
)
def test_statistics_reject_invalid_limits(
    api_client: TestClient,
    endpoint: str,
    invalid_limit: int,
) -> None:
    response = api_client.get(
        endpoint,
        params={
            "limit": invalid_limit,
        },
    )

    assert response.status_code == 422


def test_top_perfumes_rejects_negative_min_votes(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/statistics/top-perfumes",
        params={
            "min_votes": -1,
        },
    )

    assert response.status_code == 422