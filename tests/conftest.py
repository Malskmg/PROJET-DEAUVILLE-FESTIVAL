"""Shared pytest fixtures."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
DATA_FILE = PROJECT_ROOT / "data" / "festival.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture
def festival_data_path() -> Path:
    return DATA_FILE
