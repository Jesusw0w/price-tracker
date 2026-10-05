import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Settings require a URL at import; tests never connect, so any parseable one works
os.environ.setdefault("PT_DATABASE_URL", "sqlite://")

from app.db.database import Base


@pytest.fixture
def session() -> Iterator[Session]:
    # One in-memory database shared by the test and the endpoint's worker thread
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
