"""Test degli endpoint di supporto usati dall'interfaccia React."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_catalog_references_return_brands_and_accord_colors(
    api_client: TestClient,
) -> None:
    response = api_client.get("/references/catalog")

    assert response.status_code == 200
    body = response.json()

    brand_by_id = {item["_id"]: item for item in body["brands"]}
    accord_by_id = {item["_id"]: item for item in body["accords"]}

    assert brand_by_id["brand_dior"]["name"] == "Dior"
    assert accord_by_id["accord_citrus"] == {
        "_id": "accord_citrus",
        "name": "citrus",
        "color_hex": "#F5C542",
    }


def test_top_perfumes_include_ordered_accord_documents(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/statistics/top-perfumes",
        params={"limit": 5, "min_votes": 100},
    )

    assert response.status_code == 200
    body = response.json()
    vanilla_woods = next(
        item
        for item in body["items"]
        if item["_id"] == "perfume_vanilla_woods"
    )

    assert [accord["_id"] for accord in vanilla_woods["accords"]] == [
        "accord_sweet",
        "accord_woody",
    ]
    assert [accord["color_hex"] for accord in vanilla_woods["accords"]] == [
        "#D98AC7",
        "#8B5A2B",
    ]
