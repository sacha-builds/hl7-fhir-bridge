"""Map HL7 v2 ADT^A01 (patient admit) to FHIR R4 Patient + Encounter.

Follows the HL7 v2-to-FHIR Implementation Guide:
https://build.fhir.org/ig/HL7/v2-to-fhir/
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.humanname import HumanName
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.period import Period
from fhir.resources.R4B.reference import Reference

SEG_SEP = "\r"

GENDER_MAP = {"M": "male", "F": "female", "O": "other", "U": "unknown", "A": "other"}
ENCOUNTER_CLASS_MAP = {
    "I": ("IMP", "inpatient encounter"),
    "O": ("AMB", "ambulatory"),
    "E": ("EMER", "emergency"),
    "P": ("PRENC", "pre-admission"),
    "R": ("AMB", "recurring patient"),
}
V3_ACT_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
IDENTIFIER_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v2-0203"


@dataclass(frozen=True)
class MappedAdmission:
    patient: Patient
    encounter: Encounter


def map_adt_a01(raw_v2: str) -> MappedAdmission:
    """Transform an ADT^A01 message string into FHIR Patient + Encounter."""
    segments = _segments_by_name(raw_v2)
    pid = _require(segments, "PID")
    pv1 = _require(segments, "PV1")

    patient = _map_patient(pid)
    encounter = _map_encounter(pv1, patient)
    return MappedAdmission(patient=patient, encounter=encounter)


def _segments_by_name(raw_v2: str) -> dict[str, list[str]]:
    normalized = raw_v2.replace("\r\n", "\r").replace("\n", "\r").strip()
    out: dict[str, list[str]] = {}
    for seg in normalized.split(SEG_SEP):
        if not seg or len(seg) < 3:
            continue
        name = seg[:3]
        out.setdefault(name, []).append(seg)
    return out


def _require(segments: dict[str, list[str]], name: str) -> str:
    if name not in segments or not segments[name]:
        raise ValueError(f"missing required segment: {name}")
    return segments[name][0]


def _fields(segment: str) -> list[str]:
    return segment.split("|")


def _components(field: str) -> list[str]:
    return field.split("^")


def _repeats(field: str) -> list[str]:
    return field.split("~")


def _get(fields: list[str], index: int) -> str:
    return fields[index] if 0 <= index < len(fields) else ""


def _map_patient(pid_segment: str) -> Patient:
    fields = _fields(pid_segment)
    # PID-3 patient identifier list (CX), repeating
    identifiers = _build_identifiers(_get(fields, 3))
    # PID-5 patient name (XPN), repeating — first repetition
    names = _build_names(_get(fields, 5))
    # PID-7 date/time of birth
    birthdate = _parse_hl7_date(_get(fields, 7))
    # PID-8 administrative sex
    gender = GENDER_MAP.get(_get(fields, 8).strip().upper())

    payload: dict[str, Any] = {}
    if identifiers:
        payload["identifier"] = identifiers
    if names:
        payload["name"] = names
    if gender:
        payload["gender"] = gender
    if birthdate:
        payload["birthDate"] = birthdate
    return Patient(**payload)


def _map_encounter(pv1_segment: str, patient: Patient) -> Encounter:
    fields = _fields(pv1_segment)
    # PV1-2 patient class
    class_code_raw = _get(fields, 2).strip().upper()
    class_code, class_display = ENCOUNTER_CLASS_MAP.get(class_code_raw, ("AMB", "ambulatory"))
    class_coding = Coding(
        system=V3_ACT_CODE_SYSTEM,
        code=class_code,
        display=class_display,
    )

    # PV1-19 visit number (CX)
    visit_identifiers = _build_identifiers(_get(fields, 19))

    # PV1-44 admit date/time
    admit_dt = _parse_hl7_datetime(_get(fields, 44))

    # Reference the patient by identifier when we don't yet have an ID assigned
    # by the FHIR server. This is the conditional-reference pattern the v2-to-
    # FHIR IG recommends for bundles and unresolved references.
    subject_ref = _build_patient_reference(patient)

    payload: dict[str, Any] = {
        "status": "in-progress",
        "class": class_coding,
        "subject": subject_ref,
    }
    if visit_identifiers:
        payload["identifier"] = visit_identifiers
    if admit_dt:
        payload["period"] = Period(start=admit_dt)
    return Encounter(**payload)


def _build_identifiers(field: str) -> list[Identifier]:
    if not field:
        return []
    identifiers: list[Identifier] = []
    for rep in _repeats(field):
        if not rep:
            continue
        comps = _components(rep)
        value = _get(comps, 0)
        if not value:
            continue
        assigning_authority = _get(comps, 3)
        id_type_code = _get(comps, 4)
        identifier_payload: dict[str, Any] = {"value": value}
        if assigning_authority:
            identifier_payload["system"] = f"urn:id:{assigning_authority}"
        if id_type_code:
            identifier_payload["type"] = CodeableConcept(
                coding=[
                    Coding(
                        system=IDENTIFIER_TYPE_SYSTEM,
                        code=id_type_code,
                    )
                ]
            )
        identifiers.append(Identifier(**identifier_payload))
    return identifiers


def _build_names(field: str) -> list[HumanName]:
    if not field:
        return []
    names: list[HumanName] = []
    for rep in _repeats(field):
        if not rep:
            continue
        comps = _components(rep)
        family = _get(comps, 0)
        given = _get(comps, 1)
        middle = _get(comps, 2)
        suffix = _get(comps, 3)
        prefix = _get(comps, 4)
        name_type = _get(comps, 6)  # XPN.7 name type code (L, M, N, etc.)
        name_payload: dict[str, Any] = {}
        if family:
            name_payload["family"] = family
        givens = [g for g in (given, middle) if g]
        if givens:
            name_payload["given"] = givens
        if prefix:
            name_payload["prefix"] = [prefix]
        if suffix:
            name_payload["suffix"] = [suffix]
        if name_type == "L":
            name_payload["use"] = "official"
        elif name_type == "M":
            name_payload["use"] = "maiden"
        elif name_type == "N":
            name_payload["use"] = "nickname"
        if name_payload:
            names.append(HumanName(**name_payload))
    return names


def _build_patient_reference(patient: Patient) -> Reference:
    if patient.identifier:
        first = patient.identifier[0]
        return Reference(
            type="Patient",
            identifier=Identifier(
                system=first.system,
                value=first.value,
            ),
        )
    return Reference(type="Patient")


def _parse_hl7_date(raw: str) -> str | None:
    if not raw:
        return None
    digits = raw.split(".")[0].split("-")[0].split("+")[0]
    digits = digits[:8]
    try:
        return datetime.strptime(digits, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def _parse_hl7_datetime(raw: str) -> datetime | None:
    # HL7 DTM allows an optional +/-HHMM tz suffix; we drop it and default to
    # UTC. Full tz preservation is a Phase 2 concern.
    if not raw:
        return None
    digits = raw.split(".")[0].split("-")[0].split("+")[0]
    for fmt, length in (
        ("%Y%m%d%H%M%S", 14),
        ("%Y%m%d%H%M", 12),
        ("%Y%m%d", 8),
    ):
        try:
            return datetime.strptime(digits[:length], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None
