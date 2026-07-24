"""Test unitari per la normalizzazione dei filtri testuali."""

from __future__ import annotations

import re

import pytest

from backend.app.routers.perfumes import partial_case_insensitive_match


@pytest.mark.parametrize(
    "query",
    [
        "acqua di",
        "acqua-di",
        "acqua_di",
        "ACQUA DI",
    ],
)
def test_search_treats_spaces_hyphens_and_underscores_as_equivalent(
    query: str,
) -> None:
    mongo_filter = partial_case_insensitive_match(query)
    pattern = re.compile(mongo_filter["$regex"], re.IGNORECASE)

    assert pattern.search("acqua-di-gio-profondo")
    assert pattern.search("acqua di gio profondo")
    assert pattern.search("acqua_di_gio_profondo")


def test_search_keeps_other_regular_expression_characters_literal() -> None:
    mongo_filter = partial_case_insensitive_match("A.B+C")
    pattern = re.compile(mongo_filter["$regex"], re.IGNORECASE)

    assert pattern.search("A.B+C")
    assert not pattern.search("AxBBBC")


def test_search_remains_partial() -> None:
    mongo_filter = partial_case_insensitive_match("gio profondo")
    pattern = re.compile(mongo_filter["$regex"], re.IGNORECASE)

    assert pattern.search("acqua-di-gio-profondo")
