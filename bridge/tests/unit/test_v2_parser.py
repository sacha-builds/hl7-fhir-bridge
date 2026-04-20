import pytest

from bridge.parsers import get_message_type


def test_get_message_type_adt_a01(adt_a01_raw: str) -> None:
    code, event = get_message_type(adt_a01_raw)
    assert code == "ADT"
    assert event == "A01"


def test_get_message_type_handles_lf_separators() -> None:
    msg = "MSH|^~\\&|A|B|C|D|20260101||ORU^R01|X|P|2.5.1\nPID|1||1\n"
    code, event = get_message_type(msg)
    assert code == "ORU"
    assert event == "R01"


def test_get_message_type_raises_on_missing_msh() -> None:
    with pytest.raises(ValueError):
        get_message_type("PID|1||1\r")
