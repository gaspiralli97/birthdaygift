"""Application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import get_settings
from .db import create_all
from .i18n import load_all, strings
from .routes import api, pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # Validating every translation file here turns a typo in copy into a
    # startup failure instead of a 500 on somebody's birthday.
    languages = load_all()
    logger.info("languages loaded: %s", ", ".join(languages))

    # Single node, single file: creating anything missing at boot is simpler
    # than requiring a separate migrate step, and Alembic still owns changes
    # to an existing schema.
    create_all()
    logger.info("database ready at %s", settings.database_path)

    app.state.bot_username = None
    if settings.bot_enabled:
        from .bot import start_bot

        app.state.bot_username = await start_bot(app)
    else:
        logger.info("telegram disabled (no token or secret); card pages still served")

    yield

    if settings.bot_enabled:
        from .bot import stop_bot

        await stop_bot(app)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="birthdaygift",
        version=__version__,
        lifespan=lifespan,
        # Nothing here is a public API worth documenting, and the schema would
        # only advertise the creation endpoint to scrapers.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(pages.router)
    app.include_router(api.router)

    if settings.bot_enabled:
        from .routes import telegram

        app.include_router(telegram.router)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # The form speaks the visitor's language, so the error should too.
        body = exc.body if isinstance(exc.body, dict) else {}
        lang = body.get("lang", "uz")
        logger.info("validation rejected: %s", exc.errors()[:3])
        return JSONResponse(
            status_code=422,
            content={"error": "validation", "message": strings(lang).form.error_name},
        )

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("referrer-policy", "no-referrer")
        response.headers.setdefault("x-frame-options", "DENY")
        return response

    return app


app = create_app()
