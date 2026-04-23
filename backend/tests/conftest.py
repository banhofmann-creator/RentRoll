import os

os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///test.db"

from pathlib import Path

import pytest

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"
SAMPLE_CSV = SAMPLES_DIR / "Mieterliste_1-Garbe (2).csv"


@pytest.fixture
def sample_csv_bytes():
    return SAMPLE_CSV.read_bytes()
