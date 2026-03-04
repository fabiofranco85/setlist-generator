-- =============================================================================
-- Migration: Add set_org_context RPC function
-- =============================================================================
--
-- Adds the missing set_org_context() function required by client.py.
-- RLS policies reference current_setting('app.org_id', true) which is set
-- by calling this function at the start of each request.
--
-- Idempotent: uses CREATE OR REPLACE.
--
-- Run with:
--   psql $DATABASE_URL -f scripts/migrate_set_org_context.sql
--
-- =============================================================================

CREATE OR REPLACE FUNCTION set_org_context(p_org_id UUID)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  PERFORM set_config('app.org_id', p_org_id::TEXT, true);
END;
$$;
