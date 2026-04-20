"""ADT^A08 (patient information update) → update Patient; refresh Encounter if PV1 present."""

from __future__ import annotations

from bridge.mappers._common import (
    build_encounter_from_pv1,
    build_patient_from_pid,
    identifier_query_for,
    require_segment,
    segments_by_name,
)
from bridge.mappers._types import MappedResource


def map_adt_a08(raw_v2: str) -> list[MappedResource]:
    segments = segments_by_name(raw_v2)
    pid = require_segment(segments, "PID")

    patient = build_patient_from_pid(pid)
    results: list[MappedResource] = [
        MappedResource(
            resource=patient,
            operation="update",
            identifier_query=identifier_query_for(patient.identifier),
        ),
    ]

    # PV1 is optional in A08 but often present; when it is we refresh the
    # Encounter as well so class/period stay in sync with the sender.
    if "PV1" in segments:
        encounter = build_encounter_from_pv1(segments["PV1"][0], patient)
        results.append(
            MappedResource(
                resource=encounter,
                operation="update",
                identifier_query=identifier_query_for(encounter.identifier),
            )
        )
    return results
