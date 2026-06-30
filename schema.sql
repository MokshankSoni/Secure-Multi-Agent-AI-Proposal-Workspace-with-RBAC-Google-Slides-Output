-- =============================================================================
-- Schema: Smart AI Proposal
-- Compatible with: Supabase (PostgreSQL)
-- =============================================================================


-- =============================================================================
-- TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- organizations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- -----------------------------------------------------------------------------
-- users (application profile; authentication is handled by Supabase Auth)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID        NOT NULL REFERENCES organizations(id),
    role            TEXT        NOT NULL CHECK (role IN ('admin', 'member')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- -----------------------------------------------------------------------------
-- sessions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID        NOT NULL REFERENCES organizations(id),
    owner_id        UUID        NOT NULL REFERENCES users(id),
    title           TEXT        NOT NULL,
    raw_input       TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'drafting', 'reviewing', 'approved', 'failed')),
    slides_url      TEXT,
    slides_file_id  TEXT,
    final_response  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_users_organization_id
    ON users (organization_id);

CREATE INDEX IF NOT EXISTS idx_sessions_organization_id
    ON sessions (organization_id);

CREATE INDEX IF NOT EXISTS idx_sessions_owner_id
    ON sessions (owner_id);

CREATE INDEX IF NOT EXISTS idx_sessions_status
    ON sessions (status);


-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Automatically refresh updated_at on every UPDATE to sessions
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions       ENABLE ROW LEVEL SECURITY;


-- =============================================================================
-- POLICIES — organizations table
-- =============================================================================

-- Any authenticated user may read organization records (needed so /signup
-- can validate that the org_id supplied by the caller actually exists).
-- No INSERT/UPDATE/DELETE policy is defined, so those operations are
-- blocked by default under RLS for all non-service-role clients. Org
-- creation/seeding is performed with the service role key only.
CREATE POLICY organizations_select_authenticated
    ON organizations
    FOR SELECT
    USING (auth.uid() IS NOT NULL);


-- =============================================================================
-- POLICIES — users table
-- =============================================================================

-- Users may read only their own profile
CREATE POLICY users_select_own
    ON users
    FOR SELECT
    USING (id = auth.uid());

-- No INSERT policy is defined here on purpose: at signup time, the row in
-- `users` is created immediately after the Supabase Auth account is
-- created, before any session/JWT exists for that brand-new user to act
-- as auth.uid(). This insert is performed server-side with the service
-- role key (which bypasses RLS), not with a user-scoped client.


-- =============================================================================
-- POLICIES — sessions table
-- =============================================================================

-- Members (and, by extension, any user) may read sessions they own.
-- This is intentionally a simple ownership check with no role condition:
-- combined with sessions_select_admin below, Postgres OR's all permissive
-- SELECT policies together, so a member sees their own rows via this
-- policy and an admin sees their own rows via this policy too (in
-- addition to every other row in their org via the admin policy).
CREATE POLICY sessions_select_member
    ON sessions
    FOR SELECT
    USING (owner_id = auth.uid());

-- Admins may read every session within their own organization only.
-- This is the policy directly exercised by the cross-org isolation test:
-- a valid JWT for org B must not be able to read org A's sessions, even
-- as an admin, because the EXISTS subquery only matches rows where
-- sessions.organization_id equals the caller's own organization_id.
CREATE POLICY sessions_select_admin
    ON sessions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM   users
            WHERE  users.id              = auth.uid()
            AND    users.role            = 'admin'
            AND    users.organization_id = sessions.organization_id
        )
    );

-- A user may create a session only for themselves, and only tagged with
-- their own organization_id (prevents a caller from forging owner_id or
-- organization_id on insert, even if the request body is crafted by hand).
CREATE POLICY sessions_insert_own
    ON sessions
    FOR INSERT
    WITH CHECK (
        owner_id = auth.uid()
        AND organization_id = (
            SELECT organization_id FROM users WHERE id = auth.uid()
        )
    );

-- A user may update sessions within their own organization. In practice,
-- the pipeline write-back of slides_url / slides_file_id / status uses
-- the service role key (an internal system operation, not a user
-- operation), which bypasses RLS entirely. This policy exists as a
-- second line of defence for any direct, user-scoped update calls, and
-- mirrors the org-scoping used for SELECT.
CREATE POLICY sessions_update_own_org
    ON sessions
    FOR UPDATE
    USING (
        organization_id = (
            SELECT organization_id FROM users WHERE id = auth.uid()
        )
    );