"""ORU^R01 (observation result) → FHIR R4 DiagnosticReport + Observation(s).

A single ORU message carries one or more OBR groups, each with a set of
OBX result lines. The v2-to-FHIR IG maps OBR → DiagnosticReport (grouping)
and each OBX → an Observation referenced from DiagnosticReport.result.

For Phase 2 we only handle numeric (NM) and string (ST/TX) OBX value types;
coded-value (CE/CWE) and structured-numeric (SN) can be added later.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.diagnosticreport import DiagnosticReport
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.reference import Reference

from bridge.mappers._common import (
    build_patient_from_pid,
    components,
    fields,
    get_field,
    identifier_query_for,
    parse_hl7_datetime,
    patient_reference,
)
from bridge.mappers._types import MappedResource
from bridge.terminology import (
    DIAGNOSTIC_REPORT_STATUS_MAP,
    INTERPRETATION_MAP,
    LOINC_SYSTEM,
    OBSERVATION_CATEGORY_SYSTEM,
    OBSERVATION_STATUS_MAP,
    UCUM_SYSTEM,
    V2_OBSERVATION_INTERPRETATION_SYSTEM,
    coding_system_for,
)

LABORATORY_CATEGORY = CodeableConcept(
    coding=[
        Coding(
            system=OBSERVATION_CATEGORY_SYSTEM,
            code="laboratory",
            display="Laboratory",
        )
    ]
)


def map_oru_r01(raw_v2: str) -> list[MappedResource]:
    segments = _segments_in_order(raw_v2)
    pid_seg = _first_of(segments, "PID")
    if pid_seg is None:
        raise ValueError("missing required segment: PID")
    patient = build_patient_from_pid(pid_seg)

    results: list[MappedResource] = [
        MappedResource(
            resource=patient,
            operation="update",
            identifier_query=identifier_query_for(patient.identifier),
        )
    ]

    subject_ref = patient_reference(patient)

    # Walk segments in order; each OBR starts a new report. OBX lines before
    # the first OBR are ignored (rare but possible in malformed messages).
    current_obr: str | None = None
    current_obxs: list[str] = []

    def flush() -> None:
        if current_obr is None:
            return
        obr_flds = fields(current_obr)
        filler_id = get_field(obr_flds, 3) or get_field(obr_flds, 2)
        observations = _build_observations(current_obxs, subject_ref, filler_id)
        obs_refs = [_reference_for_observation(obs) for obs in observations]
        report = _build_diagnostic_report(current_obr, subject_ref, obs_refs)
        for obs in observations:
            results.append(
                MappedResource(
                    resource=obs,
                    operation="create",
                    identifier_query=identifier_query_for(obs.identifier),
                )
            )
        results.append(
            MappedResource(
                resource=report,
                operation="create",
                identifier_query=identifier_query_for(report.identifier),
            )
        )

    for name, seg in segments:
        if name == "OBR":
            flush()
            current_obr = seg
            current_obxs = []
        elif name == "OBX" and current_obr is not None:
            current_obxs.append(seg)

    flush()
    return results


def _segments_in_order(raw_v2: str) -> list[tuple[str, str]]:
    normalized = raw_v2.replace("\r\n", "\r").replace("\n", "\r").strip()
    out: list[tuple[str, str]] = []
    for seg in normalized.split("\r"):
        if not seg or len(seg) < 3:
            continue
        out.append((seg[:3], seg))
    return out


def _first_of(segments: list[tuple[str, str]], name: str) -> str | None:
    for n, seg in segments:
        if n == name:
            return seg
    return None


def _coded_element_to_coding(field: str) -> Coding | None:
    """Parse a CWE/CE field (code^display^system^...) into a FHIR Coding."""
    if not field:
        return None
    comps = components(field)
    code = get_field(comps, 0)
    display = get_field(comps, 1)
    system_id = get_field(comps, 2)
    if not code:
        return None
    payload: dict[str, Any] = {"code": code}
    system_uri = coding_system_for(system_id) if system_id else None
    if system_uri:
        payload["system"] = system_uri
    if display:
        payload["display"] = display
    return Coding(**payload)


def _require_loinc(field: str) -> Coding:
    """Coerce an OBX-3 / OBR-4 to a LOINC-ish Coding.

    If no system id is given in the CWE.3 position, we fall back to treating
    the code as LOINC since US Core and the v2-to-FHIR IG both expect it for
    lab observations. Upstream labs almost universally send LOINC.
    """
    coding = _coded_element_to_coding(field)
    if coding is None:
        raise ValueError("observation/report code is required")
    if not coding.system:
        coding.system = LOINC_SYSTEM
    return coding


def _reference_for_observation(obs: Observation) -> Reference:
    if obs.identifier and obs.identifier[0].system and obs.identifier[0].value:
        return Reference(
            type="Observation",
            identifier=Identifier(
                system=obs.identifier[0].system,
                value=obs.identifier[0].value,
            ),
        )
    return Reference(type="Observation")


def _build_observations(
    obx_segments: list[str],
    subject_ref: Reference,
    filler_id: str,
) -> list[Observation]:
    observations: list[Observation] = []
    for obx in obx_segments:
        flds = fields(obx)
        obx_id = get_field(flds, 1)  # OBX-1 set ID within the OBR
        value_type = get_field(flds, 2).strip().upper()
        code_field = get_field(flds, 3)
        value_field = get_field(flds, 5)
        units_field = get_field(flds, 6)
        ref_range = get_field(flds, 7)
        abnormal_flag = get_field(flds, 8).strip().upper()
        result_status = get_field(flds, 11).strip().upper()
        effective_dt = parse_hl7_datetime(get_field(flds, 14))

        coding = _require_loinc(code_field)
        status = OBSERVATION_STATUS_MAP.get(result_status, "final")

        payload: dict[str, Any] = {
            "status": status,
            "category": [LABORATORY_CATEGORY],
            "code": CodeableConcept(coding=[coding]),
            "subject": subject_ref,
        }
        if effective_dt:
            payload["effectiveDateTime"] = effective_dt

        value_payload = _build_value(value_type, value_field, units_field)
        if value_payload:
            payload.update(value_payload)

        if abnormal_flag:
            interp_code = INTERPRETATION_MAP.get(abnormal_flag)
            if interp_code:
                code, display = interp_code
                payload["interpretation"] = [
                    CodeableConcept(
                        coding=[
                            Coding(
                                system=V2_OBSERVATION_INTERPRETATION_SYSTEM,
                                code=code,
                                display=display,
                            )
                        ]
                    )
                ]

        if ref_range:
            payload["referenceRange"] = [_build_reference_range(ref_range)]

        if obx_id and filler_id:
            payload["identifier"] = [
                Identifier(
                    system="urn:obx",
                    value=f"{filler_id}.{obx_id}",
                )
            ]

        observations.append(Observation(**payload))
    return observations


def _build_value(value_type: str, value_field: str, units_field: str) -> dict[str, Any] | None:
    value = value_field.strip()
    if not value:
        return None
    if value_type == "NM":
        try:
            numeric = Decimal(value)
        except (ValueError, ArithmeticError):
            return {"valueString": value}
        unit_coding = components(units_field) if units_field else []
        unit_code = get_field(unit_coding, 0)
        unit_display = get_field(unit_coding, 1) or unit_code
        quantity_payload: dict[str, Any] = {"value": numeric}
        if unit_code:
            quantity_payload["unit"] = unit_display
            quantity_payload["system"] = UCUM_SYSTEM
            quantity_payload["code"] = unit_code
        return {"valueQuantity": Quantity(**quantity_payload)}
    if value_type in {"ST", "TX", "FT"}:
        return {"valueString": value}
    # Unsupported types for Phase 2 — round-trip as string so data isn't lost.
    return {"valueString": value}


def _build_reference_range(raw: str) -> Any:
    from fhir.resources.R4B.observation import ObservationReferenceRange

    low: Decimal | None = None
    high: Decimal | None = None
    text = raw.strip()
    if "-" in text:
        try:
            low_str, high_str = text.split("-", 1)
            low = Decimal(low_str)
            high = Decimal(high_str)
        except (ValueError, ArithmeticError):
            pass
    payload: dict[str, Any] = {"text": text}
    if low is not None:
        payload["low"] = Quantity(value=low)
    if high is not None:
        payload["high"] = Quantity(value=high)
    return ObservationReferenceRange(**payload)


def _build_diagnostic_report(
    obr_segment: str,
    subject_ref: Reference,
    observation_refs: list[Reference],
) -> DiagnosticReport:
    flds = fields(obr_segment)
    filler_id = get_field(flds, 3)
    placer_id = get_field(flds, 2)
    service_id_field = get_field(flds, 4)
    effective_dt = parse_hl7_datetime(get_field(flds, 7))
    result_status = get_field(flds, 25).strip().upper()
    status = DIAGNOSTIC_REPORT_STATUS_MAP.get(result_status, "final")

    coding = _require_loinc(service_id_field)
    code = CodeableConcept(coding=[coding])

    identifier_value = filler_id or placer_id
    identifiers = [Identifier(system="urn:obr", value=identifier_value)] if identifier_value else []

    payload: dict[str, Any] = {
        "status": status,
        "category": [LABORATORY_CATEGORY],
        "code": code,
        "subject": subject_ref,
    }
    if effective_dt:
        payload["effectiveDateTime"] = effective_dt
    if identifiers:
        payload["identifier"] = identifiers
    if observation_refs:
        payload["result"] = observation_refs
    return DiagnosticReport(**payload)
