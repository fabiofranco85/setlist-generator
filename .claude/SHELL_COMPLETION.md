# Shell Completion Guide

This document provides comprehensive documentation for shell completion in the songbook CLI.

## Overview

The songbook CLI supports tab completion for:
- **Commands** - All CLI commands (generate, view-song, browse, setlists, weights, …)
- **Song names** - Every song in the repertoire
- **Moment names** - Service moments (prelúdio, louvor, ofertório, saudação, crianças, poslúdio)
- **Event type slugs** - Every configured event type, described by its display name
- **Musical keys** - For `--to` / `--transpose` (C, C#, Db, …, Bm, F#m)
- **Dates** - Dates of stored setlists (YYYY-MM-DD), most recent first
- **Labels** - Labels of stored setlists
- **Options** - All CLI flags and parameters

**Supported shells:** bash, zsh, fish

**Data source:** everything data-driven goes through the **repository layer**, so
completion follows `STORAGE_BACKEND` exactly like the commands do. On this repo's
default (postgres) that means songs, dates, labels, and event types all come from the
database — see "Source of Truth" in `CLAUDE.md`.

**Performance:** ~120ms for static completions, ~250-300ms when the backend is queried
(see [Performance Characteristics](#performance-characteristics)).

## Installation

### Quick Install (Recommended)

```bash
# Auto-detect shell and install
songbook install-completion

# Or specify shell manually
songbook install-completion --shell bash
songbook install-completion --shell zsh
songbook install-completion --shell fish
```

Then start a new shell:
```bash
exec zsh            # zsh
source ~/.bashrc    # bash
exec fish           # fish
```

**What the zsh installer does** (and why it differs from bash):

1. Writes the completion function to `~/.zsh/completions/_songbook`
2. Ensures `~/.zsh/completions` is on `fpath`, **prepending** the line to `.zshrc`
   (it has to precede `compinit`, which only scans `fpath` as it stands when it runs)
3. Removes the legacy `~/.songbook-complete.zsh` + its `source` line, if present
4. Backs up your previous `.zshrc` to `~/.zshrc.songbook-backup`
5. Deletes `~/.zcompdump*` so the next shell rebuilds its completion cache

Steps 3 and 5 exist because of the failure mode described in
[Completion silently stopped working (zsh)](#completion-silently-stopped-working-zsh).

### Manual Installation

#### Bash

```bash
# Generate completion script
_SONGBOOK_COMPLETE=bash_source songbook > ~/.songbook-complete.bash

# Add to ~/.bashrc
echo 'source ~/.songbook-complete.bash' >> ~/.bashrc

# Activate
source ~/.bashrc
```

#### Zsh

Install as an **autoloaded function on `fpath`** — do not `source` it (see
[Troubleshooting](#completion-silently-stopped-working-zsh)):

```bash
# Generate the completion function into a directory on fpath
mkdir -p ~/.zsh/completions
_SONGBOOK_COMPLETE=zsh_source songbook > ~/.zsh/completions/_songbook

# Make sure that directory is on fpath BEFORE compinit runs.
# Add near the TOP of ~/.zshrc (above oh-my-zsh / compinit):
#   fpath=("$HOME/.zsh/completions" $fpath)

# Drop the cached dump so compinit rediscovers the new function
rm -f ~/.zcompdump*

# Activate
exec zsh
```

#### Fish

```bash
# Generate and install completion script
_SONGBOOK_COMPLETE=fish_source songbook > ~/.config/fish/completions/songbook.fish

# Fish auto-loads completions - just restart
exec fish
```

## Usage Examples

### Command Completion

```bash
songbook <TAB>
# Shows every registered command: add, browse, delete, edit, event-type, generate,
# info, install-completion, label, list-moments, markdown, pdf, remove, replace,
# setlists, transpose, view-setlist, view-song, weights, youtube
# (plus the developer-only maintenance subcommands).

songbook gen<TAB>
# Completes to: songbook generate
```

### Song Name Completion

```bash
songbook view-song <TAB>
# Shows every song in the repertoire, alphabetically

songbook view-song Oce<TAB>
# Completes to the common prefix: songbook view-song Oceano
# (a second TAB lists "Oceano de Paz" and "Oceanos")

# Case-insensitive, substring matching
songbook view-song santo<TAB>       # matches "Santo Pra Sempre"
songbook view-song OU<TAB>          # matches "Ousado Amor"
```

### Moment Name Completion

```bash
songbook replace --moment lou<TAB>   # → louvor
songbook remove --moment pre<TAB>    # → prelúdio
songbook weights -m <TAB>            # lists every moment
```

### Event Type Completion

```bash
songbook generate -e <TAB>
# Lists every configured event type with its display name as the description:
#   ceia          -- Culto (Ceia)
#   jejumeoracao  -- Semana de Jejum e Oração
#   main          -- Culto

songbook event-type moments jeju<TAB>   # → jejumeoracao
```

### Date and Label Completion

```bash
songbook view-setlist --date <TAB>
# Dates of stored setlists, most recent first

songbook view-setlist --date 2026-0<TAB>   # prefix-filtered
songbook view-setlist --label ev<TAB>      # → evening
```

### Combined Completion

```bash
songbook replace --moment <TAB>                                  # moment
songbook replace --moment louvor --with <TAB>                    # song name
songbook replace --moment louvor --with "Oceanos" --date <TAB>   # date
```

## What Gets Completed

### Completion Points

| Command | Parameter | Completion Type |
|---------|-----------|-----------------|
| `info` | `SONG_NAME` | Song names |
| `view-song` | `SONG_NAME` | Song names |
| `view-song` | `--transpose` / `-t` | Musical keys |
| `edit` | `SONG_NAME` | Song names |
| `transpose` | `SONG_NAME` | Song names |
| `transpose` | `--to` | Musical keys |
| `replace` | `--moment`, `--with` | Moment names, song names |
| `remove` | `--moment` | Moment names |
| `weights` | `--moment` / `-m` | Moment names |
| `event-type edit\|remove\|moments` | `SLUG` | Event type slugs |
| *all setlist commands* | `--date` | Dates |
| *all setlist commands* | `--label` / `-l` | Labels |
| *all commands accepting one* | `--event-type` / `-e` | Event type slugs |

"All setlist commands" = `generate`, `view-setlist`, `replace`, `remove`, `label`,
`delete`, `pdf`, `markdown`, `youtube create`, `youtube links`.

`browse` and `setlists` take no parameters — they are fully interactive.

### Nothing Is Completed After an Unknown Command

`songbook songs <TAB>` offers nothing, and neither does any other typo'd
command name. That takes a deliberate guard, because Click's default is the
opposite.

During completion Click parses with `resilient_parsing=True`, so a TAB press
can never crash or prompt. That flag also suppresses the "No such command"
failure in `Group.resolve_command`, so `shell_completion._resolve_context`
drops the unrecognized token and returns the *root* group's context. Completion
then offers the root's whole command list, filtered by whatever was typed:
`songbook songs a<TAB>` used to expand to `songbook songs add`, a command that
never existed, which then failed at real parse time with a confusing error.

`SongbookGroup` in `cli/completions.py` checks the leftover arguments Click
left on the context. When the first one cannot be a command (it is not an
option, and `get_command` does not know it), completion returns nothing.
`group_class = type` makes subgroups declared with `@<group>.group()` inherit
the guard, and `event-type`, declared standalone, passes `cls=SongbookGroup`.

This is upstream Click behavior (reproduced on 8.3.1 with an 8-line app), not
something specific to this CLI.

### Deliberately Not Completed

| Parameter | Why |
|-----------|-----|
| `add TITLE` | Names a song that does not exist yet |
| `event-type add SLUG` | Names an event type that does not exist yet |
| `generate --desired` / `--override`, `add --tags` | Composite comma-separated values (`"moment:song1,song2"`), where completing a fragment mid-string is more disruptive than helpful |
| `--output-dir` / `--history-dir` | Plain string options; no directory completion is wired |

### Song Name Completion

- **Source:** `repos.songs.get_all()` via the active backend
- **Features:** case-insensitive, partial substring matching, alphabetically sorted
- **Example:** "oce" matches "Oceanos", "OU" matches "Ousado Amor"

### Moment Name Completion

- **Source:** `library/config.py` (`MOMENTS_CONFIG`)
- **Values:** `prelúdio`, `louvor`, `ofertório`, `saudação`, `crianças`, `poslúdio`
- **Features:** case-insensitive substring matching
- **Note:** the global config, not the moments of the event type named earlier on the
  same command line

### Event Type Completion

- **Source:** `repos.event_types.get_all()` via the active backend
- **Features:** prefix matching on the slug, sorted alphabetically; each slug is
  described by its display name in shells that show descriptions (zsh, fish)

### Musical Key Completion

- **Source:** Static list maintained by `cli/completions.py:complete_key_names`
- **Coverage:** All major and minor roots used in the chord sheets (C, C#, Db, …, Bm, F#m)

### Date Completion

- **Source:** `repos.history.get_all()` via the active backend
- **Format:** YYYY-MM-DD
- **Features:** sorted descending (most recent first), prefix filtering
- **Note:** a date is offered once no matter how many labeled variants it has; pick the
  variant with `--label`

### Label Completion

- **Source:** the `label` field of stored setlists, via the active backend
- **Use:** wherever `--label` / `-l` is accepted

### Command Completion

- **Source:** Click CLI framework (built-in)
- **Coverage:** Every subcommand registered in `cli/main.py`

## Troubleshooting

### Completion silently stopped working (zsh)

**Symptom:** TAB does nothing at all — no completions, no error. It used to work.

**Cause:** something appended a second `compinit` to your `.zshrc` *after* the line
that registered songbook's completion. `compdef` writes into the `_comps` array;
`compinit` **rebuilds that array from scratch**. Any registration made before a later
`compinit` is silently discarded:

```zsh
source $ZSH/oh-my-zsh.sh                  # compinit #1 — compdef becomes available
source ~/.songbook-complete.zsh           # compdef _songbook_completion songbook  ✅
...
autoload -Uz compinit && compinit -C      # appended by some other installer  ❌ wipes it
```

**Diagnose:**

```bash
zsh -i -c 'print -r -- "${+functions[_songbook_completion]} [${_comps[songbook]}]"'
# "1 []"  -> function loaded but registration wiped  (this bug)
# "0 [_songbook]" or "[_songbook]" -> correctly installed on fpath
```

**Fix:** re-run `songbook install-completion --shell zsh`. The installer switched from
sourcing to an `fpath` install (`~/.zsh/completions/_songbook`), which every `compinit`
rediscovers — the same mechanism `git`, `kubectl`, and `deno` completions use.

### Completion Not Working

1. **Verify installation:**
   ```bash
   ls -l ~/.zsh/completions/_songbook              # zsh
   ls -l ~/.songbook-complete.bash                 # bash
   ls -l ~/.config/fish/completions/songbook.fish  # fish
   ```

2. **Verify the rc file wiring:**
   ```bash
   grep -n '.zsh/completions' ~/.zshrc   # zsh: must appear BEFORE any compinit line
   grep -n songbook ~/.bashrc            # bash: source line
   ```

3. **Restart the shell:**
   ```bash
   exec zsh           # zsh
   source ~/.bashrc   # bash
   exec fish          # fish
   ```

4. **Test the completion backend directly** (bypasses the shell entirely):
   ```bash
   _SONGBOOK_COMPLETE=zsh_complete COMP_WORDS="songbook view-song Oce" COMP_CWORD=2 songbook
   # Should print: plain \n Oceanos \n _ ...
   ```
   If this prints candidates but TAB does not, the bug is in the shell wiring, not in
   the CLI.

### Empty Completion Results

**Symptom:** TAB shows nothing for songs, dates, labels, or event types (but commands
and flags still complete)

Completion callbacks **never raise** — they return an empty list on any error, so a
misconfigured backend looks exactly like an empty repertoire. Check the backend:

1. **Backend reachable?**
   ```bash
   songbook view-song --list   # same data path, but shows real errors
   ```

2. **`DATABASE_URL` set?** postgres is the default backend and requires it. The repo
   `.env` supplies it, and `cli/main.py:_load_dotenv` loads that file at import time —
   which is why completion works from any directory.

3. **Nothing stored yet?** Date and label completion stay empty until at least one
   setlist exists.

### Slow Completion

**Expected:** ~120ms for static completions, ~250-300ms when the backend is queried.

Each TAB spawns a fresh Python process and (for song/date/label/event-type
completions) opens a database connection, so per-press cost is dominated by process
startup and the round trip, not by the size of your repertoire.

### Completion Shows Wrong Data

Completion honors `--history-dir` / `--output-dir` and `SETLIST_HISTORY_DIR` /
`SETLIST_OUTPUT_DIR`, but these only affect the **filesystem** backend. On postgres,
data comes from `DATABASE_URL` and those options do not change what is offered.

```bash
STORAGE_BACKEND=filesystem SETLIST_HISTORY_DIR=/custom/history songbook view-setlist --date <TAB>
```

### Aliases

Completion is bound to the command name `songbook`. An alias (e.g. `alias sb=songbook`)
does not inherit it. In zsh you can add this after the alias:

```zsh
compdef sb=songbook
```

### Accents/Unicode Issues

**Symptom:** Moment names with accents (prelúdio, ofertório) don't complete

```bash
echo $LANG                    # should be en_US.UTF-8 or similar
export LANG=en_US.UTF-8       # add to ~/.zshrc / ~/.bashrc if missing
export LC_ALL=en_US.UTF-8
```

## Uninstallation

### Zsh

```bash
rm ~/.zsh/completions/_songbook
rm -f ~/.zcompdump*
# Optionally remove the fpath line from ~/.zshrc
exec zsh
```

### Bash

```bash
rm ~/.songbook-complete.bash
# Remove the matching `source` line from ~/.bashrc
```

### Fish

```bash
rm ~/.config/fish/completions/songbook.fish
exec fish
```

## Technical Details

### How It Works

1. **Click framework:** uses Click 8.3's built-in shell completion system
2. **Environment variable:** the shell runs `_SONGBOOK_COMPLETE=<shell>_complete songbook`
   when TAB is pressed
3. **Group class:** the root group and `event-type` use
   `cli/completions.py:SongbookGroup`, which suppresses completion after an
   unknown command name (see above)
4. **Completion functions:** custom callbacks in `cli/completions.py` generate suggestions:
   - `complete_song_names()` - songs from `repos.songs.get_all()`
   - `complete_moment_names()` - `MOMENTS_CONFIG` keys from `library/config.py`
   - `complete_key_names()` - static list of supported musical keys
   - `complete_history_dates()` - dates from `repos.history.get_all()`
   - `complete_history_labels()` - labels from `repos.history.get_all()`
   - `complete_event_type_slugs()` - slugs from `repos.event_types.get_all()`
5. **Shared plumbing:** `_get_repositories(ctx)` builds the repository container,
   forwarding `--history-dir` / `--output-dir` when they are already parsed on the
   Click context. Imports are deferred so the TAB round trip stays cheap.
6. **Return format:** functions return `CompletionItem` objects (with `help=` where a
   description adds value, e.g. event type names)
6. **Shell integration:** shell-specific scripts parse the output and display suggestions

### Error Handling

All completion functions use **graceful degradation:**

```python
try:
    # Load data and generate completions
    ...
except Exception:
    # Return empty list instead of raising exception
    return []
```

**Why:** a traceback printed by a completion hook corrupts the user's command line.
Returning nothing keeps the CLI usable when the backend is unreachable. The cost is
that a misconfiguration is indistinguishable from "no data" — see
[Empty Completion Results](#empty-completion-results).

### Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Command completion | ~120ms | Click built-in; Python startup only |
| Moment name completion | ~170ms | Static list from config |
| Event type completion | ~250ms | One backend query |
| Song name completion | ~280ms | One backend query |
| Date / label completion | ~290ms | One backend query |

Cost is dominated by interpreter startup plus one database round trip; it is
effectively flat in the size of the repertoire and history.

### Dependencies

**Core:**
- Python 3.12+
- Click 8.3+ (already in project)
- Whatever the active `STORAGE_BACKEND` needs (postgres: `psycopg`, `DATABASE_URL`)

### Tests

- `tests/unit/test_completions.py` - callback behavior against fake repositories, plus a
  structural guard that walks the whole Click command tree and asserts every
  `--date` / `--label` / `--moment` / `--event-type` / song argument actually completes.
  **A new command with an uncompleted option fails that test.**
- `tests/unit/test_completion_install.py` - the zsh installer: fpath placement, ordering
  relative to `compinit`, idempotence, cache invalidation, legacy cleanup.

## FAQ

**Q: Does completion work for all commands?**
A: Yes. Commands are completed by Click (built-in). Songs, moments, keys, dates, labels,
and event types use the custom callbacks above.

**Q: Does completion work offline?**
A: It works wherever the configured backend is reachable. On postgres that means the
database must be reachable; on the filesystem backend it is fully local.

**Q: What if I have multiple songbook projects?**
A: Completion resolves data through the active backend, and `_load_dotenv()` reads the
`.env` next to the installed package — so it reflects that project regardless of your
current directory.

**Q: Can I customize completion behavior?**
A: Yes. Edit `cli/completions.py`. For example, you could filter songs by tag or sort
dates ascending.

## See Also

- **Project Documentation:** CLAUDE.md
- **CLI Reference:** .claude/rules/cli.md
- **Architecture:** .claude/rules/core-architecture.md
- **Click Completion Docs:** https://click.palletsprojects.com/en/stable/shell-completion/
