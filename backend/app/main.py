from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.duplicate_guard import PerfumeDuplicateGuardMiddleware
from backend.app.routers import (
    collections,
    health,
    perfumes,
    references,
    statistics,
)


app = FastAPI(
    title="ScentBase API",
    description="Backend API for the ScentBase MongoDB proof of concept.",
    version="0.1.0",
)

# Il controllo dei duplicati riguarda esclusivamente le scritture CRUD ricevute
# dall'API. Gli script ETL/import non attraversano questo middleware.
app.add_middleware(PerfumeDuplicateGuardMiddleware)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(collections.router)
app.include_router(perfumes.router)
app.include_router(references.router)
app.include_router(statistics.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "message": "ScentBase API",
        "docs": "/docs",
    }
