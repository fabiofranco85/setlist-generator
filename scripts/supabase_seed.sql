-- =============================================================================
-- Supabase Seed Data for Church Worship Setlist Generator
-- =============================================================================
--
-- Seeds system_config with default values matching library/config.py constants.
-- Run after supabase_schema.sql:
--   psql $DATABASE_URL -f scripts/supabase_seed.sql
--
-- Idempotent: uses ON CONFLICT DO NOTHING so safe to re-run.
-- =============================================================================

INSERT INTO system_config (key, value) VALUES
  ('moments_config',         '{"prelúdio": 1, "ofertório": 1, "saudação": 1, "crianças": 1, "louvor": 4, "poslúdio": 1}'),
  ('recency_decay_days',     '45'),
  ('default_weight',         '3'),
  ('energy_ordering_enabled','true'),
  ('energy_ordering_rules',  '{"louvor": "ascending"}'),
  ('default_energy',         '2.5')
ON CONFLICT (key) DO NOTHING;
