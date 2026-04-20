from bridge.ack import build_ack

SAMPLE_MSH = (
    "MSH|^~\\&|EPIC|HOSP|RECEIVER|FACILITY|20260419120000||ADT^A01|MSG00001|P|2.5.1\rPID|1||MRN1\r"
)


def test_build_ack_accept_echoes_control_id_and_swaps_endpoints() -> None:
    ack = build_ack(SAMPLE_MSH, code="AA")
    segments = ack.strip().split("\r")
    assert len(segments) == 2
    msh_fields = segments[0].split("|")
    msa_fields = segments[1].split("|")

    assert msh_fields[0] == "MSH"
    assert msh_fields[1] == "^~\\&"
    # Sender/receiver swapped
    assert msh_fields[2] == "RECEIVER"
    assert msh_fields[3] == "FACILITY"
    assert msh_fields[4] == "EPIC"
    assert msh_fields[5] == "HOSP"
    # MSH-9 becomes ACK
    assert msh_fields[8] == "ACK"
    # MSH-12 version preserved
    assert msh_fields[11] == "2.5.1"

    assert msa_fields[0] == "MSA"
    assert msa_fields[1] == "AA"
    assert msa_fields[2] == "MSG00001"


def test_build_ack_nack_for_malformed_message() -> None:
    ack = build_ack("this is not an HL7 message", code="AR")
    segments = ack.strip().split("\r")
    assert segments[0].startswith("MSH|^~\\&|BRIDGE|BRIDGE|")
    assert segments[1].startswith("MSA|AR|UNKNOWN")


def test_build_ack_includes_text_field_when_provided() -> None:
    ack = build_ack(SAMPLE_MSH, code="AE", text="mapping failed")
    msa = ack.strip().split("\r")[1]
    assert msa.split("|")[3] == "mapping failed"
