"""Shared test fixtures and paths."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

CORPUS_DIR = ROOT / "corpus"
FINOPS_CORPUS_DIR = ROOT / "corpus-finops"
DATASET = ROOT / "datasets" / "meridian-golden-v1.jsonl"
FINOPS_DATASET = ROOT / "datasets" / "meridian-finops-golden-v1.jsonl"
AGENTS_DIR = ROOT / "agents"

EXPECTED_DOCUMENT_COUNT = 12
EXPECTED_FINOPS_DOCUMENT_COUNT = 19


@pytest.fixture(scope="session")
def corpus_paths() -> list[Path]:
    return sorted(CORPUS_DIR.glob("*.md"))


@pytest.fixture(scope="session")
def finops_paths() -> list[Path]:
    return sorted(FINOPS_CORPUS_DIR.glob("*.md"))


@pytest.fixture(scope="session")
def finops_docs(finops_paths: list[Path]) -> dict[str, str]:
    return {path.stem: path.read_text(encoding="utf-8") for path in finops_paths}


@pytest.fixture(scope="session")
def corpus_ids(corpus_paths: list[Path]) -> set[str]:
    return {path.stem for path in corpus_paths}


@pytest.fixture(scope="session")
def dataset() -> list[dict]:
    import json

    with DATASET.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@pytest.fixture(scope="session")
def finops_dataset() -> list[dict]:
    import json

    with FINOPS_DATASET.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@pytest.fixture(scope="session")
def finops_ids(finops_paths: list[Path]) -> set[str]:
    return {path.stem for path in finops_paths}
