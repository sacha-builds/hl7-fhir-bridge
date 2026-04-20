from bridge.mllp.protocol import CR, EB, SB, extract_frame, wrap_frame


def test_wrap_frame_adds_sb_eb_cr() -> None:
    framed = wrap_frame(b"HELLO")
    assert framed == SB + b"HELLO" + EB + CR


def test_extract_single_complete_frame() -> None:
    buffer = wrap_frame(b"MSH|^~&|")
    payload, remaining = extract_frame(buffer)
    assert payload == b"MSH|^~&|"
    assert remaining == b""


def test_extract_returns_none_when_incomplete() -> None:
    buffer = SB + b"partial..."
    payload, remaining = extract_frame(buffer)
    assert payload is None
    assert remaining == buffer


def test_extract_handles_two_back_to_back_frames() -> None:
    buffer = wrap_frame(b"FIRST") + wrap_frame(b"SECOND")
    first, remaining = extract_frame(buffer)
    assert first == b"FIRST"
    second, remaining = extract_frame(remaining)
    assert second == b"SECOND"
    assert remaining == b""


def test_extract_ignores_bytes_before_sb() -> None:
    buffer = b"noise" + wrap_frame(b"PAYLOAD")
    payload, remaining = extract_frame(buffer)
    assert payload == b"PAYLOAD"
    assert remaining == b""


def test_extract_on_empty_buffer() -> None:
    payload, remaining = extract_frame(b"")
    assert payload is None
    assert remaining == b""
