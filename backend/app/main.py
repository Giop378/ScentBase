from __future__ import annotations

from fastapi import FastAPI

from backend.app.routers import collections, health, perfumes

app = FastAPI(
    title="ScentBase API",
    description="Backend API for the ScentBase MongoDB proof of concept.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(collections.router)
app.include_router(perfumes.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "message": "ScentBase API",
        "docs": "/docs",
    }