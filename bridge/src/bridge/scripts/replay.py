"""Stream HL7 v2 files to the bridge over MLLP.

Useful for demo traffic — point at a directory of `.hl7` fixtures, optionally
pace the send rate, and watch the viewer inbox fill up in real time.

Usage:
    bridge-replay FILE_OR_DIR [--host HOST] [--port PORT] [--delay MS] [--loop]
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import random
import sys
from collections.abc import Iterable
from pathlib import Path

from bridge.mllp.protocol import extract_frame, wrap_frame


def _iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    yield from sorted(p for p in path.rglob("*.hl7") if p.is_file())


async def _send_one(
    host: str,
    port: int,
    raw: bytes,
    timeout: float = 10.0,
) -> str:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(wrap_frame(raw))
        await writer.drain()

        buffer = b""
        while True:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=timeout)
            if not chunk:
                break
            buffer += chunk
            payload, _ = extract_frame(buffer)
            if payload is not None:
                return payload.decode("utf-8", errors="replace")
        return "(no ACK received)"
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


def _ack_summary(ack: str) -> str:
    lines = ack.replace("\r\n", "\r").replace("\n", "\r").split("\r")
    for line in lines:
        if line.startswith("MSA|"):
            parts = line.split("|")
            code = parts[1] if len(parts) > 1 else "?"
            return code
    return "?"


async def _run(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 2

    files = list(_iter_files(path))
    if not files:
        print(f"error: no .hl7 files under {path}", file=sys.stderr)
        return 2

    print(f"replaying {len(files)} message(s) → {args.host}:{args.port}")

    iterations = 0
    while True:
        iterations += 1
        order = list(files)
        if args.shuffle:
            random.shuffle(order)
        for file in order:
            raw = file.read_bytes()
            try:
                ack = await _send_one(args.host, args.port, raw)
            except Exception as exc:
                print(f"  ✗ {file.name}: {exc}")
                continue
            code = _ack_summary(ack)
            marker = "✓" if code == "AA" else "✗"
            print(f"  {marker} {file.name} → MSA|{code}")
            if args.delay > 0:
                await asyncio.sleep(args.delay / 1000)
        if not args.loop:
            break
        print(f"-- loop iteration {iterations} complete, restarting --")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay HL7 v2 files to an MLLP listener.")
    parser.add_argument("path", help="File or directory containing .hl7 messages")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=2575)
    parser.add_argument(
        "--delay", type=int, default=500, help="Delay between messages in milliseconds"
    )
    parser.add_argument("--loop", action="store_true", help="Replay forever")
    parser.add_argument("--shuffle", action="store_true", help="Randomize order each pass")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
