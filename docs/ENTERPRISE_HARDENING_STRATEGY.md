# HAAIS AIOS Enterprise Hardening Strategy

## Implementation Plan for P0/P1 Roadmap

This document translates the Enterprise Hardening Commitments into concrete implementation tasks, file changes, and architectural decisions.

---

## Phase 1: P0 Foundation (Days 0-30)

### 1.1 Identity & Authentication

**Current State:** `X-Tenant-ID` header (spoofable)
**Target State:** OIDC/SAML with JWT validation

#### Files to Create

```
packages/
├── auth/
│   ├── __init__.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract auth provider
│   │   ├── oidc.py          # OpenID Connect integration
│   │   ├── saml.py          # SAML 2.0 integration
│   │   └── dev_header.py    # Dev-only header auth (gated)
│   ├── jwt_validator.py     # JWT token validation
│   ├── middleware.py        # FastAPI auth middleware
│   ├── models.py            # AuthenticatedUser, TokenClaims
│   └── config.py            # Auth configuration
```

#### Implementation Tasks

| Task | Description | Estimate |
|------|-------------|----------|
| AUTH-1 | Create `AuthProvider` abstract base class | 2h |
| AUTH-2 | Implement `OIDCProvider` with token exchange | 4h |
| AUTH-3 | Implement `SAMLProvider` with assertion parsing | 4h |
| AUTH-4 | Create `JWTValidator` with JWKS support | 3h |
| AUTH-5 | Build `AuthMiddleware` for FastAPI | 2h |
| AUTH-6 | Gate `DevHeaderProvider` to non-production | 1h |
| AUTH-7 | Update all API endpoints to use authenticated context | 4h |

#### Key Code Architecture

```python
# packages/auth/models.py
class AuthenticatedUser(BaseModel):
    """Verified user identity from IdP."""
    user_id: str
    tenant_id: str  # From verified token claims
    email: str
    roles: list[str]
    groups: list[str]
    token_exp: datetime
    auth_provider: str  # "oidc", "saml", "dev_header"

class TokenClaims(BaseModel):
    """Standard JWT claims + custom AIOS claims."""
    sub: str  # Subject (user ID)
    iss: str  # Issuer
    aud: str  # Audience
    exp: int  # Expiration
    iat: int  # Issued at
    tenant_id: str  # Custom claim
    roles: list[str]  # Custom claim
```

```python
# packages/auth/middleware.py
class AuthMiddleware:
    """FastAPI middleware for authentication."""

    def __init__(self, app, auth_provider: AuthProvider):
        self.app = app
        self.auth_provider = auth_provider

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract token from Authorization header
            # Validate with provider
            # Inject AuthenticatedUser into request.state
            pass
```

#### Environment Gating

```python
# packages/auth/config.py
class AuthConfig(BaseModel):
    """Authentication configuration."""
    mode: Literal["production", "development", "test"]

    # Production: OIDC/SAML required
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_jwks_uri: str | None = None

    # SAML settings
    saml_idp_metadata_url: str | None = None
    saml_sp_entity_id: str | None = None

    # Development only - fails in production
    allow_header_auth: bool = False

    def get_provider(self) -> AuthProvider:
        if self.mode == "production":
            if self.allow_header_auth:
                raise SecurityError("Header auth not allowed in production")
            # Return OIDC or SAML provider
        elif self.mode == "development":
            if self.allow_header_auth:
                return DevHeaderProvider()
            # Fall through to OIDC/SAML
```

---

### 1.2 Tenant Data Isolation (PostgreSQL RLS)

**Current State:** Application-level filtering
**Target State:** Database-enforced row-level security

#### SQL Migrations to Create

```
migrations/
├── 001_enable_rls.sql
├── 002_tenant_policies.sql
└── 003_rls_test_validation.sql
```

#### Implementation Tasks

| Task | Description | Estimate |
|------|-------------|----------|
| RLS-1 | Design RLS policy schema | 2h |
| RLS-2 | Create migration for enabling RLS on all tables | 2h |
| RLS-3 | Implement `set_tenant_context()` function | 1h |
| RLS-4 | Update connection pool to set context on checkout | 2h |
| RLS-5 | Write cross-tenant isolation tests | 3h |
| RLS-6 | Audit all existing queries for RLS compatibility | 2h |

#### Key SQL Architecture

```sql
-- migrations/001_enable_rls.sql

-- Enable RLS on tenant-scoped tables
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE governance_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;

-- Create tenant context function
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.tenant_id', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create RLS policies
CREATE POLICY tenant_isolation_agents ON agents
    FOR ALL
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_knowledge_bases ON knowledge_bases
    FOR ALL
    USING (tenant_id = current_tenant_id());

-- ... repeat for all tenant-scoped tables
```

```python
# packages/db/rls.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def tenant_context(conn, tenant_id: str):
    """Set tenant context for RLS enforcement."""
    await conn.execute(
        "SELECT set_config('app.tenant_id', $1, true)",
        tenant_id
    )
    try:
        yield conn
    finally:
        await conn.execute(
            "SELECT set_config('app.tenant_id', '', true)"
        )
```

#### Automated Isolation Tests

```python
# tests/security/test_rls_isolation.py
async def test_cross_tenant_access_blocked():
    """Verify RLS prevents cross-tenant data access."""
    # Create data as tenant A
    async with tenant_context(conn, "tenant_a"):
        await conn.execute("INSERT INTO agents ...")

    # Attempt access as tenant B - should return empty
    async with tenant_context(conn, "tenant_b"):
        result = await conn.fetch("SELECT * FROM agents WHERE ...")
        assert len(result) == 0, "Cross-tenant access detected!"
```

---

### 1.3 Grounded Response Enforcement

**Current State:** Grounding implemented, not enforced
**Target State:** Mandatory grounding with fallback behavior

#### Files to Modify

```
packages/core/grounding.py      # Add enforcement logic
packages/api/agents.py          # Add grounding gate
packages/core/schemas/models.py # Add enforcement config
```

#### Implementation Tasks

| Task | Description | Estimate |
|------|-------------|----------|
| GRD-1 | Add `GroundingEnforcementConfig` model | 1h |
| GRD-2 | Implement `enforce_grounding()` gate function | 2h |
| GRD-3 | Add "Insufficient Verified Information" response type | 1h |
| GRD-4 | Add document version/effective date to citations | 2h |
| GRD-5 | Create grounding enforcement tests | 2h |

#### Key Code Changes

```python
# packages/core/schemas/models.py (additions)

class GroundingEnforcementConfig(BaseModel):
    """Configuration for grounding enforcement."""
    enabled: bool = True
    min_grounding_score: float = 0.5
    require_verified_sources: bool = False
    fallback_response: str = "I don't have sufficient verified information to answer this question. Please consult an authoritative source or contact support."

class DocumentVersion(BaseModel):
    """Document version tracking for citations."""
    version: str
    effective_date: date | None = None
    expiration_date: date | None = None
    is_current: bool = True
```

```python
# packages/core/grounding.py (additions)

class GroundingEnforcer:
    """Enforces grounding requirements on responses."""

    def __init__(self, config: GroundingEnforcementConfig):
        self.config = config

    def enforce(
        self,
        response: str,
        grounding: ResponseGrounding
    ) -> tuple[str, bool]:
        """
        Enforce grounding requirements.

        Returns:
            tuple: (response_text, was_blocked)
        """
        if not self.config.enabled:
            return response, False

        # Check minimum grounding score
        if grounding.overall_grounding_score < self.config.min_grounding_score:
            return self.config.fallback_response, True

        # Check for verified sources if required
        if self.config.require_verified_sources:
            if grounding.human_verified_claims == 0:
                return self.config.fallback_response, True

        return response, False
```

---

### 1.4 Audit Integrity (Tamper-Evident Logging)

**Current State:** Standard database records
**Target State:** Append-only with hash chaining

#### Files to Create

```
packages/
├── audit/
│   ├── __init__.py
│   ├── models.py           # ImmutableAuditRecord
│   ├── chain.py            # Hash chaining logic
│   ├── storage.py          # Append-only storage
│   └── verification.py     # Chain verification
```

#### Implementation Tasks

| Task | Description | Estimate |
|------|-------------|----------|
| AUD-1 | Design `ImmutableAuditRecord` schema | 2h |
| AUD-2 | Implement hash chaining algorithm | 3h |
| AUD-3 | Create append-only storage layer | 3h |
| AUD-4 | Add chain verification endpoint | 2h |
| AUD-5 | Migrate existing audit to new system | 2h |
| AUD-6 | Add WORM storage interface (optional) | 2h |

#### Key Code Architecture

```python
# packages/audit/models.py

class ImmutableAuditRecord(BaseModel):
    """Tamper-evident audit record with hash chaining."""

    # Identity
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence_number: int  # Monotonic sequence within tenant
    tenant_id: str

    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Content
    event_type: str  # "query", "response", "approval", "config_change"
    actor_id: str
    actor_type: str  # "user", "system", "agent"

    # Payload (JSON-serializable)
    payload: dict[str, Any]

    # Chain integrity
    previous_hash: str  # Hash of previous record (empty for genesis)
    record_hash: str    # Hash of this record (computed)

    # Metadata
    environment: str = "production"
    api_version: str = "1.0"
```

```python
# packages/audit/chain.py
import hashlib
import json

class AuditChain:
    """Manages hash-chained audit records."""

    HASH_ALGORITHM = "sha256"

    def compute_record_hash(self, record: ImmutableAuditRecord) -> str:
        """Compute hash for a record."""
        # Canonical JSON serialization
        content = json.dumps({
            "record_id": record.record_id,
            "sequence_number": record.sequence_number,
            "tenant_id": record.tenant_id,
            "timestamp": record.timestamp.isoformat(),
            "event_type": record.event_type,
            "actor_id": record.actor_id,
            "payload": record.payload,
            "previous_hash": record.previous_hash,
        }, sort_keys=True)

        return hashlib.sha256(content.encode()).hexdigest()

    def append_record(
        self,
        tenant_id: str,
        event_type: str,
        actor_id: str,
        payload: dict
    ) -> ImmutableAuditRecord:
        """Create and append a new audit record."""
        # Get previous record for hash chaining
        previous = self.storage.get_latest(tenant_id)
        previous_hash = previous.record_hash if previous else ""
        sequence = (previous.sequence_number + 1) if previous else 1

        record = ImmutableAuditRecord(
            sequence_number=sequence,
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            payload=payload,
            previous_hash=previous_hash,
            record_hash=""  # Computed below
        )

        record.record_hash = self.compute_record_hash(record)

        # Append-only insert (no updates allowed)
        self.storage.append(record)

        return record

    def verify_chain(self, tenant_id: str) -> tuple[bool, str | None]:
        """Verify integrity of entire audit chain."""
        records = self.storage.get_all(tenant_id, order_by="sequence_number")

        previous_hash = ""
        for record in records:
            # Verify previous hash link
            if record.previous_hash != previous_hash:
                return False, f"Chain break at sequence {record.sequence_number}"

            # Verify record hash
            computed = self.compute_record_hash(record)
            if computed != record.record_hash:
                return False, f"Hash mismatch at sequence {record.sequence_number}"

            previous_hash = record.record_hash

        return True, None
```

```sql
-- migrations/004_immutable_audit.sql

-- Create append-only audit table
CREATE TABLE immutable_audit_log (
    record_id UUID PRIMARY KEY,
    sequence_number BIGINT NOT NULL,
    tenant_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    previous_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    environment TEXT NOT NULL DEFAULT 'production',
    api_version TEXT NOT NULL DEFAULT '1.0',

    -- Ensure sequence is unique per tenant
    UNIQUE (tenant_id, sequence_number)
);

-- Create index for chain verification
CREATE INDEX idx_audit_tenant_sequence
ON immutable_audit_log(tenant_id, sequence_number);

-- CRITICAL: Remove UPDATE and DELETE permissions
-- Only INSERT is allowed (application-level enforcement)
-- For true WORM, use external storage integration

-- Create trigger to prevent updates
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit records cannot be modified';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_immutability
BEFORE UPDATE OR DELETE ON immutable_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

---

### 1.5 Compliance Positioning Alignment

**Current State:** Broad compliance claims
**Target State:** Accurate "designed to support" language

#### Files to Create/Modify

```
docs/
├── compliance/
│   ├── SOC2_CONTROL_MAPPING.md
│   ├── HIPAA_SAFEGUARD_MAPPING.md
│   ├── GDPR_REQUIREMENTS_MAPPING.md
│   └── COMPLIANCE_POSITIONING.md
```

#### Implementation Tasks

| Task | Description | Estimate |
|------|-------------|----------|
| CMP-1 | Create SOC 2 control mapping document | 4h |
| CMP-2 | Create HIPAA safeguard mapping | 4h |
| CMP-3 | Create GDPR requirements mapping | 4h |
| CMP-4 | Update all marketing/docs language | 2h |
| CMP-5 | Create compliance FAQ for sales | 2h |

#### Language Guidelines

**AVOID:**
- "AIOS is HIPAA compliant"
- "SOC 2 certified platform"
- "GDPR compliant solution"

**USE:**
- "AIOS is designed to support HIPAA-covered workflows"
- "Platform architecture aligns with SOC 2 security principles"
- "Built with GDPR data governance requirements in mind"
- "Enables deployment of compliant AI solutions when combined with appropriate organizational controls"

---

## Phase 2: P1 Enhancements (Days 30-90)

### 2.1 Authorization & Policy Control (RBAC/ABAC)

#### Files to Create

```
packages/
├── authz/
│   ├── __init__.py
│   ├── models.py           # Role, Permission, Policy
│   ├── rbac.py             # Role-based access control
│   ├── abac.py             # Attribute-based access control
│   ├── engine.py           # Authorization decision engine
│   └── middleware.py       # FastAPI authorization
```

#### Key Models

```python
# packages/authz/models.py

class Permission(str, Enum):
    """Granular permissions."""
    # Agents
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_DELETE = "agent:delete"
    AGENT_QUERY = "agent:query"

    # Knowledge
    KB_READ = "kb:read"
    KB_WRITE = "kb:write"
    KB_DELETE = "kb:delete"

    # Governance
    POLICY_READ = "policy:read"
    POLICY_WRITE = "policy:write"
    POLICY_APPROVE = "policy:approve"

    # Admin
    TENANT_ADMIN = "tenant:admin"
    AUDIT_READ = "audit:read"

class Role(BaseModel):
    """Role with associated permissions."""
    role_id: str
    name: str
    permissions: list[Permission]
    tenant_id: str

class PolicyCondition(BaseModel):
    """ABAC policy condition."""
    attribute: str  # "user.department", "resource.classification"
    operator: str   # "eq", "in", "contains"
    value: Any

class ABACPolicy(BaseModel):
    """Attribute-based access control policy."""
    policy_id: str
    name: str
    effect: Literal["allow", "deny"]
    conditions: list[PolicyCondition]
    permissions: list[Permission]
```

---

### 2.2 SIEM Integration

#### Files to Create

```
packages/
├── integrations/
│   ├── siem/
│   │   ├── __init__.py
│   │   ├── base.py         # Abstract SIEM connector
│   │   ├── splunk.py       # Splunk HEC integration
│   │   ├── sentinel.py     # Azure Sentinel integration
│   │   └── webhook.py      # Generic webhook for others
```

#### Key Interface

```python
# packages/integrations/siem/base.py

class SIEMConnector(ABC):
    """Abstract base for SIEM integrations."""

    @abstractmethod
    async def send_event(self, event: AuditEvent) -> bool:
        """Send security event to SIEM."""
        pass

    @abstractmethod
    async def send_alert(self, alert: SecurityAlert) -> bool:
        """Send high-priority security alert."""
        pass

class AuditEvent(BaseModel):
    """Standard audit event for SIEM."""
    timestamp: datetime
    event_type: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    actor: str
    action: str
    resource: str
    outcome: Literal["success", "failure"]
    details: dict[str, Any]
```

---

### 2.3 Threat Model Documentation

#### Files to Create

```
docs/
├── security/
│   ├── THREAT_MODEL.md
│   ├── DATA_FLOW_DIAGRAMS.md
│   ├── KEY_MANAGEMENT.md
│   └── INCIDENT_RESPONSE.md
```

#### Threat Categories to Document

| Category | Threats | Mitigations |
|----------|---------|-------------|
| **Prompt Injection** | Malicious prompts bypassing governance | Input sanitization, governance rules |
| **Data Exfiltration** | Extracting tenant data via queries | RLS, output filtering, audit |
| **KB Poisoning** | Malicious content in knowledge base | Content validation, source verification |
| **Auth Bypass** | Token manipulation, session hijacking | JWT validation, short expiry |
| **Privilege Escalation** | Users accessing unauthorized resources | RBAC/ABAC, least privilege |

---

## Execution Timeline

### Days 0-10: Foundation

```
[ ] AUTH-1: Create AuthProvider base class
[ ] AUTH-2: Implement OIDCProvider
[ ] RLS-1: Design RLS policy schema
[ ] RLS-2: Create RLS migration
[ ] AUD-1: Design ImmutableAuditRecord schema
```

### Days 11-20: Core Security

```
[ ] AUTH-3: Implement SAMLProvider
[ ] AUTH-4: Create JWTValidator
[ ] AUTH-5: Build AuthMiddleware
[ ] RLS-3: Implement set_tenant_context()
[ ] RLS-4: Update connection pool
[ ] AUD-2: Implement hash chaining
```

### Days 21-30: Integration & Testing

```
[ ] AUTH-6: Gate DevHeaderProvider
[ ] AUTH-7: Update all API endpoints
[ ] RLS-5: Write isolation tests
[ ] AUD-3: Create append-only storage
[ ] GRD-1-5: Grounding enforcement
[ ] CMP-1-5: Compliance documentation
```

### Days 31-60: P1 Features

```
[ ] RBAC/ABAC implementation
[ ] SIEM integration (Splunk/Sentinel)
[ ] Threat model documentation
```

### Days 61-90: Production Readiness

```
[ ] SLO/SLA framework
[ ] DR planning
[ ] Governance versioning
[ ] Environment separation validation
```

---

## Success Criteria

### P0 Complete When:

1. **Auth**: No API endpoint accepts unauthenticated requests in production
2. **RLS**: Cross-tenant isolation tests pass with 100% coverage
3. **Grounding**: Ungrounded responses return fallback message
4. **Audit**: Chain verification passes for all historical records
5. **Compliance**: All documentation uses "designed to support" language

### P1 Complete When:

1. **RBAC/ABAC**: All endpoints enforce permission checks
2. **SIEM**: Events flowing to configured SIEM platform
3. **Threat Model**: Published and reviewed by security team
4. **SLO**: Monitoring dashboards operational

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| RLS breaks existing queries | High | Comprehensive test suite before migration |
| Auth integration delays | High | Parallel development with header auth fallback |
| Audit migration data loss | Critical | Shadow-write to new system before cutover |
| SIEM integration complexity | Medium | Start with webhook, add native connectors later |

---

## Resource Requirements

| Role | Allocation | Duration |
|------|------------|----------|
| Backend Engineer | 1 FTE | 90 days |
| Security Engineer | 0.5 FTE | 60 days |
| DevOps | 0.25 FTE | 30 days |
| Technical Writer | 0.25 FTE | 30 days |

---

*HAAIS AIOS Enterprise Hardening Strategy v1.0*
*© 2026 DEF1LIVE LLC*
