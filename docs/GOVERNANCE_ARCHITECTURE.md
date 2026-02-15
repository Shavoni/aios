# AIOS Governance Architecture Review

**Date:** January 2026  
**Purpose:** Answer critical questions about governance implementation and "immutable rules"

---

## Executive Summary

This document reviews the AIOS governance system against the requirements for a robust, enterprise-grade policy enforcement framework. It addresses five critical questions:

**Status Overview:**
- ✅ **Single Source of Truth**: Implemented (`data/governance_policies.json`)
- ⚠️ **Override Prevention**: Partially implemented (priority system exists, but no hard enforcement)
- ❌ **Policy Versioning**: NOT implemented
- ❌ **Approval Workflow**: NOT implemented (file-based, no audit trail)
- ❌ **Drift Detection**: NOT implemented

---

## A) Single Source of Truth for Policies

### ✅ Status: **IMPLEMENTED**

**Location:** `data/governance_policies.json`

This is the single, authoritative source for all governance policies. The file defines three tiers of rules:

```
data/governance_policies.json (Single Source of Truth)
├── constitutional_rules[]     # Tier 1: Highest priority (10000+)
├── organization_rules          # Tier 2: Organization-wide (5000+)
│   └── default[]
└── department_rules            # Tier 3: Department-specific (0+)
    └── {domain}
        └── defaults[]
```

**Implementation Details:**

1. **File Location:** `/home/runner/work/aios/aios/data/governance_policies.json`

2. **Runtime Loading:** 
   - Loaded via `GovernanceManager` singleton (`packages/core/governance/manager.py`)
   - Singleton pattern ensures one instance across entire application
   - Loaded on first access via `get_governance_manager()`

3. **Access Pattern:**
   ```python
   # All code uses the singleton
   from packages.core.governance.manager import get_governance_manager
   
   governance = get_governance_manager()
   decision = governance.evaluate(query, domain)
   ```

4. **Storage Format:**
   ```json
   {
     "constitutional_rules": [
       {
         "id": "const-001",
         "name": "PII Protection",
         "conditions": [...],
         "action": {...},
         "priority": 100
       }
     ],
     "organization_rules": { "default": [...] },
     "department_rules": {},
     "prohibited_topics": []
   }
   ```

**✅ Good:**
- Single file, single manager, clear ownership
- Centralized in-memory cache
- All agents query the same manager
- Changes to the file require explicit reload via `/governance/reload` API

**⚠️ Concerns:**
- File-based storage has no transactional guarantees
- No database backend option
- No backup/restore mechanism
- Manual file edits can break JSON structure

---

## B) Department Override Prevention

### ⚠️ Status: **PARTIALLY IMPLEMENTED**

**Current Implementation:**

The system uses a **priority-based hierarchy** to prevent overrides:

```python
# From packages/core/governance/__init__.py:172-186

# Constitutional rules: priority + 10000
for rule in policy_set.constitutional_rules:
    if _evaluate_rule(rule, intent, risk, ctx):
        matching_rules.append((rule.priority + 10000, rule))

# Organization rules: priority + 5000
for rule in policy_set.organization_rules.default:
    if _evaluate_rule(rule, intent, risk, ctx):
        matching_rules.append((rule.priority + 5000, rule))

# Department rules: raw priority (0+)
dept_rules = policy_set.department_rules.get(intent.domain)
if dept_rules:
    for rule in dept_rules.defaults:
        if _evaluate_rule(rule, intent, risk, ctx):
            matching_rules.append((rule.priority, rule))
```

**How It Works:**

1. **Priority Calculation:**
   - Constitutional: `priority + 10,000` (e.g., priority 100 → 10,100)
   - Organization: `priority + 5,000` (e.g., priority 50 → 5,050)
   - Department: `raw priority` (e.g., priority 10 → 10)

2. **Rule Merging:**
   - Rules are sorted by priority (highest first)
   - Each matching rule **merges** its action into the decision
   - More restrictive settings win (e.g., `ESCALATE > DRAFT > INFORM`)

3. **Merge Logic** (`packages/core/governance/__init__.py:133-154`):
   ```python
   def _merge_action(decision, action, rule_id):
       # HITL mode: higher priority wins
       if action.hitl_mode:
           current_priority = HITL_PRIORITY.get(decision.hitl_mode, 0)
           new_priority = HITL_PRIORITY.get(action.hitl_mode, 0)
           if new_priority > current_priority:
               decision.hitl_mode = action.hitl_mode
       
       # Restrictions: once set to True, can't be unset
       if action.local_only:
           decision.provider_constraints.local_only = True
       
       if not action.tools_allowed:
           decision.tools_allowed = False
       
       if action.approval_required:
           decision.approval_required = True
   ```

**✅ Strengths:**
- Constitutional rules ALWAYS have highest priority
- Lower tiers cannot weaken restrictions set by higher tiers
- Explicit priority boosting makes hierarchy clear

**⚠️ Weaknesses:**

1. **No Hard Validation:**
   - Nothing prevents adding a department rule with `priority = 20000`
   - No validation at rule creation time
   - Trust-based system, not enforced

2. **No "Immutable" Flag:**
   - No way to mark a rule as "cannot be overridden"
   - No explicit "final" modifier

3. **Department Rules CAN Add Restrictions:**
   - A department can add MORE restrictions (which is fine)
   - But there's no clarity on whether this is intended behavior

4. **File-Level Access:**
   - Anyone with file system access can edit `governance_policies.json`
   - No validation prevents malicious edits

**Recommendation:**
```python
# Add validation in PolicyRule model
class PolicyRule(BaseModel):
    # ... existing fields ...
    immutable: bool = Field(default=False, description="Cannot be overridden")
    final: bool = Field(default=False, description="No further rules can modify")
    
    @validator('priority')
    def validate_priority_by_tier(cls, v, values):
        # Prevent department rules from using constitutional priority
        tier = values.get('tier')
        if tier == 'department' and v > 5000:
            raise ValueError("Department rules cannot have priority > 5000")
        if tier == 'organization' and v > 10000:
            raise ValueError("Organization rules cannot have priority > 10000")
        return v
```

---

## C) Policy Versioning System

### ❌ Status: **NOT IMPLEMENTED**

**Current State:**

- No version tracking in `governance_policies.json`
- No `version` or `effective_date` field in `PolicySet`
- No policy version enforcement at runtime
- No history of policy changes
- File overwrites destroy previous versions

**What's Missing:**

1. **No Version Metadata:**
   ```json
   // Current format (no version)
   {
     "constitutional_rules": [...],
     "organization_rules": {...},
     "department_rules": {...}
   }
   
   // Needed format
   {
     "version": "2.1.0",
     "effective_date": "2026-01-28T00:00:00Z",
     "created_by": "admin@haais.io",
     "approved_by": "governance-board",
     "approval_date": "2026-01-27T15:30:00Z",
     "changelog": "Added PII protection rule const-004",
     "constitutional_rules": [...],
     ...
   }
   ```

2. **No Version History:**
   - No `data/governance_policies.v1.json`, `.v2.json`, etc.
   - Cannot rollback to previous policy version
   - No audit trail of what changed

3. **No Runtime Enforcement:**
   - No check that loaded policy meets minimum version
   - No validation that policy is still within effective date range
   - No warning if policy is outdated

4. **No Migration Path:**
   - No way to schedule policy changes for future date
   - No "pending" vs "active" policy states
   - Cannot test new policy version in staging

**Impact:**

- **Compliance Risk:** No proof of which policy was in effect at a given time
- **Audit Failure:** Cannot answer "what policy was enforced on date X?"
- **Rollback Issues:** Cannot undo bad policy changes
- **Change Control:** No formal change management process

**Recommendation:**

Implement a versioning system:

```python
class PolicyVersion(BaseModel):
    """Policy version metadata."""
    version: str = Field(..., description="Semantic version (e.g., 2.1.0)")
    effective_date: datetime = Field(..., description="When policy takes effect")
    expiry_date: datetime | None = Field(None, description="When policy expires")
    created_by: str = Field(..., description="User/service that created")
    approved_by: str | None = Field(None, description="Approver")
    approval_date: datetime | None = Field(None)
    changelog: str = Field(default="", description="What changed")
    min_runtime_version: str | None = Field(None, description="Min AIOS version")

class VersionedPolicySet(PolicySet):
    """Policy set with version tracking."""
    metadata: PolicyVersion
    
    def is_active(self) -> bool:
        """Check if policy is within effective date range."""
        now = datetime.now(timezone.utc)
        if now < self.metadata.effective_date:
            return False
        if self.metadata.expiry_date and now > self.metadata.expiry_date:
            return False
        return True

# Storage structure
data/governance_policies/
├── current.json              # Symlink to active version
├── v1.0.0.json              # Historical versions
├── v1.1.0.json
├── v2.0.0.json
└── pending/                  # Approved but not yet effective
    └── v2.1.0.json
```

---

## D) Approval Workflow for Global Rules

### ❌ Status: **NOT IMPLEMENTED**

**Current State:**

Changes to governance policies have **NO approval workflow**:

1. **Manual File Edit:**
   ```bash
   vim data/governance_policies.json  # Direct edit, no checks
   ```

2. **API Call:**
   ```bash
   # Add rule via API - NO approval required
   curl -X POST http://localhost:8000/governance/rules \
     -H "Content-Type: application/json" \
     -d '{"id": "new-rule", "name": "New Rule", ...}'
   ```

3. **Immediate Effect:**
   - Changes via API are saved immediately
   - File changes take effect on next reload
   - No review, no approval, no audit

**What's Missing:**

1. **No Authentication/Authorization:**
   - API has no auth checks
   - Anyone can POST to `/governance/rules`
   - No role-based access control (RBAC)

2. **No Approval Queue:**
   - No "pending approval" state
   - No governance board workflow
   - No multi-signature requirement

3. **No Change Request System:**
   - No formal RFC (Request for Change) process
   - No justification required
   - No impact assessment

4. **No Audit Trail:**
   - No record of who made changes
   - No timestamp of changes
   - No reason for change documented

5. **No Review Process:**
   - No peer review requirement
   - No testing in staging environment
   - No rollback plan required

**Impact:**

- **Security Risk:** Unauthorized policy changes
- **Compliance Risk:** No audit trail for regulators
- **Operational Risk:** No validation before deployment
- **Governance Risk:** Defeats purpose of "immutable rules"

**Recommendation:**

Implement a formal approval workflow:

```python
class PolicyChangeRequest(BaseModel):
    """Request to change a governance policy."""
    id: str = Field(default_factory=lambda: f"pcr-{uuid4()}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(..., description="User requesting change")
    change_type: str = Field(..., description="add_rule|remove_rule|modify_rule")
    rule_data: dict = Field(..., description="Rule to add/modify")
    justification: str = Field(..., min_length=50, description="Why this change?")
    impact_assessment: str = Field(..., description="What agents/domains affected?")
    
    status: str = Field(default="pending", description="pending|approved|rejected")
    reviewed_by: list[str] = Field(default_factory=list)
    approved_by: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    
    # Approval requirements
    requires_approvals: int = Field(default=2, description="Min approvals needed")
    requires_roles: list[str] = Field(default_factory=lambda: ["governance-admin"])

# Workflow
"""
1. User submits PolicyChangeRequest via API
2. Request goes to approval queue
3. Governance board reviews (min 2 approvals)
4. If approved, change applied to next policy version
5. Policy version deployed on effective_date
6. All changes logged in audit table
"""

# API endpoints
@router.post("/governance/change-requests")
async def create_change_request(request: PolicyChangeRequest):
    """Submit a policy change for approval."""
    pass

@router.post("/governance/change-requests/{id}/approve")
async def approve_change(id: str, current_user: User):
    """Approve a policy change (requires governance-admin role)."""
    pass

@router.post("/governance/change-requests/{id}/reject")
async def reject_change(id: str, reason: str, current_user: User):
    """Reject a policy change."""
    pass
```

**Interim Solution (Without Full Workflow):**

1. **Git-Based Workflow:**
   ```bash
   # Treat governance_policies.json as code
   # Require PR review before merge
   # Use branch protection rules
   # Require 2+ approvals for constitutional rules
   ```

2. **Add Audit Logging:**
   ```python
   # Log every governance change
   def _save_policies(self):
       # ... save file ...
       
       # Log change
       audit_log.info({
           "action": "governance_policy_updated",
           "timestamp": datetime.now(timezone.utc).isoformat(),
           "changed_by": get_current_user(),
           "file": str(self._policy_path),
           "rules_count": {
               "constitutional": len(self._policy_set.constitutional_rules),
               "organization": len(self._policy_set.organization_rules.default),
               "department": sum(len(d.defaults) for d in self._policy_set.department_rules.values()),
           }
       })
   ```

---

## E) Policy Drift Detection

### ❌ Status: **NOT IMPLEMENTED**

**Current State:**

- No monitoring for policy differences
- No alerts if configs differ
- No comparison tools
- Single file assumed to be source of truth

**What's Missing:**

1. **No Multi-Instance Detection:**
   - If AIOS runs on multiple servers, no check that they have same policies
   - No health check that compares policy versions across instances

2. **No Department Drift Detection:**
   - Cannot detect if department rules violate org standards
   - No report showing which departments have custom rules
   - No alert if department rule seems to contradict constitutional rule

3. **No Anomaly Detection:**
   - No baseline for "normal" policy configuration
   - No alert if policy file is modified outside API
   - No checksum validation

4. **No Synchronization:**
   - No mechanism to propagate policy changes to multiple instances
   - No central policy server
   - No pub/sub for policy updates

**Impact:**

- **Configuration Drift:** Different servers enforcing different policies
- **Compliance Risk:** Some agents operating under old policies
- **Debugging Nightmare:** Cannot explain why Agent A behaves differently than Agent B
- **Security Risk:** Policy file tampering goes undetected

**Recommendation:**

Implement drift detection:

```python
class PolicyDriftDetector:
    """Detect and alert on policy configuration drift."""
    
    def __init__(self):
        self._baseline_checksum: str | None = None
        self._last_check: datetime | None = None
        self._check_interval = timedelta(minutes=5)
    
    def compute_checksum(self, policy_set: PolicySet) -> str:
        """Compute SHA-256 checksum of policy set."""
        serialized = json.dumps(self._serialize(policy_set), sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def check_drift(self) -> DriftReport:
        """Check if policy has drifted from baseline."""
        current = get_governance_manager().get_policy_set()
        current_checksum = self.compute_checksum(current)
        
        if self._baseline_checksum is None:
            # First check - establish baseline
            self._baseline_checksum = current_checksum
            return DriftReport(has_drift=False, message="Baseline established")
        
        if current_checksum != self._baseline_checksum:
            # DRIFT DETECTED
            logger.warning(f"Policy drift detected! Checksum changed from {self._baseline_checksum} to {current_checksum}")
            alert_governance_board("Policy file modified outside expected workflow")
            
            return DriftReport(
                has_drift=True,
                message="Policy file modified unexpectedly",
                baseline_checksum=self._baseline_checksum,
                current_checksum=current_checksum,
                detected_at=datetime.now(timezone.utc),
            )
        
        return DriftReport(has_drift=False, message="No drift")
    
    def compare_department_rules(self) -> list[DriftAlert]:
        """Check if any department rules contradict constitutional rules."""
        alerts = []
        policy_set = get_governance_manager().get_policy_set()
        
        # Check each department
        for dept, dept_rules in policy_set.department_rules.items():
            for dept_rule in dept_rules.defaults:
                # Check if department rule tries to weaken restrictions
                for const_rule in policy_set.constitutional_rules:
                    if self._rules_conflict(const_rule, dept_rule):
                        alerts.append(DriftAlert(
                            severity="high",
                            department=dept,
                            message=f"Department rule {dept_rule.id} may conflict with constitutional rule {const_rule.id}",
                            recommendation="Review and align with constitutional policy",
                        ))
        
        return alerts

# Add health check endpoint
@router.get("/governance/drift-check")
async def check_policy_drift():
    """Check for policy drift and return report."""
    detector = PolicyDriftDetector()
    report = detector.check_drift()
    alerts = detector.compare_department_rules()
    
    return {
        "drift_report": report,
        "department_alerts": alerts,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
```

**Interim Solution:**

1. **File Integrity Monitoring:**
   ```bash
   # Use inotify or similar to watch governance_policies.json
   # Alert on any modification not via API
   ```

2. **Regular Audits:**
   ```python
   # Scheduled job to validate policy consistency
   @scheduler.scheduled_job('interval', minutes=10)
   def audit_governance_policies():
       manager = get_governance_manager()
       policy_set = manager.get_policy_set()
       
       # Validate structure
       assert len(policy_set.constitutional_rules) >= 3, "Missing constitutional rules!"
       
       # Check priorities
       for rule in policy_set.constitutional_rules:
           assert rule.priority >= 80, f"Constitutional rule {rule.id} has too low priority"
       
       # Log status
       logger.info(f"Governance audit passed: {len(policy_set.constitutional_rules)} constitutional rules active")
   ```

---

## Summary Matrix

| Requirement | Status | Location | Gaps | Priority |
|-------------|--------|----------|------|----------|
| **Single Source of Truth** | ✅ Implemented | `data/governance_policies.json` + `GovernanceManager` singleton | No database option, no backup | Medium |
| **Override Prevention** | ⚠️ Partial | Priority system in `evaluate_governance()` | No hard validation, trust-based | **HIGH** |
| **Policy Versioning** | ❌ Missing | N/A | No version, history, or effective dates | **CRITICAL** |
| **Approval Workflow** | ❌ Missing | N/A | No auth, no approval queue, no audit trail | **CRITICAL** |
| **Drift Detection** | ❌ Missing | N/A | No monitoring, alerts, or sync | **HIGH** |

---

## Recommendations (Priority Order)

### 1. **CRITICAL: Add Policy Versioning** 
**Timeline:** Immediate (Week 1)

- Add `version`, `effective_date`, `approved_by` to policy file
- Implement version history storage
- Add runtime version validation
- Create migration path for existing policies

### 2. **CRITICAL: Implement Approval Workflow**
**Timeline:** Week 2-3

- Add authentication/authorization to governance API
- Create `PolicyChangeRequest` model and approval queue
- Require min 2 approvals for constitutional rule changes
- Log all changes with user, timestamp, reason

### 3. **HIGH: Harden Override Prevention**
**Timeline:** Week 3-4

- Add `immutable` and `final` flags to rules
- Implement validation that prevents department rules from having priority > 5000
- Add explicit checks that department rules can only add restrictions, not remove them
- Create admin dashboard showing rule hierarchy

### 4. **HIGH: Implement Drift Detection**
**Timeline:** Week 4-5

- Add policy checksum computation
- Implement periodic drift checks
- Add `/governance/drift-check` health endpoint
- Alert on unexpected policy file modifications
- Add department rule conflict detection

### 5. **MEDIUM: Database Backend Option**
**Timeline:** Week 6-8

- Add PostgreSQL/SQLite backend for policies (in addition to file)
- Implement transactional policy updates
- Add automatic backups
- Support multi-instance synchronization

---

## Code Changes Needed

### File: `packages/core/governance/__init__.py`

```python
# Add validation to prevent priority abuse
class PolicyRule(BaseModel):
    # ... existing fields ...
    immutable: bool = Field(default=False)
    final: bool = Field(default=False)
    tier: str = Field(default="organization")  # Track tier explicitly
    
    @validator('priority')
    def validate_priority_by_tier(cls, v, values):
        tier = values.get('tier', 'organization')
        if tier == 'department' and v > 5000:
            raise ValueError("Department rules cannot have priority > 5000")
        if tier == 'organization' and v > 10000:
            raise ValueError("Organization rules cannot have priority > 10000")
        return v
```

### File: `packages/core/governance/manager.py`

```python
class PolicyVersion(BaseModel):
    """Track policy version and approval."""
    version: str
    effective_date: datetime
    created_by: str
    approved_by: list[str] = Field(default_factory=list)
    approval_date: datetime | None = None
    changelog: str = ""

class GovernanceManager:
    def __init__(self, policy_path: Path | None = None):
        # ... existing code ...
        self._policy_version: PolicyVersion | None = None
        self._baseline_checksum: str | None = None
    
    def _save_policies(self) -> None:
        """Save with version tracking and audit."""
        # Require version info for saves
        if self._policy_version is None:
            raise ValueError("Cannot save policies without version metadata")
        
        # Compute checksum
        data = self._serialize_policy_set()
        data["version"] = self._policy_version.dict()
        
        # Save with version in filename
        version_file = self._policy_path.parent / f"governance_policies.v{self._policy_version.version}.json"
        version_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
        # Update symlink to current
        self._policy_path.unlink(missing_ok=True)
        self._policy_path.symlink_to(version_file)
        
        # Audit log
        logger.info(f"Governance policies saved: version {self._policy_version.version}, approved by {self._policy_version.approved_by}")
    
    def check_drift(self) -> dict:
        """Detect policy drift."""
        current_checksum = self._compute_checksum()
        has_drift = self._baseline_checksum and current_checksum != self._baseline_checksum
        
        return {
            "has_drift": has_drift,
            "baseline": self._baseline_checksum,
            "current": current_checksum,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
```

### File: `packages/api/governance.py`

```python
@router.post("/rules")
async def add_policy_rule(request: PolicyRuleRequest, current_user: User = Depends(get_current_user)):
    """Add rule - requires authentication and approval for constitutional rules."""
    
    # Check authorization
    if request.tier == "constitutional" and "governance-admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Only governance-admin can add constitutional rules")
    
    # Create change request instead of immediate application
    change_request = PolicyChangeRequest(
        created_by=current_user.email,
        change_type="add_rule",
        rule_data=request.dict(),
        justification=request.get("justification", ""),
    )
    
    # If constitutional, require approval
    if request.tier == "constitutional":
        # Save to approval queue
        await save_change_request(change_request)
        return {"status": "pending_approval", "request_id": change_request.id}
    
    # Otherwise, apply immediately (but still log)
    governance = get_governance_manager()
    # ... existing logic ...
    
    audit_log.info(f"Policy rule added by {current_user.email}: {request.id}")
```

---

## Conclusion

The AIOS governance system has a **solid foundation** with a clear single source of truth and priority-based hierarchy. However, it is **NOT production-ready** for enterprise use due to:

1. **No policy versioning** - Cannot prove compliance or rollback
2. **No approval workflow** - Anyone can change critical rules
3. **No drift detection** - Silent configuration drift across environments
4. **Weak override prevention** - Trust-based, not enforced

**Bottom Line:** Implement the recommendations above before deploying to production, especially for sensitive environments like government deployments where audit trails and change control are mandatory.

---

**Document Version:** 1.0  
**Author:** Code Review Analysis  
**Next Review:** After implementing recommendations
