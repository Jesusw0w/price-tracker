import logging

from alembic import context

from app.db import models  # noqa: F401  # registers the tables on Base.metadata
from app.db.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
