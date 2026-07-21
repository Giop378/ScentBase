#!/usr/bin/env python3
"""Crea, elenca o rimuove gli indici MongoDB gestiti da ScentBase.

Esempi:

    python scripts/manage_indexes.py create
    python scripts/manage_indexes.py list
    python scripts/manage_indexes.py drop

Lo script deve essere eseguito dalla radice del repository. Le variabili
``MONGO_URI`` e ``MONGO_DATABASE`` vengono lette dal file ``.env`` oppure
dall'ambiente del processo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo.errors import PyMongoError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

load_dotenv(REPOSITORY_ROOT / ".env")

from backend.app.config import MONGO_DATABASE  # noqa: E402
from backend.app.database import (  # noqa: E402
    check_connection,
    close_connection,
    get_database,
)
from backend.app.indexes import (  # noqa: E402
    create_managed_indexes,
    drop_managed_indexes,
    list_collection_indexes,
)


def parse_args() -> argparse.Namespace:
    """Legge il comando richiesto da terminale."""
    parser = argparse.ArgumentParser(
        description=(
            "Gestisce gli indici MongoDB definiti dal progetto ScentBase."
        )
    )
    parser.add_argument(
        "command",
        choices=("create", "list", "drop"),
        help=(
            "'create' crea gli indici, 'list' li elenca, "
            "'drop' rimuove soltanto quelli gestiti dal progetto."
        ),
    )
    return parser.parse_args()


def print_indexes(indexes: list[dict[str, object]]) -> None:
    """Stampa gli indici in formato JSON leggibile."""
    print(json.dumps(indexes, ensure_ascii=False, indent=2))


def main() -> int:
    """Esegue il comando selezionato."""
    args = parse_args()

    if not check_connection():
        print(
            "Errore: impossibile connettersi a MongoDB. "
            "Avviare il servizio con 'docker compose up -d' "
            "e controllare il file .env.",
            file=sys.stderr,
        )
        return 1

    database = get_database()

    print("ScentBase index management")
    print(f"Database: {MONGO_DATABASE}")
    print("Collection: perfumes")
    print(f"Command: {args.command}\n")

    try:
        if args.command == "create":
            created_names = create_managed_indexes(database)
            print("Indici gestiti disponibili:")
            for index_name in created_names:
                print(f"  - {index_name}")

            print("\nStato corrente:")
            print_indexes(list_collection_indexes(database))
            return 0

        if args.command == "drop":
            dropped_names = drop_managed_indexes(database)

            if dropped_names:
                print("Indici gestiti rimossi:")
                for index_name in dropped_names:
                    print(f"  - {index_name}")
            else:
                print("Nessun indice gestito da rimuovere.")

            print("\nStato corrente:")
            print_indexes(list_collection_indexes(database))
            return 0

        print_indexes(list_collection_indexes(database))
        return 0

    except PyMongoError as exc:
        print(
            f"Errore MongoDB durante la gestione degli indici: {exc}",
            file=sys.stderr,
        )
        return 1
    finally:
        close_connection()


if __name__ == "__main__":
    raise SystemExit(main())
