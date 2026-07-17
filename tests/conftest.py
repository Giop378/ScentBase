"""Fixture pytest per i test di integrazione del backend ScentBase.

La suite usa un database MongoDB separato, denominato per impostazione
predefinita ``scentbase_test``. Il database viene eliminato, ricreato e
popolato con dati sintetici prima dei test, quindi eliminato nuovamente al
termine della sessione.

La variabile ``MONGO_DATABASE`` viene impostata prima di importare
l'applicazione FastAPI, così tutti i router utilizzano esclusivamente il
database di test.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.database import Database


# Carica le variabili locali senza sovrascrivere quelle già impostate
# esplicitamente nel processo che esegue pytest.
load_dotenv()

TEST_DATABASE_NAME = os.getenv(
    "MONGO_TEST_DATABASE",
    "scentbase_test",
).strip()

if not TEST_DATABASE_NAME:
    raise RuntimeError("MONGO_TEST_DATABASE non può essere vuota.")

if not TEST_DATABASE_NAME.endswith("_test"):
    raise RuntimeError(
        "Il database utilizzato dai test deve terminare con '_test'. "
        f"Valore ricevuto: {TEST_DATABASE_NAME!r}"
    )

# Questa assegnazione deve avvenire prima degli import del backend.
os.environ["MONGO_DATABASE"] = TEST_DATABASE_NAME

from backend.app.config import MONGO_URI  # noqa: E402
from backend.app.main import app  # noqa: E402


BRANDS: list[dict[str, Any]] = [
    {
        "_id": "brand_dior",
        "name": "Dior",
        "country": "France",
    },
    {
        "_id": "brand_guerlain",
        "name": "Guerlain",
        "country": "France",
    },
    {
        "_id": "brand_test_house",
        "name": "Test House",
        "country": "Italy",
    },
]

NOTES: list[dict[str, Any]] = [
    {
        "_id": "note_vanilla",
        "name": "Vanilla",
        "olfactory_group": "gourmand",
    },
    {
        "_id": "note_bergamot",
        "name": "Bergamot",
        "olfactory_group": "citrus",
    },
    {
        "_id": "note_rose",
        "name": "Rose",
        "olfactory_group": "floral",
    },
    {
        "_id": "note_jasmine",
        "name": "Jasmine",
        "olfactory_group": "floral",
    },
    {
        "_id": "note_sandalwood",
        "name": "Sandalwood",
        "olfactory_group": "woody",
    },
]

ACCORDS: list[dict[str, Any]] = [
    {
        "_id": "accord_citrus",
        "name": "citrus",
        "color_hex": "#F5C542",
    },
    {
        "_id": "accord_sweet",
        "name": "sweet",
        "color_hex": "#D98AC7",
    },
    {
        "_id": "accord_woody",
        "name": "woody",
        "color_hex": "#8B5A2B",
    },
    {
        "_id": "accord_floral",
        "name": "floral",
        "color_hex": "#E8A0BF",
    },
]

PERFUMERS: list[dict[str, Any]] = [
    {
        "_id": "perfumer_alberto_morillas",
        "name": "Alberto Morillas",
        "nationality": "Spanish",
    },
    {
        "_id": "perfumer_jacques_polge",
        "name": "Jacques Polge",
        "nationality": "French",
    },
    {
        "_id": "perfumer_test",
        "name": "Test Perfumer",
        "nationality": "Italian",
    },
]

PERFUMES: list[dict[str, Any]] = [
    {
        "_id": "perfume_citrus_dawn",
        "name": "Citrus Dawn",
        "brand_id": "brand_dior",
        "gender": "unisex",
        "rating": 4.5,
        "votes": 500,
        "year": 2020,
        "top_note_ids": ["note_bergamot"],
        "middle_note_ids": [],
        "base_note_ids": [],
        "all_note_ids": ["note_bergamot"],
        "accord_ids": ["accord_citrus"],
        "perfumer_ids": ["perfumer_alberto_morillas"],
        "source_url": "https://example.com/perfumes/citrus-dawn",
    },
    {
        "_id": "perfume_vanilla_night",
        "name": "Vanilla Night",
        "brand_id": "brand_guerlain",
        "gender": "women",
        "rating": 4.7,
        "votes": 1000,
        "year": 2018,
        "top_note_ids": [],
        "middle_note_ids": ["note_vanilla"],
        "base_note_ids": [],
        "all_note_ids": ["note_vanilla"],
        "accord_ids": ["accord_sweet"],
        "perfumer_ids": ["perfumer_jacques_polge"],
        "source_url": "https://example.com/perfumes/vanilla-night",
    },
    {
        "_id": "perfume_woody_trail",
        "name": "Woody Trail",
        "brand_id": "brand_dior",
        "gender": "men",
        "rating": 4.1,
        "votes": 300,
        "year": 2010,
        "top_note_ids": [],
        "middle_note_ids": [],
        "base_note_ids": ["note_sandalwood"],
        "all_note_ids": ["note_sandalwood"],
        "accord_ids": ["accord_woody"],
        "perfumer_ids": ["perfumer_alberto_morillas"],
        "source_url": "https://example.com/perfumes/woody-trail",
    },
    {
        "_id": "perfume_rose_garden",
        "name": "Rose Garden",
        "brand_id": "brand_test_house",
        "gender": "women",
        "rating": 3.8,
        "votes": 80,
        "year": 2022,
        "top_note_ids": ["note_rose"],
        "middle_note_ids": [],
        "base_note_ids": [],
        "all_note_ids": ["note_rose"],
        "accord_ids": ["accord_floral"],
        "perfumer_ids": ["perfumer_test"],
        "source_url": "https://example.com/perfumes/rose-garden",
    },
    {
        "_id": "perfume_vanilla_woods",
        "name": "Vanilla Woods",
        "brand_id": "brand_dior",
        "gender": "unisex",
        "rating": 4.3,
        "votes": 700,
        "year": 2015,
        "top_note_ids": ["note_vanilla"],
        "middle_note_ids": [],
        "base_note_ids": ["note_sandalwood"],
        "all_note_ids": ["note_vanilla", "note_sandalwood"],
        "accord_ids": ["accord_sweet", "accord_woody"],
        "perfumer_ids": ["perfumer_alberto_morillas"],
        "source_url": "https://example.com/perfumes/vanilla-woods",
    },
    {
        "_id": "perfume_jasmine_light",
        "name": "Jasmine Light",
        "brand_id": "brand_guerlain",
        "gender": "women",
        "rating": 3.5,
        "votes": 40,
        "year": 2005,
        "top_note_ids": ["note_jasmine"],
        "middle_note_ids": [],
        "base_note_ids": [],
        "all_note_ids": ["note_jasmine"],
        "accord_ids": ["accord_floral"],
        "perfumer_ids": ["perfumer_jacques_polge"],
        "source_url": "https://example.com/perfumes/jasmine-light",
    },
    {
        "_id": "perfume_sweet_rose",
        "name": "Sweet Rose",
        "brand_id": "brand_test_house",
        "gender": "unisex",
        "rating": 4.0,
        "votes": 150,
        "year": 2012,
        "top_note_ids": ["note_rose"],
        "middle_note_ids": ["note_vanilla"],
        "base_note_ids": [],
        "all_note_ids": ["note_rose", "note_vanilla"],
        "accord_ids": ["accord_floral", "accord_sweet"],
        "perfumer_ids": ["perfumer_test"],
        "source_url": "https://example.com/perfumes/sweet-rose",
    },
]


def seed_test_database(database: Database) -> None:
    """Inserisce nelle cinque collection i documenti sintetici della suite."""
    database["brands"].insert_many(BRANDS)
    database["notes"].insert_many(NOTES)
    database["accords"].insert_many(ACCORDS)
    database["perfumers"].insert_many(PERFUMERS)
    database["perfumes"].insert_many(PERFUMES)


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Generator[Database, None, None]:
    """Crea, popola e infine elimina il database MongoDB di test."""
    setup_client: MongoClient = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    try:
        setup_client.admin.command("ping")
    except Exception as exc:
        setup_client.close()
        raise RuntimeError(
            "Impossibile connettersi a MongoDB. "
            "Avviare il servizio con 'docker compose up -d' prima dei test."
        ) from exc

    # Il controllo sul suffisso _test è già stato eseguito all'importazione,
    # ma viene ripetuto immediatamente prima della cancellazione.
    if not TEST_DATABASE_NAME.endswith("_test"):
        setup_client.close()
        raise RuntimeError(
            "Operazione annullata: il database da eliminare non termina "
            "con '_test'."
        )

    setup_client.drop_database(TEST_DATABASE_NAME)
    database = setup_client[TEST_DATABASE_NAME]
    seed_test_database(database)

    yield database

    # Pulizia finale indipendente dallo stato dei test.
    setup_client.drop_database(TEST_DATABASE_NAME)
    setup_client.close()


@pytest.fixture(scope="session")
def api_client(test_database: Database) -> Generator[TestClient, None, None]:
    """Fornisce un client HTTP per chiamare l'app FastAPI nei test."""
    with TestClient(app) as client:
        yield client
