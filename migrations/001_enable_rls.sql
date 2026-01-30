-- Migration: 001_enable_rls.sql
-- Purpose: Enable Row-Level Security on all tenant-scoped tables
-- Author: HAAIS AIOS Enterprise Hardening
-- Date: 2026-01-29

-- ============================================================================
-- TENANT CONTEXT FUNCTION
-- ============================================================================

-- Function to get current tenant from session variable
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS TEXT AS $$
BEGIN
    -- Returns the tenant_id set via set_config('app.tenant_id', ..., true)
    -- Returns NULL if not set (which will cause RLS to block access)
    RETURN current_setting('app.tenant_id', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION current_tenant_id() IS
    'Returns the current tenant context set by the application layer';

-- Function to set tenant context (called by application on connection checkout)
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.tenant_id', p_tenant_id, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION set_tenant_context(TEXT) IS
    'Sets the tenant context for the current transaction';

-- Function to clear tenant context (called after request)
CREATE OR REPLACE FUNCTION clear_tenant_context()
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.tenant_id', '', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION clear_tenant_context() IS
    'Clears the tenant context after request processing';

-- ============================================================================
-- ENABLE RLS ON TENANT-SCOPED TABLES
-- ============================================================================

-- Agents table
ALTER TABLE IF EXISTS agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS agents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_agents ON agents;
CREATE POLICY tenant_isolation_agents ON agents
    FOR ALL
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Knowledge bases table
ALTER TABLE IF EXISTS knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS knowledge_bases FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_knowledge_bases ON knowledge_bases;
CREATE POLICY tenant_isolation_knowledge_bases ON knowledge_bases
    FOR ALL
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Documents table
ALTER TABLE IF EXISTS documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS documents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_documents ON documents;
CREATE POLICY tenant_isolation_documents ON documents
    FOR ALL
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Governance policies table
ALTER TABLE IF EXISTS governance_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS governance_policies FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_governance_policies ON governance_policies;
CREATE POLICY tenant_isolation_governance_policies ON governance_policies
    FOR ALL
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Approvals table
ALTER TABLE IF EXISTS approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS approvals FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_approvals ON approvals;
CREATE POLICY tenant_isolation_approvals ON approvals
    FOR ALL
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Conversations table (if exists)
ALTER TABLE IF EXISTS conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS conversations FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_conversations ON conversations;
CREATE POLICY tenant_isolation_conversations ON conversations
    FOR ALL
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- ============================================================================
-- ADMIN BYPASS ROLE
-- ============================================================================

-- Create admin role that bypasses RLS (for migrations, maintenance)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aios_admin') THEN
        CREATE ROLE aios_admin NOLOGIN;
    END IF;
END
$$;

-- Grant bypass to admin role
ALTER TABLE IF EXISTS agents OWNER TO aios_admin;
ALTER TABLE IF EXISTS knowledge_bases OWNER TO aios_admin;
ALTER TABLE IF EXISTS documents OWNER TO aios_admin;
ALTER TABLE IF EXISTS governance_policies OWNER TO aios_admin;
ALTER TABLE IF EXISTS approvals OWNER TO aios_admin;
ALTER TABLE IF EXISTS conversations OWNER TO aios_admin;

COMMENT ON ROLE aios_admin IS
    'Administrative role that bypasses RLS for maintenance operations';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- View to check RLS status on all tables
CREATE OR REPLACE VIEW rls_status AS
SELECT
    schemaname,
    tablename,
    rowsecurity as rls_enabled,
    forcerowsecurity as rls_forced
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
    'agents',
    'knowledge_bases',
    'documents',
    'governance_policies',
    'approvals',
    'conversations'
);

COMMENT ON VIEW rls_status IS
    'Shows RLS status for tenant-scoped tables';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
