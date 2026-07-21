#!/usr/bin/env python3
"""Confronta query MongoDB di ScentBase con e senza gli indici gestiti.

Output predefiniti:
- benchmarks/results/benchmark-results.json
- docs/indexes-and-benchmarks.md

Esempio:
    python benchmarks/run_benchmarks.py --warmup 3 --runs 20
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from backend.app.indexes import (  # noqa: E402
    MONGODB_ID_INDEX_NAME,
    create_managed_indexes,
    drop_managed_indexes,
    get_managed_index_definitions,
    get_managed_index_names,
    list_collection_indexes,
)
from backend.app.services.aggregations import (  # noqa: E402
    build_top_perfumes_pipeline,
)
from backend.app.services.similarity import (  # noqa: E402
    build_similar_perfumes_pipeline,
)


DEFAULT_OUTPUT = Path("benchmarks/results/benchmark-results.json")
DEFAULT_REPORT = Path("docs/indexes-and-benchmarks.md")
DEFAULT_LIMIT = 20
DEFAULT_MIN_VOTES = 100

Document = dict[str, Any]
Operation = Callable[[], list[Document]]
ExplainOperation = Callable[[], dict[str, Any]]


@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    description: str
    parameters: dict[str, Any]
    run: Operation
    explain: ExplainOperation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark MongoDB di ScentBase con e senza indici."
    )
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--mongo-uri", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--min-perfumes", type=int, default=1000)
    parser.add_argument("--allow-small-dataset", action="store_true")
    parser.add_argument("--allow-test-database", action="store_true")
    parser.add_argument("--allow-unmanaged-indexes", action="store_true")
    return parser.parse_args()


def repository_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def validate_args(args: argparse.Namespace) -> None:
    if args.warmup < 0:
        raise ValueError("--warmup non può essere negativo.")
    if args.runs <= 0:
        raise ValueError("--runs deve essere maggiore di 0.")
    if args.min_perfumes < 0:
        raise ValueError("--min-perfumes non può essere negativo.")


def first_nested(value: Any, key: str) -> Any | None:
    """Trova ricorsivamente il primo valore associato a ``key``."""
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for nested in value.values():
            found = first_nested(nested, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = first_nested(nested, key)
            if found is not None:
                return found
    return None


def collect_nested(value: Any, key: str) -> list[Any]:
    """Raccoglie ricorsivamente tutti i valori associati a ``key``."""
    found: list[Any] = []
    if isinstance(value, dict):
        for current_key, nested in value.items():
            if current_key == key:
                found.append(nested)
            found.extend(collect_nested(nested, key))
    elif isinstance(value, list):
        for nested in value:
            found.extend(collect_nested(nested, key))
    return found


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def result_signature(documents: list[Document]) -> list[str]:
    signature: list[str] = []
    for position, document in enumerate(documents):
        if "_id" not in document:
            raise RuntimeError(
                f"Il risultato in posizione {position} non contiene _id."
            )
        signature.append(str(document["_id"]))
    return signature


def explain_summary(
    explain: dict[str, Any],
    result_count: int,
) -> dict[str, Any]:
    execution = first_nested(explain, "executionStats")
    plan = first_nested(explain, "winningPlan")

    if not isinstance(execution, dict):
        execution = {}
    if plan is None:
        plan = {}

    return {
        "execution_time_millis": execution.get("executionTimeMillis"),
        "total_docs_examined": execution.get("totalDocsExamined"),
        "total_keys_examined": execution.get("totalKeysExamined"),
        "n_returned": execution.get("nReturned", result_count),
        "winning_plan_stages": unique(
            [str(value) for value in collect_nested(plan, "stage")]
        ),
        "used_indexes": unique(
            [str(value) for value in collect_nested(plan, "indexName")]
        ),
    }


def measure(
    scenario: Scenario,
    *,
    warmup: int,
    runs: int,
) -> dict[str, Any]:
    for _ in range(warmup):
        scenario.run()

    durations: list[float] = []
    expected_signature: list[str] | None = None
    result_count = 0

    for _ in range(runs):
        started = perf_counter()
        documents = scenario.run()
        durations.append((perf_counter() - started) * 1000)

        current_signature = result_signature(documents)
        if expected_signature is None:
            expected_signature = current_signature
        elif current_signature != expected_signature:
            raise RuntimeError(
                f"Lo scenario '{scenario.name}' non è deterministico."
            )
        result_count = len(documents)

    return {
        "result_count": result_count,
        "result_signature": expected_signature or [],
        "timings_ms": {
            "mean": round(statistics.mean(durations), 6),
            "median": round(statistics.median(durations), 6),
            "minimum": round(min(durations), 6),
            "maximum": round(max(durations), 6),
            "standard_deviation": round(statistics.pstdev(durations), 6),
        },
        "execution_stats": explain_summary(
            scenario.explain(),
            result_count,
        ),
    }


def find_scenario(
    database: Database,
    *,
    name: str,
    title: str,
    description: str,
    query: dict[str, Any],
    sort: list[tuple[str, int]],
    limit: int,
    parameters: dict[str, Any],
) -> Scenario:
    collection = database["perfumes"]

    def run() -> list[Document]:
        cursor = collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def explain() -> dict[str, Any]:
        command: dict[str, Any] = {
            "find": collection.name,
            "filter": query,
        }
        if sort:
            command["sort"] = dict(sort)
        if limit:
            command["limit"] = limit
        return database.command(
            "explain",
            command,
            verbosity="executionStats",
        )

    return Scenario(
        name=name,
        title=title,
        description=description,
        parameters=parameters,
        run=run,
        explain=explain,
    )


def aggregation_scenario(
    database: Database,
    *,
    name: str,
    title: str,
    description: str,
    pipeline: list[dict[str, Any]],
    parameters: dict[str, Any],
) -> Scenario:
    collection = database["perfumes"]

    def run() -> list[Document]:
        return list(collection.aggregate(pipeline, allowDiskUse=True))

    def explain() -> dict[str, Any]:
        command = {
            "aggregate": collection.name,
            "pipeline": pipeline,
            "cursor": {},
            "allowDiskUse": True,
        }
        return database.command(
            "explain",
            command,
            verbosity="executionStats",
        )

    return Scenario(
        name=name,
        title=title,
        description=description,
        parameters=parameters,
        run=run,
        explain=explain,
    )


def most_frequent_array_value(
    collection: Collection[Document],
    field: str,
) -> str:
    result = list(
        collection.aggregate(
            [
                {"$project": {field: {"$ifNull": [f"${field}", []]}}},
                {"$unwind": f"${field}"},
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1, "_id": 1}},
                {"$limit": 1},
            ]
        )
    )
    if not result:
        raise RuntimeError(f"Nessun valore disponibile per '{field}'.")
    return str(result[0]["_id"])


def most_frequent_scalar_value(
    collection: Collection[Document],
    field: str,
) -> str:
    result = list(
        collection.aggregate(
            [
                {"$match": {field: {"$ne": None}}},
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1, "_id": 1}},
                {"$limit": 1},
            ]
        )
    )
    if not result:
        raise RuntimeError(f"Nessun valore disponibile per '{field}'.")
    return str(result[0]["_id"])


def similarity_source(collection: Collection[Document]) -> Document:
    result = list(
        collection.aggregate(
            [
                {
                    "$project": {
                        "_id": 1,
                        "rating": 1,
                        "votes": 1,
                        "all_note_ids": {
                            "$ifNull": ["$all_note_ids", []]
                        },
                        "accord_ids": {"$ifNull": ["$accord_ids", []]},
                    }
                },
                {
                    "$set": {
                        "_feature_count": {
                            "$add": [
                                {"$size": "$all_note_ids"},
                                {"$size": "$accord_ids"},
                            ]
                        }
                    }
                },
                {"$match": {"_feature_count": {"$gt": 0}}},
                {
                    "$sort": {
                        "_feature_count": -1,
                        "votes": -1,
                        "rating": -1,
                        "_id": 1,
                    }
                },
                {"$limit": 1},
            ]
        )
    )
    if not result:
        raise RuntimeError("Nessun profumo con note o accordi.")
    return result[0]


def string_source_url(collection: Collection[Document]) -> str:
    document = collection.find_one(
        {"source_url": {"$type": "string"}},
        {"_id": 0, "source_url": 1},
        sort=[("_id", ASCENDING)],
    )
    if document is None:
        raise RuntimeError("Nessun source_url stringa disponibile.")
    return str(document["source_url"])


def ensure_unique_source_urls(collection: Collection[Document]) -> None:
    duplicates = list(
        collection.aggregate(
            [
                {"$match": {"source_url": {"$type": "string"}}},
                {
                    "$group": {
                        "_id": "$source_url",
                        "count": {"$sum": 1},
                    }
                },
                {"$match": {"count": {"$gt": 1}}},
                {"$limit": 1},
            ]
        )
    )
    if duplicates:
        duplicate = duplicates[0]
        raise RuntimeError(
            "source_url duplicato: "
            f"{duplicate['_id']!r} ({duplicate['count']} documenti)."
        )


def build_scenarios(database: Database) -> list[Scenario]:
    perfumes = database["perfumes"]
    note_id = most_frequent_array_value(perfumes, "all_note_ids")
    accord_id = most_frequent_array_value(perfumes, "accord_ids")
    brand_id = most_frequent_scalar_value(perfumes, "brand_id")
    gender = most_frequent_scalar_value(perfumes, "gender")
    source_url = string_source_url(perfumes)
    source = similarity_source(perfumes)

    source_id = str(source["_id"])
    source_notes = [str(value) for value in source["all_note_ids"]]
    source_accords = [str(value) for value in source["accord_ids"]]

    combined_query = {
        "gender": gender,
        "rating": {"$gte": 4.0},
        "votes": {"$gte": DEFAULT_MIN_VOTES},
    }
    if perfumes.count_documents(combined_query) == 0:
        combined_query = {
            "gender": gender,
            "rating": {"$gte": 0.0},
            "votes": {"$gte": 0},
        }

    return [
        find_scenario(
            database,
            name="filter_by_note",
            title="Ricerca per nota olfattiva",
            description="Filtro sulla nota più frequente del dataset.",
            query={"all_note_ids": {"$in": [note_id]}},
            sort=[("_id", ASCENDING)],
            limit=DEFAULT_LIMIT,
            parameters={"note_id": note_id, "limit": DEFAULT_LIMIT},
        ),
        find_scenario(
            database,
            name="filter_by_accord",
            title="Ricerca per accordo principale",
            description="Filtro sull'accordo più frequente del dataset.",
            query={"accord_ids": {"$in": [accord_id]}},
            sort=[("_id", ASCENDING)],
            limit=DEFAULT_LIMIT,
            parameters={
                "accord_id": accord_id,
                "limit": DEFAULT_LIMIT,
            },
        ),
        find_scenario(
            database,
            name="brand_sorted_by_rating",
            title="Brand ordinato per rating",
            description="Filtro sul brand più frequente con sort per rating.",
            query={"brand_id": {"$in": [brand_id]}},
            sort=[("rating", DESCENDING), ("_id", ASCENDING)],
            limit=DEFAULT_LIMIT,
            parameters={"brand_id": brand_id, "limit": DEFAULT_LIMIT},
        ),
        find_scenario(
            database,
            name="combined_filters",
            title="Filtri combinati",
            description="Genere, rating minimo e numero minimo di voti.",
            query=combined_query,
            sort=[
                ("rating", DESCENDING),
                ("votes", DESCENDING),
                ("_id", ASCENDING),
            ],
            limit=DEFAULT_LIMIT,
            parameters={"filter": combined_query, "limit": DEFAULT_LIMIT},
        ),
        aggregation_scenario(
            database,
            name="top_perfumes",
            title="Profumi meglio valutati",
            description="Pipeline reale della classifica per rating e voti.",
            pipeline=build_top_perfumes_pipeline(
                limit=DEFAULT_LIMIT,
                min_votes=DEFAULT_MIN_VOTES,
            ),
            parameters={
                "min_votes": DEFAULT_MIN_VOTES,
                "limit": DEFAULT_LIMIT,
            },
        ),
        aggregation_scenario(
            database,
            name="similar_perfumes",
            title="Profumi simili",
            description="Pipeline reale di similarità per note e accordi.",
            pipeline=build_similar_perfumes_pipeline(
                source_perfume_id=source_id,
                source_note_ids=source_notes,
                source_accord_ids=source_accords,
                limit=DEFAULT_LIMIT,
            ),
            parameters={
                "source_perfume_id": source_id,
                "source_note_count": len(source_notes),
                "source_accord_count": len(source_accords),
                "limit": DEFAULT_LIMIT,
            },
        ),
        find_scenario(
            database,
            name="source_url_lookup",
            title="Ricerca esatta per source_url",
            description="Ricerca sul campo con indice univoco parziale.",
            query={"source_url": source_url},
            sort=[],
            limit=1,
            parameters={"source_url": source_url},
        ),
    ]


def run_configuration(
    scenarios: list[Scenario],
    *,
    warmup: int,
    runs: int,
    label: str,
) -> dict[str, dict[str, Any]]:
    print(f"\nConfigurazione: {label}")
    results: dict[str, dict[str, Any]] = {}

    for position, scenario in enumerate(scenarios, start=1):
        print(
            f"  [{position}/{len(scenarios)}] {scenario.title}...",
            end="",
            flush=True,
        )
        result = measure(scenario, warmup=warmup, runs=runs)
        results[scenario.name] = result
        print(
            f" media={result['timings_ms']['mean']:.3f} ms, "
            f"mediana={result['timings_ms']['median']:.3f} ms"
        )

    return results


def reduction(
    before: float | int | None,
    after: float | int | None,
) -> float | None:
    if before is None or after is None or float(before) == 0:
        return None
    return round(
        ((float(before) - float(after)) / float(before)) * 100,
        3,
    )


def compare(
    without_indexes: dict[str, Any],
    with_indexes: dict[str, Any],
) -> dict[str, Any]:
    return {
        "results_equivalent": (
            without_indexes["result_signature"]
            == with_indexes["result_signature"]
        ),
        "mean_time_reduction_percent": reduction(
            without_indexes["timings_ms"]["mean"],
            with_indexes["timings_ms"]["mean"],
        ),
        "median_time_reduction_percent": reduction(
            without_indexes["timings_ms"]["median"],
            with_indexes["timings_ms"]["median"],
        ),
        "docs_examined_reduction_percent": reduction(
            without_indexes["execution_stats"]["total_docs_examined"],
            with_indexes["execution_stats"]["total_docs_examined"],
        ),
    }


def format_value(value: Any) -> str:
    if value is None:
        return "N/D"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "Nessuno"
    return str(value).replace("|", r"\|")


def direction_name(direction: int) -> str:
    return "ASC" if direction == ASCENDING else "DESC"


def generate_report(payload: dict[str, Any]) -> str:
    env = payload["environment"]
    scenarios = payload["scenarios"]

    lines = [
        "# Indici MongoDB e benchmark",
        "",
        "## Obiettivo",
        "",
        (
            "Confrontare query rappresentative di ScentBase prima e dopo "
            "la creazione degli indici gestiti. Le misurazioni sono eseguite "
            "direttamente tramite PyMongo."
        ),
        "",
        "## Ambiente",
        "",
        f"- Data UTC: `{env['generated_at_utc']}`",
        f"- Database: `{env['database']}`",
        f"- MongoDB: `{env['mongodb_version']}`",
        f"- Python: `{env['python_version']}`",
        f"- Piattaforma: `{env['platform']}`",
        f"- Profumi: **{env['perfume_count']}**",
        f"- Warm-up: **{env['warmup_runs']}**",
        f"- Esecuzioni misurate: **{env['measured_runs']}**",
        "",
        "## Indici gestiti",
        "",
        "| Nome | Chiavi | Unique | Filtro parziale |",
        "|---|---|---:|---|",
    ]

    for index in payload["managed_indexes"]:
        keys = ", ".join(
            f"`{item['field']} {direction_name(item['direction'])}`"
            for item in index["keys"]
        )
        partial = index["partial_filter_expression"]
        partial_text = (
            f"`{json.dumps(partial, ensure_ascii=False)}`"
            if partial is not None
            else "—"
        )
        lines.append(
            f"| `{index['name']}` | {keys} | "
            f"{'Sì' if index['unique'] else 'No'} | {partial_text} |"
        )

    lines += [
        "",
        "## Metodologia",
        "",
        (
            "Per ogni scenario vengono eseguite iterazioni di warm-up e "
            "successivamente le misurazioni con `perf_counter`. Lo script "
            "verifica che gli identificativi restituiti siano identici nelle "
            "due configurazioni e raccoglie `executionStats` tramite `explain`."
        ),
        "",
        "## Risultati",
        "",
        (
            "| Scenario | Configurazione | Media ms | Mediana ms | "
            "Docs esaminati | Keys esaminate | nReturned | Piano | Indici |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]

    for scenario in scenarios:
        for key, label in (
            ("without_indexes", "Senza indici gestiti"),
            ("with_indexes", "Con indici gestiti"),
        ):
            result = scenario[key]
            timing = result["timings_ms"]
            execution = result["execution_stats"]
            lines.append(
                f"| {scenario['title']} | {label} | "
                f"{format_value(timing['mean'])} | "
                f"{format_value(timing['median'])} | "
                f"{format_value(execution['total_docs_examined'])} | "
                f"{format_value(execution['total_keys_examined'])} | "
                f"{format_value(execution['n_returned'])} | "
                f"{format_value(execution['winning_plan_stages'])} | "
                f"{format_value(execution['used_indexes'])} |"
            )

    lines += [
        "",
        "## Confronto",
        "",
        (
            "| Scenario | Risultati equivalenti | Riduzione media tempo | "
            "Riduzione mediana tempo | Riduzione docs esaminati |"
        ),
        "|---|---:|---:|---:|---:|",
    ]

    for scenario in scenarios:
        comparison = scenario["comparison"]
        lines.append(
            f"| {scenario['title']} | "
            f"{'Sì' if comparison['results_equivalent'] else 'No'} | "
            f"{format_value(comparison['mean_time_reduction_percent'])}% | "
            f"{format_value(comparison['median_time_reduction_percent'])}% | "
            f"{format_value(comparison['docs_examined_reduction_percent'])}% |"
        )

    lines += ["", "## Osservazioni automatiche", ""]

    for scenario in scenarios:
        comparison = scenario["comparison"]
        indexed_stats = scenario["with_indexes"]["execution_stats"]
        used = indexed_stats["used_indexes"]
        mean_change = comparison["mean_time_reduction_percent"]
        docs_change = comparison["docs_examined_reduction_percent"]

        observation = (
            "MongoDB ha usato " + ", ".join(f"`{name}`" for name in used)
            if used
            else "Il piano vincente non mostra un indice gestito"
        )
        if mean_change is not None:
            verb = "ridotto" if mean_change >= 0 else "aumentato"
            observation += (
                f"; il tempo medio è {verb} del "
                f"{abs(mean_change):.3f}%"
            )
        if docs_change is not None:
            verb = "ridotti" if docs_change >= 0 else "aumentati"
            observation += (
                f"; i documenti esaminati sono {verb} del "
                f"{abs(docs_change):.3f}%"
            )
        lines.append(f"- **{scenario['title']}**: {observation}.")

    lines += [
        "",
        "## Interpretazione manuale",
        "",
        (
            "Prima della consegna integrare questa sezione commentando gli "
            "scenari più significativi, gli indici non utilizzati e le "
            "eventuali differenze tra riduzione dei documenti esaminati e "
            "tempo misurato."
        ),
        "",
        "## Limiti",
        "",
        "- Il benchmark è locale e dipende da hardware, cache e carico.",
        (
            "- La configurazione senza indici rimuove soltanto gli indici "
            "gestiti; `_id_` rimane sempre presente."
        ),
        (
            "- Gli indici `_id_` delle collection collegate rimangono "
            "disponibili nei `$lookup`."
        ),
        (
            "- Su circa 24.000 documenti differenze temporali piccole possono "
            "essere sensibili al rumore; vanno osservati anche piano, "
            "documenti e chiavi esaminati."
        ),
        "",
        "## Riproduzione",
        "",
        "```bash",
        "docker compose up -d",
        "python scripts/verify_mongodb_import.py",
        "python -m pytest tests/test_indexes.py -v",
        (
            f"python benchmarks/run_benchmarks.py "
            f"--warmup {env['warmup_runs']} "
            f"--runs {env['measured_runs']}"
        ),
        "```",
        "",
        (
            "I dati grezzi sono salvati in "
            "`benchmarks/results/benchmark-results.json`."
        ),
        "",
    ]

    return "\n".join(lines)


def unmanaged_index_names(database: Database) -> list[str]:
    existing = {item["name"] for item in list_collection_indexes(database)}
    allowed = {MONGODB_ID_INDEX_NAME, *get_managed_index_names()}
    return sorted(existing - allowed)


def main() -> int:
    args = parse_args()
    client: MongoClient[Document] | None = None
    database: Database | None = None
    restore_indexes = False

    try:
        validate_args(args)

        mongo_uri = args.mongo_uri or os.getenv("MONGO_URI")
        database_name = args.database or os.getenv(
            "MONGO_DATABASE",
            "scentbase",
        )
        if not mongo_uri:
            raise RuntimeError("MONGO_URI non configurata.")
        if not database_name:
            raise RuntimeError("MONGO_DATABASE non configurata.")
        if database_name.endswith("_test") and not args.allow_test_database:
            raise RuntimeError(
                "Benchmark sul database _test bloccato. "
                "Usare --allow-test-database solo consapevolmente."
            )

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        database = client[database_name]
        perfumes = database["perfumes"]
        count = perfumes.count_documents({})

        if count < args.min_perfumes and not args.allow_small_dataset:
            raise RuntimeError(
                f"Dataset troppo piccolo: {count} profumi. "
                "Importare il dataset completo o usare "
                "--allow-small-dataset."
            )

        ensure_unique_source_urls(perfumes)

        unmanaged = unmanaged_index_names(database)
        if unmanaged and not args.allow_unmanaged_indexes:
            raise RuntimeError(
                "Indici non gestiti presenti: "
                + ", ".join(unmanaged)
                + ". Rimuoverli o usare --allow-unmanaged-indexes."
            )

        print("ScentBase MongoDB benchmark")
        print(f"Database: {database_name}")
        print(f"Profumi: {count}")
        print(f"Warm-up: {args.warmup}; run: {args.runs}")

        scenarios = build_scenarios(database)

        restore_indexes = True
        drop_managed_indexes(database)
        without = run_configuration(
            scenarios,
            warmup=args.warmup,
            runs=args.runs,
            label="senza indici gestiti",
        )

        create_managed_indexes(database)
        with_indexes = run_configuration(
            scenarios,
            warmup=args.warmup,
            runs=args.runs,
            label="con indici gestiti",
        )

        scenario_results: list[dict[str, Any]] = []
        for scenario in scenarios:
            comparison = compare(
                without[scenario.name],
                with_indexes[scenario.name],
            )
            if not comparison["results_equivalent"]:
                raise RuntimeError(
                    f"Risultati diversi nello scenario '{scenario.name}'."
                )
            scenario_results.append(
                {
                    "name": scenario.name,
                    "title": scenario.title,
                    "description": scenario.description,
                    "parameters": scenario.parameters,
                    "without_indexes": without[scenario.name],
                    "with_indexes": with_indexes[scenario.name],
                    "comparison": comparison,
                }
            )

        payload = {
            "environment": {
                "generated_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "database": database_name,
                "mongodb_version": client.server_info().get(
                    "version",
                    "unknown",
                ),
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "perfume_count": count,
                "warmup_runs": args.warmup,
                "measured_runs": args.runs,
                "unmanaged_indexes": unmanaged,
            },
            "managed_indexes": get_managed_index_definitions(),
            "final_collection_indexes": list_collection_indexes(database),
            "scenarios": scenario_results,
        }

        output = repository_path(args.output)
        report = repository_path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)

        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report.write_text(generate_report(payload), encoding="utf-8")

        print("\nBenchmark completato.")
        print(f"JSON: {output}")
        print(f"Report: {report}")
        print("Gli indici gestiti restano installati.")
        return 0

    except (PyMongoError, OSError, ValueError, RuntimeError) as exc:
        print(f"Benchmark fallito: {exc}", file=sys.stderr)
        return 1

    finally:
        if restore_indexes and database is not None:
            try:
                create_managed_indexes(database)
            except PyMongoError as exc:
                print(
                    f"Attenzione: ripristino indici fallito: {exc}",
                    file=sys.stderr,
                )
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
