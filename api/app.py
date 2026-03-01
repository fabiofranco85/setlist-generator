"""FastAPI application factory.

Run with: uvicorn api:create_app --factory --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from .middleware import register_error_handlers
from .routes import (
    songs,
    setlists,
    event_types,
    labels,
    sharing,
    admin,
    config,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Songbook API",
        description="Multi-tenant church worship setlist generator API",
        version="1.0.0",
    )

    # CORS middleware
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure per deployment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    register_error_handlers(app)

    # Register route modules
    app.include_router(songs.router, prefix="/songs", tags=["songs"])
    app.include_router(setlists.router, prefix="/setlists", tags=["setlists"])
    app.include_router(event_types.router, prefix="/event-types", tags=["event-types"])
    app.include_router(labels.router, prefix="/labels", tags=["labels"])
    app.include_router(sharing.router, prefix="/sharing", tags=["sharing"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(config.router, prefix="/config", tags=["config"])

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
