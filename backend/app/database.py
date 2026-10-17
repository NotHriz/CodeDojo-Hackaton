"""Lazy PostgreSQL engine and operation-scoped SQLModel sessions."""

from contextlib import contextmanager

from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine


class Database:
    def __init__(self, database_url: str):
        try:
            url = make_url(database_url)
            if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
                raise ValueError()
            url = url.set(drivername="postgresql+psycopg")
        except Exception:
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL.") from None
        # Engine creation does not connect. Disable prepared statements for
        # compatibility with Supabase transaction poolers; bound SQL remains used.
        self.engine = create_engine(
            url, pool_pre_ping=True, pool_size=5, max_overflow=5,
            connect_args={"connect_timeout": 5, "prepare_threshold": None},
        )

    @contextmanager
    def session(self):
        with Session(self.engine) as session:
            yield session

    @contextmanager
    def transaction(self):
        """Own one mutation transaction; commit on success, roll back on failure.

        Repositories must still acquire target/contributor locks and perform
        all vote, status and event writes inside this single context.
        """
        with self.session() as session:
            with session.begin():
                yield session

    def close(self):
        self.engine.dispose()
