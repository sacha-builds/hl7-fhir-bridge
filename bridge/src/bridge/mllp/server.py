from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

import structlog

from bridge.mllp.protocol import extract_frame, wrap_frame

log = structlog.get_logger()

MessageHandler = Callable[[str], Awaitable[str]]


class MLLPServer:
    """Asyncio TCP server speaking MLLP.

    Accepts framed HL7 v2 messages, hands the raw message text to `handler`,
    and frames the returned ACK text back to the sender.
    """

    def __init__(self, host: str, port: int, handler: MessageHandler) -> None:
        self.host = host
        self.port = port
        self.handler = handler
        self._server: asyncio.base_events.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._on_client, self.host, self.port)
        sockets = self._server.sockets or ()
        bound = [sock.getsockname() for sock in sockets]
        log.info("mllp.listening", bound=bound)

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        log.info("mllp.stopped")

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def _on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        log.info("mllp.client_connected", peer=peer)
        buffer = b""
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while True:
                    payload, buffer = extract_frame(buffer)
                    if payload is None:
                        break
                    text = payload.decode("utf-8", errors="replace")
                    ack = await self.handler(text)
                    writer.write(wrap_frame(ack.encode("utf-8")))
                    await writer.drain()
        except Exception:
            log.exception("mllp.client_error", peer=peer)
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            log.info("mllp.client_disconnected", peer=peer)
