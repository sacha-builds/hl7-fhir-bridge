from __future__ import annotations

from typing import Any

from hl7apy.consts import VALIDATION_LEVEL
from hl7apy.parser import parse_message

SEG_SEP = "\r"


def _normalize(raw: str) -> str:
    return raw.replace("\r\n", "\r").replace("\n", "\r").strip()


def parse_v2(raw: str) -> Any:
    """Parse an HL7 v2 message using hl7apy in tolerant mode."""
    return parse_message(_normalize(raw), validation_level=VALIDATION_LEVEL.TOLERANT)


def get_message_type(raw: str) -> tuple[str, str]:
    """Return `(message_code, trigger_event)` from MSH-9 without full parsing."""
    first_seg = _normalize(raw).split(SEG_SEP, 1)[0]
    parts = first_seg.split("|")
    if len(parts) < 10 or parts[0] != "MSH":
        raise ValueError("invalid MSH segment")
    msh_9 = parts[8]
    components = msh_9.split("^")
    code = components[0] if components else ""
    event = components[1] if len(components) > 1 else ""
    return code, event
