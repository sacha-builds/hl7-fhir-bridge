"""US Core 6.1.0 conformance checks for the resources we emit.

This is deliberately a subset of the full US Core IG — it asserts the
required and "must-support" fields for Patient, Encounter, Observation, and
DiagnosticReport as produced by our v2 mappers. For full IG conformance we
defer to the HAPI FHIR Validator / ONC Inferno harness (Phase 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    path: str
    message: str


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


def validate_resource(resource: Any) -> list[ValidationIssue]:
    resource_type = resource.__class__.__name__
    if resource_type == "Patient":
        return _validate_patient(resource)
    if resource_type == "Encounter":
        return _validate_encounter(resource)
    if resource_type == "Observation":
        return _validate_observation(resource)
    if resource_type == "DiagnosticReport":
        return _validate_diagnostic_report(resource)
    return []


def _validate_patient(patient: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not patient.identifier:
        issues.append(
            ValidationIssue("error", "Patient.identifier", "at least one identifier required")
        )
    if not patient.name:
        issues.append(ValidationIssue("error", "Patient.name", "at least one name required"))
    if not patient.gender:
        issues.append(ValidationIssue("error", "Patient.gender", "required"))
    if not patient.birthDate:
        issues.append(ValidationIssue("warning", "Patient.birthDate", "must-support field missing"))
    return issues


def _validate_encounter(enc: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not enc.status:
        issues.append(ValidationIssue("error", "Encounter.status", "required"))
    # fhir.resources aliases Encounter.class as class_fhir in Python
    class_value = getattr(enc, "class_fhir", None)
    if class_value is None:
        issues.append(ValidationIssue("error", "Encounter.class", "required"))
    if not enc.subject:
        issues.append(ValidationIssue("error", "Encounter.subject", "required"))
    if not enc.period:
        issues.append(ValidationIssue("warning", "Encounter.period", "must-support field missing"))
    return issues


def _validate_observation(obs: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not obs.status:
        issues.append(ValidationIssue("error", "Observation.status", "required"))
    if not obs.category:
        issues.append(ValidationIssue("error", "Observation.category", "required"))
    if not obs.code:
        issues.append(ValidationIssue("error", "Observation.code", "required"))
    if not obs.subject:
        issues.append(ValidationIssue("error", "Observation.subject", "required"))
    has_effective = obs.effectiveDateTime or obs.effectivePeriod
    if not has_effective:
        issues.append(ValidationIssue("error", "Observation.effective[x]", "required"))
    has_value = any(
        getattr(obs, attr, None) is not None
        for attr in (
            "valueQuantity",
            "valueCodeableConcept",
            "valueString",
            "valueBoolean",
            "valueInteger",
            "valueRange",
            "valueRatio",
            "valueSampledData",
            "valueTime",
            "valueDateTime",
            "valuePeriod",
        )
    )
    if not has_value and obs.dataAbsentReason is None:
        issues.append(
            ValidationIssue(
                "error",
                "Observation.value[x]",
                "either value[x] or dataAbsentReason required",
            )
        )
    return issues


def _validate_diagnostic_report(report: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not report.status:
        issues.append(ValidationIssue("error", "DiagnosticReport.status", "required"))
    if not report.category:
        issues.append(ValidationIssue("error", "DiagnosticReport.category", "required"))
    if not report.code:
        issues.append(ValidationIssue("error", "DiagnosticReport.code", "required"))
    if not report.subject:
        issues.append(ValidationIssue("error", "DiagnosticReport.subject", "required"))
    if not (report.effectiveDateTime or report.effectivePeriod):
        issues.append(
            ValidationIssue(
                "warning",
                "DiagnosticReport.effective[x]",
                "must-support field missing",
            )
        )
    return issues
