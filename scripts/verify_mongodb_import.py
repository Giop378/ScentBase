#!/usr/bin/env python3
"""
Verifica l'importazione dei documenti ScentBase in MongoDB.

Lo script controlla che le collection MongoDB popolate tramite `import_to_mongodb.py`
siano coerenti con gli output generati dalla pipeline ETL.

La connessione al database viene configurata tramite variabili d'ambiente lette da `.env`:

- `MONGO_URI`: URI di connessione a MongoDB;
- `MONGO_DATABASE`: nome del database da usare.

Controlli effettuati:

- conteggio dei documenti importati per collection;
- unicità degli `_id`;
- presenza e unicità di `source_url` nella collection `perfumes`;
- validità del riferimento `brand_id`;
- validità dei riferimenti verso `notes`;
- validità dei riferimenti verso `accords`;
- validità dei riferimenti verso `perfumers`;
- presenza degli array di riferimenti previsti nei documenti `perfumes`.

Lo script stampa un riepilogo sintetico dei controlli e termina con errore se almeno
una verifica fallisce.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


EXPECTED_COUNTS = {
    "perfumes": 24063,
    "brands": 1060,
    "notes": 1668,
    "accords": 84,
    "perfumers": 905,
}

PERFUME_REFERENCE_FIELDS = (
    "top_note_ids",
    "middle_note_ids",
    "base_note_ids",
    "all_note_ids",
    "accord_ids",
    "perfumer_ids",
)

NOTE_REFERENCE_FIELDS = (
    "top_note_ids",
    "middle_note_ids",
    "base_note_ids",
    "all_note_ids",
)


def get_database(mongo_uri: str, database_name: str) -> Database:
    """Crea la connessione a MongoDB e restituisce il database richiesto."""
    client: MongoClient = MongoClient(mongo_uri)
    client.admin.command("ping")
    return client[database_name]


def count_duplicate_values(collection: Collection, field_name: str, *, ignore_missing: bool = False) -> int:
    """Conta quanti valori duplicati esistono per un campo."""
    match_stage: dict[str, Any] = {}

    if ignore_missing:
        match_stage[field_name] = {"$exists": True, "$nin": [None, ""]}

    pipeline: list[dict[str, Any]] = []

    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend(
        [
            {"$group": {"_id": f"${field_name}", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
            {"$count": "duplicate_values"},
        ]
    )

    result = list(collection.aggregate(pipeline))
    if not result:
        return 0

    return int(result[0]["duplicate_values"])


def count_missing_or_empty(collection: Collection, field_name: str) -> int:
    """Conta documenti in cui un campo è mancante, nullo o stringa vuota."""
    return collection.count_documents(
        {
            "$or": [
                {field_name: {"$exists": False}},
                {field_name: None},
                {field_name: ""},
            ]
        }
    )


def load_id_set(db: Database, collection_name: str) -> set[str]:
    """Carica gli `_id` di una collection in un set."""
    return {document["_id"] for document in db[collection_name].find({}, {"_id": 1})}


def format_preview(values: list[str], *, limit: int = 10) -> str:
    """Formatta un'anteprima leggibile di una lista di errori."""
    if not values:
        return "-"
    preview = values[:limit]
    suffix = "" if len(values) <= limit else f" ... (+{len(values) - limit})"
    return "; ".join(preview) + suffix


def verify_counts(db: Database, *, skip_expected_counts: bool) -> int:
    """Verifica i conteggi delle collection."""
    errors = 0

    print("Collection counts:")

    for collection_name, expected_count in EXPECTED_COUNTS.items():
        actual_count = db[collection_name].count_documents({})
        print(f"  {collection_name}: {actual_count}")

        if not skip_expected_counts and actual_count != expected_count:
            print(f"    ERROR: expected {expected_count}, found {actual_count}")
            errors += 1

    return errors


def verify_unique_ids(db: Database) -> int:
    """Verifica l'unicità degli `_id` nelle collection importate."""
    errors = 0

    print("\n_id uniqueness checks:")

    for collection_name in EXPECTED_COUNTS:
        collection = db[collection_name]
        duplicate_ids = count_duplicate_values(collection, "_id")
        missing_ids = count_missing_or_empty(collection, "_id")

        print(f"  {collection_name} duplicate _id values: {duplicate_ids}")
        print(f"  {collection_name} documents without valid _id: {missing_ids}")

        if duplicate_ids or missing_ids:
            errors += duplicate_ids + missing_ids

    return errors


def verify_source_urls(db: Database) -> int:
    """Verifica presenza e unicità di `source_url` nella collection `perfumes`."""
    collection = db["perfumes"]

    duplicate_source_urls = count_duplicate_values(collection, "source_url", ignore_missing=True)
    missing_source_urls = count_missing_or_empty(collection, "source_url")

    print("\nsource_url checks:")
    print(f"  Duplicate source_url values: {duplicate_source_urls}")
    print(f"  Documents without valid source_url: {missing_source_urls}")

    return duplicate_source_urls + missing_source_urls


def verify_perfume_reference_arrays(db: Database) -> int:
    """Verifica che i campi di riferimento multipli dei profumi siano array."""
    invalid_documents: list[str] = []

    projection = {field: 1 for field in PERFUME_REFERENCE_FIELDS}
    projection["_id"] = 1

    for perfume in db["perfumes"].find({}, projection):
        perfume_id = str(perfume.get("_id", "<missing _id>"))

        for field in PERFUME_REFERENCE_FIELDS:
            value = perfume.get(field)
            if not isinstance(value, list):
                invalid_documents.append(f"{perfume_id}: {field} non è un array")
                continue

            invalid_items = [item for item in value if item is None or str(item).strip() == ""]
            if invalid_items:
                invalid_documents.append(f"{perfume_id}: {field} contiene valori vuoti")

    print("\nPerfume array field checks:")
    print(f"  Invalid perfume array fields: {len(invalid_documents)}")

    if invalid_documents:
        print(f"  Preview: {format_preview(invalid_documents)}")

    return len(invalid_documents)


def verify_references(db: Database) -> int:
    """Verifica che i riferimenti da `perfumes` puntino a documenti esistenti."""
    brand_ids = load_id_set(db, "brands")
    note_ids = load_id_set(db, "notes")
    accord_ids = load_id_set(db, "accords")
    perfumer_ids = load_id_set(db, "perfumers")

    invalid_brand_references: list[str] = []
    invalid_note_references: list[str] = []
    invalid_accord_references: list[str] = []
    invalid_perfumer_references: list[str] = []

    projection = {
        "_id": 1,
        "brand_id": 1,
        "top_note_ids": 1,
        "middle_note_ids": 1,
        "base_note_ids": 1,
        "all_note_ids": 1,
        "accord_ids": 1,
        "perfumer_ids": 1,
    }

    for perfume in db["perfumes"].find({}, projection):
        perfume_id = str(perfume.get("_id", "<missing _id>"))

        brand_id = perfume.get("brand_id")
        if brand_id not in brand_ids:
            invalid_brand_references.append(f"{perfume_id}: {brand_id!r}")

        for field in NOTE_REFERENCE_FIELDS:
            values = perfume.get(field, [])
            if not isinstance(values, list):
                continue

            for note_id in values:
                if note_id not in note_ids:
                    invalid_note_references.append(f"{perfume_id}: {field} -> {note_id!r}")

        accord_values = perfume.get("accord_ids", [])
        if isinstance(accord_values, list):
            for accord_id in accord_values:
                if accord_id not in accord_ids:
                    invalid_accord_references.append(f"{perfume_id}: {accord_id!r}")

        perfumer_values = perfume.get("perfumer_ids", [])
        if isinstance(perfumer_values, list):
            for perfumer_id in perfumer_values:
                if perfumer_id not in perfumer_ids:
                    invalid_perfumer_references.append(f"{perfume_id}: {perfumer_id!r}")

    print("\nReference checks:")
    print(f"  Invalid brand references: {len(invalid_brand_references)}")
    print(f"  Invalid note references: {len(invalid_note_references)}")
    print(f"  Invalid accord references: {len(invalid_accord_references)}")
    print(f"  Invalid perfumer references: {len(invalid_perfumer_references)}")

    if invalid_brand_references:
        print(f"  Brand preview: {format_preview(invalid_brand_references)}")
    if invalid_note_references:
        print(f"  Note preview: {format_preview(invalid_note_references)}")
    if invalid_accord_references:
        print(f"  Accord preview: {format_preview(invalid_accord_references)}")
    if invalid_perfumer_references:
        print(f"  Perfumer preview: {format_preview(invalid_perfumer_references)}")

    return (
        len(invalid_brand_references)
        + len(invalid_note_references)
        + len(invalid_accord_references)
        + len(invalid_perfumer_references)
    )


def parse_args() -> argparse.Namespace:
    """Legge gli argomenti da terminale."""
    parser = argparse.ArgumentParser(description="Verifica l'importazione dei dati ScentBase in MongoDB.")
    parser.add_argument(
        "--mongo-uri",
        default=None,
        help="URI MongoDB. Se non indicata, viene letta da MONGO_URI.",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Nome database. Se non indicato, viene letto da MONGO_DATABASE.",
    )
    parser.add_argument(
        "--skip-expected-counts",
        action="store_true",
        help="Non fallisce se i conteggi sono diversi dai valori attesi del dataset corrente.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    mongo_uri = args.mongo_uri or os.getenv("MONGO_URI")
    database_name = args.database or os.getenv("MONGO_DATABASE")

    if not mongo_uri:
        raise RuntimeError("Variabile MONGO_URI non configurata. Verificare il file .env.")
    if not database_name:
        raise RuntimeError("Variabile MONGO_DATABASE non configurata. Verificare il file .env.")

    print("MongoDB import verification started")
    print(f"Database: {database_name}\n")

    db = get_database(mongo_uri, database_name)

    errors = 0
    errors += verify_counts(db, skip_expected_counts=args.skip_expected_counts)
    errors += verify_unique_ids(db)
    errors += verify_source_urls(db)
    errors += verify_perfume_reference_arrays(db)
    errors += verify_references(db)

    print("\nVerification summary:")
    print(f"  Total errors: {errors}")

    if errors:
        raise SystemExit("Verification failed.")

    print("Verification completed successfully.")


if __name__ == "__main__":
    main()