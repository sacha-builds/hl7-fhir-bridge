import json
from pathlib import Path

from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.patient import Patient

from bridge.mappers import map_adt_a03


def _dump(resource: object) -> dict:
    return json.loads(resource.model_dump_json(by_alias=True, exclude_none=True))


def _find(resources, cls):
    for mr in resources:
        if isinstance(mr.resource, cls):
            return mr
    raise AssertionError(f"no {cls.__name__} in mapped resources")


def test_adt_a03_golden_file(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "adt_a03_simple.hl7").read_text()
    expected = json.loads((fixtures_dir / "adt_a03_simple.expected.json").read_text())

    resources = map_adt_a03(raw)
    patient_mr = _find(resources, Patient)
    encounter_mr = _find(resources, Encounter)

    assert _dump(patient_mr.resource) == expected["patient"]
    assert _dump(encounter_mr.resource) == expected["encounter"]


def test_adt_a03_emits_updates_not_creates(fixtures_dir: Path) -> None:
    raw = (fixtures_dir / "adt_a03_simple.hl7").read_text()
    resources = map_adt_a03(raw)
    assert all(mr.operation == "update" for mr in resources)


def test_adt_a03_marks_encounter_finished_even_without_discharge_time() -> None:
    msg = (
        "MSH|^~\\&|A|B|C|D|20260420||ADT^A03|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JANE||19700101|F\r"
        "PV1|1|I|||||||||||||||||V00042\r"
    )
    encounter_mr = _find(map_adt_a03(msg), Encounter)
    assert encounter_mr.resource.status == "finished"
