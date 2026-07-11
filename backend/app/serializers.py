from __future__ import annotations

from datetime import date, datetime
from typing import Any

from bson import ObjectId


def serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, list):
        return [serialize_value(item) for item in value]

    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}

    return value


def serialize_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None

    return {key: serialize_value(value) for key, value in document.items()}


def serialize_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_document(document) for document in documents if document is not None]