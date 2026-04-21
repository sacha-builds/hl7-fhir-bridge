"""Dispatch inbound v2 messages to the correct mapper, validate, persist, ACK.

Every processed message (success or failure) is also recorded in the in-
memory `MessageStore` so the viewer UI can show an inbox with live
updates.
"""

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
from bridge.metrics import Metrics
from bridge.parsers import get_message_type
from bridge.store import MessageRecord, MessageStore, ResourceRecord
from bridge.store.messages import new_message_id, now_iso
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
    def __init__(
        self,
        fhir_client: FHIRClient,
        store: MessageStore | None = None,
        metrics: Metrics | None = None,
    ) -> None:
        self._fhir = fhir_client
        self._store = store
        self._metrics = metrics

    async def handle(self, raw_v2: str) -> str:
        message_type = "UNKNOWN"
        resources: list[MappedResource] = []
        validation_issue_records: list[dict[str, str]] = []
        error_text: str | None = None
        ack_code = "AR"
        ack = ""

        try:
            try:
                code, event = get_message_type(raw_v2)
                message_type = f"{code}^{event}"
            except ValueError as exc:
                log.warning("v2.malformed_msh", error=str(exc))
                error_text = "malformed MSH"
                ack = build_ack(raw_v2, code="AR", text=error_text)
                ack_code = "AR"
                return ack

            log.info("v2.received", message_type=message_type)
            mapper = MAPPERS.get((code, event))
            if mapper is None:
                error_text = f"unsupported message type {message_type}"
                ack = build_ack(raw_v2, code="AR", text=error_text)
                ack_code = "AR"
                return ack

            try:
                resources = mapper(raw_v2)
            except Exception as exc:
                log.exception("mapper.failed", message_type=message_type)
                error_text = f"mapping failed: {exc}"
                ack = build_ack(raw_v2, code="AE", text=error_text)
                ack_code = "AE"
                return ack

            for mr in resources:
                issues = validate_resource(mr.resource)
                for issue in issues:
                    validation_issue_records.append(
                        {
                            "resource_type": mr.resource.__class__.__name__,
                            "severity": issue.severity,
                            "path": issue.path,
                            "message": issue.message,
                        }
                    )
                    logger = log.warning if issue.severity == "warning" else log.error
                    logger(
                        "validation.issue",
                        resource_type=mr.resource.__class__.__name__,
                        severity=issue.severity,
                        path=issue.path,
                        message=issue.message,
                    )
                if has_errors(issues):
                    error_text = f"validation failed on {mr.resource.__class__.__name__}"
                    ack = build_ack(raw_v2, code="AE", text=error_text)
                    ack_code = "AE"
                    return ack

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
                error_text = f"FHIR write failed: {exc}"
                ack = build_ack(raw_v2, code="AE", text=error_text)
                ack_code = "AE"
                return ack

            ack = build_ack(raw_v2, code="AA")
            ack_code = "AA"
            return ack
        finally:
            if self._metrics is not None:
                # Only count resources that were actually written (happens on
                # AA ACKs; on AE we bailed out before writing).
                resource_types_written = (
                    [mr.resource.__class__.__name__ for mr in resources] if ack_code == "AA" else []
                )
                self._metrics.record_message(
                    message_type=message_type,
                    ack_code=ack_code,
                    resource_types_written=resource_types_written,
                    issue_severities=[i["severity"] for i in validation_issue_records],
                )
            if self._store is not None:
                record = MessageRecord(
                    id=new_message_id(),
                    received_at=now_iso(),
                    message_type=message_type,
                    raw_v2=raw_v2,
                    ack=ack,
                    ack_code=ack_code,
                    resources=[
                        ResourceRecord(
                            resource_type=mr.resource.__class__.__name__,
                            operation=mr.operation,
                            identifier_query=mr.identifier_query,
                            resource=mr.resource.model_dump(
                                by_alias=True, exclude_none=True, mode="json"
                            ),
                        )
                        for mr in resources
                    ],
                    validation_issues=validation_issue_records,
                    error=error_text,
                )
                await self._store.add(record)
