-- Schema for PostgreSQL backend
-- Run with: psql $DATABASE_URL -f scripts/schema.sql
-- Idempotent: safe to re-run (uses IF NOT EXISTS / ON CONFLICT DO NOTHING)

-- Songs table: one row per song
CREATE TABLE IF NOT EXISTS songs (
    title       TEXT PRIMARY KEY,
    energy      REAL NOT NULL DEFAULT 2.5,
    content     TEXT NOT NULL DEFAULT '',
    youtube_url TEXT NOT NULL DEFAULT '',
    event_types TEXT[] NOT NULL DEFAULT '{}'
);

-- Normalized song-moment tags with weights
CREATE TABLE IF NOT EXISTS song_tags (
    song_title  TEXT NOT NULL REFERENCES songs(title) ON DELETE CASCADE,
    moment      TEXT NOT NULL,
    weight      INTEGER NOT NULL DEFAULT 3,
    PRIMARY KEY (song_title, moment)
);

CREATE INDEX IF NOT EXISTS idx_song_tags_moment ON song_tags(moment);

-- Setlist history: one row per service date + event type + optional label
CREATE TABLE IF NOT EXISTS setlists (
    date        DATE NOT NULL,
    event_type  TEXT NOT NULL DEFAULT '',
    label       TEXT NOT NULL DEFAULT '',
    moments     JSONB NOT NULL,
    UNIQUE (date, event_type, label)
);

CREATE INDEX IF NOT EXISTS idx_setlists_date ON setlists(date DESC);

-- Event types: configurable service types with custom moments
CREATE TABLE IF NOT EXISTS event_types (
    slug        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    moments     JSONB NOT NULL
);

-- Seed default event type
INSERT INTO event_types (slug, name, description, moments) VALUES
    ('main', 'Main Event', '', '{"prelúdio": 1, "ofertório": 1, "saudação": 1, "crianças": 1, "louvor": 4, "poslúdio": 1}')
ON CONFLICT (slug) DO NOTHING;

-- Key-value configuration (enables per-org customization)
CREATE TABLE IF NOT EXISTS config (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL
);

-- Seed default configuration values (matches library/config.py)
INSERT INTO config (key, value) VALUES
    ('moments_config', '{"prelúdio": 1, "ofertório": 1, "saudação": 1, "crianças": 1, "louvor": 4, "poslúdio": 1}'),
    ('recency_decay_days', '45'),
    ('default_weight', '3'),
    ('energy_ordering_enabled', 'true'),
    ('energy_ordering_rules', '{"louvor": "ascending"}'),
    ('default_energy', '2.5')
ON CONFLICT (key) DO NOTHING;
