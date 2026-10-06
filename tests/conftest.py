"""Ortak pytest fixture'ları ve örnek dizin yolları."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"
GOLDEN_DIR = EXAMPLES / "golden"


@pytest.fixture(scope="session")
def golden_dir() -> Path:
    return GOLDEN_DIR


@pytest.fixture(scope="session")
def broken_catalog() -> Path:
    return EXAMPLES / "data" / "catalog.json"


@pytest.fixture(scope="session")
def demo_glossary() -> Path:
    return EXAMPLES / "data" / "glossary.yaml"


@pytest.fixture
def catalog_file(tmp_path: Path) -> Callable[..., Path]:
    """Write a catalog JSON to a temp file and return the path."""

    def _write(payload: dict[str, object], name: str = "catalog.json") -> Path:
        path = tmp_path / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    return _write
