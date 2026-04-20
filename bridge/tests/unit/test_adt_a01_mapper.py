import json

from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.patient import Patient

from bridge.mappers import MappedResource, map_adt_a01


def _dump(resource: object) -> dict:
    return json.loads(resource.model_dump_json(by_alias=True, exclude_none=True))


def _find(resources: list[MappedResource], cls: type) -> object:
    for mr in resources:
        if isinstance(mr.resource, cls):
            return mr.resource
    raise AssertionError(f"no {cls.__name__} in mapped resources")


def test_adt_a01_maps_to_expected_patient_and_encounter(
    adt_a01_raw: str, adt_a01_expected: dict
) -> None:
    resources = map_adt_a01(adt_a01_raw)
    patient = _find(resources, Patient)
    encounter = _find(resources, Encounter)

    assert _dump(patient) == adt_a01_expected["patient"]
    assert _dump(encounter) == adt_a01_expected["encounter"]


def test_adt_a01_both_resources_are_creates() -> None:
    msg = (
        "MSH|^~\\&|A|B|C|D|20260101||ADT^A01|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JANE||19700101|F\r"
        "PV1|1|O\r"
    )
    resources = map_adt_a01(msg)
    assert [mr.operation for mr in resources] == ["create", "create"]


def test_adt_a01_maps_gender_variants() -> None:
    msg = (
        "MSH|^~\\&|A|B|C|D|20260101||ADT^A01|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JOHN||19700101|M\r"
        "PV1|1|O\r"
    )
    patient = _find(map_adt_a01(msg), Patient)
    assert patient.gender == "male"


def test_adt_a01_ambulatory_class_for_outpatient() -> None:
    msg = (
        "MSH|^~\\&|A|B|C|D|20260101||ADT^A01|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JANE||19700101|F\r"
        "PV1|1|O\r"
    )
    encounter = _find(map_adt_a01(msg), Encounter)
    assert encounter.class_fhir.code == "AMB"
