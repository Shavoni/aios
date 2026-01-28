# HAAIS AIOS Tenancy Model

## Overview

HAAIS AIOS uses **PostgreSQL Row-Level Security (RLS)** as the primary tenancy enforcement mechanism. This provides database-enforced isolation without requiring application-level filtering.

## Architecture Decision

### Chosen Model: Row-Level Security (RLS)

**Why RLS over alternatives:**

| Model | Pros | Cons | Decision |
|-------|------|------|----------|
| **RLS (Chosen)** | Database-enforced, no code changes, automatic filtering | Slightly more complex setup | ✅ Primary |
| Schema-per-tenant | Complete isolation | Connection pool overhead, migration complexity | Fallback for high-security |
| Database-per-tenant | Maximum isolation | Operational overhead, cost | Enterprise custom |
| Application-level WHERE | Simple to implement | Error-prone, bypass risk | ❌ Rejected |

### Key Principles

1. **Defense in Depth**: RLS is the primary barrier; application code is secondary.
2. **Fail Secure**: Missing `org_id` = request rejected (no default tenant).
3. **Audit Everything**: All cross-tenant access attempts are logged.
4. **Zero Trust**: Every query is filtered; no exceptions.

---

## Implementation

### 1. Session Context Variable

Every request sets the tenant context using PostgreSQL's session variables:

```sql
-- Set at the start of every request
SET LOCAL app.org_id = 'tenant-123';
```

The `LOCAL` keyword ensures the setting is transaction-scoped and automatically cleared.

### 2. RLS Policies

All tenant-scoped tables have RLS enabled with policies:

```sql
-- Enable RLS on table
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Create policy using session variable
CREATE POLICY tenant_isolation_policy ON agents
    USING (tenant_id = current_setting('app.org_id', true));

-- Force RLS even for table owners
ALTER TABLE agents FORCE ROW LEVEL SECURITY;
```

### 3. Request Middleware

FastAPI middleware sets the tenant context:

```python
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Extract org_id from JWT or header
    org_id = extract_org_id(request)

    if not org_id:
        raise HTTPException(status_code=401, detail="Missing org_id")

    # Set in database session
    async with get_db_session() as session:
        await session.execute(
            text("SET LOCAL app.org_id = :org_id"),
            {"org_id": org_id}
        )

        # Store in request state for app code
        request.state.org_id = org_id

        response = await call_next(request)

    return response
```

### 4. Tenant-Scoped Tables

All tables with tenant data include:

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    -- ... other columns
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX idx_agents_tenant ON agents(tenant_id);
```

---

## Tenant-Scoped Resources

The following resources are tenant-isolated:

| Resource | Table | Isolation Level |
|----------|-------|-----------------|
| Agents | `agents` | RLS |
| Knowledge Base | `kb_documents` | RLS |
| Audit Logs | `audit_events` | RLS |
| Conversations | `conversations` | RLS |
| Users | `users` | RLS |
| Policies | `governance_policies` | RLS |
| Traces | `execution_traces` | RLS |
| Approvals | `hitl_approvals` | RLS |

---

## Alembic Migrations

### Migration: Enable RLS

```python
# migrations/versions/001_enable_rls.py

def upgrade():
    # Enable RLS on all tenant tables
    tenant_tables = [
        'agents', 'kb_documents', 'audit_events',
        'conversations', 'users', 'governance_policies',
        'execution_traces', 'hitl_approvals'
    ]

    for table in tenant_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
                USING (tenant_id = current_setting('app.org_id', true))
        """)

def downgrade():
    # Remove RLS policies
    for table in tenant_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
```

---

## Security Guarantees

### 1. Cross-Tenant Read Blocked

Even if application code forgets a WHERE clause:

```python
# This query is SAFE - RLS filters automatically
result = await session.execute(select(Agent))
# Returns only agents for current tenant
```

### 2. Cross-Tenant Write Blocked

Inserts/updates to wrong tenant are rejected:

```python
# This INSERT will FAIL if tenant_id doesn't match session
agent = Agent(tenant_id="wrong-tenant", name="Test")
session.add(agent)
await session.commit()  # Raises IntegrityError
```

### 3. Admin Bypass (Controlled)

Super-admin operations use a separate connection pool with RLS disabled:

```python
# Admin-only operations (audited)
async with get_admin_session() as session:
    # RLS is bypassed, full access
    await session.execute(select(Agent))  # Returns ALL agents
```

---

## Testing Requirements

### Required Tests (TENANT-001)

```python
def test_cross_tenant_read_is_blocked_without_where():
    """Query without WHERE still respects RLS."""
    # Set tenant A context
    set_tenant("tenant-a")

    # Insert data for tenant A
    create_agent(tenant_id="tenant-a", name="Agent A")

    # Insert data for tenant B (via admin bypass)
    with admin_session():
        create_agent(tenant_id="tenant-b", name="Agent B")

    # Query ALL agents (no WHERE clause)
    agents = session.execute(select(Agent)).all()

    # Should only see tenant A's agent
    assert len(agents) == 1
    assert agents[0].name == "Agent A"


def test_cross_tenant_write_is_blocked():
    """Cannot insert data for another tenant."""
    set_tenant("tenant-a")

    # Try to insert for wrong tenant
    with pytest.raises(IntegrityError):
        create_agent(tenant_id="tenant-b", name="Sneaky")


def test_end_to_end_api_propagation():
    """Tenant context propagates through entire request."""
    # Make API request as tenant A
    response = client.get(
        "/api/agents",
        headers={"X-Tenant-ID": "tenant-a"}
    )

    # Should only see tenant A's data
    agents = response.json()
    assert all(a["tenant_id"] == "tenant-a" for a in agents)
```

---

## Monitoring & Alerts

### Metrics to Track

1. **Cross-tenant access attempts** (should be 0)
2. **RLS policy evaluations per second**
3. **Tenant context missing errors**
4. **Admin bypass usage** (audit trail)

### Alert Conditions

- Any cross-tenant access attempt
- RLS policy dropped or disabled
- Admin session without audit log entry

---

## Fallback: Schema-per-Tenant

For high-security tenants (government, healthcare), schema isolation is available:

```python
# High-security tenant uses dedicated schema
tenant = Tenant(
    id="gov-agency",
    isolation_level=IsolationLevel.SCHEMA,
)

# Creates schema: tenant_gov_agency
# All tables are created in that schema
# Connection uses search_path = tenant_gov_agency
```

---

## Summary

| Aspect | Implementation |
|--------|----------------|
| Primary Model | PostgreSQL RLS |
| Context Variable | `app.org_id` (SET LOCAL) |
| Enforcement | Database-level (cannot bypass) |
| Middleware | Sets context on every request |
| Missing Tenant | 401 Unauthorized |
| Admin Access | Separate pool, fully audited |
| Fallback | Schema-per-tenant for high-security |

---

*Document Version: 1.0*
*Last Updated: 2024*
*TENANT-001 Specification*
