"""Dispatch inbound v2 messages to the correct mapper, validate, persist, ACK."""

from __future__ import annotations

from collections.abc import Callable

import structlog

from bridge.ack import build_ack
from bridge.fhir_client import FHIRClient
from bridge.mappers import (
    MappedResource,
    map_adt_a01,
    map_adt_a03,
    map_adt_a08,
    map_oru_r01,
)
from bridge.parsers import get_message_type
from bridge.validators import has_errors, validate_resource

log = structlog.get_logger()

Mapper = Callable[[str], list[MappedResource]]

MAPPERS: dict[tuple[str, str], Mapper] = {
    ("ADT", "A01"): map_adt_a01,
    ("ADT", "A03"): map_adt_a03,
    ("ADT", "A08"): map_adt_a08,
    ("ORU", "R01"): map_oru_r01,
}


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
        mapper = MAPPERS.get((code, event))
        if mapper is None:
            return build_ack(raw_v2, code="AR", text=f"unsupported message type {code}^{event}")

        try:
            resources = mapper(raw_v2)
        except Exception as exc:
            log.exception("mapper.failed", message_type=f"{code}^{event}")
            return build_ack(raw_v2, code="AE", text=f"mapping failed: {exc}")

        # Validate before any write. Error-severity issues short-circuit the
        # whole message — we'd rather NACK than persist a non-conformant
        # record and contaminate the FHIR store.
        for mr in resources:
            issues = validate_resource(mr.resource)
            for issue in issues:
                logger = log.warning if issue.severity == "warning" else log.error
                logger(
                    "validation.issue",
                    resource_type=mr.resource.__class__.__name__,
                    severity=issue.severity,
                    path=issue.path,
                    message=issue.message,
                )
            if has_errors(issues):
                return build_ack(
                    raw_v2,
                    code="AE",
                    text=f"validation failed on {mr.resource.__class__.__name__}",
                )

        try:
            for mr in resources:
                if mr.operation == "update":
                    if not mr.identifier_query:
                        raise ValueError(
                            f"update on {mr.resource.__class__.__name__} requires identifier"
                        )
                    await self._fhir.conditional_update(
                        mr.resource, identifier_query=mr.identifier_query
                    )
                else:
                    await self._fhir.conditional_create(
                        mr.resource, identifier_query=mr.identifier_query
                    )
        except Exception as exc:
            log.exception("fhir.write_failed")
            return build_ack(raw_v2, code="AE", text=f"FHIR write failed: {exc}")

        return build_ack(raw_v2, code="AA")
