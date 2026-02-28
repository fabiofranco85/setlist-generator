---
paths:
  - "api/**/*.py"
  - "library/repositories/supabase/**/*.py"
  - "library/repositories/s3/**/*.py"
  - "library/sharing.py"
  - "scripts/supabase_*.sql"
---

# SaaS API Documentation

This document describes the FastAPI multi-tenant API layer, the Supabase and S3 backends, and the config injection system. This documentation is loaded when working on API, Supabase, or S3 code.

**OpenAPI spec:** [`api/openapi.yaml`](../../api/openapi.yaml) — static OpenAPI 3.1 specification for all endpoints, schemas, and security definitions. Keep it in sync when adding or modifying endpoints.

## Architecture Overview

The API wraps the existing sync `library/` modules in async FastAPI endpoints. Each request is scoped to a user (Supabase JWT) and an organization (`X-Org-Id` header). RLS policies in Supabase enforce tenant isolation automatically.

```
Client → FastAPI → Dependency Injection → Library (sync, via to_thread) → Supabase/S3
          │              │
          │         get_repos()        → SupabaseRepositoryContainer (per-request)
          │         get_generation_config() → GenerationConfig.from_config_repo()
          │         require_role()     → UserRepository.get_user_role()
          │
          └── Error handlers: ValueError→422, KeyError→404, PermissionError→403
```

**Key design decisions:**
- Sync library wrapped with `asyncio.to_thread()` (not rewritten as async)
- Per-request repository instances with user JWT and org context
- `GenerationConfig` frozen dataclass bridges module constants (CLI) and per-org overrides (SaaS)
- Song identity: titles at the API boundary, UUIDs internal to Supabase layer
- Output files: filesystem for CLI, S3 for SaaS (configurable)

## Running the API

```bash
# Install dependencies
uv sync --group saas

# Apply Supabase schema
psql $SUPABASE_DB_URL -f scripts/supabase_schema.sql
psql $SUPABASE_DB_URL -f scripts/supabase_seed.sql

# Start server
SUPABASE_URL=https://xxx.supabase.co SUPABASE_KEY=service-role-key \
  uvicorn api:create_app --factory --reload

# Health check
curl http://localhost:8000/health
```

**Environment variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase service role key |

Per-request (via headers):
- `Authorization: Bearer <jwt>` — Supabase user JWT
- `X-Org-Id: <uuid>` — Organization UUID

## Package Structure

```
api/
├── __init__.py            # Exports create_app()
├── app.py                 # FastAPI application factory
├── auth.py                # get_current_user() — Supabase JWT validation
├── deps.py                # Dependency injection (repos, config, RBAC)
├── middleware.py           # Exception-to-HTTP-status handlers
├── schemas/               # Pydantic request/response models
│   ├── songs.py           # SongCreate, SongResponse, SongUpdate, SongFork
│   ├── setlists.py        # GenerateRequest, SetlistResponse, ReplaceRequest, DeriveRequest
│   ├── event_types.py     # EventTypeCreate, EventTypeResponse, EventTypeUpdate
│   ├── sharing.py         # ShareRequest, ShareReview, ShareRequestResponse
│   └── config.py          # OrgConfigUpdate, ConfigResponse
└── routes/                # Endpoint modules (one router each)
    ├── songs.py           # CRUD + fork + search + share + transpose + info
    ├── setlists.py        # generate + list + get + replace + derive + PDF
    ├── event_types.py     # CRUD (org_admin only for writes)
    ├── labels.py          # add + rename + remove
    ├── sharing.py         # submit request + list pending + approve/reject
    ├── admin.py           # System admin endpoints
    └── config.py          # Get/update org config overrides
```

## Dependency Injection Chain

All in `api/deps.py`:

```python
# Auth: validates JWT, returns {id, email, jwt}
get_current_user(credentials) → dict

# Org context: extracts X-Org-Id header
get_org_id(header) → str

# Repositories: creates per-request Supabase-backed repos
get_repos(user, org_id) → RepositoryContainer

# Config: loads from repos with org overrides
get_generation_config(repos) → GenerationConfig

# RBAC: checks user role in org
require_role("editor", "org_admin") → dependency
require_system_admin() → dependency
```

**Usage in routes:**
```python
@router.post("/", dependencies=[Depends(require_role("editor", "org_admin"))])
async def create_something(
    repos: RepositoryContainer = Depends(get_repos),
    config: GenerationConfig = Depends(get_generation_config),
):
    result = await asyncio.to_thread(some_library_func, ...)
```

## RBAC Roles

| Role | Songs | Setlists | Event Types | Config | Sharing |
|------|-------|----------|-------------|--------|---------|
| `viewer` | read | read | read | read | — |
| `editor` | CRUD (own) | generate, replace | read | read | submit requests |
| `org_admin` | CRUD (org) | all | CRUD | read/write | submit requests |
| `system_admin` | all | all | all | all | approve/reject |

System admins bypass all role checks.

## Endpoint Reference

### Songs (`/songs`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/songs` | all | List effective library |
| GET | `/songs/search?q=...` | all | Search by title |
| GET | `/songs/{title}` | all | Get song details + chords |
| POST | `/songs` | editor+ | Create song (body: `SongCreate`) |
| PATCH | `/songs/{title}` | editor+ | Update song (body: `SongUpdate`) |
| DELETE | `/songs/{title}` | editor+ | Delete song |
| POST | `/songs/{title}/fork` | editor+ | Fork with overrides (body: `SongFork`) |
| POST | `/songs/{title}/share` | editor+ | Promote user→org visibility |
| POST | `/songs/{title}/transpose?to=G` | all | Preview transposition |
| GET | `/songs/{title}/info` | all | Usage stats + history |

### Setlists (`/setlists`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/setlists/generate` | editor+ | Generate setlist (body: `GenerateRequest`) |
| GET | `/setlists` | all | List setlists (?label, ?event_type) |
| GET | `/setlists/{date}` | all | Get setlist (?label, ?event_type) |
| POST | `/setlists/{date}/replace` | editor+ | Replace song (body: `ReplaceRequest`) |
| POST | `/setlists/{date}/derive` | editor+ | Derive variant (body: `DeriveRequest`) |
| GET | `/setlists/{date}/pdf` | all | Download PDF (?label, ?event_type) |

### Event Types (`/event-types`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/event-types` | all | List all |
| GET | `/event-types/{slug}` | all | Get one |
| POST | `/event-types` | org_admin | Create (body: `EventTypeCreate`) |
| PATCH | `/event-types/{slug}` | org_admin | Update (body: `EventTypeUpdate`) |
| DELETE | `/event-types/{slug}` | org_admin | Remove |

### Labels (`/labels`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/labels?date=...&label=...` | editor+ | Add label to setlist |
| PATCH | `/labels/{label}?date=...&new_label=...` | editor+ | Rename label |
| DELETE | `/labels/{label}?date=...` | editor+ | Remove labeled setlist |

### Sharing (`/sharing`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/sharing/request/{title}` | editor+ | Submit global share request |
| GET | `/sharing/pending` | system_admin | List pending requests |
| POST | `/sharing/{id}/review` | system_admin | Approve/reject (body: `ShareReview`) |

### Config (`/config`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/config` | all | Get effective config |
| PATCH | `/config` | org_admin | Update org overrides (body: `OrgConfigUpdate`) |

### Admin (`/admin`)

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/admin/songs/global` | system_admin | List all global songs |

## Error Handling

Library exceptions are mapped to HTTP status codes in `api/middleware.py`:

| Library Exception | HTTP Status | Response |
|-------------------|-------------|----------|
| `ValueError` | 422 | `{"detail": "..."}` |
| `KeyError` | 404 | `{"detail": "..."}` |
| `PermissionError` | 403 | `{"detail": "..."}` |
| Supabase auth error | 401 | `{"detail": "Invalid or expired token"}` |

Routes raise these exceptions naturally — the library functions already use `ValueError` for validation and `KeyError` for not-found. The middleware catches them globally.

## GenerationConfig (Config Injection)

`GenerationConfig` is a frozen dataclass in `library/config.py` that bundles all generation parameters. It replaces direct module-constant imports for per-org customization.

```python
@dataclass(frozen=True)
class GenerationConfig:
    moments_config: dict[str, int]
    recency_decay_days: int = 45
    default_weight: int = 3
    energy_ordering_enabled: bool = True
    energy_ordering_rules: dict[str, str]
    default_energy: float = 2.5

    @classmethod
    def from_defaults(cls) -> GenerationConfig: ...      # CLI path
    @classmethod
    def from_config_repo(cls, repo) -> GenerationConfig: ...  # SaaS path
```

**Config cascade** (Supabase): `org_config` → `system_config` → Python constants

**Injected functions** (all backward-compatible — no config param = module defaults):

| Module | Function | Config Parameter |
|--------|----------|-----------------|
| `selector.py` | `calculate_recency_scores()` | `recency_decay_days` |
| `ordering.py` | `apply_energy_ordering()` | `energy_ordering_enabled`, `energy_ordering_rules` |
| `loader.py` | `parse_tags()` | `default_weight` |
| `replacer.py` | `replace_song_in_setlist()`, `replace_songs_batch()`, `derive_setlist()`, `validate_replacement_request()` | `config: GenerationConfig` |
| `generator.py` | `SetlistGenerator.__init__()` | `config: GenerationConfig` |
| `generator.py` | `SetlistGenerator.from_repositories()` | `config_repo: ConfigRepository` |
| `config.py` | `canonical_moment_order()` | `reference_config` |

## Multi-Tenant Song Visibility

Songs have three visibility scopes, merged with priority user > org > global:

| Scope | Visible to | Created by |
|-------|-----------|------------|
| `global` | All orgs | System admin (via share approval) |
| `org` | Org members | Editors (promoted from user) |
| `user` | Owner only | Any editor |

**Library module:** `library/sharing.py`
- `merge_effective_library(global_songs, org_songs, user_songs)` — dict.update priority merge
- `validate_share_request(song, from_scope, to_scope)` — only widening allowed

**Supabase RLS** enforces visibility automatically via the `songs` table's SELECT policy.

## Supabase Backend

### Package: `library/repositories/supabase/`

| File | Class | Implements |
|------|-------|-----------|
| `client.py` | — | `create_supabase_client()` with JWT + org headers |
| `songs.py` | `SupabaseSongRepository` | `MultiTenantSongRepository` |
| `history.py` | `SupabaseHistoryRepository` | `HistoryRepository` |
| `config.py` | `SupabaseConfigRepository` | `ConfigRepository` (with cascade) |
| `event_types.py` | `SupabaseEventTypeRepository` | `EventTypeRepository` |
| `users.py` | `SupabaseUserRepository` | `UserRepository` |
| `share_requests.py` | `SupabaseShareRequestRepository` | `ShareRequestRepository` |
| `__init__.py` | `SupabaseRepositoryContainer` | Factory `.create()` method |

**Key patterns:**
- Songs and config are cached; history is NOT cached
- UUID ↔ title mapping built during `get_all()`, stored in `_uuid_map`
- `SupabaseConfigRepository` cascade: try org_config → system_config → Python constant
- Output always uses `FilesystemOutputRepository` (or S3 in cloud)

### Schema: `scripts/supabase_schema.sql`

11 tables with RLS: `orgs`, `memberships`, `system_admins`, `songs`, `song_tags`, `song_event_types`, `setlists`, `system_config`, `org_config`, `event_types`, `share_requests`

Org context set via `current_setting('app.org_id', true)::UUID` in RLS policies.

Seed data: `scripts/supabase_seed.sql` (system_config matching Python defaults).

## S3 Output Backend

### Package: `library/repositories/s3/`

`S3OutputRepository` implements `CloudOutputRepository`:

**Key layout:**
```
orgs/{org_id}/setlists/{event_type}/{date}_{label}.md
orgs/{org_id}/setlists/{event_type}/{date}_{label}.pdf
orgs/{org_id}/songs/{song_id}/chords.md
```

- Empty event_type → `"default"` in key
- Empty label → just `{date}` (no underscore)
- Presigned URLs with 1-hour expiry for `get_*_url()` methods
- Compatible with AWS S3, Cloudflare R2, MinIO via `endpoint_url`
- Constructor accepts optional `s3_client` for dependency injection/testing

## Library Functions Reused by API

The API reuses existing library functions rather than reimplementing:

| Function | File | Used in endpoint |
|----------|------|-----------------|
| `SetlistGenerator` | `library/generator.py` | `POST /setlists/generate` |
| `validate_replacement_request()` | `library/replacer.py` | `POST /setlists/{date}/replace` |
| `select_replacement_song()` | `library/replacer.py` | `POST /setlists/{date}/replace` |
| `replace_song_in_setlist()` | `library/replacer.py` | `POST /setlists/{date}/replace` |
| `derive_setlist()` | `library/replacer.py` | `POST /setlists/{date}/derive` |
| `find_target_setlist()` | `library/replacer.py` | `POST /setlists/{date}/replace` |
| `relabel_setlist()` | `library/labeler.py` | `POST /labels`, `PATCH /labels/{label}` |
| `format_setlist_markdown()` | `library/formatter.py` | `POST /setlists/generate` |
| `generate_setlist_pdf_bytes()` | `library/pdf_formatter.py` | `GET /setlists/{date}/pdf` |
| `transpose_content()` | `library/transposer.py` | `POST /songs/{title}/transpose` |
| `get_song_usage_history()` | `library/selector.py` | `GET /songs/{title}/info` |
| `get_days_since_last_use()` | `library/selector.py` | `GET /songs/{title}/info` |
| `filter_songs_for_event_type()` | `library/event_type.py` | Internal filtering |

## Adding a New Endpoint

1. Add Pydantic schema to `api/schemas/<module>.py` if needed
2. Add route function in `api/routes/<module>.py`:
   - Use `Depends(get_repos)` for repository access
   - Use `Depends(get_generation_config)` if generation config needed
   - Use `dependencies=[Depends(require_role(...))]` for RBAC
   - Wrap sync library calls with `await asyncio.to_thread(...)`
   - Raise `KeyError` for not-found, `ValueError` for bad input
3. The router is already registered in `api/app.py` — no wiring needed

**Example:**
```python
@router.post("/{date}/do-something", dependencies=[Depends(require_role("editor", "org_admin"))])
async def do_something(
    date: str,
    repos: RepositoryContainer = Depends(get_repos),
    config: GenerationConfig = Depends(get_generation_config),
):
    songs = await asyncio.to_thread(repos.songs.get_all)
    result = await asyncio.to_thread(library_function, songs, date)
    return {"result": result}
```

## Testing

- Unit tests: `tests/unit/test_generation_config.py`, `tests/unit/test_sharing.py`, `tests/unit/test_s3_output.py`
- API tests: `tests/api/` (with FastAPI `TestClient` and mocked repos)
- Supabase integration tests: marked `@pytest.mark.supabase`, require local Supabase
- S3 tests use `MagicMock` for the boto3 client; `pytest.importorskip("boto3")` for skip
- Coverage omits: `library/repositories/supabase/*`, `library/repositories/s3/*`, `api/*`

## Dependencies

Installed via `uv sync --group saas`:
- `supabase>=2.0` — Supabase Python client
- `boto3>=1.28` — AWS S3 / R2 / MinIO client
- `fastapi>=0.115` — Web framework
- `uvicorn>=0.30` — ASGI server
