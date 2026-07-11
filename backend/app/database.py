from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from backend.app.config import MONGO_DATABASE, MONGO_URI

client: MongoClient = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    return client[MONGO_DATABASE]


def check_connection() -> bool:
    try:
        client.admin.command("ping")
        return True
    except Exception:
        return False


def close_connection() -> None:
    client.close()