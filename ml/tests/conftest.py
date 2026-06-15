"""Pytest fixtures — use in-memory SQLite for tests."""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(autouse=True)
def setup_db():
    from apps.api.db.database import engine
    from apps.api.db.init_db import init_db

    init_db()
    yield
    engine.dispose()
