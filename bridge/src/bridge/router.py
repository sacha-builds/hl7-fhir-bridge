"""Dispatch inbound v2 messages to the correct mapper, persist, ACK."""

from __future__ import annotations

from typing import Any

import structlog

from bridge.ack import build_ack
from bridge.fhir_client import FHIRClient
from bridge.mappers import map_adt_a01
from bridge.parsers import get_message_type

log = structlog.get_logger()


class MessageRouter:
    def __init__(self, fhir_client: FHIRClient) -> None:
        self._fhir = fhir_client

    async def handle(self, raw_v2: str) -> str:
        try:
            code, event = get_message_type(raw_v2)
        except ValueError as exc:
            log.warning("v2.malformed_msh", error=str(exc))
            return build_ack(raw_v2, code="AR", text="malformed MSH")

        log.info("v2.received", message_type=f"{code}^{event}")

        if code == "ADT" and event == "A01":
            return await self._handle_adt_a01(raw_v2)

        return build_ack(raw_v2, code="AR", text=f"unsupported message type {code}^{event}")

    async def _handle_adt_a01(self, raw_v2: str) -> str:
        try:
            mapped = map_adt_a01(raw_v2)
        except Exception as exc:
            log.exception("adt_a01.map_failed")
            return build_ack(raw_v2, code="AE", text=f"mapping failed: {exc}")

        try:
            patient_identifier_query = _identifier_query(mapped.patient.identifier)
            await self._fhir.conditional_create(
                mapped.patient, identifier_query=patient_identifier_query
            )
            encounter_identifier_query = _identifier_query(mapped.encounter.identifier)
            await self._fhir.conditional_create(
                mapped.encounter, identifier_query=encounter_identifier_query
            )
        except Exception as exc:
            log.exception("fhir.write_failed")
            return build_ack(raw_v2, code="AE", text=f"FHIR write failed: {exc}")

        return build_ack(raw_v2, code="AA")


def _identifier_query(identifiers: list[Any] | None) -> str | None:
    if not identifiers:
        return None
    first = identifiers[0]
    if first.system and first.value:
        return f"{first.system}|{first.value}"
    if first.value:
        return str(first.value)
    return None
