"""Integration-specific fixtures.

Integration tests may touch the filesystem (via ``tmp_project``) or exercise
the full repository stack.  They should still avoid real network calls.

Includes Docker-based PostgreSQL fixtures for tests that need a real database.
"""

import subprocess
import time
import uuid

import pytest


def _is_docker_available() -> bool:
    """Check if Docker CLI is available."""
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _wait_for_postgres(url: str, timeout: int = 30) -> bool:
    """Wait for PostgreSQL to accept connections."""
    try:
        import psycopg
    except ImportError:
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = psycopg.connect(url, connect_timeout=2)
            conn.close()
            return True
        except Exception:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def docker_postgres():
    """Spin up a temporary Docker PostgreSQL container.

    Yields the DATABASE_URL. The container is removed after the session.
    Skips if Docker is not available or psycopg is not installed.
    """
    if not _is_docker_available():
        pytest.skip("Docker not available")

    try:
        import psycopg  # noqa: F401
    except ImportError:
        pytest.skip("psycopg not installed — run: uv sync --group postgres")

    container_name = f"songbook-test-pg-{uuid.uuid4().hex[:8]}"
    password = "testpass"
    port = "15433"  # Non-standard port to avoid conflicts
    db_name = "songbook_test"
    db_url = f"postgresql://postgres:{password}@localhost:{port}/{db_name}"

    # Start container
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container_name,
            "-e", f"POSTGRES_PASSWORD={password}",
            "-e", f"POSTGRES_DB={db_name}",
            "-p", f"{port}:5432",
            "postgres:16-alpine",
        ],
        check=True, capture_output=True,
    )

    try:
        if not _wait_for_postgres(db_url, timeout=30):
            pytest.fail("PostgreSQL container did not become ready in time")

        # Apply schema
        from pathlib import Path
        schema_path = (
            Path(__file__).resolve().parent.parent.parent / "scripts" / "schema.sql"
        )
        import psycopg
        conn = psycopg.connect(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(schema_path.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

        yield db_url
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
        )


@pytest.fixture()
def pg_pool(docker_postgres):
    """Create a connection pool for the temporary container."""
    from library.repositories.postgres.connection import create_pool

    pool = create_pool(conninfo=docker_postgres, min_size=1, max_size=2)
    yield pool
    pool.close()


@pytest.fixture(autouse=False)
def pg_clean_tables(pg_pool):
    """Truncate relevant tables between tests."""
    with pg_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE song_tags, songs, setlists, config, event_types CASCADE"
            )
            cur.execute("""
                INSERT INTO config (key, value) VALUES
                    ('moments_config', '{"prelúdio": 1, "ofertório": 1, "saudação": 1, "crianças": 1, "louvor": 4, "poslúdio": 1}'),
                    ('recency_decay_days', '45'),
                    ('default_weight', '3'),
                    ('energy_ordering_enabled', 'true'),
                    ('energy_ordering_rules', '{"louvor": "ascending"}'),
                    ('default_energy', '2.5')
                ON CONFLICT (key) DO NOTHING
            """)
        conn.commit()
    yield
