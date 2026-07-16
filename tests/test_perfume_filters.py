"""Test di integrazione per ricerca e filtri di ``GET /perfumes``.

I test utilizzano le fixture definite in ``tests/conftest.py`` e vengono
eseguiti esclusivamente sul database MongoDB ``scentbase_test``.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def response_items(response_body: dict[str, Any]) -> list[dict[str, Any]]:
    """Restituisce gli elementi della risposta paginata."""
    return response_body["items"]


def response_names(response_body: dict[str, Any]) -> list[str]:
    """Restituisce i nomi dei profumi nella risposta, nello stesso ordine."""
    return [item["name"] for item in response_items(response_body)]


def test_get_perfumes_without_filters(api_client: TestClient) -> None:
    response = api_client.get("/perfumes")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 7
    assert body["limit"] == 20
    assert body["skip"] == 0
    assert len(body["items"]) == 7


def test_filter_by_partial_case_insensitive_name(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={"name": "VANILLA"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert set(response_names(body)) == {
        "Vanilla Night",
        "Vanilla Woods",
    }


def test_name_filter_escapes_regular_expression_characters(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={"name": "."},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_filter_by_brand_name(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={"brand": "DIOR"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert set(response_names(body)) == {
        "Citrus Dawn",
        "Vanilla Woods",
        "Woody Trail",
    }


def test_filter_by_gender(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={"gender": "women"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert set(response_names(body)) == {
        "Jasmine Light",
        "Rose Garden",
        "Vanilla Night",
    }


def test_filter_by_year_range(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "year_min": 2010,
            "year_max": 2018,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 4
    assert set(response_names(body)) == {
        "Sweet Rose",
        "Vanilla Night",
        "Vanilla Woods",
        "Woody Trail",
    }


def test_filter_by_rating_range(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "rating_min": 4.0,
            "rating_max": 4.5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 4
    assert set(response_names(body)) == {
        "Citrus Dawn",
        "Sweet Rose",
        "Vanilla Woods",
        "Woody Trail",
    }


def test_filter_by_minimum_votes(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={"votes_min": 500},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert set(response_names(body)) == {
        "Citrus Dawn",
        "Vanilla Night",
        "Vanilla Woods",
    }


def test_filter_by_note_name(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={"note": "ROSE"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert set(response_names(body)) == {
        "Rose Garden",
        "Sweet Rose",
    }


def test_filter_by_accord_name(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={"accord": "floral"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert set(response_names(body)) == {
        "Jasmine Light",
        "Rose Garden",
        "Sweet Rose",
    }


def test_filter_by_perfumer_name(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={"perfumer": "morillas"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert set(response_names(body)) == {
        "Citrus Dawn",
        "Vanilla Woods",
        "Woody Trail",
    }


def test_combined_brand_and_gender_filters(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "brand": "Dior",
            "gender": "unisex",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert set(response_names(body)) == {
        "Citrus Dawn",
        "Vanilla Woods",
    }


def test_combined_note_rating_and_votes_filters(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "note": "Vanilla",
            "rating_min": 4.0,
            "votes_min": 600,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert set(response_names(body)) == {
        "Vanilla Night",
        "Vanilla Woods",
    }


def test_combined_accord_and_year_filters(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "accord": "woody",
            "year_min": 2010,
            "year_max": 2016,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert set(response_names(body)) == {
        "Vanilla Woods",
        "Woody Trail",
    }


def test_sort_by_rating_descending(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "sort_by": "rating",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 200

    ratings = [
        item["rating"]
        for item in response.json()["items"]
    ]

    assert ratings == sorted(ratings, reverse=True)


def test_sort_by_name_ascending(api_client: TestClient) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "sort_by": "name",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200

    names = response_names(response.json())

    assert names == sorted(names)


def test_sort_by_votes_descending_with_filter(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "gender": "women",
            "sort_by": "votes",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 200
    assert response_names(response.json()) == [
        "Vanilla Night",
        "Rose Garden",
        "Jasmine Light",
    ]


def test_pagination_returns_distinct_pages(
    api_client: TestClient,
) -> None:
    common_params = {
        "sort_by": "name",
        "sort_order": "asc",
        "limit": 2,
    }

    first_response = api_client.get(
        "/perfumes",
        params={
            **common_params,
            "skip": 0,
        },
    )
    second_response = api_client.get(
        "/perfumes",
        params={
            **common_params,
            "skip": 2,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_page = first_response.json()
    second_page = second_response.json()

    assert first_page["total"] == 7
    assert second_page["total"] == 7
    assert first_page["limit"] == 2
    assert first_page["skip"] == 0
    assert second_page["limit"] == 2
    assert second_page["skip"] == 2
    assert len(first_page["items"]) == 2
    assert len(second_page["items"]) == 2
    assert response_names(first_page) == [
        "Citrus Dawn",
        "Jasmine Light",
    ]
    assert response_names(second_page) == [
        "Rose Garden",
        "Sweet Rose",
    ]


def test_total_is_calculated_before_pagination(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "accord": "floral",
            "sort_by": "name",
            "limit": 1,
            "skip": 0,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert len(body["items"]) == 1


@pytest.mark.parametrize(
    ("parameter_name", "parameter_value"),
    [
        ("brand", "Unknown Brand"),
        ("note", "Unknown Note"),
        ("accord", "Unknown Accord"),
        ("perfumer", "Unknown Perfumer"),
    ],
)
def test_unknown_reference_name_returns_empty_result(
    api_client: TestClient,
    parameter_name: str,
    parameter_value: str,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={parameter_name: parameter_value},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_invalid_year_range_returns_400(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "year_min": 2020,
            "year_max": 2000,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "year_min cannot be greater than year_max"
    )


def test_invalid_rating_range_returns_400(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={
            "rating_min": 4.5,
            "rating_max": 3.0,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "rating_min cannot be greater than rating_max"
    )


@pytest.mark.parametrize(
    "params",
    [
        {"rating_min": 6},
        {"rating_max": -1},
        {"votes_min": -1},
        {"limit": 0},
        {"limit": 101},
        {"skip": -1},
        {"sort_by": "country"},
        {"sort_order": "random"},
        {"gender": "other"},
        {"year_min": 2200},
    ],
)
def test_invalid_query_parameters_return_422(
    api_client: TestClient,
    params: dict[str, Any],
) -> None:
    response = api_client.get(
        "/perfumes",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "parameter_name",
    [
        "name",
        "brand",
        "note",
        "accord",
        "perfumer",
    ],
)
def test_blank_text_filter_returns_422(
    api_client: TestClient,
    parameter_name: str,
) -> None:
    response = api_client.get(
        "/perfumes",
        params={parameter_name: "   "},
    )

    assert response.status_code == 422


def test_get_perfume_by_id_still_works(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_citrus_dawn",
    )

    assert response.status_code == 200
    assert response.json()["_id"] == "perfume_citrus_dawn"
    assert response.json()["name"] == "Citrus Dawn"


def test_get_unknown_perfume_still_returns_404(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/perfumes/perfume_not_existing",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfume not found"


def test_health_endpoint_still_works(
    api_client: TestClient,
) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
