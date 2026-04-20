"""Terminology systems we emit into FHIR codings.

Exposed as module constants so mappers and tests share a single source of
truth. No lookups against external terminology servers yet — that's a
Phase 4 concern.
"""

from __future__ import annotations

LOINC_SYSTEM = "http://loinc.org"
SNOMED_SYSTEM = "http://snomed.info/sct"
UCUM_SYSTEM = "http://unitsofmeasure.org"
OBSERVATION_CATEGORY_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category"
V2_OBSERVATION_INTERPRETATION_SYSTEM = (
    "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"
)
DIAGNOSTIC_SERVICE_SECTION_ID_SYSTEM = "http://terminology.hl7.org/CodeSystem/v2-0074"

# HL7 v2 coding system IDs (CWE.3) we accept as "this is LOINC/SNOMED".
V2_LOINC_CODING_IDS = {"LN", "LOINC"}
V2_SNOMED_CODING_IDS = {"SCT", "SNOMED", "SNM"}


def coding_system_for(v2_coding_system_id: str) -> str | None:
    """Translate a CWE.3 coding system ID into a FHIR system URI."""
    upper = v2_coding_system_id.strip().upper()
    if upper in V2_LOINC_CODING_IDS:
        return LOINC_SYSTEM
    if upper in V2_SNOMED_CODING_IDS:
        return SNOMED_SYSTEM
    return None


# OBX.11 (observation result status) → FHIR Observation.status
OBSERVATION_STATUS_MAP: dict[str, str] = {
    "F": "final",
    "C": "corrected",
    "P": "preliminary",
    "X": "cancelled",
    "D": "entered-in-error",
    "R": "registered",
    "I": "registered",
    "S": "preliminary",
    "W": "entered-in-error",
}

# OBR.25 (result status) → FHIR DiagnosticReport.status
DIAGNOSTIC_REPORT_STATUS_MAP: dict[str, str] = {
    "F": "final",
    "C": "corrected",
    "P": "preliminary",
    "X": "cancelled",
    "I": "registered",
    "R": "registered",
    "S": "partial",
    "A": "partial",
}

# OBX.8 abnormal flags → FHIR v3 observation interpretation code
INTERPRETATION_MAP: dict[str, tuple[str, str]] = {
    "L": ("L", "Low"),
    "H": ("H", "High"),
    "LL": ("LL", "Critical low"),
    "HH": ("HH", "Critical high"),
    "N": ("N", "Normal"),
    "A": ("A", "Abnormal"),
    "AA": ("AA", "Critically abnormal"),
    ">": ("H", "High"),
    "<": ("L", "Low"),
}
