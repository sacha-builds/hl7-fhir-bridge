"""ADT^A03 (discharge) → update Patient + Encounter with end-of-stay info.

The v2-to-FHIR IG maps A03 to the same Patient + Encounter pair as A01, but
with Encounter.status=finished and Encounter.period.end populated from
PV1-45 (discharge date/time). We send a conditional update on both
resources so the existing records are superseded rather than duplicated.
"""

from __future__ import annotations

from bridge.mappers._common import (
    build_encounter_from_pv1,
    build_patient_from_pid,
    identifier_query_for,
    require_segment,
    segments_by_name,
)
from bridge.mappers._types import MappedResource


def map_adt_a03(raw_v2: str) -> list[MappedResource]:
    segments = segments_by_name(raw_v2)
    pid = require_segment(segments, "PID")
    pv1 = require_segment(segments, "PV1")

    patient = build_patient_from_pid(pid)
    encounter = build_encounter_from_pv1(pv1, patient)

    # If the PV1 didn't carry a PV1-45 discharge datetime but we know this is
    # an A03, the encounter should still be marked finished.
    if encounter.status != "finished":
        encounter.status = "finished"

    return [
        MappedResource(
            resource=patient,
            operation="update",
            identifier_query=identifier_query_for(patient.identifier),
        ),
        MappedResource(
            resource=encounter,
            operation="update",
            identifier_query=identifier_query_for(encounter.identifier),
        ),
    ]
