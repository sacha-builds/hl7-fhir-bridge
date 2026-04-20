from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.humanname import HumanName
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.reference import Reference

from bridge.validators import has_errors, validate_resource


def _patient(**overrides) -> Patient:
    base = dict(
        identifier=[Identifier(system="urn:id:H", value="1")],
        name=[HumanName(family="DOE", given=["JANE"])],
        gender="female",
        birthDate="1980-01-01",
    )
    base.update(overrides)
    return Patient(**base)


def test_valid_patient_has_no_errors() -> None:
    assert not has_errors(validate_resource(_patient()))


def test_patient_without_identifier_errors() -> None:
    issues = validate_resource(_patient(identifier=None))
    assert has_errors(issues)
    assert any(i.path == "Patient.identifier" for i in issues)


def test_patient_without_birthdate_warns_but_does_not_error() -> None:
    issues = validate_resource(_patient(birthDate=None))
    assert not has_errors(issues)
    assert any(i.severity == "warning" and i.path == "Patient.birthDate" for i in issues)


def test_observation_missing_value_and_datetime_errors() -> None:
    obs = Observation(
        status="final",
        category=[
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/observation-category",
                        code="laboratory",
                    )
                ]
            )
        ],
        code=CodeableConcept(coding=[Coding(system="http://loinc.org", code="2093-3")]),
        subject=Reference(type="Patient"),
    )
    issues = validate_resource(obs)
    assert has_errors(issues)
    paths = [i.path for i in issues]
    assert "Observation.effective[x]" in paths
    assert "Observation.value[x]" in paths


def test_encounter_missing_class_errors() -> None:
    encounter = Encounter.model_construct(
        status="in-progress",
        subject=Reference(type="Patient"),
    )
    issues = validate_resource(encounter)
    assert has_errors(issues)
    assert any(i.path == "Encounter.class" for i in issues)
