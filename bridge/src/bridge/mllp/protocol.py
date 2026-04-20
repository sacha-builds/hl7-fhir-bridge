"""MLLP framing.

HL7 v2 messages travel inside an MLLP envelope:

    <SB> message <EB><CR>

where SB = 0x0B, EB = 0x1C, CR = 0x0D. See the HL7 Minimal Lower Layer
Protocol spec (v1.0) for the full state machine.
"""

from __future__ import annotations

SB = b"\x0b"
EB = b"\x1c"
CR = b"\x0d"
END = EB + CR


def wrap_frame(payload: bytes) -> bytes:
    return SB + payload + END


def extract_frame(buffer: bytes) -> tuple[bytes | None, bytes]:
    """Pull the first complete framed message off the buffer.

    Returns `(payload, remaining)`. `payload` is `None` if no complete frame
    is available yet; `remaining` is what's left in the buffer (may still
    contain a partial frame).
    """
    start = buffer.find(SB)
    if start == -1:
        return None, b""
    end = buffer.find(END, start + 1)
    if end == -1:
        return None, buffer[start:]
    payload = buffer[start + 1 : end]
    remaining = buffer[end + len(END) :]
    return payload, remaining
