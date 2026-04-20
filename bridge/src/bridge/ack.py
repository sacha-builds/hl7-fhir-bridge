"""HL7 v2 MSA acknowledgement builder.

Produces minimal ACK messages suitable for MLLP responses. We avoid going
through `hl7apy` here so that we can always return *some* reply even when
the inbound message is malformed — an AE/AR is still useful to the sender.
"""

from __future__ import annotations

from datetime import UTC, datetime

SEG_SEP = "\r"


def build_ack(original_v2: str, code: str = "AA", text: str | None = None) -> str:
    """Build an ACK in response to the given v2 message.

    `code` is one of AA (accept), AE (application error), AR (application
    reject). Sender/receiver are swapped; MSH-10 is echoed into MSA-2.
    """
    now = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    first_seg = original_v2.split(SEG_SEP, 1)[0] if original_v2 else ""
    parts = first_seg.split("|")

    if len(parts) < 12 or parts[0] != "MSH":
        msh = f"MSH|^~\\&|BRIDGE|BRIDGE|UNKNOWN|UNKNOWN|{now}||ACK|ACK{now}|P|2.5.1"
        msa = "MSA|AR|UNKNOWN|malformed MSH"
        return msh + SEG_SEP + msa + SEG_SEP

    encoding = parts[1]
    sending_app = parts[2]
    sending_fac = parts[3]
    receiving_app = parts[4]
    receiving_fac = parts[5]
    control_id = parts[9]
    version = parts[11]

    msh = (
        f"MSH|{encoding}|{receiving_app}|{receiving_fac}|"
        f"{sending_app}|{sending_fac}|{now}||ACK|ACK-{control_id}|P|{version}"
    )
    msa_fields = ["MSA", code, control_id]
    if text:
        msa_fields.append(text)
    msa = "|".join(msa_fields)
    return msh + SEG_SEP + msa + SEG_SEP
