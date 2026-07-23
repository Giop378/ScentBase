"""Middleware per il controllo dei duplicati nelle scritture CRUD manuali."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.schemas.perfumes import PerfumeCreate, PerfumeUpdate
from backend.app.services.perfume_names import ensure_no_duplicate_perfume


class PerfumeDuplicateGuardMiddleware:
    """Controlla i duplicati solo su POST e PUT eseguiti tramite l'API.

    La pipeline ETL e gli script di caricamento del CSV non attraversano il
    middleware, quindi mantengono integralmente il comportamento già definito.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._is_perfume_write(scope):
            await self.app(scope, receive, send)
            return

        body = await self._read_body(receive)
        replay_receive = self._replay_body(body)

        try:
            payload = json.loads(body.decode("utf-8"))
            document = self._build_document(scope, payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, TypeError):
            # La validazione e la relativa risposta 422 restano responsabilità
            # dell'endpoint FastAPI già esistente.
            await self.app(scope, replay_receive, send)
            return

        excluded_perfume_id = self._updated_perfume_id(scope)

        try:
            await run_in_threadpool(
                ensure_no_duplicate_perfume,
                document,
                excluded_perfume_id=excluded_perfume_id,
            )
        except HTTPException as exc:
            response = JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
            await response(scope, replay_receive, send)
            return

        await self.app(scope, replay_receive, send)

    @staticmethod
    def _is_perfume_write(scope: Scope) -> bool:
        if scope.get("type") != "http":
            return False

        method = scope.get("method")
        path = str(scope.get("path") or "").rstrip("/")

        if method == "POST":
            return path == "/perfumes"

        if method == "PUT":
            parts = path.split("/")
            return len(parts) == 3 and parts[1] == "perfumes" and bool(parts[2])

        return False

    @staticmethod
    async def _read_body(receive: Receive) -> bytes:
        chunks: list[bytes] = []
        more_body = True

        while more_body:
            message = await receive()
            chunks.append(message.get("body", b""))
            more_body = bool(message.get("more_body", False))

        return b"".join(chunks)

    @staticmethod
    def _replay_body(body: bytes) -> Receive:
        sent = False

        async def receive() -> Message:
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        return receive

    @staticmethod
    def _build_document(scope: Scope, payload: Any) -> dict[str, Any]:
        schema = PerfumeCreate if scope.get("method") == "POST" else PerfumeUpdate
        model = schema.model_validate(payload)
        document = model.model_dump(mode="json")

        array_fields = (
            "top_note_ids",
            "middle_note_ids",
            "base_note_ids",
            "accord_ids",
            "perfumer_ids",
        )
        for field in array_fields:
            document[field] = list(dict.fromkeys(document[field]))

        document["all_note_ids"] = list(
            dict.fromkeys(
                document["top_note_ids"]
                + document["middle_note_ids"]
                + document["base_note_ids"]
            )
        )
        return document

    @staticmethod
    def _updated_perfume_id(scope: Scope) -> str | None:
        if scope.get("method") != "PUT":
            return None
        return str(scope.get("path") or "").rstrip("/").split("/")[-1]
