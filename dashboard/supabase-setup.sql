-- ============================================================
-- Wolfpack AI — Supabase Schema Setup
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- 1. wolfpack_clients table
CREATE TABLE IF NOT EXISTS wolfpack_clients (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at       timestamptz DEFAULT now(),
  email            text UNIQUE NOT NULL,
  name             text,
  business_name    text,
  city             text,
  tier             text,
  amount_monthly   integer,
  stripe_customer_id text,
  vapi_agent_id    text,
  phone_number     text,
  demo_url         text,
  status           text DEFAULT 'active',
  notes            text,
  tier_display     text,
  password_hash    text
);

-- 2. wolfpack_calls table
CREATE TABLE IF NOT EXISTS wolfpack_calls (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at       timestamptz DEFAULT now(),
  client_email     text,
  caller_name      text,
  phone_number     text,
  duration_seconds integer,
  outcome          text,
  transcript       text,
  interested       boolean DEFAULT false,
  demo_sent        boolean DEFAULT false,
  notes            text
);

-- 3. wolfpack_leads table
CREATE TABLE IF NOT EXISTS wolfpack_leads (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at       timestamptz DEFAULT now(),
  client_email     text,
  lead_name        text,
  lead_phone       text,
  lead_business    text,
  status           text DEFAULT 'warm',
  notes            text,
  call_id          uuid REFERENCES wolfpack_calls(id)
);

-- ============================================================
-- Row Level Security (RLS) Policies
-- Each client can only see their own data
-- ============================================================

-- Enable RLS
ALTER TABLE wolfpack_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE wolfpack_calls   ENABLE ROW LEVEL SECURITY;
ALTER TABLE wolfpack_leads   ENABLE ROW LEVEL SECURITY;

-- wolfpack_clients: users see only their own row
CREATE POLICY "clients_select_own"
  ON wolfpack_clients FOR SELECT
  USING (email = auth.email());

-- wolfpack_calls: users see only calls for their email
CREATE POLICY "calls_select_own"
  ON wolfpack_calls FOR SELECT
  USING (client_email = auth.email());

-- wolfpack_leads: users see only leads for their email
CREATE POLICY "leads_select_own"
  ON wolfpack_leads FOR SELECT
  USING (client_email = auth.email());

-- Allow service role (used by onboarding.py) to insert/update all tables
-- These policies use service_role which bypasses RLS automatically.
-- No additional policy needed for service role.

-- ============================================================
-- Enable Email Auth in Supabase:
-- Dashboard → Authentication → Providers → Email → Enable
-- Also enable "Confirm email" = OFF (so temp passwords work immediately)
-- ============================================================

-- ============================================================
-- Test data (optional — remove before production)
-- ============================================================
/*
INSERT INTO wolfpack_clients (email, name, business_name, city, tier, tier_display, amount_monthly, phone_number, demo_url, status)
VALUES (
  'test@example.com',
  'Jake Williams',
  'Mountain Plumbing Co',
  'Salt Lake City',
  'managed',
  'Wolfpack Managed',
  1497,
  '+18013408526',
  'https://bummerland17.github.io/wolfpack-ai/demos/mountain-plumbing.html',
  'active'
);

INSERT INTO wolfpack_calls (client_email, caller_name, phone_number, duration_seconds, outcome, interested, transcript)
VALUES 
  ('test@example.com', 'Sarah Johnson', '+18015551234', 142, 'interested', true, 'Hi, I need a plumber for a leaky pipe...'),
  ('test@example.com', 'Mike Torres', '+18015555678', 38, 'voicemail', false, null),
  ('test@example.com', 'Unknown', '+18015559999', 0, 'no_answer', false, null);

INSERT INTO wolfpack_leads (client_email, lead_name, lead_phone, lead_business, status, notes)
VALUES ('test@example.com', 'Sarah Johnson', '+18015551234', 'Home Owner', 'warm', 'Interested in same-day service');
*/
