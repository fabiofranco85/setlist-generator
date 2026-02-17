-- Schema for PostgreSQL backend
-- Run with: psql $DATABASE_URL -f scripts/schema.sql
-- Idempotent: safe to re-run (uses IF NOT EXISTS / ON CONFLICT DO NOTHING)

-- Songs table: one row per song
CREATE TABLE IF NOT EXISTS songs (
    title       TEXT PRIMARY KEY,
    energy      REAL NOT NULL DEFAULT 2.5,
    content     TEXT NOT NULL DEFAULT '',
    youtube_url TEXT NOT NULL DEFAULT ''
);

-- Normalized song-moment tags with weights
CREATE TABLE IF NOT EXISTS song_tags (
    song_title  TEXT NOT NULL REFERENCES songs(title) ON DELETE CASCADE,
    moment      TEXT NOT NULL,
    weight      INTEGER NOT NULL DEFAULT 3,
    PRIMARY KEY (song_title, moment)
);

CREATE INDEX IF NOT EXISTS idx_song_tags_moment ON song_tags(moment);

-- Setlist history: one row per service date + optional label
CREATE TABLE IF NOT EXISTS setlists (
    date        DATE NOT NULL,
    label       TEXT NOT NULL DEFAULT '',
    moments     JSONB NOT NULL,
    UNIQUE (date, label)
);

CREATE INDEX IF NOT EXISTS idx_setlists_date ON setlists(date DESC);

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
