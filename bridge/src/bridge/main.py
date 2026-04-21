from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress
from typing import Any

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from bridge import __version__
from bridge.config import settings
from bridge.fhir_client import FHIRClient
from bridge.mllp import MLLPServer
from bridge.router import MessageRouter
from bridge.store import MessageStore

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


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
    store = MessageStore()
    router = MessageRouter(fhir_client, store=store)
    mllp = MLLPServer(host="0.0.0.0", port=settings.mllp_port, handler=router.handle)
    await mllp.start()
    serve_task = asyncio.create_task(mllp.serve_forever())

    app.state.fhir_client = fhir_client
    app.state.router = router
    app.state.store = store
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


def create_app(lifespan_fn: Lifespan = lifespan) -> FastAPI:
    """Build the FastAPI app.

    `lifespan_fn` is overridable so tests can skip the real MLLP/FHIR wiring
    and inject mocks directly onto `app.state` before making requests.
    """
    app = FastAPI(title="HL7 v2 → FHIR Bridge", version=__version__, lifespan=lifespan_fn)

    # The viewer is served from a different origin during local dev (Vite on
    # 5173) and from Cloudflare Pages in production. Keep this permissive —
    # the bridge is not an auth boundary in this project.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    @app.get("/v2/messages")
    def list_messages(limit: int = 100) -> list[dict[str, Any]]:
        store: MessageStore = app.state.store
        return store.list_summaries(limit=limit)

    @app.get("/v2/messages/{message_id}")
    def get_message(message_id: str) -> dict[str, Any]:
        store: MessageStore = app.state.store
        record = store.get(message_id)
        if record is None:
            raise HTTPException(status_code=404, detail="message not found")
        return record.to_detail()

    @app.websocket("/ws/messages")
    async def messages_ws(websocket: WebSocket) -> None:
        store: MessageStore = app.state.store
        await websocket.accept()
        try:
            await websocket.send_text(
                json.dumps({"event": "hello", "data": {"version": __version__}})
            )
            async for event in store.subscribe():
                await websocket.send_text(json.dumps(event))
        except WebSocketDisconnect:
            return

    @app.api_route("/fhir/{full_path:path}", methods=["GET"])
    async def fhir_proxy(full_path: str, request: Request) -> Response:
        """Proxy read requests to the upstream FHIR server.

        The viewer queries FHIR directly via this proxy so it doesn't need
        CORS configured on HAPI / Medplum and so every read goes through a
        single auditable choke point.
        """
        fhir_client: FHIRClient = app.state.fhir_client
        upstream = f"{fhir_client.base_url}/{full_path}"
        query = dict(request.query_params)
        try:
            response = await fhir_client._client.get(upstream, params=query)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"upstream error: {exc}") from exc
        if response.headers.get("content-type", "").startswith("application/fhir+json"):
            return JSONResponse(
                status_code=response.status_code,
                content=response.json(),
            )
        return Response(
            status_code=response.status_code,
            content=response.content,
            media_type=response.headers.get("content-type", "application/json"),
        )

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
