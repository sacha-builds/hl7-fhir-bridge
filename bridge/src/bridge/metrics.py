"""In-memory metrics collected as the bridge processes v2 messages.

Demo-grade only — not persisted, not exported in Prometheus format (yet).
The viewer reads these via GET /metrics to render a live dashboard tile.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Metrics:
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    messages_total: int = 0
    messages_by_type: Counter[str] = field(default_factory=Counter)
    messages_by_ack_code: Counter[str] = field(default_factory=Counter)
    resources_written: Counter[str] = field(default_factory=Counter)
    validation_issues_by_severity: Counter[str] = field(default_factory=Counter)

    def record_message(
        self,
        *,
        message_type: str,
        ack_code: str,
        resource_types_written: list[str],
        issue_severities: list[str],
    ) -> None:
        self.messages_total += 1
        self.messages_by_type[message_type] += 1
        self.messages_by_ack_code[ack_code] += 1
        for rt in resource_types_written:
            self.resources_written[rt] += 1
        for sev in issue_severities:
            self.validation_issues_by_severity[sev] += 1

    def snapshot(self) -> dict[str, Any]:
        uptime = (datetime.now(UTC) - self.started_at).total_seconds()
        return {
            "uptime_seconds": round(uptime, 1),
            "started_at": self.started_at.isoformat(),
            "messages_total": self.messages_total,
            "messages_by_type": dict(self.messages_by_type),
            "messages_by_ack_code": dict(self.messages_by_ack_code),
            "resources_written": dict(self.resources_written),
            "validation_issues_by_severity": dict(self.validation_issues_by_severity),
        }

    def reset(self) -> None:
        self.started_at = datetime.now(UTC)
        self.messages_total = 0
        self.messages_by_type.clear()
        self.messages_by_ack_code.clear()
        self.resources_written.clear()
        self.validation_issues_by_severity.clear()
