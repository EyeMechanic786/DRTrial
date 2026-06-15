"""Pytest fixtures — use SQLite for tests."""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_drtrial.db")


@pytest.fixture(autouse=True)
def setup_db():
    from apps.api.db.init_db import init_db

    init_db()
    yield
    try:
        os.remove("test_drtrial.db")
    except OSError:
        pass
