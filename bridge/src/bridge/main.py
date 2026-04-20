from __future__ import annotations

import logging

import structlog
import uvicorn
from fastapi import FastAPI

from bridge import __version__
from bridge.config import settings


def configure_logging() -> None:
    logging.basicConfig(level=settings.log_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


log = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(title="HL7 v2 → FHIR Bridge", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "HL7 v2 → FHIR Bridge",
            "version": __version__,
            "fhir_base_url": settings.fhir_base_url,
        }

    return app


app = create_app()


def main() -> None:
    configure_logging()
    log.info(
        "bridge.starting",
        version=__version__,
        http_port=settings.http_port,
        mllp_port=settings.mllp_port,
        fhir_base_url=settings.fhir_base_url,
    )
    uvicorn.run(
        "bridge.main:app",
        host="0.0.0.0",
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
