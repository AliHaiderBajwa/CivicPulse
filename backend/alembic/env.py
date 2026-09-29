import os

from sqlalchemy import create_engine

from alembic import context

config = context.config          # (no fileConfig: it would clobber the JSON logging setup)
url = os.environ["DATABASE_URL"]  # read directly so migrations don't also demand REDIS_URL


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
