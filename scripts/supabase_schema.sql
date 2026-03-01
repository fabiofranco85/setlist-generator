-- =============================================================================
-- Supabase Multi-Tenant Schema for Church Worship Setlist Generator
-- =============================================================================
--
-- This schema supports a multi-tenant SaaS deployment on Supabase where each
-- church (organization) has isolated data with row-level security (RLS).
--
-- Run with:
--   psql $DATABASE_URL -f scripts/supabase_schema.sql
--
-- Conventions:
--   - All tables have RLS enabled.
--   - Per-connection org context is set via:
--       SET app.org_id = '<uuid>';
--     and read via:
--       current_setting('app.org_id', true)::UUID
--   - auth.uid() returns the current Supabase-authenticated user ID.
--   - Visibility layers: global (all users), org (org members), user (owner only).
--
-- =============================================================================


-- ---------------------------------------------------------------------------
-- 1. Helper: updated_at trigger function
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ---------------------------------------------------------------------------
-- 2. Tables
-- ---------------------------------------------------------------------------

-- Organizations
CREATE TABLE orgs (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL,
  slug       TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- User-org memberships with role-based access
CREATE TABLE memberships (
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  org_id     UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  role       TEXT NOT NULL CHECK (role IN ('org_admin', 'editor', 'viewer')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, org_id)
);

-- System-wide administrators (bypass org-level restrictions)
CREATE TABLE system_admins (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Songs with layered visibility (global / org / user)
CREATE TABLE songs (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title          TEXT NOT NULL,
  energy         REAL NOT NULL CHECK (energy >= 1 AND energy <= 4),
  youtube_url    TEXT DEFAULT '',
  visibility     TEXT NOT NULL DEFAULT 'user'
                   CHECK (visibility IN ('global', 'org', 'user')),
  org_id         UUID REFERENCES orgs(id) ON DELETE CASCADE,
  user_id        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  parent_id      UUID REFERENCES songs(id) ON DELETE SET NULL,
  content_s3_key TEXT,
  status         TEXT NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active', 'pending_review', 'rejected')),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (title, org_id, user_id, visibility)
);

-- Song moment/weight associations
CREATE TABLE song_tags (
  song_id UUID NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
  moment  TEXT NOT NULL,
  weight  INT  NOT NULL DEFAULT 3 CHECK (weight >= 1 AND weight <= 10),
  UNIQUE (song_id, moment)
);

-- Song event type bindings (empty = available for all types)
CREATE TABLE song_event_types (
  song_id         UUID NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
  event_type_slug TEXT NOT NULL,
  PRIMARY KEY (song_id, event_type_slug)
);

-- Generated setlists with org ownership
CREATE TABLE setlists (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  date       DATE NOT NULL,
  label      TEXT NOT NULL DEFAULT '',
  event_type TEXT NOT NULL DEFAULT '',
  moments    JSONB NOT NULL,
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  updated_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (org_id, date, label, event_type)
);

-- System-wide configuration (defaults for all orgs)
CREATE TABLE system_config (
  key   TEXT PRIMARY KEY,
  value JSONB NOT NULL
);

-- Per-org configuration overrides
CREATE TABLE org_config (
  org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  key    TEXT NOT NULL,
  value  JSONB NOT NULL,
  UNIQUE (org_id, key)
);

-- Org-scoped event types with custom moments config
CREATE TABLE event_types (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  slug        TEXT NOT NULL,
  name        TEXT NOT NULL,
  description TEXT DEFAULT '',
  moments     JSONB NOT NULL,
  UNIQUE (org_id, slug)
);

-- Song share request workflow (user → org or org → global)
CREATE TABLE share_requests (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  song_id      UUID NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
  org_id       UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
  requested_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'approved', 'rejected')),
  reviewer_id  UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  review_note  TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at  TIMESTAMPTZ
);


-- ---------------------------------------------------------------------------
-- 3. Triggers: auto-update updated_at
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_songs_updated_at
  BEFORE UPDATE ON songs
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_setlists_updated_at
  BEFORE UPDATE ON setlists
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX idx_songs_org_id       ON songs(org_id);
CREATE INDEX idx_songs_visibility   ON songs(visibility);
CREATE INDEX idx_song_tags_song_id  ON song_tags(song_id);
CREATE INDEX idx_song_tags_moment   ON song_tags(moment);
CREATE INDEX idx_setlists_org_date  ON setlists(org_id, date);
CREATE INDEX idx_memberships_user   ON memberships(user_id);
CREATE INDEX idx_memberships_org    ON memberships(org_id);
CREATE INDEX idx_share_requests_pending
  ON share_requests(status) WHERE status = 'pending';


-- ---------------------------------------------------------------------------
-- 5. Row-Level Security (RLS)
-- ---------------------------------------------------------------------------
-- All policies assume:
--   - auth.uid() returns the authenticated Supabase user ID.
--   - current_setting('app.org_id', true)::UUID returns the active org
--     context set at connection time by the application layer.
-- ---------------------------------------------------------------------------

ALTER TABLE orgs            ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships     ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_admins   ENABLE ROW LEVEL SECURITY;
ALTER TABLE songs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE song_tags       ENABLE ROW LEVEL SECURITY;
ALTER TABLE song_event_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE setlists        ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_config   ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_config      ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_types     ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_requests  ENABLE ROW LEVEL SECURITY;


-- ---- orgs ----

-- Users can see orgs they belong to
CREATE POLICY orgs_select ON orgs FOR SELECT USING (
  id IN (SELECT org_id FROM memberships WHERE user_id = auth.uid())
);


-- ---- memberships ----

-- Users can see their own memberships
CREATE POLICY memberships_select_own ON memberships FOR SELECT USING (
  user_id = auth.uid()
);

-- Org admins can see all memberships in their org
CREATE POLICY memberships_select_admin ON memberships FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = memberships.org_id
      AND m.role = 'org_admin'
  )
);

-- Org admins can insert memberships for their org
CREATE POLICY memberships_insert ON memberships FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = memberships.org_id
      AND m.role = 'org_admin'
  )
);

-- Org admins can update memberships in their org
CREATE POLICY memberships_update ON memberships FOR UPDATE USING (
  EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = memberships.org_id
      AND m.role = 'org_admin'
  )
);

-- Org admins can delete memberships in their org
CREATE POLICY memberships_delete ON memberships FOR DELETE USING (
  EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = memberships.org_id
      AND m.role = 'org_admin'
  )
);


-- ---- system_admins ----

-- Only system admins can see the system_admins table
CREATE POLICY system_admins_select ON system_admins FOR SELECT USING (
  user_id = auth.uid()
);


-- ---- songs ----

-- Layered visibility: global songs, org songs for current org, own user songs
CREATE POLICY songs_select ON songs FOR SELECT USING (
  visibility = 'global'
  OR (visibility = 'org' AND org_id = current_setting('app.org_id', true)::UUID)
  OR (visibility = 'user' AND user_id = auth.uid())
);

-- Users can insert songs owned by themselves within their active org
CREATE POLICY songs_insert ON songs FOR INSERT WITH CHECK (
  user_id = auth.uid()
  AND org_id = current_setting('app.org_id', true)::UUID
);

-- Song owner or org admin can update
CREATE POLICY songs_update ON songs FOR UPDATE USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = songs.org_id
      AND m.role = 'org_admin'
  )
);

-- Song owner or org admin can delete
CREATE POLICY songs_delete ON songs FOR DELETE USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = songs.org_id
      AND m.role = 'org_admin'
  )
);


-- ---- song_tags ----

-- Readable if the parent song is readable (piggybacks on songs policy)
CREATE POLICY song_tags_select ON song_tags FOR SELECT USING (
  EXISTS (SELECT 1 FROM songs s WHERE s.id = song_tags.song_id)
);

-- Writable if the user owns or is admin of the parent song's org
CREATE POLICY song_tags_insert ON song_tags FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM songs s
    WHERE s.id = song_tags.song_id
      AND (s.user_id = auth.uid()
           OR EXISTS (
             SELECT 1 FROM memberships m
             WHERE m.user_id = auth.uid()
               AND m.org_id = s.org_id
               AND m.role = 'org_admin'
           ))
  )
);

CREATE POLICY song_tags_update ON song_tags FOR UPDATE USING (
  EXISTS (
    SELECT 1 FROM songs s
    WHERE s.id = song_tags.song_id
      AND (s.user_id = auth.uid()
           OR EXISTS (
             SELECT 1 FROM memberships m
             WHERE m.user_id = auth.uid()
               AND m.org_id = s.org_id
               AND m.role = 'org_admin'
           ))
  )
);

CREATE POLICY song_tags_delete ON song_tags FOR DELETE USING (
  EXISTS (
    SELECT 1 FROM songs s
    WHERE s.id = song_tags.song_id
      AND (s.user_id = auth.uid()
           OR EXISTS (
             SELECT 1 FROM memberships m
             WHERE m.user_id = auth.uid()
               AND m.org_id = s.org_id
               AND m.role = 'org_admin'
           ))
  )
);


-- ---- song_event_types ----

-- Same access rules as song_tags (follows parent song)
CREATE POLICY song_event_types_select ON song_event_types FOR SELECT USING (
  EXISTS (SELECT 1 FROM songs s WHERE s.id = song_event_types.song_id)
);

CREATE POLICY song_event_types_insert ON song_event_types FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM songs s
    WHERE s.id = song_event_types.song_id
      AND (s.user_id = auth.uid()
           OR EXISTS (
             SELECT 1 FROM memberships m
             WHERE m.user_id = auth.uid()
               AND m.org_id = s.org_id
               AND m.role = 'org_admin'
           ))
  )
);

CREATE POLICY song_event_types_update ON song_event_types FOR UPDATE USING (
  EXISTS (
    SELECT 1 FROM songs s
    WHERE s.id = song_event_types.song_id
      AND (s.user_id = auth.uid()
           OR EXISTS (
             SELECT 1 FROM memberships m
             WHERE m.user_id = auth.uid()
               AND m.org_id = s.org_id
               AND m.role = 'org_admin'
           ))
  )
);

CREATE POLICY song_event_types_delete ON song_event_types FOR DELETE USING (
  EXISTS (
    SELECT 1 FROM songs s
    WHERE s.id = song_event_types.song_id
      AND (s.user_id = auth.uid()
           OR EXISTS (
             SELECT 1 FROM memberships m
             WHERE m.user_id = auth.uid()
               AND m.org_id = s.org_id
               AND m.role = 'org_admin'
           ))
  )
);


-- ---- setlists ----

-- Org members can read setlists for their active org
CREATE POLICY setlists_select ON setlists FOR SELECT USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = setlists.org_id
  )
);

-- Editors and org admins can create setlists
CREATE POLICY setlists_insert ON setlists FOR INSERT WITH CHECK (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = setlists.org_id
      AND m.role IN ('org_admin', 'editor')
  )
);

-- Creator or org admin can update setlists
CREATE POLICY setlists_update ON setlists FOR UPDATE USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND (
    created_by = auth.uid()
    OR EXISTS (
      SELECT 1 FROM memberships m
      WHERE m.user_id = auth.uid()
        AND m.org_id = setlists.org_id
        AND m.role = 'org_admin'
    )
  )
);

-- Creator or org admin can delete setlists
CREATE POLICY setlists_delete ON setlists FOR DELETE USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND (
    created_by = auth.uid()
    OR EXISTS (
      SELECT 1 FROM memberships m
      WHERE m.user_id = auth.uid()
        AND m.org_id = setlists.org_id
        AND m.role = 'org_admin'
    )
  )
);


-- ---- system_config ----

-- Readable by all authenticated users
CREATE POLICY system_config_select ON system_config FOR SELECT USING (
  auth.uid() IS NOT NULL
);

-- Only system admins can write
CREATE POLICY system_config_insert ON system_config FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM system_admins sa WHERE sa.user_id = auth.uid())
);

CREATE POLICY system_config_update ON system_config FOR UPDATE USING (
  EXISTS (SELECT 1 FROM system_admins sa WHERE sa.user_id = auth.uid())
);

CREATE POLICY system_config_delete ON system_config FOR DELETE USING (
  EXISTS (SELECT 1 FROM system_admins sa WHERE sa.user_id = auth.uid())
);


-- ---- org_config ----

-- Org members can read their org's config
CREATE POLICY org_config_select ON org_config FOR SELECT USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = org_config.org_id
  )
);

-- Org admins can write their org's config
CREATE POLICY org_config_insert ON org_config FOR INSERT WITH CHECK (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = org_config.org_id
      AND m.role = 'org_admin'
  )
);

CREATE POLICY org_config_update ON org_config FOR UPDATE USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = org_config.org_id
      AND m.role = 'org_admin'
  )
);

CREATE POLICY org_config_delete ON org_config FOR DELETE USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = org_config.org_id
      AND m.role = 'org_admin'
  )
);


-- ---- event_types ----

-- Org members can read their org's event types
CREATE POLICY event_types_select ON event_types FOR SELECT USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = event_types.org_id
  )
);

-- Org admins can manage event types
CREATE POLICY event_types_insert ON event_types FOR INSERT WITH CHECK (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = event_types.org_id
      AND m.role = 'org_admin'
  )
);

CREATE POLICY event_types_update ON event_types FOR UPDATE USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = event_types.org_id
      AND m.role = 'org_admin'
  )
);

CREATE POLICY event_types_delete ON event_types FOR DELETE USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = event_types.org_id
      AND m.role = 'org_admin'
  )
);


-- ---- share_requests ----

-- Org members can see share requests for their org
CREATE POLICY share_requests_select_org ON share_requests FOR SELECT USING (
  org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = share_requests.org_id
  )
);

-- System admins can see all share requests (for review)
CREATE POLICY share_requests_select_admin ON share_requests FOR SELECT USING (
  EXISTS (SELECT 1 FROM system_admins sa WHERE sa.user_id = auth.uid())
);

-- Org members can submit share requests
CREATE POLICY share_requests_insert ON share_requests FOR INSERT WITH CHECK (
  requested_by = auth.uid()
  AND org_id = current_setting('app.org_id', true)::UUID
  AND EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.user_id = auth.uid()
      AND m.org_id = share_requests.org_id
  )
);

-- System admins can update share requests (approve/reject)
CREATE POLICY share_requests_update ON share_requests FOR UPDATE USING (
  EXISTS (SELECT 1 FROM system_admins sa WHERE sa.user_id = auth.uid())
);
