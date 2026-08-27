"""The PostgreSQL connection boundary for Document AI."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection

from .config import settings


class DatabaseConnectionError(RuntimeError):
    """Raised when PostgreSQL cannot be reached with the configured settings."""


@contextmanager
def get_database_connection() -> Iterator[connection]:
    """Open one short-lived database connection for a unit of RAG work."""

    try:
        database_connection = psycopg2.connect(
            **settings.database_connection_parameters,
            connect_timeout=5,
        )
    except psycopg2.OperationalError as error:
        raise DatabaseConnectionError(
            "Could not connect to PostgreSQL. Check the database settings and server."
        ) from error

    try:
        yield database_connection
    finally:
        database_connection.close()
