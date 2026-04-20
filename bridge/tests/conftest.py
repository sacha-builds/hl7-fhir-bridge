from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def adt_a01_raw(fixtures_dir: Path) -> str:
    return (fixtures_dir / "adt_a01_simple.hl7").read_text()


@pytest.fixture
def adt_a01_expected(fixtures_dir: Path) -> dict:
    import json

    return json.loads((fixtures_dir / "adt_a01_simple.expected.json").read_text())
