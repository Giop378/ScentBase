#!/usr/bin/env python3
"""
Estrae i valori distinti dal dataset principale di ScentBase.

Lo script legge `data/raw/fra_cleaned.csv` e genera tre file di testo in
`data/enrichment/`:

- `distinct_notes.txt`: note olfattive distinte estratte da Top, Middle e Base;
- `distinct_accords.txt`: accordi distinti estratti da mainaccord1-mainaccord5;
- `distinct_perfumers.txt`: profumieri distinti estratti da Perfumer1 e Perfumer2.

Questi file servono come input per creare i mapping di arricchimento con supporto AI:
`note_olfactory_groups.json`, `accord_colors.json` e `perfumer_nationalities.json`.
"""

from __future__ import annotations

import argparse
import ast
import csv
import re
from pathlib import Path
from typing import Iterable

DEFAULT_INPUT = Path("data/raw/fra_cleaned.csv")
DEFAULT_OUTPUT_DIR = Path("data/enrichment")

NOTE_COLUMNS = ("Top", "Middle", "Base")
ACCORD_COLUMNS = ("mainaccord1", "mainaccord2", "mainaccord3", "mainaccord4", "mainaccord5")
PERFUMER_COLUMNS = ("Perfumer1", "Perfumer2")
MISSING_VALUES = {"", "nan", "none", "null", "n/a", "na", "unknown", "-"}
ENCODINGS_TO_TRY = ("utf-8-sig", "cp1252", "latin1")


def is_missing(value: object) -> bool:
    """Restituisce True se il valore è vuoto o rappresenta un valore mancante."""
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_VALUES


def clean_text(value: str) -> str:
    """Normalizza spazi e virgolette mantenendo il valore leggibile originale."""
    value = str(value).replace("\u00a0", " ").strip()
    value = value.strip("'\"`“”‘’ ")
    value = re.sub(r"\s+", " ", value)
    return value


def split_list_field(value: object) -> list[str]:
    """
    Converte un campo CSV che può contenere una lista di valori in una lista Python.

    Gestisce sia formati simili a liste Python, ad esempio ['Rose', 'Jasmine'],
    sia stringhe separate da virgola, pipe o newline.
    """
    if is_missing(value):
        return []

    text = str(value).strip()

    # Caso: campo rappresentato come lista testuale, es. "['Rose', 'Jasmine']".
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple, set)):
                return [clean_text(item) for item in parsed if not is_missing(item)]
        except (ValueError, SyntaxError):
            pass

    # Caso più comune: valori separati da virgola, pipe o nuova riga.
    parts = re.split(r",|\||\n", text)
    return [clean_text(part) for part in parts if not is_missing(clean_text(part))]


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], str]:
    """Legge il CSV provando più encoding e restituisce righe + encoding usato."""
    last_error: UnicodeDecodeError | None = None

    for encoding in ENCODINGS_TO_TRY:
        try:
            with path.open("r", encoding=encoding, newline="") as file:
                reader = csv.DictReader(file, delimiter=";")
                return list(reader), encoding
        except UnicodeDecodeError as exc:
            last_error = exc

    raise UnicodeDecodeError(
        last_error.encoding if last_error else "unknown",
        last_error.object if last_error else b"",
        last_error.start if last_error else 0,
        last_error.end if last_error else 0,
        "Unable to decode CSV with supported encodings",
    )


def extract_from_columns(rows: Iterable[dict[str, str]], columns: Iterable[str], split_values: bool) -> set[str]:
    """Estrae valori distinti da un insieme di colonne."""
    values: set[str] = set()

    for row in rows:
        for column in columns:
            raw_value = row.get(column)
            items = split_list_field(raw_value) if split_values else [clean_text(raw_value)] if not is_missing(raw_value) else []

            for item in items:
                if not is_missing(item):
                    values.add(item)

    return values


def write_values(path: Path, values: Iterable[str]) -> None:
    """Scrive valori ordinati alfabeticamente, uno per riga."""
    sorted_values = sorted(set(values), key=lambda item: item.lower())
    path.write_text("\n".join(sorted_values) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Estrae note, accordi e profumieri distinti da fra_cleaned.csv.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Percorso del CSV sorgente.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Cartella di output.")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"CSV non trovato: {args.input}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows, encoding = read_csv_rows(args.input)

    notes = extract_from_columns(rows, NOTE_COLUMNS, split_values=True)
    accords = extract_from_columns(rows, ACCORD_COLUMNS, split_values=False)
    perfumers = extract_from_columns(rows, PERFUMER_COLUMNS, split_values=False)

    write_values(args.output_dir / "distinct_notes.txt", notes)
    write_values(args.output_dir / "distinct_accords.txt", accords)
    write_values(args.output_dir / "distinct_perfumers.txt", perfumers)

    print("Distinct values extraction completed")
    print(f"Input file: {args.input}")
    print(f"Encoding used: {encoding}")
    print(f"Rows read: {len(rows)}")
    print(f"Distinct notes: {len(notes)}")
    print(f"Distinct accords: {len(accords)}")
    print(f"Distinct perfumers: {len(perfumers)}")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
