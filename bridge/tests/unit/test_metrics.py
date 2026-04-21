from bridge.metrics import Metrics


def test_records_message_increments_expected_counters() -> None:
    m = Metrics()
    m.record_message(
        message_type="ADT^A01",
        ack_code="AA",
        resource_types_written=["Patient", "Encounter"],
        issue_severities=[],
    )
    m.record_message(
        message_type="ORU^R01",
        ack_code="AA",
        resource_types_written=["DiagnosticReport", "Observation", "Observation"],
        issue_severities=["warning"],
    )

    snapshot = m.snapshot()
    assert snapshot["messages_total"] == 2
    assert snapshot["messages_by_type"] == {"ADT^A01": 1, "ORU^R01": 1}
    assert snapshot["messages_by_ack_code"] == {"AA": 2}
    assert snapshot["resources_written"] == {
        "Patient": 1,
        "Encounter": 1,
        "DiagnosticReport": 1,
        "Observation": 2,
    }
    assert snapshot["validation_issues_by_severity"] == {"warning": 1}


def test_reject_messages_do_not_add_resources_written() -> None:
    m = Metrics()
    m.record_message(
        message_type="ADT^A01",
        ack_code="AE",
        resource_types_written=[],
        issue_severities=["error"],
    )
    snapshot = m.snapshot()
    assert snapshot["messages_total"] == 1
    assert snapshot["messages_by_ack_code"] == {"AE": 1}
    assert snapshot["resources_written"] == {}
    assert snapshot["validation_issues_by_severity"] == {"error": 1}


def test_reset_clears_counters_and_restarts_uptime() -> None:
    m = Metrics()
    m.record_message(
        message_type="ADT^A01",
        ack_code="AA",
        resource_types_written=["Patient"],
        issue_severities=[],
    )
    m.reset()
    snapshot = m.snapshot()
    assert snapshot["messages_total"] == 0
    assert snapshot["messages_by_type"] == {}
    assert snapshot["resources_written"] == {}
