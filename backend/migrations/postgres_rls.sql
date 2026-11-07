-- Reporter: Postgres hardening (run once as the database owner, AFTER the app has created tables).
-- Second wall behind the application's tenant scoping:
--   1. Row-level security: every tenant-owned row is visible only when app.tenant_id matches.
--   2. Separate DB roles per process, so a bug in one portal can't read the other's tables.
--
-- Replace the passwords, then put the matching URLs in each process's PP_DATABASE_URL:
--   admin -> pp_admin    webhooks -> pp_bot    worker -> pp_worker    employee portal -> pp_portal

-- ---------------------------------------------------------------- roles
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pp_admin')  THEN CREATE ROLE pp_admin  LOGIN PASSWORD 'CHANGE_ME_admin';  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pp_portal') THEN CREATE ROLE pp_portal LOGIN PASSWORD 'CHANGE_ME_portal'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pp_bot')    THEN CREATE ROLE pp_bot    LOGIN PASSWORD 'CHANGE_ME_bot';    END IF;
END $$;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO pp_admin, pp_portal, pp_bot;

-- Admin portal: full access to tenant data (still filtered by RLS).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pp_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pp_admin;

-- Webhook receiver + worker: conversation tables only. No admin users, no employee login codes.
GRANT SELECT ON tenants, rounds, round_interviewers, channel_configs, employees TO pp_bot;
GRANT SELECT, INSERT, UPDATE ON candidates, messages, action_nonces, reminders_sent TO pp_bot;
GRANT DELETE ON messages, action_nonces, login_codes, audit_events TO pp_bot;  -- retention purge
GRANT INSERT ON audit_events TO pp_bot;
GRANT SELECT ON audit_events, login_codes TO pp_bot;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pp_bot;

-- Employee portal: NO access to admin_users, channel_configs (tokens), messages (candidate chats)
-- or action_nonces. Candidate columns are limited to what an interviewer needs:
-- no phone_enc / phone_hash / email_enc / channel ids.
GRANT SELECT ON tenants, rounds TO pp_portal;
GRANT SELECT, UPDATE (session_version) ON employees TO pp_portal;
GRANT SELECT, INSERT, UPDATE ON login_codes TO pp_portal;
GRANT INSERT ON audit_events TO pp_portal;
GRANT SELECT (id, tenant_id, round_id, name, status, booked_start, interviewer_id, outcome, fsm_state)
  ON candidates TO pp_portal;
GRANT UPDATE (outcome, fsm_state) ON candidates TO pp_portal;
-- Phase 2 help desk: the portal reads policies/FAQs/leave balances (app code filters to the
-- signed-in employee), and writes only its own tickets and question metadata.
GRANT SELECT ON policies, policy_clauses, faq_overrides, leave_balances TO pp_portal;
GRANT SELECT, INSERT, UPDATE ON hr_tickets, hr_ticket_messages, ask_events TO pp_portal;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pp_portal;
-- Retention purge of closed help-desk conversations.
GRANT SELECT ON hr_tickets TO pp_bot;
GRANT DELETE ON hr_ticket_messages TO pp_bot;
GRANT SELECT ON hr_ticket_messages TO pp_bot;
GRANT SELECT, DELETE ON ask_events TO pp_bot;

-- ---------------------------------------------------------------- row-level security
-- app.tenant_id is set per transaction by db.set_tenant(). Unset => no rows.
CREATE OR REPLACE FUNCTION pp_current_tenant() RETURNS integer
  LANGUAGE sql STABLE AS $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::integer $$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['rounds','round_interviewers','candidates','messages','action_nonces',
                           'reminders_sent','audit_events','policies','policy_clauses',
                           'faq_overrides','leave_balances','hr_tickets','hr_ticket_messages','ask_events',
                           'eval_cases'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
    EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id = pp_current_tenant()) '
                   'WITH CHECK (tenant_id = pp_current_tenant())', t);
  END LOOP;
END $$;

-- Tables that must be readable BEFORE the tenant is known (login, webhook routing) keep
-- application-level scoping only: tenants, admin_users, employees, login_codes, channel_configs.
-- The worker sends reminders across tenants, so it gets its own role that bypasses RLS.
-- The public webhook receiver keeps pp_bot, which stays under RLS.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pp_worker') THEN
    CREATE ROLE pp_worker LOGIN PASSWORD 'CHANGE_ME_worker' BYPASSRLS;
  END IF;
END $$;
GRANT pp_bot TO pp_worker;
