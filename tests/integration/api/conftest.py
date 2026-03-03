"""Fixtures for API integration tests against local Supabase.

Architecture:
  - ``supabase_instance`` (session) — parses ``supabase status`` for connection
    info.  Skips the entire session when Supabase CLI or Docker is missing.
  - ``db_conn`` (session) — raw psycopg connection for direct SQL operations
    (user/org/song setup, cleanup).
  - ``test_org`` (session) — two organisations inserted via SQL.
  - ``test_users`` (session) — five GoTrue users created via the admin API,
    each with a role in the test org.
  - ``make_client`` (function) — factory that produces a ``TestClient`` with
    ``get_current_user`` and ``get_repos`` overridden.
  - ``seed_songs`` (function) — inserts four songs with tags via SQL.
  - ``clean_test_data`` (function, autouse) — truncates mutable tables after
    each test while preserving users/orgs/memberships.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from typing import Any, Generator

import pytest

# ---------------------------------------------------------------------------
# Module-level marker — all tests in this package require Supabase
# ---------------------------------------------------------------------------
pytestmark = [pytest.mark.supabase, pytest.mark.slow]


# ── helpers ────────────────────────────────────────────────────────────────


def _run_supabase_status() -> dict[str, Any]:
    """Run ``npx supabase status -o json`` and return parsed output."""
    result = subprocess.run(
        ["npx", "supabase", "status", "-o", "json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        pytest.skip(f"supabase status failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


# ── session-scoped fixtures ────────────────────────────────────────────────


@pytest.fixture(scope="session")
def supabase_instance() -> dict[str, str]:
    """Return connection info from a running local Supabase instance.

    Yields a dict with keys: ``api_url``, ``service_role_key``, ``anon_key``,
    ``db_url``.  Skips the session if Docker or the Supabase CLI is missing.
    """
    # Check Docker
    try:
        docker = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        if docker.returncode != 0:
            pytest.skip("Docker is not running")
    except FileNotFoundError:
        pytest.skip("Docker not installed")

    # Check supabase CLI
    try:
        status = _run_supabase_status()
    except FileNotFoundError:
        pytest.skip("supabase CLI not found (install via npm)")
    except subprocess.TimeoutExpired:
        pytest.skip("supabase status timed out")

    # Parse the status output — keys vary by Supabase CLI version
    api_url = status.get("API_URL") or status.get("api_url") or status.get("API URL", "")
    service_role = (
        status.get("SERVICE_ROLE_KEY")
        or status.get("service_role_key")
        or status.get("SERVICE_ROLE KEY", "")
    )
    anon_key = (
        status.get("ANON_KEY")
        or status.get("anon_key")
        or status.get("ANON KEY", "")
    )
    db_url = status.get("DB_URL") or status.get("db_url") or status.get("DB URL", "")

    if not api_url or not service_role:
        pytest.skip(
            "Could not parse supabase status output — is supabase running? "
            f"Got keys: {list(status.keys())}"
        )

    return {
        "api_url": api_url,
        "service_role_key": service_role,
        "anon_key": anon_key,
        "db_url": db_url,
    }


@pytest.fixture(scope="session")
def db_conn(supabase_instance: dict[str, str]):
    """Raw psycopg connection for direct SQL operations.

    Uses the DB_URL from ``supabase status``.  Falls back to constructing a
    connection string from API_URL port inference when DB_URL is missing.
    """
    import psycopg

    db_url = supabase_instance["db_url"]
    if not db_url:
        # Fallback: default local Supabase DB URL
        db_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

    conn = psycopg.connect(db_url, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def test_org(db_conn) -> dict[str, str]:
    """Create two test organisations and return their IDs.

    Returns ``{"org_id": ..., "other_org_id": ...}``.
    """
    org_id = str(uuid.uuid4())
    other_org_id = str(uuid.uuid4())

    db_conn.execute(
        "INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s) ON CONFLICT (slug) DO NOTHING",
        (org_id, "Test Church", "test-church"),
    )
    db_conn.execute(
        "INSERT INTO orgs (id, name, slug) VALUES (%s, %s, %s) ON CONFLICT (slug) DO NOTHING",
        (other_org_id, "Other Church", "other-church"),
    )

    # Re-read to handle ON CONFLICT (slug already existed from a prior run)
    row = db_conn.execute(
        "SELECT id::TEXT FROM orgs WHERE slug = 'test-church'"
    ).fetchone()
    real_org_id = row[0]

    row2 = db_conn.execute(
        "SELECT id::TEXT FROM orgs WHERE slug = 'other-church'"
    ).fetchone()
    real_other_id = row2[0]

    return {"org_id": real_org_id, "other_org_id": real_other_id}


@pytest.fixture(scope="session")
def test_users(
    supabase_instance: dict[str, str],
    test_org: dict[str, str],
    db_conn,
) -> dict[str, dict[str, str]]:
    """Create test users via GoTrue admin API and assign org memberships.

    Creates five users: ``viewer``, ``editor``, ``org_admin``,
    ``other_org_user``, ``system_admin``.  Each dict contains ``id`` and
    ``email``.

    Memberships and system_admin rows are inserted via direct SQL to bypass
    RLS restrictions on the memberships table.
    """
    from supabase import create_client

    client = create_client(
        supabase_instance["api_url"],
        supabase_instance["service_role_key"],
    )

    users: dict[str, dict[str, str]] = {}
    role_map = {
        "viewer": ("viewer@test.local", "viewer", test_org["org_id"]),
        "editor": ("editor@test.local", "editor", test_org["org_id"]),
        "org_admin": ("admin@test.local", "org_admin", test_org["org_id"]),
        "other_org_user": ("other@test.local", "editor", test_org["other_org_id"]),
        "system_admin": ("sysadmin@test.local", "org_admin", test_org["org_id"]),
    }

    for key, (email, role, org_id) in role_map.items():
        # Create or re-use user via GoTrue admin API
        try:
            resp = client.auth.admin.create_user(
                {"email": email, "password": "test-password-123!", "email_confirm": True}
            )
            user_id = resp.user.id
        except Exception:
            # User may already exist from a previous session — look them up
            users_list = client.auth.admin.list_users()
            existing = [u for u in users_list if u.email == email]
            if not existing:
                raise
            user_id = existing[0].id

        users[key] = {"id": str(user_id), "email": email}

        # Upsert membership via direct SQL (bypasses RLS)
        db_conn.execute(
            """
            INSERT INTO memberships (user_id, org_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, org_id) DO UPDATE SET role = EXCLUDED.role
            """,
            (str(user_id), org_id, role),
        )

    # Mark system_admin in the system_admins table
    db_conn.execute(
        "INSERT INTO system_admins (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (users["system_admin"]["id"],),
    )

    return users


# ── function-scoped fixtures ───────────────────────────────────────────────


@pytest.fixture()
def seed_songs(
    db_conn,
    test_org: dict[str, str],
    test_users: dict[str, dict[str, str]],
) -> dict[str, str]:
    """Insert four test songs with tags.  Returns ``{title: uuid}`` mapping."""
    org_id = test_org["org_id"]
    user_id = test_users["editor"]["id"]
    songs_data = [
        ("Upbeat Song", 1, "org"),
        ("Moderate Song", 2, "org"),
        ("Reflective Song", 3, "org"),
        ("Worship Song", 4, "org"),
    ]

    result: dict[str, str] = {}
    for title, energy, visibility in songs_data:
        song_id = str(uuid.uuid4())
        db_conn.execute(
            """
            INSERT INTO songs (id, title, energy, visibility, org_id, user_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'active')
            """,
            (song_id, title, energy, visibility, org_id, user_id),
        )
        result[title] = song_id

    # Insert tags: all songs tagged for 'louvor' plus extras
    tags = [
        (result["Upbeat Song"], "louvor", 4),
        (result["Upbeat Song"], "prelúdio", 3),
        (result["Moderate Song"], "louvor", 3),
        (result["Moderate Song"], "saudação", 4),
        (result["Reflective Song"], "louvor", 5),
        (result["Reflective Song"], "ofertório", 3),
        (result["Worship Song"], "louvor", 4),
        (result["Worship Song"], "poslúdio", 2),
    ]
    for song_id, moment, weight in tags:
        db_conn.execute(
            "INSERT INTO song_tags (song_id, moment, weight) VALUES (%s, %s, %s)",
            (song_id, moment, weight),
        )

    return result


@pytest.fixture()
def make_client(
    supabase_instance: dict[str, str],
    test_org: dict[str, str],
    test_users: dict[str, dict[str, str]],
    tmp_path,
):
    """Factory that produces a ``httpx``-backed ``TestClient``.

    Usage::

        client = make_client("editor")          # editor in primary org
        client = make_client("viewer")           # viewer in primary org
        client = make_client("other_org_user")   # editor in other org
    """
    from fastapi.testclient import TestClient

    from api.app import create_app
    from api.auth import get_current_user
    from api.deps import get_repos, get_org_id

    def _factory(
        user_key: str,
        org_id: str | None = None,
    ) -> TestClient:
        user = test_users[user_key]
        resolved_org_id = org_id or test_org["org_id"]

        app = create_app()

        # Override auth — return a fake user dict (no real JWT needed)
        async def _fake_user() -> dict[str, Any]:
            return {
                "id": user["id"],
                "email": user["email"],
                "jwt": "fake-jwt-for-testing",
            }

        # Override repos — use service_role key (bypasses RLS) but real
        # Supabase PostgREST queries
        async def _fake_repos() -> Any:
            from library.repositories.supabase import SupabaseRepositoryContainer

            return SupabaseRepositoryContainer.create(
                supabase_url=supabase_instance["api_url"],
                supabase_key=supabase_instance["service_role_key"],
                user_jwt="",  # service_role doesn't need user JWT
                org_id=resolved_org_id,
                base_path=tmp_path,
            )

        # Override org_id — return the resolved org directly
        async def _fake_org_id() -> str:
            return resolved_org_id

        app.dependency_overrides[get_current_user] = _fake_user
        app.dependency_overrides[get_repos] = _fake_repos
        app.dependency_overrides[get_org_id] = _fake_org_id

        return TestClient(app)

    return _factory


@pytest.fixture(autouse=True)
def clean_test_data(db_conn, test_org: dict[str, str]) -> Generator[None, None, None]:
    """Truncate mutable tables after each test.

    Preserves session-scoped rows: ``orgs``, ``memberships``,
    ``system_admins``, ``auth.users``.
    """
    yield

    # Truncate in dependency order (children first)
    for table in [
        "share_requests",
        "song_event_types",
        "song_tags",
        "setlists",
        "event_types",
        "org_config",
        "songs",
    ]:
        db_conn.execute(f"TRUNCATE {table} CASCADE")

    # Re-seed system_config
    db_conn.execute("DELETE FROM system_config")
    db_conn.execute("""
        INSERT INTO system_config (key, value) VALUES
          ('moments_config',         '{"prelúdio": 1, "ofertório": 1, "saudação": 1, "crianças": 1, "louvor": 4, "poslúdio": 1}'),
          ('recency_decay_days',     '45'),
          ('default_weight',         '3'),
          ('energy_ordering_enabled','true'),
          ('energy_ordering_rules',  '{"louvor": "ascending"}'),
          ('default_energy',         '2.5')
        ON CONFLICT (key) DO NOTHING
    """)
