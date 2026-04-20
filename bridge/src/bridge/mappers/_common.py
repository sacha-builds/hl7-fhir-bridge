"""Shared HL7 v2 parsing + FHIR building helpers used across mappers."""

from __future__ import annotations

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


def segments_by_name(raw_v2: str) -> dict[str, list[str]]:
    normalized = raw_v2.replace("\r\n", "\r").replace("\n", "\r").strip()
    out: dict[str, list[str]] = {}
    for seg in normalized.split(SEG_SEP):
        if not seg or len(seg) < 3:
            continue
        out.setdefault(seg[:3], []).append(seg)
    return out


def require_segment(segments: dict[str, list[str]], name: str) -> str:
    if name not in segments or not segments[name]:
        raise ValueError(f"missing required segment: {name}")
    return segments[name][0]


def fields(segment: str) -> list[str]:
    return segment.split("|")


def components(field: str) -> list[str]:
    return field.split("^")


def repeats(field: str) -> list[str]:
    return field.split("~")


def get_field(flds: list[str], index: int) -> str:
    return flds[index] if 0 <= index < len(flds) else ""


def parse_hl7_date(raw: str) -> str | None:
    if not raw:
        return None
    digits = raw.split(".")[0].split("-")[0].split("+")[0][:8]
    try:
        return datetime.strptime(digits, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def parse_hl7_datetime(raw: str) -> datetime | None:
    # HL7 DTM allows +/-HHMM tz; we drop it and default to UTC. Full tz
    # preservation is a Phase 2+ concern.
    if not raw:
        return None
    digits = raw.split(".")[0].split("-")[0].split("+")[0]
    for fmt, length in (("%Y%m%d%H%M%S", 14), ("%Y%m%d%H%M", 12), ("%Y%m%d", 8)):
        try:
            return datetime.strptime(digits[:length], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def build_identifiers(field: str) -> list[Identifier]:
    if not field:
        return []
    out: list[Identifier] = []
    for rep in repeats(field):
        if not rep:
            continue
        comps = components(rep)
        value = get_field(comps, 0)
        if not value:
            continue
        assigning_authority = get_field(comps, 3)
        id_type_code = get_field(comps, 4)
        payload: dict[str, Any] = {"value": value}
        if assigning_authority:
            payload["system"] = f"urn:id:{assigning_authority}"
        if id_type_code:
            payload["type"] = CodeableConcept(
                coding=[Coding(system=IDENTIFIER_TYPE_SYSTEM, code=id_type_code)]
            )
        out.append(Identifier(**payload))
    return out


def build_names(field: str) -> list[HumanName]:
    if not field:
        return []
    out: list[HumanName] = []
    for rep in repeats(field):
        if not rep:
            continue
        comps = components(rep)
        family = get_field(comps, 0)
        given = get_field(comps, 1)
        middle = get_field(comps, 2)
        suffix = get_field(comps, 3)
        prefix = get_field(comps, 4)
        name_type = get_field(comps, 6)
        payload: dict[str, Any] = {}
        if family:
            payload["family"] = family
        givens = [g for g in (given, middle) if g]
        if givens:
            payload["given"] = givens
        if prefix:
            payload["prefix"] = [prefix]
        if suffix:
            payload["suffix"] = [suffix]
        use = {"L": "official", "M": "maiden", "N": "nickname"}.get(name_type)
        if use:
            payload["use"] = use
        if payload:
            out.append(HumanName(**payload))
    return out


def build_patient_from_pid(pid_segment: str) -> Patient:
    flds = fields(pid_segment)
    identifiers = build_identifiers(get_field(flds, 3))
    names = build_names(get_field(flds, 5))
    birthdate = parse_hl7_date(get_field(flds, 7))
    gender = GENDER_MAP.get(get_field(flds, 8).strip().upper())

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


def build_encounter_from_pv1(pv1_segment: str, patient: Patient) -> Encounter:
    flds = fields(pv1_segment)
    class_code_raw = get_field(flds, 2).strip().upper()
    class_code, class_display = ENCOUNTER_CLASS_MAP.get(class_code_raw, ("AMB", "ambulatory"))
    class_coding = Coding(
        system=V3_ACT_CODE_SYSTEM,
        code=class_code,
        display=class_display,
    )

    visit_identifiers = build_identifiers(get_field(flds, 19))
    admit_dt = parse_hl7_datetime(get_field(flds, 44))
    discharge_dt = parse_hl7_datetime(get_field(flds, 45))

    period_payload: dict[str, Any] = {}
    if admit_dt:
        period_payload["start"] = admit_dt
    if discharge_dt:
        period_payload["end"] = discharge_dt

    payload: dict[str, Any] = {
        "status": "finished" if discharge_dt else "in-progress",
        "class": class_coding,
        "subject": patient_reference(patient),
    }
    if visit_identifiers:
        payload["identifier"] = visit_identifiers
    if period_payload:
        payload["period"] = Period(**period_payload)
    return Encounter(**payload)


def patient_reference(patient: Patient) -> Reference:
    if patient.identifier:
        first = patient.identifier[0]
        return Reference(
            type="Patient",
            identifier=Identifier(system=first.system, value=first.value),
        )
    return Reference(type="Patient")


def identifier_query_for(identifiers: list[Any] | None) -> str | None:
    if not identifiers:
        return None
    first = identifiers[0]
    if first.system and first.value:
        return f"{first.system}|{first.value}"
    if first.value:
        return str(first.value)
    return None
