"""Test di integrazione per la gestione degli indici MongoDB di ScentBase."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pymongo import ASCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from backend.app.indexes import (
    MONGODB_ID_INDEX_NAME,
    create_managed_indexes,
    drop_managed_indexes,
    get_managed_index_names,
    list_collection_indexes,
)


TEST_DOCUMENT_PREFIX = "index_test_"
UNMANAGED_TEST_INDEX_NAME = "test_unmanaged_index"


@pytest.fixture
def clean_index_state(
    test_database: Database,
) -> Generator[Database, None, None]:
    """Isola gli indici e i documenti temporanei creati da ogni test."""
    perfumes = test_database["perfumes"]

    drop_managed_indexes(test_database)

    if UNMANAGED_TEST_INDEX_NAME in perfumes.index_information():
        perfumes.drop_index(UNMANAGED_TEST_INDEX_NAME)

    perfumes.delete_many(
        {
            "_id": {
                "$regex": f"^{TEST_DOCUMENT_PREFIX}",
            }
        }
    )

    yield test_database

    drop_managed_indexes(test_database)

    if UNMANAGED_TEST_INDEX_NAME in perfumes.index_information():
        perfumes.drop_index(UNMANAGED_TEST_INDEX_NAME)

    perfumes.delete_many(
        {
            "_id": {
                "$regex": f"^{TEST_DOCUMENT_PREFIX}",
            }
        }
    )


def test_create_managed_indexes_creates_all_expected_indexes(
    clean_index_state: Database,
) -> None:
    created_names = create_managed_indexes(clean_index_state)

    assert set(created_names) == set(get_managed_index_names())

    existing_names = set(
        clean_index_state["perfumes"].index_information()
    )
    assert set(get_managed_index_names()).issubset(existing_names)


def test_create_managed_indexes_is_idempotent(
    clean_index_state: Database,
) -> None:
    first_result = create_managed_indexes(clean_index_state)
    second_result = create_managed_indexes(clean_index_state)

    assert first_result == second_result
    assert set(first_result) == set(get_managed_index_names())


def test_list_collection_indexes_returns_stable_serializable_data(
    clean_index_state: Database,
) -> None:
    create_managed_indexes(clean_index_state)

    indexes = list_collection_indexes(clean_index_state)
    indexes_by_name = {
        index["name"]: index
        for index in indexes
    }

    assert MONGODB_ID_INDEX_NAME in indexes_by_name
    assert set(get_managed_index_names()).issubset(indexes_by_name)

    source_url_index = indexes_by_name["uq_perfumes_source_url"]
    assert source_url_index["unique"] is True
    assert source_url_index["partial_filter_expression"] == {
        "source_url": {
            "$type": "string",
        }
    }


def test_drop_managed_indexes_preserves_id_and_unmanaged_indexes(
    clean_index_state: Database,
) -> None:
    perfumes = clean_index_state["perfumes"]

    create_managed_indexes(clean_index_state)
    perfumes.create_index(
        [("year", ASCENDING)],
        name=UNMANAGED_TEST_INDEX_NAME,
    )

    dropped_names = drop_managed_indexes(clean_index_state)
    remaining_names = set(perfumes.index_information())

    assert set(dropped_names) == set(get_managed_index_names())
    assert MONGODB_ID_INDEX_NAME in remaining_names
    assert UNMANAGED_TEST_INDEX_NAME in remaining_names
    assert set(get_managed_index_names()).isdisjoint(remaining_names)


def test_unique_partial_source_url_rejects_duplicate_strings(
    clean_index_state: Database,
) -> None:
    perfumes = clean_index_state["perfumes"]
    create_managed_indexes(clean_index_state)

    with pytest.raises(DuplicateKeyError):
        perfumes.insert_one(
            {
                "_id": f"{TEST_DOCUMENT_PREFIX}duplicate_source_url",
                "source_url": (
                    "https://example.com/perfumes/citrus-dawn"
                ),
            }
        )


def test_unique_partial_source_url_allows_missing_values(
    clean_index_state: Database,
) -> None:
    perfumes = clean_index_state["perfumes"]
    create_managed_indexes(clean_index_state)

    result = perfumes.insert_many(
        [
            {
                "_id": f"{TEST_DOCUMENT_PREFIX}missing_source_url_1",
                "name": "Missing Source URL 1",
            },
            {
                "_id": f"{TEST_DOCUMENT_PREFIX}missing_source_url_2",
                "name": "Missing Source URL 2",
            },
        ]
    )

    assert len(result.inserted_ids) == 2


def test_unique_partial_source_url_allows_null_values(
    clean_index_state: Database,
) -> None:
    perfumes = clean_index_state["perfumes"]
    create_managed_indexes(clean_index_state)

    result = perfumes.insert_many(
        [
            {
                "_id": f"{TEST_DOCUMENT_PREFIX}null_source_url_1",
                "name": "Null Source URL 1",
                "source_url": None,
            },
            {
                "_id": f"{TEST_DOCUMENT_PREFIX}null_source_url_2",
                "name": "Null Source URL 2",
                "source_url": None,
            },
        ]
    )

    assert len(result.inserted_ids) == 2


def test_query_results_are_equal_before_and_after_index_creation(
    clean_index_state: Database,
) -> None:
    perfumes = clean_index_state["perfumes"]
    query = {
        "all_note_ids": "note_vanilla",
    }

    before_indexes = [
        document["_id"]
        for document in perfumes.find(
            query,
            {
                "_id": 1,
            },
        ).sort("_id", ASCENDING)
    ]

    create_managed_indexes(clean_index_state)

    after_indexes = [
        document["_id"]
        for document in perfumes.find(
            query,
            {
                "_id": 1,
            },
        ).sort("_id", ASCENDING)
    ]

    assert before_indexes
    assert before_indexes == after_indexes
