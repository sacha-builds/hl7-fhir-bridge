import json
from pathlib import Path

from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.patient import Patient

from bridge.mappers import map_adt_a08


def _dump(resource: object) -> dict:
    return json.loads(resource.model_dump_json(by_alias=True, exclude_none=True))


def test_adt_a08_golden_file_patient_only(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "adt_a08_simple.hl7").read_text()
    expected = json.loads((fixtures_dir / "adt_a08_simple.expected.json").read_text())

    resources = map_adt_a08(raw)
    assert len(resources) == 1
    assert isinstance(resources[0].resource, Patient)
    assert resources[0].operation == "update"
    assert _dump(resources[0].resource) == expected["patient"]


def test_adt_a08_refreshes_encounter_when_pv1_present() -> None:
    msg = (
        "MSH|^~\\&|A|B|C|D|20260420||ADT^A08|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JANE||19700101|F\r"
        "PV1|1|I|||||||||||||||||V00099\r"
    )
    resources = map_adt_a08(msg)
    assert len(resources) == 2
    kinds = [type(mr.resource).__name__ for mr in resources]
    assert kinds == ["Patient", "Encounter"]
    assert all(mr.operation == "update" for mr in resources)
    encounter_mr = resources[1]
    assert isinstance(encounter_mr.resource, Encounter)
    assert encounter_mr.resource.identifier[0].value == "V00099"
