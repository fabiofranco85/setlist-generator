#!/usr/bin/env sh
# Dump the songbook database (DATABASE_URL from .env) into .backups/.
#
# Produces the same plain-SQL, --clean --if-exists --no-owner format that
# scripts/reconstruct_from_outputs.py assumes for a restore:
#     gunzip -c .backups/songbook-<stamp>.sql.gz | psql "$DATABASE_URL" -v ON_ERROR_STOP=1 --single-transaction
#
# pg_dump must be at least as new as the server. Homebrew's postgresql@14
# client refuses a Postgres 15/17 server; use `brew install libpq` and put
# its bin first on PATH, or run it through Docker:
#     docker run --rm postgres:17 pg_dump "$DATABASE_URL" ... | gzip > ...
set -eu
cd "$(dirname "$0")/.."
set -a
. ./.env
set +a
mkdir -p .backups
out=".backups/songbook-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
pg_dump "$DATABASE_URL" --schema=public --clean --if-exists --no-owner --no-privileges | gzip > "$out"
echo "$out"
