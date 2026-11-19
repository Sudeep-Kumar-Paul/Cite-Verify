from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.exceptions import add_exception_handlers
from app.database import init_db

settings = get_settings()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "app": {"level": "DEBUG" if settings.debug else "INFO", "propagate": True},
        "uvicorn": {"level": "INFO", "propagate": True},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(f"Starting {settings.app_name} backend service...")
    settings.ensure_directories()
    init_db()
    logger.info(f"{settings.app_name} backend ready. Running in {settings.app_env} mode.")
    yield
    logger.info(f"{settings.app_name} backend shutting down.")


app = FastAPI(
    title="CiteVerify API",
    description=(
        "AI-powered scientific claim and citation verification platform. "
        "Upload academic PDFs to verify claims against original research evidence."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
def _resolve_origins() -> list[str]:
    origins = []
    for source in [settings.allowed_origins, settings.cors_origins]:
        if isinstance(source, list):
            origins.extend(source)
        elif isinstance(source, str) and source:
            origins.extend([s.strip() for s in source.split(",") if s.strip()])
    return list(dict.fromkeys([o for o in origins if o]))

resolved_origins = _resolve_origins()
is_cors_wildcard = "*" in resolved_origins

if is_cors_wildcard:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_origins,
        allow_origin_regex=r"https://.*(\.vercel\.app|\.onrender\.com)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register custom exception handlers
add_exception_handlers(app)

# Register routers
from app.api.routes import (  # noqa: E402
    claims,
    citations,
    documents,
    history,
    reports,
    verification,
)

app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(claims.router, prefix="/api/documents", tags=["Claims"])
app.include_router(citations.router, prefix="/api/documents", tags=["Citations"])
app.include_router(verification.router, prefix="/api/verification", tags=["Verification"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(history.router, prefix="/api/history", tags=["History"])


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check() -> dict:
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=settings.debug)
