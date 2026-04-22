"""Background demo seeder.

When `BRIDGE_DEMO_REPLAY_INTERVAL_MINUTES` is > 0, the bridge process
periodically picks a random fixture from `BRIDGE_DEMO_FIXTURES_PATH` and
hands it to the router — same code path as a real MLLP message. This
keeps the deployed showcase inbox populated so a visitor always lands
on something alive instead of an empty state.
"""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

import structlog

from bridge.router import MessageRouter

log = structlog.get_logger()


def load_fixtures(directory: str) -> list[Path]:
    path = Path(directory)
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*.hl7") if p.is_file())


async def run_seeder(
    router: MessageRouter,
    fixtures_dir: str,
    interval_minutes: int,
) -> None:
    fixtures = load_fixtures(fixtures_dir)
    if not fixtures:
        log.warning("seeder.no_fixtures", path=fixtures_dir)
        return
    if interval_minutes <= 0:
        return

    log.info(
        "seeder.started",
        fixtures=len(fixtures),
        interval_minutes=interval_minutes,
    )
    try:
        while True:
            await asyncio.sleep(interval_minutes * 60)
            fixture = random.choice(fixtures)
            try:
                raw = fixture.read_text()
                await router.handle(raw)
                log.info("seeder.sent", fixture=fixture.name)
            except Exception:
                log.exception("seeder.send_failed", fixture=fixture.name)
    except asyncio.CancelledError:
        log.info("seeder.stopped")
        raise


async def send_random(router: MessageRouter, fixtures_dir: str) -> str | None:
    """Process one random fixture through the router. Returns its filename."""
    fixtures = load_fixtures(fixtures_dir)
    if not fixtures:
        return None
    fixture = random.choice(fixtures)
    raw = fixture.read_text()
    await router.handle(raw)
    return fixture.name
