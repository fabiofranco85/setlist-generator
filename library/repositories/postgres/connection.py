"""Connection pool management for PostgreSQL backend.

Creates and manages a psycopg connection pool shared across all repositories.
The pool is created once by PostgresRepositoryContainer and passed to each repo.
"""

import os


def create_pool(conninfo=None, min_size=1, max_size=5):
    """Create a psycopg connection pool.

    Args:
        conninfo: PostgreSQL connection string. If None, reads DATABASE_URL
                  environment variable.
        min_size: Minimum number of connections in the pool.
        max_size: Maximum number of connections in the pool.

    Returns:
        A psycopg_pool.ConnectionPool instance.

    Raises:
        ImportError: If psycopg or psycopg_pool is not installed.
        ValueError: If no connection string is provided or found in env.
    """
    try:
        from psycopg_pool import ConnectionPool
    except ImportError as e:
        raise ImportError(
            "PostgreSQL backend requires psycopg. "
            "Install with: uv sync --group postgres"
        ) from e

    if conninfo is None:
        conninfo = os.getenv("DATABASE_URL")

    if not conninfo:
        raise ValueError(
            "No database URL provided. Either pass database_url= to "
            "get_repositories() or set the DATABASE_URL environment variable."
        )

    return ConnectionPool(conninfo=conninfo, min_size=min_size, max_size=max_size)
