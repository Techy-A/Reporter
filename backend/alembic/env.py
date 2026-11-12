"""Alembic environment. The database URL comes from the app's settings (PP_DATABASE_URL), never from alembic.ini."""
from alembic import context

from peoplepilot import models  # noqa: F401  (register tables)
from peoplepilot.db import Base, get_engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
