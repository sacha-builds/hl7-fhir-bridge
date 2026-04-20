import json

from bridge.mappers import map_adt_a01


def _dump(resource) -> dict:
    return json.loads(resource.model_dump_json(by_alias=True, exclude_none=True))


def test_adt_a01_maps_to_expected_patient_and_encounter(
    adt_a01_raw: str, adt_a01_expected: dict
) -> None:
    mapped = map_adt_a01(adt_a01_raw)
    patient_json = _dump(mapped.patient)
    encounter_json = _dump(mapped.encounter)

    assert patient_json == adt_a01_expected["patient"]
    assert encounter_json == adt_a01_expected["encounter"]


def test_adt_a01_maps_gender_variants() -> None:
    msg = (
        "MSH|^~\\&|A|B|C|D|20260101||ADT^A01|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JOHN||19700101|M\r"
        "PV1|1|O\r"
    )
    mapped = map_adt_a01(msg)
    assert mapped.patient.gender == "male"


def test_adt_a01_ambulatory_class_for_outpatient() -> None:
    msg = (
        "MSH|^~\\&|A|B|C|D|20260101||ADT^A01|X|P|2.5.1\r"
        "PID|1||M1^^^H^MR||SMITH^JANE||19700101|F\r"
        "PV1|1|O\r"
    )
    mapped = map_adt_a01(msg)
    klass = mapped.encounter.class_fhir
    assert klass.code == "AMB"
