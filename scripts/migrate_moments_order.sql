-- Migration: Add moments_order column to event_types
-- Run with: psql $DATABASE_URL -f scripts/migrate_moments_order.sql
-- Idempotent: safe to re-run

-- Add the column
ALTER TABLE event_types ADD COLUMN IF NOT EXISTS moments_order JSONB DEFAULT NULL;

-- Backfill existing rows with alphabetical order (best we can do for JSONB)
UPDATE event_types SET moments_order = (
  SELECT jsonb_agg(key ORDER BY key) FROM jsonb_each(moments) AS t(key, value)
) WHERE moments_order IS NULL;
