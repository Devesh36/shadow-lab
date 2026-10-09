from pathlib import Path

import pytest

from packages.db.store import Store

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("SHADOWLAB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SHADOWLAB_REPOSITORY_ROOT", str(PROJECT))
    database = Store(f"sqlite:///{tmp_path / 'test.db'}")
    database.initialize()
    yield database
    database.engine.dispose()
