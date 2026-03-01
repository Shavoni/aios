# Auditability + Multi-Tenancy: Quick Reference

**Production-Ready Security & Compliance** ✅

---

## Quick Answers

### D) Auditability + Decision Trace

**Q1: Decision trace for every response?**
✅ YES - `DecisionTraceV1` schema (v1.0.0) in `packages/core/simulation/schema.py`
- Captures: inputs, policy IDs, tool calls, approvals, outputs
- ⚠️ Minor gap: Policy version/hash (IDs captured, version not)

**Q2: Deterministic/hashable?**
✅ YES - SHA-256 with canonical JSON
- Sorted keys, stable floats (6 decimals), timestamps excluded
- Test: 100-run determinism verified

**Q3: Export audit logs?**
✅ YES (JSON), ⚠️ CSV/SIEM easy to add
- Filter by: department, org, time range
- Format: JSON ready, CSV/SIEM code examples provided

**Q4: Approval tracking?**
✅ YES - Complete who/when/what
- WHO: `resolved_by`, WHEN: `resolved_at`, WHAT: `modified_response`
- Storage: `data/hitl/approvals.json` + audit log

---

### E) Multi-Tenancy Security

**Q1: Database-level RLS?**
✅ YES - PostgreSQL RLS on 11 tables
- Migration: `001_enable_rls.py`
- FORCE ROW LEVEL SECURITY enabled
- Policy: `tenant_id = current_setting('app.org_id', true)`

**Q2: Tenant context setting?**
✅ YES - `SET LOCAL app.org_id` per request
- Middleware: `TenantMiddleware` extracts from header/JWT
- Missing context: 401 Unauthorized
- Transaction-scoped (auto-cleared)

**Q3: Cross-tenant isolation tests?**
✅ YES - `test_rls.py` with 4 comprehensive tests
- Read blocking without WHERE ✅
- Write blocking ✅
- End-to-end propagation ✅
- No context blocks all ✅

**Q4: RLS coverage?**
✅ 11 critical tables, ⚠️ Verify additional
- Protected: agents, kb_documents, audit_events, conversations, messages, users, governance_policies, execution_traces, hitl_approvals, deployments, onboarding_wizards
- Coverage verification script provided

---

## Key Code Locations

| Component | File |
|-----------|------|
| **Decision Trace Schema** | `packages/core/simulation/schema.py` |
| **Trace Determinism** | `DecisionTraceV1.compute_hash()` |
| **Audit Manager** | `packages/core/audit/__init__.py` |
| **RLS Migration** | `migrations/versions/001_enable_rls.py` |
| **Tenant Middleware** | `packages/core/multitenancy/middleware.py` |
| **RLS Tests** | `packages/core/multitenancy/tests/test_rls.py` |
| **Trace Tests** | `packages/core/simulation/tests/test_trace_v1.py` |

---

## Status Summary

### Auditability: ✅ Strong
- Decision traces: ✅ Versioned schema
- Determinism: ✅ SHA-256, canonical JSON
- Export: ✅ JSON ready
- Approvals: ✅ Complete tracking

### Multi-Tenancy: ✅ Enterprise-Grade
- RLS: ✅ Database-enforced
- Context: ✅ Middleware sets per request
- Tests: ✅ Comprehensive isolation
- Coverage: ✅ 11 critical tables

### Minor Enhancements Recommended
1. Add `policy_version` field to traces
2. Add CSV/SIEM export formats
3. Run RLS coverage verification
4. Link approval resolutions to traces

---

## Example Usage

### Decision Trace

```python
from packages.core.simulation.schema import create_trace

# Create trace
trace = create_trace(
    request_text="What is the leave policy?",
    tenant_id="cleveland",
    user_id="user-123"
)

# Add classification results
trace.intent = IntentResultV1(...)
trace.risk = RiskResultV1(...)
trace.governance = GovernanceResultV1(policy_ids=["policy-001"])

# Finalize with hash
trace.finalize()

# Export
print(trace.trace_hash)  # Deterministic hash
json_output = trace.to_canonical_json()
```

### Audit Export

```python
from packages.core.audit import get_audit_manager

audit_mgr = get_audit_manager()

# Export by department/time
events = audit_mgr.get_events(
    start_date="2026-01-01",
    end_date="2026-01-31",
    user_department="HR",  # Filter by department
)

# Generate compliance report
report = audit_mgr.generate_compliance_report(
    start_date="2026-01-01",
    end_date="2026-01-31",
    generated_by="admin-456"
)

# Export as JSON
json_data = report.model_dump_json(indent=2)
```

### Multi-Tenancy

```python
from fastapi import FastAPI
from packages.core.multitenancy.middleware import TenantMiddleware

app = FastAPI()

# Add middleware (extracts X-Tenant-ID header)
app.add_middleware(
    TenantMiddleware,
    require_tenant=True,  # Reject requests without tenant
)

# In route handler - tenant context automatically set
@app.get("/agents")
async def list_agents(request: Request):
    # request.state.org_id contains tenant ID
    # Database queries automatically filtered by RLS
    # SELECT * FROM agents → only returns tenant's data
    pass
```

### RLS Verification

```python
# Check RLS status
import psycopg2

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Check if table has RLS
cur.execute("""
    SELECT relrowsecurity, relforcerowsecurity
    FROM pg_class
    WHERE relname = 'agents'
""")
has_rls, forced = cur.fetchone()
print(f"RLS enabled: {has_rls}, Forced: {forced}")

# Check policy exists
cur.execute("""
    SELECT policyname
    FROM pg_policies
    WHERE tablename = 'agents'
""")
policies = cur.fetchall()
print(f"Policies: {policies}")
```

---

## Production Checklist

**Auditability:**
- [ ] Enable decision tracing in production mode
- [ ] Set up audit log retention (e.g., 90 days)
- [ ] Configure audit export schedule
- [ ] Add CSV/SIEM export if needed
- [ ] Review PII detection patterns
- [ ] Add policy version tracking

**Multi-Tenancy:**
- [ ] Run RLS coverage verification
- [ ] Add RLS to additional tables if needed
- [ ] Test middleware with production auth
- [ ] Verify `require_tenant=True` in production
- [ ] Document excluded paths for health checks
- [ ] Monitor for missing tenant context errors

**Testing:**
- [ ] Run RLS isolation tests
- [ ] Run trace determinism tests
- [ ] Test cross-tenant access attempts
- [ ] Verify audit log exports
- [ ] Load test with multiple tenants

---

**Complete documentation:** See `AUDITABILITY_AND_MULTITENANCY.md` (36KB)

**Quick Reference Version:** 1.0  
**Date:** January 28, 2026
