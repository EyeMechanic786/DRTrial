"""Create database tables."""

from apps.api.db.database import Base, engine
from apps.api.db import models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables created.")
