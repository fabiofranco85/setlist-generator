# Design: `songbook add` — add a new song to the repertoire

**Date:** 2026-06-23
**Status:** Approved

## Goal

Give users a first-class way to add a new song to their repertoire from the
CLI — the natural mirror of `songbook edit`. The command collects the song's
metadata through interactive prompts, persists it to the active storage
backend, then opens the user's editor on the new chord sheet.

## Motivation

Today a new song can only be added by hand-editing `database.csv` (filesystem)
or inserting rows directly (postgres/supabase). `songbook edit` already lets a
user open a song's chord file in their editor; there is no equivalent "create
a new song" entry point. This closes that gap.

## New repository capability

Add `add(song: Song) -> None` to the `SongRepository` protocol
(`library/repositories/protocols.py`). Contract:

- Persists the full song: metadata (title, energy, youtube_url, event_types),
  tags (`{moment: weight}`), and content (chord sheet).
- Raises `ValueError` if a song with the same title already exists.
- Invalidates the in-memory cache.

Implementations (mirrors how `update_tags` / `update_youtube` were rolled out):

- **Filesystem** (`repositories/filesystem/songs.py`): append a row to
  `database.csv`, preserving the existing column order and only adding the
  optional `youtube` / `event_types` columns when the song needs them; write
  the chord file `chords/<title>.md` from `song.content`.
- **Postgres** (`repositories/postgres/songs.py`): `INSERT` into `songs` plus
  one `INSERT` per tag into `song_tags`, in a single transaction; pre-check the
  title and raise `ValueError` on conflict.
- **Supabase** (`repositories/supabase/songs.py`): thin `add(song)` delegating
  to the existing `create(song)` so the type keeps conforming to the protocol.
  The CLI never targets supabase (that is the API's domain).

## CLI command — `cli/commands/add.py`

`run(title, energy, tags, youtube, event_types, editor, no_edit)`:

1. **Title** — positional arg or prompt; reject empty; if it already exists,
   error and suggest `songbook edit`.
2. **Energy** — `--energy` or prompt; integer 1–4, re-prompt on invalid.
3. **Moments/tags** — `--tags "louvor(5),prelúdio"` or prompt; parsed by
   `library.loader.parse_tags`; **at least one moment required**; weights
   1–10; re-prompt on invalid.
4. **YouTube** — `--youtube` or prompt; blank skips; a non-empty value is
   validated with `library.youtube.extract_video_id` and re-prompts if it is
   not a recognized YouTube URL.
5. **Event-type binding** — `--event-type` / `-e`, repeatable, flag only
   (no prompt — advanced/rare, keeps the flow short).
6. Build a stub chord sheet `### {title} ()\n\n`, then `repos.songs.add(...)`.
7. Unless `--no-edit`: open the editor on the chord sheet, reusing `edit`'s
   machinery (`resolve_editor`, `_edit_filesystem` / `_edit_via_tempfile`,
   GUI-editor auto-wait). The song already exists at this point, so quitting
   the editor without typing still leaves a valid (stub) song.

**Non-TTY behavior** (mirrors `weights`): works fully from flags; if a required
field is missing and there is no TTY to prompt, error clearly; the editor step
is skipped when non-interactive.

### Flags

- `TITLE` — optional positional
- `--energy` INT
- `--tags` TEXT
- `--youtube` TEXT
- `--event-type` / `-e` — repeatable
- `--editor` TEXT (same semantics as `edit`)
- `--no-edit` — create the record without opening the editor

## Reuse (no duplication)

- `library.loader.parse_tags` for tag parsing
- `library.youtube.extract_video_id` for URL validation
- `cli.commands.edit`: `resolve_editor`, `_edit_filesystem`,
  `_edit_via_tempfile` for the editor step
- `_is_interactive()` TTY pattern from `cli.commands.weights`

## Testing (TDD)

- Filesystem `add` unit test: writes the CSV row + chord file, rejects a
  duplicate title, preserves existing columns.
- Postgres `add` integration test (`postgres` marker): inserts song + tags,
  duplicate → `ValueError`.
- CLI integration test: flags-only create succeeds; duplicate errors;
  missing-moment rejected; `--no-edit` skips the editor.

## Documentation (same commit)

- `CLAUDE.md` Basic Usage
- New `### songbook add` section in `.claude/rules/cli.md`
- `development.md` (the new repository method) and `core-architecture.md`
  repository-methods list
- `main.py` group help (Core Commands)

## Out of scope (YAGNI)

- No key prompt (the key lives in the chord heading, edited in step 7).
- No event-type prompt (flag only).
- No edit-metadata or delete-song commands (separate features).
