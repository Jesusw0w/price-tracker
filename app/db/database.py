from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    # Supabase's pooler drops idle connections; ping before reuse, not mid-request
    pool_pre_ping=True,
    # Transaction pooler hands each transaction a different backend, so a statement
    # psycopg prepared on one is missing on the next
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
