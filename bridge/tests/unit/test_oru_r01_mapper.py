from pathlib import Path

from fhir.resources.R4B.diagnosticreport import DiagnosticReport
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient

from bridge.mappers import map_oru_r01


def test_oru_r01_produces_patient_four_observations_and_one_report(
    fixtures_dir: Path,
) -> None:
    raw = (fixtures_dir / "oru_r01_simple.hl7").read_text()
    resources = map_oru_r01(raw)

    kinds = [type(mr.resource).__name__ for mr in resources]
    assert kinds == [
        "Patient",
        "Observation",
        "Observation",
        "Observation",
        "Observation",
        "DiagnosticReport",
    ]
    assert resources[0].operation == "update"
    assert all(mr.operation == "create" for mr in resources[1:])


def test_oru_r01_observation_values_and_units(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "oru_r01_simple.hl7").read_text()
    resources = map_oru_r01(raw)
    observations = [mr.resource for mr in resources if isinstance(mr.resource, Observation)]
    assert [obs.code.coding[0].code for obs in observations] == [
        "2093-3",
        "2085-9",
        "2089-1",
        "2571-8",
    ]
    assert [obs.code.coding[0].system for obs in observations] == ["http://loinc.org"] * 4
    assert [float(obs.valueQuantity.value) for obs in observations] == [
        185.0,
        55.0,
        110.0,
        100.0,
    ]
    assert all(obs.valueQuantity.code == "mg/dL" for obs in observations)
    assert all(obs.valueQuantity.system == "http://unitsofmeasure.org" for obs in observations)


def test_oru_r01_ldl_is_flagged_high(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "oru_r01_simple.hl7").read_text()
    resources = map_oru_r01(raw)
    observations = [mr.resource for mr in resources if isinstance(mr.resource, Observation)]
    ldl = next(obs for obs in observations if obs.code.coding[0].code == "2089-1")
    assert ldl.interpretation[0].coding[0].code == "H"


def test_oru_r01_diagnostic_report_references_observations(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "oru_r01_simple.hl7").read_text()
    resources = map_oru_r01(raw)
    report = next(mr.resource for mr in resources if isinstance(mr.resource, DiagnosticReport))
    assert report.code.coding[0].code == "24331-1"
    assert report.category[0].coding[0].code == "laboratory"
    assert len(report.result) == 4
    # Each report result reference should be to an Observation identified in
    # our urn:obx scheme.
    for ref in report.result:
        assert ref.type == "Observation"
        assert ref.identifier is not None
        assert ref.identifier.system == "urn:obx"


def test_oru_r01_observations_carry_unique_identifiers_per_filler(
    fixtures_dir: Path,
) -> None:
    raw = (fixtures_dir / "oru_r01_simple.hl7").read_text()
    observations = [mr.resource for mr in map_oru_r01(raw) if isinstance(mr.resource, Observation)]
    ids = [(obs.identifier[0].system, obs.identifier[0].value) for obs in observations]
    assert ids == [
        ("urn:obx", "FIL99001.1"),
        ("urn:obx", "FIL99001.2"),
        ("urn:obx", "FIL99001.3"),
        ("urn:obx", "FIL99001.4"),
    ]


def test_oru_r01_patient_is_first() -> None:
    raw = (
        "MSH|^~\\&|LAB|HOSP|RECV|FAC|20260419|||ORU^R01|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JOHN||19700101|M\r"
        "OBR|1|||24331-1^LIPID^LN|||20260419130000\r"
        "OBX|1|NM|2093-3^CHOL^LN||180|mg/dL^mg/dL^UCUM|||||F|||20260419130000\r"
    )
    resources = map_oru_r01(raw)
    assert isinstance(resources[0].resource, Patient)
