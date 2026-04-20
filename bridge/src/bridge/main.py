from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import structlog
import uvicorn
from fastapi import FastAPI

from bridge import __version__
from bridge.config import settings
from bridge.fhir_client import FHIRClient
from bridge.mllp import MLLPServer
from bridge.router import MessageRouter


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    fhir_client = FHIRClient(settings.fhir_base_url)
    router = MessageRouter(fhir_client)
    mllp = MLLPServer(host="0.0.0.0", port=settings.mllp_port, handler=router.handle)
    await mllp.start()
    serve_task = asyncio.create_task(mllp.serve_forever())

    app.state.fhir_client = fhir_client
    app.state.router = router
    app.state.mllp = mllp

    log.info(
        "bridge.started",
        version=__version__,
        http_port=settings.http_port,
        mllp_port=settings.mllp_port,
        fhir_base_url=settings.fhir_base_url,
    )
    try:
        yield
    finally:
        await mllp.stop()
        serve_task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await serve_task
        await fhir_client.aclose()
        log.info("bridge.stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="HL7 v2 → FHIR Bridge", version=__version__, lifespan=lifespan)

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

    @app.post("/v2/replay")
    async def replay(payload: dict[str, str]) -> dict[str, str]:
        """Dev-only convenience endpoint: process a v2 message without MLLP."""
        message = payload.get("message", "")
        router: MessageRouter = app.state.router
        ack = await router.handle(message)
        return {"ack": ack}

    return app


app = create_app()


def main() -> None:
    configure_logging()
    uvicorn.run(
        "bridge.main:app",
        host="0.0.0.0",
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
