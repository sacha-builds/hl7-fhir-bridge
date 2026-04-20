"""End-to-end: TCP client → MLLP server → router → mock FHIR → ACK."""

from __future__ import annotations

import asyncio
import contextlib
import json

import httpx
import pytest

from bridge.fhir_client import FHIRClient
from bridge.mllp.protocol import extract_frame, wrap_frame
from bridge.mllp.server import MLLPServer
from bridge.router import MessageRouter


@pytest.mark.asyncio
async def test_adt_a01_end_to_end_produces_ack_and_two_fhir_writes(
    adt_a01_raw: str,
) -> None:
    fhir_calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        fhir_calls.append(
            {
                "url": str(request.url),
                "if_none_exist": request.headers.get("If-None-Exist"),
                "body": json.loads(request.content.decode()),
            }
        )
        resource_type = str(request.url).rsplit("/", 1)[-1]
        return httpx.Response(
            201,
            headers={"Location": f"{resource_type}/1/_history/1"},
            json={"resourceType": resource_type, "id": "1"},
        )

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    fhir_client = FHIRClient("http://fhir.test/fhir", client=http)
    router = MessageRouter(fhir_client)

    server = MLLPServer(host="127.0.0.1", port=0, handler=router.handle)
    await server.start()
    assert server._server is not None
    port = server._server.sockets[0].getsockname()[1]
    serve_task = asyncio.create_task(server.serve_forever())

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(wrap_frame(adt_a01_raw.encode()))
        await writer.drain()

        buf = b""
        while True:
            chunk = await asyncio.wait_for(reader.read(1024), timeout=5)
            if not chunk:
                break
            buf += chunk
            payload, _ = extract_frame(buf)
            if payload is not None:
                ack_text = payload.decode()
                break

        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()
        serve_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await serve_task
        await http.aclose()

    assert "MSA|AA|MSG00001" in ack_text
    assert len(fhir_calls) == 2
    resource_types = [call["url"].rsplit("/", 1)[-1] for call in fhir_calls]
    assert resource_types == ["Patient", "Encounter"]
    assert fhir_calls[0]["if_none_exist"] == "identifier=urn:id:HOSP|MRN12345"
    assert fhir_calls[1]["if_none_exist"] == "identifier=V00042"
