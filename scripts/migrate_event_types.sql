-- Migration: Add event types support
-- Run with: psql $DATABASE_URL -f scripts/migrate_event_types.sql
-- Idempotent: safe to re-run

-- 1. Add event_types column to songs (TEXT array, default empty)
ALTER TABLE songs ADD COLUMN IF NOT EXISTS event_types TEXT[] NOT NULL DEFAULT '{}';

-- 2. Add event_type column to setlists
ALTER TABLE setlists ADD COLUMN IF NOT EXISTS event_type TEXT NOT NULL DEFAULT '';

-- 3. Update unique constraint from (date, label) to (date, event_type, label)
--    Drop old constraint if it exists, then create new one
DO $$
BEGIN
    -- Check if old constraint exists and drop it
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'setlists_date_label_key'
    ) THEN
        ALTER TABLE setlists DROP CONSTRAINT setlists_date_label_key;
    END IF;
END $$;

-- Create new unique constraint (idempotent via IF NOT EXISTS pattern)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'setlists_date_event_type_label_key'
    ) THEN
        ALTER TABLE setlists ADD CONSTRAINT setlists_date_event_type_label_key
            UNIQUE (date, event_type, label);
    END IF;
END $$;

-- 4. Create event_types table
CREATE TABLE IF NOT EXISTS event_types (
    slug        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    moments     JSONB NOT NULL
);

-- 5. Seed default event type
INSERT INTO event_types (slug, name, description, moments) VALUES
    ('main', 'Main Event', '', '{"prelúdio": 1, "ofertório": 1, "saudação": 1, "crianças": 1, "louvor": 4, "poslúdio": 1}')
ON CONFLICT (slug) DO NOTHING;
