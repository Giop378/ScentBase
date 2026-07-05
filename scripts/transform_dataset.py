#!/usr/bin/env python3
"""
Trasforma il dataset principale di ScentBase in documenti JSON per MongoDB.

Lo script legge `data/raw/fra_cleaned.csv`, valida i mapping di arricchimento
presenti in `data/enrichment/` e genera in `data/processed/` i file JSON per le
collection previste dal modello documentale:

- `perfumes.json`
- `brands.json`
- `notes.json`
- `accords.json`
- `perfumers.json`

La trasformazione genera identificativi deterministici, normalizza rating/voti/anno,
ignora i profumieri `unknown`, crea `all_note_ids` e valorizza i campi di
arricchimento:

- `notes.olfactory_group`
- `accords.color_hex`
- `perfumers.nationality`

Prima di generare gli output, lo script valida i mapping generati con supporto AI:

- controlla che ogni valore distinto presente nel dataset sia presente nel mapping;
- controlla che il mapping non contenga chiavi inventate o non presenti nel dataset;
- controlla che i valori di `note_olfactory_groups.json` appartengano ai gruppi ammessi;
- controlla che i valori di `accord_colors.json` siano nel formato `#RRGGBB`;
- controlla che `perfumer_nationalities.json` non contenga valori nulli o vuoti;
- blocca la trasformazione se trova chiavi mancanti, chiavi extra, valori nulli,
  duplicati normalizzati o valori non validi.

Per scelta progettuale non vengono usati fallback automatici durante la trasformazione:
i mapping devono contenere tutti e soli i valori distinti estratti dal dataset. Eventuali
casi incerti devono essere gestiti direttamente nei mapping AI con valori espliciti come
`other`, `#9E9E9E` o `Unknown`.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, NamedTuple

DEFAULT_INPUT = Path("data/raw/fra_cleaned.csv")
DEFAULT_ENRICHMENT_DIR = Path("data/enrichment")
DEFAULT_OUTPUT_DIR = Path("data/processed")

NOTE_COLUMNS = ("Top", "Middle", "Base")
ACCORD_COLUMNS = ("mainaccord1", "mainaccord2", "mainaccord3", "mainaccord4", "mainaccord5")
PERFUMER_COLUMNS = ("Perfumer1", "Perfumer2")

CSV_MISSING_VALUES = {"", "nan", "none", "null", "n/a", "na", "unknown", "-"}
MAPPING_MISSING_VALUES = {"", "nan", "none", "null", "n/a", "na", "-"}
ENCODINGS_TO_TRY = ("utf-8-sig", "cp1252", "latin1")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
DEFAULT_ACCORD_COLOR = "#9E9E9E"
UNKNOWN_NATIONALITY = "Unknown"
OTHER_OLFACTORY_GROUP = "other"

ALLOWED_OLFACTORY_GROUPS = {
    "citrus",
    "floral",
    "fruity",
    "green",
    "aromatic",
    "spicy",
    "woody",
    "resinous",
    "balsamic",
    "gourmand",
    "sweet",
    "musky",
    "animalic",
    "aquatic",
    "ozonic",
    "powdery",
    "smoky",
    "earthy",
    "herbal",
    "leathery",
    "aldehydic",
    OTHER_OLFACTORY_GROUP,
}


class MappingData(NamedTuple):
    """Contiene un mapping normalizzato e metadati utili alla validazione."""

    values: dict[str, str]
    original_keys_by_normalized_key: dict[str, str]
    invalid_values: dict[str, str]
    duplicate_normalized_keys: dict[str, list[str]]


class MappingValidationError(ValueError):
    """Errore sollevato quando un mapping AI non è coerente con il dataset."""


def is_csv_missing(value: object) -> bool:
    """Restituisce True se il valore del CSV è vuoto o rappresenta un valore mancante."""
    if value is None:
        return True
    return str(value).strip().lower() in CSV_MISSING_VALUES


def is_mapping_missing(value: object) -> bool:
    """Restituisce True se un valore del mapping è vuoto o non valido."""
    if value is None:
        return True
    return str(value).strip().lower() in MAPPING_MISSING_VALUES


def clean_text(value: object) -> str:
    """Normalizza spazi e virgolette mantenendo il valore leggibile originale."""
    value = str(value).replace("\u00a0", " ").strip()
    value = value.strip("'\"`“”‘’ ")
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_lookup_key(value: object) -> str:
    """Crea una chiave stabile per confrontare dataset e mapping AI."""
    return clean_text(value).lower()


def slugify(value: object) -> str:
    """Converte un valore leggibile in una stringa adatta agli identificativi."""
    text = clean_text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def make_id(prefix: str, value: object) -> str:
    """Genera un identificativo deterministico con prefisso di collection."""
    return f"{prefix}_{slugify(value)}"


def make_perfume_id(source_url: str, name: str, brand: str) -> str:
    """
    Genera un id stabile per i profumi.

    `Perfume` non viene usato da solo perché non è completamente univoco. Se l'URL
    è disponibile viene usato come base stabile; altrimenti si usa nome + brand.
    """
    base = clean_text(source_url) if not is_csv_missing(source_url) else f"{clean_text(name)}_{clean_text(brand)}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    return f"perfume_{digest}"


def split_list_field(value: object) -> list[str]:
    """
    Converte un campo CSV che può contenere una lista di valori in una lista Python.

    Gestisce sia formati simili a liste Python, ad esempio ['Rose', 'Jasmine'],
    sia stringhe separate da virgola, pipe o newline.
    """
    if is_csv_missing(value):
        return []

    text = str(value).strip()

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple, set)):
                return [clean_text(item) for item in parsed if not is_csv_missing(item)]
        except (ValueError, SyntaxError):
            pass

    parts = re.split(r",|\||\n", text)
    return [clean_text(part) for part in parts if not is_csv_missing(clean_text(part))]


def parse_float(value: object) -> float | None:
    """Converte rating con virgola decimale in float."""
    if is_csv_missing(value):
        return None
    text = clean_text(value).replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    """Converte valori numerici interi, gestendo separatori e valori mancanti."""
    if is_csv_missing(value):
        return None
    text = clean_text(value)
    text = text.replace(".", "").replace(",", "")
    text = re.sub(r"[^0-9-]", "", text)
    if is_csv_missing(text):
        return None
    try:
        return int(text)
    except ValueError:
        return None


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


def validate_note_group(value: str) -> str | None:
    """Valida e normalizza un gruppo olfattivo."""
    normalized = clean_text(value).lower()
    if normalized not in ALLOWED_OLFACTORY_GROUPS:
        return None
    return normalized


def validate_color_hex(value: str) -> str | None:
    """Valida e normalizza un colore HEX."""
    normalized = clean_text(value).upper()
    if not HEX_COLOR_PATTERN.fullmatch(normalized):
        return None
    return normalized


def validate_nationality(value: str) -> str | None:
    """Valida e normalizza la nazionalità descrittiva di un profumiere."""
    normalized = clean_text(value)
    if normalized.lower() == "unknown":
        return UNKNOWN_NATIONALITY
    if is_mapping_missing(normalized):
        return None
    return normalized


def load_mapping(
    path: Path,
    *,
    value_validator: Callable[[str], str | None],
) -> MappingData:
    """
    Carica un mapping JSON e normalizza le chiavi per confronto case-insensitive.

    La funzione non applica fallback automatici. Se il file non esiste, se non è un
    oggetto JSON, se contiene valori nulli/vuoti o se contiene valori non ammessi,
    la trasformazione viene bloccata dalla validazione.
    """
    if not path.exists():
        raise FileNotFoundError(f"Mapping di arricchimento non trovato: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Mapping non valido: {path}. Il contenuto deve essere un oggetto JSON.")

    values: dict[str, str] = {}
    original_keys: dict[str, str] = {}
    invalid_values: dict[str, str] = {}
    normalized_to_originals: dict[str, list[str]] = {}

    for key, value in data.items():
        if is_mapping_missing(key):
            raise ValueError(f"Mapping non valido: {path}. Trovata una chiave vuota o non valida.")
        if is_mapping_missing(value):
            invalid_values[clean_text(key)] = str(value)
            continue

        normalized_key = normalize_lookup_key(key)
        clean_key = clean_text(key)
        clean_value = clean_text(value)
        validated_value = value_validator(clean_value)

        normalized_to_originals.setdefault(normalized_key, []).append(clean_key)
        original_keys[normalized_key] = clean_key

        if validated_value is None:
            invalid_values[clean_key] = clean_value
        else:
            values[normalized_key] = validated_value

    duplicate_normalized_keys = {
        normalized_key: originals
        for normalized_key, originals in normalized_to_originals.items()
        if len(set(originals)) > 1
    }

    return MappingData(
        values=values,
        original_keys_by_normalized_key=original_keys,
        invalid_values=invalid_values,
        duplicate_normalized_keys=duplicate_normalized_keys,
    )


def get_required_mapped_value(mapping: dict[str, str], value: object, *, mapping_name: str) -> str:
    """Recupera un valore dal mapping. Se manca, blocca la trasformazione."""
    normalized_key = normalize_lookup_key(value)
    if normalized_key not in mapping:
        raise MappingValidationError(
            f"Valore {clean_text(value)!r} non presente nel mapping {mapping_name}. "
            "Correggere il file di arricchimento prima di rieseguire la trasformazione."
        )
    return mapping[normalized_key]


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    """Rimuove duplicati preservando l'ordine originale."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def sorted_distinct_values(rows: list[dict[str, str]], columns: Iterable[str], *, list_fields: bool) -> list[str]:
    """Estrae valori distinti dal CSV per confrontarli con i mapping AI."""
    values: set[str] = set()

    for row in rows:
        for column in columns:
            if list_fields:
                values.update(split_list_field(row.get(column)))
            else:
                value = clean_text(row.get(column, ""))
                if not is_csv_missing(value):
                    values.add(value)

    return sorted(values, key=lambda value: value.lower())


def format_preview(values: list[str], *, limit: int = 20) -> str:
    """Formatta un'anteprima leggibile di una lista di valori."""
    if not values:
        return "-"
    preview = values[:limit]
    suffix = "" if len(values) <= limit else f" ... (+{len(values) - limit})"
    return ", ".join(preview) + suffix


def print_value_count(label: str, mapping: dict[str, str], target_value: str) -> None:
    """Stampa quante volte un valore specifico compare in un mapping."""
    counter = Counter(mapping.values())
    print(f"  {label}: {counter.get(target_value, 0)}")


def validate_mapping(
    *,
    label: str,
    expected_values: list[str],
    mapping: MappingData,
) -> None:
    """
    Confronta i valori distinti del dataset con le chiavi del mapping.

    La validazione richiede corrispondenza esatta tra dataset e mapping:
    - nessun valore del dataset deve mancare nel mapping;
    - nessuna chiave del mapping deve essere estranea al dataset;
    - nessun valore del mapping deve essere nullo, vuoto o invalido.
    """
    expected_keys_by_normalized = {normalize_lookup_key(value): value for value in expected_values}
    expected_keys = set(expected_keys_by_normalized)
    mapping_keys = set(mapping.original_keys_by_normalized_key)

    missing_keys = sorted(expected_keys - mapping_keys)
    extra_keys = sorted(mapping_keys - expected_keys)

    missing_values = [expected_keys_by_normalized[key] for key in missing_keys]
    extra_values = [mapping.original_keys_by_normalized_key[key] for key in extra_keys]

    print(f"{label} mapping check:")
    print(f"  Expected values from dataset: {len(expected_keys)}")
    print(f"  Mapping keys: {len(mapping_keys)}")
    print(f"  Missing mapping keys: {len(missing_values)}")
    print(f"  Extra mapping keys: {len(extra_values)}")
    print(f"  Invalid mapped values: {len(mapping.invalid_values)}")
    print(f"  Duplicate normalized keys: {len(mapping.duplicate_normalized_keys)}")

    if missing_values:
        print(f"  Missing preview: {format_preview(missing_values)}")
    if extra_values:
        print(f"  Extra preview: {format_preview(extra_values)}")
    if mapping.invalid_values:
        invalid_preview = [f"{key}: {value}" for key, value in mapping.invalid_values.items()]
        print(f"  Invalid preview: {format_preview(invalid_preview)}")
    if mapping.duplicate_normalized_keys:
        duplicate_preview = [
            f"{normalized}: {originals}"
            for normalized, originals in mapping.duplicate_normalized_keys.items()
        ]
        print(f"  Duplicate preview: {format_preview(duplicate_preview)}")

    has_errors = bool(missing_values or extra_values or mapping.invalid_values or mapping.duplicate_normalized_keys)
    if has_errors:
        raise MappingValidationError(
            f"Mapping {label} non coerente con il dataset: correggere chiavi mancanti, "
            "chiavi inventate/extra, duplicati normalizzati o valori non validi prima di rieseguire la trasformazione."
        )


def write_json(path: Path, documents: Iterable[dict[str, Any]]) -> None:
    """Scrive una lista di documenti JSON con indentazione leggibile."""
    with path.open("w", encoding="utf-8") as file:
        json.dump(list(documents), file, ensure_ascii=False, indent=2)
        file.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trasforma fra_cleaned.csv in collection JSON per MongoDB.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Percorso del CSV sorgente.")
    parser.add_argument("--enrichment-dir", type=Path, default=DEFAULT_ENRICHMENT_DIR, help="Cartella dei mapping di arricchimento.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Cartella di output dei JSON trasformati.")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"CSV non trovato: {args.input}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows, encoding = read_csv_rows(args.input)

    expected_notes = sorted_distinct_values(rows, NOTE_COLUMNS, list_fields=True)
    expected_accords = sorted_distinct_values(rows, ACCORD_COLUMNS, list_fields=False)
    expected_perfumers = sorted_distinct_values(rows, PERFUMER_COLUMNS, list_fields=False)

    note_groups = load_mapping(
        args.enrichment_dir / "note_olfactory_groups.json",
        value_validator=validate_note_group,
    )
    accord_colors = load_mapping(
        args.enrichment_dir / "accord_colors.json",
        value_validator=validate_color_hex,
    )
    perfumer_nationalities = load_mapping(
        args.enrichment_dir / "perfumer_nationalities.json",
        value_validator=validate_nationality,
    )

    validate_mapping(label="Notes", expected_values=expected_notes, mapping=note_groups)
    print_value_count("Notes classified as other", note_groups.values, OTHER_OLFACTORY_GROUP)

    validate_mapping(label="Accords", expected_values=expected_accords, mapping=accord_colors)
    print_value_count("Accords using default color #9E9E9E", accord_colors.values, DEFAULT_ACCORD_COLOR)

    validate_mapping(label="Perfumers", expected_values=expected_perfumers, mapping=perfumer_nationalities)
    print_value_count("Perfumers with Unknown nationality", perfumer_nationalities.values, UNKNOWN_NATIONALITY)

    brands: dict[str, dict[str, Any]] = {}
    notes: dict[str, dict[str, Any]] = {}
    accords: dict[str, dict[str, Any]] = {}
    perfumers: dict[str, dict[str, Any]] = {}
    perfumes: list[dict[str, Any]] = []

    for row in rows:
        perfume_name = clean_text(row.get("Perfume", ""))
        brand_name = clean_text(row.get("Brand", ""))
        country = clean_text(row.get("Country", "")) if not is_csv_missing(row.get("Country")) else None
        source_url = clean_text(row.get("url", ""))

        if is_csv_missing(perfume_name) or is_csv_missing(brand_name):
            continue

        brand_id = make_id("brand", brand_name)
        brands.setdefault(
            brand_id,
            {
                "_id": brand_id,
                "name": brand_name,
                "country": country,
            },
        )

        top_note_ids: list[str] = []
        middle_note_ids: list[str] = []
        base_note_ids: list[str] = []

        note_ids_by_column = {
            "Top": top_note_ids,
            "Middle": middle_note_ids,
            "Base": base_note_ids,
        }

        for column, target_list in note_ids_by_column.items():
            for note_name in split_list_field(row.get(column)):
                note_id = make_id("note", note_name)
                target_list.append(note_id)
                notes.setdefault(
                    note_id,
                    {
                        "_id": note_id,
                        "name": note_name,
                        "olfactory_group": get_required_mapped_value(
                            note_groups.values,
                            note_name,
                            mapping_name="note_olfactory_groups.json",
                        ),
                    },
                )

        accord_ids: list[str] = []
        for column in ACCORD_COLUMNS:
            accord_name = clean_text(row.get(column, ""))
            if is_csv_missing(accord_name):
                continue
            accord_id = make_id("accord", accord_name)
            accord_ids.append(accord_id)
            accords.setdefault(
                accord_id,
                {
                    "_id": accord_id,
                    "name": accord_name,
                    "color_hex": get_required_mapped_value(
                        accord_colors.values,
                        accord_name,
                        mapping_name="accord_colors.json",
                    ),
                },
            )

        perfumer_ids: list[str] = []
        for column in PERFUMER_COLUMNS:
            perfumer_name = clean_text(row.get(column, ""))
            if is_csv_missing(perfumer_name):
                continue
            perfumer_id = make_id("perfumer", perfumer_name)
            perfumer_ids.append(perfumer_id)
            perfumers.setdefault(
                perfumer_id,
                {
                    "_id": perfumer_id,
                    "name": perfumer_name,
                    "nationality": get_required_mapped_value(
                        perfumer_nationalities.values,
                        perfumer_name,
                        mapping_name="perfumer_nationalities.json",
                    ),
                },
            )

        all_note_ids = unique_preserve_order(top_note_ids + middle_note_ids + base_note_ids)

        perfume = {
            "_id": make_perfume_id(source_url, perfume_name, brand_name),
            "source_url": source_url,
            "name": perfume_name,
            "brand_id": brand_id,
            "gender": clean_text(row.get("Gender", "")).lower(),
            "rating": parse_float(row.get("Rating Value")),
            "votes": parse_int(row.get("Rating Count")),
            "year": parse_int(row.get("Year")),
            "top_note_ids": unique_preserve_order(top_note_ids),
            "middle_note_ids": unique_preserve_order(middle_note_ids),
            "base_note_ids": unique_preserve_order(base_note_ids),
            "all_note_ids": all_note_ids,
            "accord_ids": unique_preserve_order(accord_ids),
            "perfumer_ids": unique_preserve_order(perfumer_ids),
        }
        perfumes.append(perfume)

    write_json(args.output_dir / "brands.json", sorted(brands.values(), key=lambda item: item["name"].lower()))
    write_json(args.output_dir / "notes.json", sorted(notes.values(), key=lambda item: item["name"].lower()))
    write_json(args.output_dir / "accords.json", sorted(accords.values(), key=lambda item: item["name"].lower()))
    write_json(args.output_dir / "perfumers.json", sorted(perfumers.values(), key=lambda item: item["name"].lower()))
    write_json(args.output_dir / "perfumes.json", perfumes)

    notes_other_count = sum(1 for item in notes.values() if item["olfactory_group"] == OTHER_OLFACTORY_GROUP)
    accords_default_color_count = sum(1 for item in accords.values() if item["color_hex"] == DEFAULT_ACCORD_COLOR)
    perfumers_unknown_count = sum(1 for item in perfumers.values() if item["nationality"] == UNKNOWN_NATIONALITY)

    print("Dataset transformation completed")
    print(f"Input file: {args.input}")
    print(f"Encoding used: {encoding}")
    print(f"Rows read: {len(rows)}")
    print(f"Perfumes generated: {len(perfumes)}")
    print(f"Brands generated: {len(brands)}")
    print(f"Notes generated: {len(notes)}")
    print(f"Accords generated: {len(accords)}")
    print(f"Perfumers generated: {len(perfumers)}")
    print(f"Notes classified as other: {notes_other_count}")
    print(f"Accords using default color #9E9E9E: {accords_default_color_count}")
    print(f"Perfumers with Unknown nationality: {perfumers_unknown_count}")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()