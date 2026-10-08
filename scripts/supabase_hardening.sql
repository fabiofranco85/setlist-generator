-- Close the Data API surface of a Supabase project that hosts the songbook
-- schema (scripts/schema.sql).
--
-- Supabase exposes every table in `public` through PostgREST, so without this
-- the anon key could read the whole repertoire and history. Enabling RLS with
-- no policies hides every row from the `anon` and `authenticated` API roles.
-- The CLI connects as `postgres`, which has BYPASSRLS, so it is unaffected.
--
-- Idempotent. Apply right after restoring or creating the schema:
--     psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/supabase_hardening.sql

ALTER TABLE public.songs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.song_tags   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.setlists    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.config      ENABLE ROW LEVEL SECURITY;

-- Belt and braces: drop the default grants the API roles receive in `public`.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
