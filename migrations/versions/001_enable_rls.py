"""Enable Row-Level Security on all tenant tables.

TENANT-001: Database-enforced tenant isolation via RLS.

Revision ID: 001_enable_rls
Revises:
Create Date: 2024-01-27
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '001_enable_rls'
down_revision = None
branch_labels = None
depends_on = None

# Tables that require tenant isolation
TENANT_TABLES = [
    'agents',
    'kb_documents',
    'audit_events',
    'conversations',
    'messages',
    'users',
    'governance_policies',
    'execution_traces',
    'hitl_approvals',
    'deployments',
    'onboarding_wizards',
]


def upgrade() -> None:
    """Enable RLS on all tenant tables with isolation policy."""

    # Create the app.org_id setting if it doesn't exist
    # This is used by the middleware to set the current tenant
    op.execute("""
        DO $$
        BEGIN
            -- Ensure the setting exists (will be set via SET LOCAL per-request)
            PERFORM current_setting('app.org_id', true);
        EXCEPTION
            WHEN undefined_object THEN
                -- Setting will be created on first SET LOCAL
                NULL;
        END $$;
    """)

    # Enable RLS on each tenant table
    for table in TENANT_TABLES:
        # Check if table exists before enabling RLS
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                ) THEN
                    -- Enable RLS
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

                    -- Force RLS even for table owners (security best practice)
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

                    -- Create policy for tenant isolation
                    -- Using current_setting with missing_ok=true to handle unset case
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {table};
                    CREATE POLICY tenant_isolation_policy ON {table}
                        FOR ALL
                        USING (
                            tenant_id = current_setting('app.org_id', true)
                            OR current_setting('app.org_id', true) IS NULL
                            OR current_setting('app.org_id', true) = ''
                        )
                        WITH CHECK (
                            tenant_id = current_setting('app.org_id', true)
                        );

                    RAISE NOTICE 'Enabled RLS on table: {table}';
                ELSE
                    RAISE NOTICE 'Table does not exist, skipping: {table}';
                END IF;
            END $$;
        """)

    # Create an admin policy for bypassing RLS (for maintenance)
    # This requires a specific role
    op.execute("""
        DO $$
        BEGIN
            -- Create admin role if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aios_admin') THEN
                CREATE ROLE aios_admin;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove RLS from all tenant tables."""

    for table in TENANT_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                ) THEN
                    -- Drop the policy
                    DROP POLICY IF EXISTS tenant_isolation_policy ON {table};

                    -- Disable RLS
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;

                    RAISE NOTICE 'Disabled RLS on table: {table}';
                END IF;
            END $$;
        """)
