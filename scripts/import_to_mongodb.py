#!/usr/bin/env python3
"""
Importa in MongoDB i documenti JSON generati dalla pipeline ETL di ScentBase.

Lo script legge i file presenti in `data/processed/`:

- `brands.json`
- `notes.json`
- `accords.json`
- `perfumers.json`
- `perfumes.json`

e li importa nelle collection MongoDB corrispondenti.

La connessione al database viene configurata tramite variabili d'ambiente lette da `.env`:

- `MONGO_URI`: URI di connessione a MongoDB;
- `MONGO_DATABASE`: nome del database da usare.

L'importazione avviene in ordine controllato, caricando prima le collection collegate
e poi la collection centrale `perfumes`, che contiene riferimenti verso brand, note,
accordi e profumieri.

Con l'opzione `--reset`, lo script elimina prima le collection target dal database locale,
rendendo possibile rigenerare l'ambiente da zero durante test e demo.

Lo script stampa un riepilogo finale con il numero di documenti importati per collection.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database


DEFAULT_INPUT_DIR = Path("data/processed")
DEFAULT_BATCH_SIZE = 1000

COLLECTION_FILES = (
    ("brands", "brands.json"),
    ("notes", "notes.json"),
    ("accords", "accords.json"),
    ("perfumers", "perfumers.json"),
    ("perfumes", "perfumes.json"),
)


def load_json_documents(path: Path) -> list[dict[str, Any]]:
    """Carica una lista di documenti JSON da file."""
    if not path.exists():
        raise FileNotFoundError(f"File JSON non trovato: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"File JSON non valido: {path}. Il contenuto deve essere una lista di documenti.")

    invalid_items = [index for index, item in enumerate(data) if not isinstance(item, dict)]
    if invalid_items:
        preview = invalid_items[:10]
        raise ValueError(
            f"File JSON non valido: {path}. Tutti gli elementi devono essere oggetti JSON. "
            f"Indici non validi: {preview}"
        )

    return data


def batched(items: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    """Divide una lista di documenti in batch."""
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def get_database(mongo_uri: str, database_name: str) -> Database:
    """Crea la connessione a MongoDB e restituisce il database richiesto."""
    client: MongoClient = MongoClient(mongo_uri)
    client.admin.command("ping")
    return client[database_name]


def reset_collections(db: Database) -> None:
    """Elimina le collection gestite dallo script."""
    print("Reset enabled: dropping target collections...")

    for collection_name, _ in COLLECTION_FILES:
        db[collection_name].drop()
        print(f"  Dropped collection: {collection_name}")


def ensure_collection_is_empty(db: Database, collection_name: str) -> None:
    """
    Evita import accidentali su collection già popolate.

    Se si vuole rigenerare il database, usare l'opzione `--reset`.
    """
    existing_documents = db[collection_name].count_documents({})

    if existing_documents > 0:
        raise RuntimeError(
            f"La collection '{collection_name}' contiene già {existing_documents} documenti. "
            "Usare --reset per eliminare e rigenerare le collection target."
        )


def import_collection(
    db: Database,
    *,
    collection_name: str,
    json_path: Path,
    batch_size: int,
) -> int:
    """Importa una collection MongoDB a partire da un file JSON."""
    documents = load_json_documents(json_path)
    collection = db[collection_name]

    print(f"Importing {collection_name} from {json_path}...")

    if documents:
        for batch in batched(documents, batch_size):
            collection.insert_many(batch, ordered=True)

    imported_count = collection.count_documents({})

    if imported_count != len(documents):
        raise RuntimeError(
            f"Conteggio non coerente per '{collection_name}': "
            f"documenti nel file={len(documents)}, documenti importati={imported_count}"
        )

    print(f"  Imported {collection_name}: {imported_count}")
    return imported_count


def parse_args() -> argparse.Namespace:
    """Legge gli argomenti da terminale."""
    parser = argparse.ArgumentParser(description="Importa in MongoDB i JSON generati dalla pipeline ETL.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Cartella contenente i file JSON generati dalla trasformazione.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina le collection target prima dell'importazione.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Numero di documenti da inserire per batch.",
    )
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
    if args.batch_size <= 0:
        raise ValueError("--batch-size deve essere maggiore di 0.")

    print("MongoDB import started")
    print(f"Input directory: {args.input_dir}")
    print(f"Database: {database_name}")

    db = get_database(mongo_uri, database_name)

    if args.reset:
        reset_collections(db)
    else:
        for collection_name, _ in COLLECTION_FILES:
            ensure_collection_is_empty(db, collection_name)

    imported_counts: dict[str, int] = {}

    for collection_name, filename in COLLECTION_FILES:
        json_path = args.input_dir / filename
        imported_counts[collection_name] = import_collection(
            db,
            collection_name=collection_name,
            json_path=json_path,
            batch_size=args.batch_size,
        )

    print("\nMongoDB import completed successfully")
    print("Imported documents:")

    for collection_name, _ in COLLECTION_FILES:
        print(f"  {collection_name}: {imported_counts[collection_name]}")


if __name__ == "__main__":
    main()